#-------------------------------------------------------------------------------
# elftools: elf/elffile.py
#
# ELFFile - main class for accessing ELF files
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import io
import struct
import zlib

try:
    import resource
    PAGESIZE = resource.getpagesize()
except ImportError:
    # Windows system
    import mmap
    PAGESIZE = mmap.PAGESIZE

from ..common.py3compat import BytesIO
from ..common.exceptions import ELFError
from ..common.utils import struct_parse, elf_assert
from .structs import ELFStructs
from .sections import (
        Section, StringTableSection, SymbolTableSection,
        SUNWSyminfoTableSection, NullSection, NoteSection,
        StabSection, ARMAttributesSection)
from .dynamic import DynamicSection, DynamicSegment
from .relocation import RelocationSection, RelocationHandler
from .gnuversions import (
        GNUVerNeedSection, GNUVerDefSection,
        GNUVerSymSection)
from .segments import Segment, InterpSegment, NoteSegment
from ..dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig


class ELFFile(object):
    """ Creation: the constructor accepts a stream (file-like object) with the
        contents of an ELF file.

        Accessible attributes:

            stream:
                The stream holding the data of the file - must be a binary
                stream (bytes, not string).

            elfclass:
                32 or 64 - specifies the word size of the target machine

            little_endian:
                boolean - specifies the target machine's endianness

            elftype:
                string or int, either known value of E_TYPE enum defining ELF
                type (e.g. executable, dynamic library or core dump) or integral
                unparsed value

            header:
                the complete ELF file header

            e_ident_raw:
                the raw e_ident field of the header
    """
    def __init__(self, stream):
        self.stream = stream
        self._identify_file()
        self.structs = ELFStructs(
            little_endian=self.little_endian,
            elfclass=self.elfclass)

        self.structs.create_basic_structs()
        self.header = self._parse_elf_header()
        self.structs.create_advanced_structs(
                self['e_type'],
                self['e_machine'],
                self['e_ident']['EI_OSABI'])
        self.stream.seek(0)
        self.e_ident_raw = self.stream.read(16)

        self._file_stringtable_section = self._get_file_stringtable()
        self._section_name_map = None

    def num_sections(self):
        """ Number of sections in the file
        """
        return self['e_shnum']

    def get_section(self, n):
        """ Get the section at index #n from the file (Section object or a
            subclass)
        """
        section_header = self._get_section_header(n)
        return self._make_section(section_header)

    def get_section_by_name(self, name):
        """ Get a section from the file, by name. Return None if no such
            section exists.
        """
        # The first time this method is called, construct a name to number
        # mapping
        #
        if self._section_name_map is None:
            self._section_name_map = {}
            for i, sec in enumerate(self.iter_sections()):
                self._section_name_map[sec.name] = i
        secnum = self._section_name_map.get(name, None)
        return None if secnum is None else self.get_section(secnum)

    def iter_sections(self):
        """ Yield all the sections in the file
        """
        for i in range(self.num_sections()):
            yield self.get_section(i)

    def num_segments(self):
        """ Number of segments in the file
        """
        return self['e_phnum']

    def get_segment(self, n):
        """ Get the segment at index #n from the file (Segment object)
        """
        segment_header = self._get_segment_header(n)
        return self._make_segment(segment_header)

    def iter_segments(self):
        """ Yield all the segments in the file
        """
        for i in range(self.num_segments()):
            yield self.get_segment(i)

    def address_offsets(self, start, size=1):
        """ Yield a file offset for each ELF segment containing a memory region.

            A memory region is defined by the range [start...start+size). The
            offset of the region is yielded.
        """
        end = start + size
        for seg in self.iter_segments():
            # consider LOAD only to prevent same address being yielded twice
            if seg['p_type'] != 'PT_LOAD':
                continue
            if (start >= seg['p_vaddr'] and
                end <= seg['p_vaddr'] + seg['p_filesz']):
                yield start - seg['p_vaddr'] + seg['p_offset']

    def has_dwarf_info(self):
        """ Check whether this file appears to have debugging information.
            We assume that if it has the .debug_info or .zdebug_info section, it
            has all the other required sections as well.
        """
        return (self.get_section_by_name('.debug_info') or
            self.get_section_by_name('.zdebug_info') or
            self.get_section_by_name('.eh_frame'))

    def get_dwarf_info(self, relocate_dwarf_sections=True):
        """ Return a DWARFInfo object representing the debugging information in
            this file.

            If relocate_dwarf_sections is True, relocations for DWARF sections
            are looked up and applied.
        """
        # Expect that has_dwarf_info was called, so at least .debug_info is
        # present.
        # Sections that aren't found will be passed as None to DWARFInfo.

        section_names = ('.debug_info', '.debug_aranges', '.debug_abbrev',
                         '.debug_str', '.debug_line', '.debug_frame',
                         '.debug_loc', '.debug_ranges')

        compressed = bool(self.get_section_by_name('.zdebug_info'))
        if compressed:
            section_names = tuple(map(lambda x: '.z' + x[1:], section_names))

        # As it is loaded in the process image, .eh_frame cannot be compressed
        section_names += ('.eh_frame', )

        (debug_info_sec_name, debug_aranges_sec_name, debug_abbrev_sec_name,
         debug_str_sec_name, debug_line_sec_name, debug_frame_sec_name,
         debug_loc_sec_name, debug_ranges_sec_name,
         eh_frame_sec_name) = section_names

        debug_sections = {}
        for secname in section_names:
            section = self.get_section_by_name(secname)
            if section is None:
                debug_sections[secname] = None
            else:
                dwarf_section = self._read_dwarf_section(
                    section,
                    relocate_dwarf_sections)
                if compressed and secname.startswith('.z'):
                    dwarf_section = self._decompress_dwarf_section(dwarf_section)
                debug_sections[secname] = dwarf_section

        return DWARFInfo(
                config=DwarfConfig(
                    little_endian=self.little_endian,
                    default_address_size=self.elfclass // 8,
                    machine_arch=self.get_machine_arch()),
                debug_info_sec=debug_sections[debug_info_sec_name],
                debug_aranges_sec=debug_sections[debug_aranges_sec_name],
                debug_abbrev_sec=debug_sections[debug_abbrev_sec_name],
                debug_frame_sec=debug_sections[debug_frame_sec_name],
                eh_frame_sec=debug_sections[eh_frame_sec_name],
                debug_str_sec=debug_sections[debug_str_sec_name],
                debug_loc_sec=debug_sections[debug_loc_sec_name],
                debug_ranges_sec=debug_sections[debug_ranges_sec_name],
                debug_line_sec=debug_sections[debug_line_sec_name])

    def get_machine_arch(self):
        """ Return the machine architecture, as detected from the ELF header.
            Not all architectures are supported at the moment.
        """
        if self['e_machine'] == 'EM_X86_64':
            return 'x64'
        elif self['e_machine'] in ('EM_386', 'EM_486'):
            return 'x86'
        elif self['e_machine'] == 'EM_ARM':
            return 'ARM'
        elif self['e_machine'] == 'EM_AARCH64':
            return 'AArch64'
        elif self['e_machine'] == 'EM_MIPS':
            return 'MIPS'
        else:
            return '<unknown>'

    #-------------------------------- PRIVATE --------------------------------#

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _identify_file(self):
        """ Verify the ELF file and identify its class and endianness.
        """
        # Note: this code reads the stream directly, without using ELFStructs,
        # since we don't yet know its exact format. ELF was designed to be
        # read like this - its e_ident field is word-size and endian agnostic.
        self.stream.seek(0)
        magic = self.stream.read(4)
        elf_assert(magic == b'\x7fELF', 'Magic number does not match')

        ei_class = self.stream.read(1)
        if ei_class == b'\x01':
            self.elfclass = 32
        elif ei_class == b'\x02':
            self.elfclass = 64
        else:
            raise ELFError('Invalid EI_CLASS %s' % repr(ei_class))

        ei_data = self.stream.read(1)
        if ei_data == b'\x01':
            self.little_endian = True
        elif ei_data == b'\x02':
            self.little_endian = False
        else:
            raise ELFError('Invalid EI_DATA %s' % repr(ei_data))

    def _section_offset(self, n):
        """ Compute the offset of section #n in the file
        """
        return self['e_shoff'] + n * self['e_shentsize']

    def _segment_offset(self, n):
        """ Compute the offset of segment #n in the file
        """
        return self['e_phoff'] + n * self['e_phentsize']

    def _make_segment(self, segment_header):
        """ Create a Segment object of the appropriate type
        """
        segtype = segment_header['p_type']
        if segtype == 'PT_INTERP':
            return InterpSegment(segment_header, self.stream)
        elif segtype == 'PT_DYNAMIC':
            return DynamicSegment(segment_header, self.stream, self)
        elif segtype == 'PT_NOTE':
            return NoteSegment(segment_header, self.stream, self)
        else:
            return Segment(segment_header, self.stream)

    def _get_section_header(self, n):
        """ Find the header of section #n, parse it and return the struct
        """
        return struct_parse(
            self.structs.Elf_Shdr,
            self.stream,
            stream_pos=self._section_offset(n))

    def _get_section_name(self, section_header):
        """ Given a section header, find this section's name in the file's
            string table
        """
        name_offset = section_header['sh_name']
        return self._file_stringtable_section.get_string(name_offset)

    def _make_section(self, section_header):
        """ Create a section object of the appropriate type
        """
        name = self._get_section_name(section_header)
        sectype = section_header['sh_type']

        if sectype == 'SHT_STRTAB':
            return StringTableSection(section_header, name, self)
        elif sectype == 'SHT_NULL':
            return NullSection(section_header, name, self)
        elif sectype in ('SHT_SYMTAB', 'SHT_DYNSYM', 'SHT_SUNW_LDYNSYM'):
            return self._make_symbol_table_section(section_header, name)
        elif sectype == 'SHT_SUNW_syminfo':
            return self._make_sunwsyminfo_table_section(section_header, name)
        elif sectype == 'SHT_GNU_verneed':
            return self._make_gnu_verneed_section(section_header, name)
        elif sectype == 'SHT_GNU_verdef':
            return self._make_gnu_verdef_section(section_header, name)
        elif sectype == 'SHT_GNU_versym':
            return self._make_gnu_versym_section(section_header, name)
        elif sectype in ('SHT_REL', 'SHT_RELA'):
            return RelocationSection(section_header, name, self)
        elif sectype == 'SHT_DYNAMIC':
            return DynamicSection(section_header, name, self)
        elif sectype == 'SHT_NOTE':
            return NoteSection(section_header, name, self)
        elif sectype == 'SHT_PROGBITS' and name == '.stab':
            return StabSection(section_header, name, self)
        elif sectype == 'SHT_ARM_ATTRIBUTES':
            return ARMAttributesSection(section_header, name, self)
        else:
            return Section(section_header, name, self)

    def _make_symbol_table_section(self, section_header, name):
        """ Create a SymbolTableSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return SymbolTableSection(
            section_header, name,
            elffile=self,
            stringtable=strtab_section)

    def _make_sunwsyminfo_table_section(self, section_header, name):
        """ Create a SUNWSyminfoTableSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return SUNWSyminfoTableSection(
            section_header, name,
            elffile=self,
            symboltable=strtab_section)

    def _make_gnu_verneed_section(self, section_header, name):
        """ Create a GNUVerNeedSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return GNUVerNeedSection(
            section_header, name,
            elffile=self,
            stringtable=strtab_section)

    def _make_gnu_verdef_section(self, section_header, name):
        """ Create a GNUVerDefSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return GNUVerDefSection(
            section_header, name,
            elffile=self,
            stringtable=strtab_section)

    def _make_gnu_versym_section(self, section_header, name):
        """ Create a GNUVerSymSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return GNUVerSymSection(
            section_header, name,
            elffile=self,
            symboltable=strtab_section)

    def _get_segment_header(self, n):
        """ Find the header of segment #n, parse it and return the struct
        """
        return struct_parse(
            self.structs.Elf_Phdr,
            self.stream,
            stream_pos=self._segment_offset(n))

    def _get_file_stringtable(self):
        """ Find the file's string table section
        """
        stringtable_section_num = self['e_shstrndx']
        return StringTableSection(
                header=self._get_section_header(stringtable_section_num),
                name='',
                elffile=self)

    def _parse_elf_header(self):
        """ Parses the ELF file header and assigns the result to attributes
            of this object.
        """
        return struct_parse(self.structs.Elf_Ehdr, self.stream, stream_pos=0)

    def _read_dwarf_section(self, section, relocate_dwarf_sections):
        """ Read the contents of a DWARF section from the stream and return a
            DebugSectionDescriptor. Apply relocations if asked to.
        """
        # The section data is read into a new stream, for processing
        section_stream = BytesIO()
        section_stream.write(section.data())

        if relocate_dwarf_sections:
            reloc_handler = RelocationHandler(self)
            reloc_section = reloc_handler.find_relocations_for_section(section)
            if reloc_section is not None:
                reloc_handler.apply_section_relocations(
                        section_stream, reloc_section)

        return DebugSectionDescriptor(
                stream=section_stream,
                name=section.name,
                global_offset=section['sh_offset'],
                size=section['sh_size'],
                address=section['sh_addr'])

    @staticmethod
    def _decompress_dwarf_section(section):
        """ Returns the uncompressed contents of the provided DWARF section.
        """
        # TODO: support other compression formats from readelf.c
        assert section.size > 12, 'Unsupported compression format.'

        section.stream.seek(0)
        # According to readelf.c the content should contain "ZLIB"
        # followed by the uncompressed section size - 8 bytes in
        # big-endian order
        compression_type = section.stream.read(4)
        assert compression_type == b'ZLIB', \
            'Invalid compression type: %r' % (compression_type)

        uncompressed_size = struct.unpack('>Q', section.stream.read(8))[0]

        decompressor = zlib.decompressobj()
        uncompressed_stream = BytesIO()
        while True:
            chunk = section.stream.read(PAGESIZE)
            if not chunk:
                break
            uncompressed_stream.write(decompressor.decompress(chunk))
        uncompressed_stream.write(decompressor.flush())

        uncompressed_stream.seek(0, io.SEEK_END)
        size = uncompressed_stream.tell()
        assert uncompressed_size == size, \
                'Wrong uncompressed size: expected %r, but got %r' % (
                    uncompressed_size, size,
                )

        return section._replace(stream=uncompressed_stream, size=size)
