#-------------------------------------------------------------------------------
# elftools: dwarf/dwarfinfo.py
#
# DWARFInfo - Main class for accessing DWARF debug information
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple
from bisect import bisect_right

from ..common.exceptions import DWARFError
from ..common.utils import (struct_parse, dwarf_assert,
                            parse_cstring_from_stream)
from .structs import DWARFStructs
from .compileunit import CompileUnit
from .abbrevtable import AbbrevTable
from .lineprogram import LineProgram
from .callframe import CallFrameInfo
from .locationlists import LocationLists
from .ranges import RangeLists
from .aranges import ARanges
from .namelut import NameLUT


# Describes a debug section
#
# stream: a stream object containing the data of this section
# name: section name in the container file
# global_offset: the global offset of the section in its container file
# size: the size of the section's data, in bytes
# address: the virtual address for the section's data
#
# 'name' and 'global_offset' are for descriptional purposes only and
# aren't strictly required for the DWARF parsing to work. 'address' is required
# to properly decode the special '.eh_frame' format.
#
DebugSectionDescriptor = namedtuple('DebugSectionDescriptor',
    'stream name global_offset size address')


# Some configuration parameters for the DWARF reader. This exists to allow
# DWARFInfo to be independent from any specific file format/container.
#
# little_endian:
#   boolean flag specifying whether the data in the file is little endian
#
# machine_arch:
#   Machine architecture as a string. For example 'x86' or 'x64'
#
# default_address_size:
#   The default address size for the container file (sizeof pointer, in bytes)
#
DwarfConfig = namedtuple('DwarfConfig',
    'little_endian machine_arch default_address_size')


class DWARFInfo(object):
    """ Acts also as a "context" to other major objects, bridging between
        various parts of the debug infromation.
    """
    def __init__(self,
            config,
            debug_info_sec,
            debug_aranges_sec,
            debug_abbrev_sec,
            debug_frame_sec,
            eh_frame_sec,
            debug_str_sec,
            debug_loc_sec,
            debug_ranges_sec,
            debug_line_sec,
            debug_pubtypes_sec,
            debug_pubnames_sec,
            debug_addr_sec,
            debug_str_offsets_sec):
        """ config:
                A DwarfConfig object

            debug_*_sec:
                DebugSectionDescriptor for a section. Pass None for sections
                that don't exist. These arguments are best given with
                keyword syntax.
        """
        self.config = config
        self.debug_info_sec = debug_info_sec
        self.debug_aranges_sec = debug_aranges_sec
        self.debug_abbrev_sec = debug_abbrev_sec
        self.debug_frame_sec = debug_frame_sec
        self.eh_frame_sec = eh_frame_sec
        self.debug_str_sec = debug_str_sec
        self.debug_loc_sec = debug_loc_sec
        self.debug_ranges_sec = debug_ranges_sec
        self.debug_line_sec = debug_line_sec
        self.debug_pubtypes_sec = debug_pubtypes_sec
        self.debug_pubnames_sec = debug_pubnames_sec

        # This is the DWARFStructs the context uses, so it doesn't depend on
        # DWARF format and address_size (these are determined per CU) - set them
        # to default values.
        self.structs = DWARFStructs(
            little_endian=self.config.little_endian,
            dwarf_format=32,
            address_size=self.config.default_address_size)

        # Cache for abbrev tables: a dict keyed by offset
        self._abbrevtable_cache = {}

        # Cache of compile units and map of their offsets for bisect lookup.
        # Access with .iter_CUs(), .get_CU_containing(), and/or .get_CU_at().
        self._cu_cache = []
        self._cu_offsets_map = []

    @property
    def has_debug_info(self):
        """ Return whether this contains debug information.

        It can be not the case when the ELF only contains .eh_frame, which is
        encoded DWARF but not actually for debugging.
        """
        return bool(self.debug_info_sec)

    def get_DIE_from_lut_entry(self, lut_entry):
        """ Get the DIE from the pubnames or putbtypes lookup table entry.

            lut_entry:
                A NameLUTEntry object from a NameLUT instance (see
                .get_pubmames and .get_pubtypes methods).
        """
        cu = self.get_CU_at(lut_entry.cu_ofs)
        return self.get_DIE_from_refaddr(lut_entry.die_ofs, cu)

    def get_DIE_from_refaddr(self, refaddr, cu=None):
        """ Given a .debug_info section offset of a DIE, return the DIE.

            refaddr:
                The refaddr may come from a DW_FORM_ref_addr attribute.

            cu:
                The compile unit object, if known.  If None a search
                from the closest offset less than refaddr will be performed.
        """
        if cu is None:
            cu = self.get_CU_containing(refaddr)
        return cu.get_DIE_from_refaddr(refaddr)

    def get_CU_containing(self, refaddr):
        """ Find the CU that includes the given reference address in the
            .debug_info section.

            refaddr:
                Either a refaddr of a DIE (possibly from a DW_FORM_ref_addr
                attribute) or the section offset of a CU (possibly from an
                aranges table).

           This function will parse and cache CUs until the search criteria
           is met, starting from the closest known offset lessthan or equal
           to the given address.
        """
        dwarf_assert(
            self.has_debug_info,
            'CU lookup but no debug info section')
        dwarf_assert(
            0 <= refaddr < self.debug_info_sec.size,
            "refaddr %s beyond .debug_info size" % refaddr)

        # The CU containing the DIE we desire will be to the right of the
        # DIE insert point.  If we have a CU address, then it will be a
        # match but the right insert minus one will still be the item.
        # The first CU starts at offset 0, so start there if cache is empty.
        i = bisect_right(self._cu_offsets_map, refaddr)
        start = self._cu_offsets_map[i - 1] if i > 0 else 0

        # parse CUs until we find one containing the desired address
        for cu in self._parse_CUs_iter(start):
            if cu.cu_offset <= refaddr < cu.cu_offset + cu.size:
                return cu

        raise ValueError("CU for reference address %s not found" % refaddr)

    def get_CU_at(self, offset):
        """ Given a CU header offset, return the parsed CU.

            offset:
                The offset may be from an accelerated access table such as
                the public names, public types, address range table, or
                prior use.

            This function will directly parse the CU doing no validation of
            the offset beyond checking the size of the .debug_info section.
        """
        dwarf_assert(
            self.has_debug_info,
            'CU lookup but no debug info section')
        dwarf_assert(
            0 <= offset < self.debug_info_sec.size,
            "offset %s beyond .debug_info size" % offset)

        return self._cached_CU_at_offset(offset)

    def iter_CUs(self):
        """ Yield all the compile units (CompileUnit objects) in the debug info
        """
        return self._parse_CUs_iter()

    def get_abbrev_table(self, offset):
        """ Get an AbbrevTable from the given offset in the debug_abbrev
            section.

            The only verification done on the offset is that it's within the
            bounds of the section (if not, an exception is raised).
            It is the caller's responsibility to make sure the offset actually
            points to a valid abbreviation table.

            AbbrevTable objects are cached internally (two calls for the same
            offset will return the same object).
        """
        dwarf_assert(
            offset < self.debug_abbrev_sec.size,
            "Offset '0x%x' to abbrev table out of section bounds" % offset)
        if offset not in self._abbrevtable_cache:
            self._abbrevtable_cache[offset] = AbbrevTable(
                structs=self.structs,
                stream=self.debug_abbrev_sec.stream,
                offset=offset)
        return self._abbrevtable_cache[offset]

    def get_string_from_table(self, offset):
        """ Obtain a string from the string table section, given an offset
            relative to the section.
        """
        return parse_cstring_from_stream(self.debug_str_sec.stream, offset)

    def line_program_for_CU(self, CU):
        """ Given a CU object, fetch the line program it points to from the
            .debug_line section.
            If the CU doesn't point to a line program, return None.
        """
        # The line program is pointed to by the DW_AT_stmt_list attribute of
        # the top DIE of a CU.
        top_DIE = CU.get_top_DIE()
        if 'DW_AT_stmt_list' in top_DIE.attributes:
            return self._parse_line_program_at_offset(
                    top_DIE.attributes['DW_AT_stmt_list'].value, CU.structs)
        else:
            return None

    def has_CFI(self):
        """ Does this dwarf info have a dwarf_frame CFI section?
        """
        return self.debug_frame_sec is not None

    def CFI_entries(self):
        """ Get a list of dwarf_frame CFI entries from the .debug_frame section.
        """
        cfi = CallFrameInfo(
            stream=self.debug_frame_sec.stream,
            size=self.debug_frame_sec.size,
            address=self.debug_frame_sec.address,
            base_structs=self.structs)
        return cfi.get_entries()

    def has_EH_CFI(self):
        """ Does this dwarf info have a eh_frame CFI section?
        """
        return self.eh_frame_sec is not None

    def EH_CFI_entries(self):
        """ Get a list of eh_frame CFI entries from the .eh_frame section.
        """
        cfi = CallFrameInfo(
            stream=self.eh_frame_sec.stream,
            size=self.eh_frame_sec.size,
            address=self.eh_frame_sec.address,
            base_structs=self.structs,
            for_eh_frame=True)
        return cfi.get_entries()

    def get_pubtypes(self):
        """
        Returns a NameLUT object that contains information read from the
        .debug_pubtypes section in the ELF file.

        NameLUT is essentially a dictionary containing the CU/DIE offsets of
        each symbol. See the NameLUT doc string for more details.
        """

        if self.debug_pubtypes_sec:
            return NameLUT(self.debug_pubtypes_sec.stream,
                    self.debug_pubtypes_sec.size,
                    self.structs)
        else:
            return None

    def get_pubnames(self):
        """
        Returns a NameLUT object that contains information read from the
        .debug_pubnames section in the ELF file.

        NameLUT is essentially a dictionary containing the CU/DIE offsets of
        each symbol. See the NameLUT doc string for more details.
        """

        if self.debug_pubnames_sec:
            return NameLUT(self.debug_pubnames_sec.stream,
                    self.debug_pubnames_sec.size,
                    self.structs)
        else:
            return None

    def get_aranges(self):
        """ Get an ARanges object representing the .debug_aranges section of
            the DWARF data, or None if the section doesn't exist
        """
        if self.debug_aranges_sec:
            return ARanges(self.debug_aranges_sec.stream,
                self.debug_aranges_sec.size,
                self.structs)
        else:
            return None

    def location_lists(self):
        """ Get a LocationLists object representing the .debug_loc section of
            the DWARF data, or None if this section doesn't exist.
        """
        if self.debug_loc_sec:
            return LocationLists(self.debug_loc_sec.stream, self.structs)
        else:
            return None

    def range_lists(self):
        """ Get a RangeLists object representing the .debug_ranges section of
            the DWARF data, or None if this section doesn't exist.
        """
        if self.debug_ranges_sec:
            return RangeLists(self.debug_ranges_sec.stream, self.structs)
        else:
            return None

    #------ PRIVATE ------#

    def _parse_CUs_iter(self, offset=0):
        """ Iterate CU objects in order of appearance in the debug_info section.

            offset:
                The offset of the first CU to yield.  Additional iterations
                will return the sequential unit objects.

            See .iter_CUs(), .get_CU_containing(), and .get_CU_at().
        """
        if self.debug_info_sec is None:
            return

        while offset < self.debug_info_sec.size:
            cu = self._cached_CU_at_offset(offset)
            # Compute the offset of the next CU in the section. The unit_length
            # field of the CU header contains its size not including the length
            # field itself.
            offset = (  offset +
                        cu['unit_length'] +
                        cu.structs.initial_length_field_size())
            yield cu

    def _cached_CU_at_offset(self, offset):
        """ Return the CU with unit header at the given offset into the
            debug_info section from the cache.  If not present, the unit is
            header is parsed and the object is installed in the cache.

            offset:
                The offset of the unit header in the .debug_info section
                to of the unit to fetch from the cache.

            See get_CU_at().
        """
        # Find the insert point for the requested offset.  With bisect_right,
        # if this entry is present in the cache it will be the prior entry.
        i = bisect_right(self._cu_offsets_map, offset)
        if i >= 1 and offset == self._cu_offsets_map[i - 1]:
            return self._cu_cache[i - 1]

        # Parse the CU and insert the offset and object into the cache.
        # The ._cu_offsets_map[] contains just the numeric offsets for the
        # bisect_right search while the parallel indexed ._cu_cache[] holds
        # the object references.
        cu = self._parse_CU_at_offset(offset)
        self._cu_offsets_map.insert(i, offset)
        self._cu_cache.insert(i, cu)
        return cu

    def _parse_CU_at_offset(self, offset):
        """ Parse and return a CU at the given offset in the debug_info stream.
        """
        # Section 7.4 (32-bit and 64-bit DWARF Formats) of the DWARF spec v3
        # states that the first 32-bit word of the CU header determines
        # whether the CU is represented with 32-bit or 64-bit DWARF format.
        #
        # So we peek at the first word in the CU header to determine its
        # dwarf format. Based on it, we then create a new DWARFStructs
        # instance suitable for this CU and use it to parse the rest.
        #
        initial_length = struct_parse(
            self.structs.Dwarf_uint32(''), self.debug_info_sec.stream, offset)
        dwarf_format = 64 if initial_length == 0xFFFFFFFF else 32


        # Temporary structs for parsing the header
        # The structs for the rest of the CU depend on the header data.
        #
        cu_structs = DWARFStructs(
            little_endian=self.config.little_endian,
            dwarf_format=dwarf_format,
            address_size=4,
            dwarf_version=2)

        cu_header = struct_parse(
            cu_structs.Dwarf_CU_header, self.debug_info_sec.stream, offset)

        # structs for the rest of the CU, taking into account bitness and DWARF version
        cu_structs = DWARFStructs(
            little_endian=self.config.little_endian,
            dwarf_format=dwarf_format,
            address_size=cu_header['address_size'],
            dwarf_version=cu_header['version'])

        cu_die_offset = self.debug_info_sec.stream.tell()
        dwarf_assert(
            self._is_supported_version(cu_header['version']),
            "Expected supported DWARF version. Got '%s'" % cu_header['version'])
        return CompileUnit(
                header=cu_header,
                dwarfinfo=self,
                structs=cu_structs,
                cu_offset=offset,
                cu_die_offset=cu_die_offset)

    def _is_supported_version(self, version):
        """ DWARF version supported by this parser
        """
        return 2 <= version <= 5

    def _parse_line_program_at_offset(self, debug_line_offset, structs):
        """ Given an offset to the .debug_line section, parse the line program
            starting at this offset in the section and return it.
            structs is the DWARFStructs object used to do this parsing.
        """
        lineprog_header = struct_parse(
            structs.Dwarf_lineprog_header,
            self.debug_line_sec.stream,
            debug_line_offset)

        # Calculate the offset to the next line program (see DWARF 6.2.4)
        end_offset = (  debug_line_offset + lineprog_header['unit_length'] +
                        structs.initial_length_field_size())

        return LineProgram(
            header=lineprog_header,
            stream=self.debug_line_sec.stream,
            structs=structs,
            program_start_offset=self.debug_line_sec.stream.tell(),
            program_end_offset=end_offset)
