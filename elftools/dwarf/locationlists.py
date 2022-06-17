#-------------------------------------------------------------------------------
# elftools: dwarf/locationlists.py
#
# DWARF location lists section decoding (.debug_loc)
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
from collections import namedtuple
from ..common.exceptions import DWARFError
from ..common.utils import struct_parse

LocationExpr = namedtuple('LocationExpr', 'loc_expr')
LocationEntry = namedtuple('LocationEntry', 'entry_offset entry_length begin_offset end_offset loc_expr is_absolute')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'entry_offset entry_length base_address')
LocationViewPair = namedtuple('LocationViewPair', 'entry_offset begin end')

class LocationLists(object):
    """ A single location list is a Python list consisting of LocationEntry or
        BaseAddressEntry objects.

        Starting with DWARF5, it may also contain LocationViewPair, but only
        if scanning the section, never when requested for a DIE attribute.

        The default location entries are returned as LocationEntry with
        begin_offset == end_offset == -1

        Version determines whether the executable contains a debug_loc
        section, or a DWARFv5 style debug_loclists one. Only the 4/5
        distinction matters.

        Dwarfinfo is only needed for DWARFv5 location entry encodings
        that contain references to other sections (e. g. DW_LLE_startx_endx),
        and only for location list enumeration.
    """
    def __init__(self, stream, structs, version=4, dwarfinfo=None):
        self.stream = stream
        self.structs = structs
        self.dwarfinfo = dwarfinfo
        self.version = version
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1

    def get_location_list_at_offset(self, offset, die=None):
        """ Get a location list at the given offset in the section.
        Passing the die is only neccessary in DWARF5+, for decoding
        location entry encodings that contain references to other sections.
        """
        self.stream.seek(offset, os.SEEK_SET)
        return self._parse_location_list_from_stream_v5(die) if self.version >= 5 else self._parse_location_list_from_stream()

    def iter_location_lists(self):
        """ Iterates through location lists and view pairs. Returns lists of
        LocationEntry, BaseAddressEntry, and LocationViewPair objects.
        """
        # The location lists section was never meant for sequential access.
        # Location lists are referenced by DIE attributes by offset or by index.

        # As of DWARFv5, it may contain, in addition to proper location lists,
        #location list view pairs, which are referenced by the nonstandard DW_AT_GNU_locviews
        # attribute. A set of locview pairs (which is a couple of ULEB128 values) may preceed
        # a location list; the former is referenced by the DW_AT_GNU_locviews attribute, the
        # latter - by DW_AT_location (in the same DIE). Binutils' readelf dumps those.
        # There is a view pair for each location-type entry in the list.
        #
        # Also, the section may contain gaps.
        #
        # Taking a cue from binutils, we would have to scan this section while looking at
        # what's in DIEs.
        stream = self.stream
        stream.seek(0, os.SEEK_END)
        endpos = stream.tell()

        stream.seek(0, os.SEEK_SET)

        if self.version >= 5:
            # Need to provide support for DW_AT_GNU_locviews. They are interspersed in
            # the locations section, no way to tell where short of checking all DIEs
            all_offsets = set() # Set of offsets where either a locview pair set can be found, or a view-less loclist
            locviews = dict() # Map of locview offset to the respective loclist offset
            cu_map = dict() # Map of loclist offsets to CUs
            for cu in self.dwarfinfo.iter_CUs():
                cu_ver = cu['version']
                for die in cu.iter_DIEs():
                    # A combination of location and locviews means there is a location list
                    # preceed by several locview pairs
                    if 'DW_AT_GNU_locviews' in die.attributes:
                        assert('DW_AT_location' in die.attributes and
                            LocationParser._attribute_has_loc_list(die.attributes['DW_AT_location'], cu_ver))
                        views_offset = die.attributes['DW_AT_GNU_locviews'].value
                        list_offset = die.attributes['DW_AT_location'].value
                        locviews[views_offset] = list_offset
                        cu_map[list_offset] = cu
                        all_offsets.add(views_offset)

                    # Scan other attributes for location lists
                    for key in die.attributes:
                        attr = die.attributes[key]
                        if (key != 'DW_AT_location' and
                            LocationParser.attribute_has_location(attr, cu_ver) and
                            LocationParser._attribute_has_loc_list(attr, cu_ver)):
                            list_offset = attr.value
                            all_offsets.add(list_offset)
                            cu_map[list_offset] = cu
            all_offsets = list(all_offsets)
            all_offsets.sort()

            # Loclists section is organized as an array of CUs, each length prefixed.
            # We don't assume that the CUs go in the same order as the ones in info.
            offset_index = 0
            while stream.tell() < endpos:
                # We are at the start of the CU block in the loclists now
                unit_length = struct_parse(self.structs.Dwarf_initial_length(''), stream)
                offset_past_len = stream.tell()
                cu_header = struct_parse(self.structs.Dwarf_loclists_CU_header, stream)
                assert(cu_header.version == 5)

                # GNU binutils supports two traversal modes: by offsets in CU header, and sequential.
                # We don't have a binary for the former yet. On an off chance that we one day might,
                # let's parse the header anyway.

                cu_end_offset = offset_past_len + unit_length
                # Unit_length includes the header but doesn't include the length

                while stream.tell() < cu_end_offset:
                    # Skip the gap to the next object
                    next_offset = all_offsets[offset_index]
                    if next_offset == stream.tell(): # At an object, either a loc list or a loc view pair
                        locview_pairs = self._parse_locview_pairs(locviews)
                        entries = self._parse_location_list_from_stream_v5()
                        yield locview_pairs + entries
                        offset_index += 1
                    else: # We are at a gap - skip the gap to the next object or to the next CU
                        if next_offset > cu_end_offset: # Gap at the CU end - the next object is in the next CU
                            next_offset = cu_end_offset # And implicitly quit the loop within the CU
                        stream.seek(next_offset, os.SEEK_SET)
        else:
            # Just call _parse_location_list_from_stream until the stream ends
            while stream.tell() < endpos:
                yield self._parse_location_list_from_stream()

    #------ PRIVATE ------#

    def _parse_location_list_from_stream(self):
        lst = []
        while True:
            entry_offset = self.stream.tell()
            begin_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            end_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            if begin_offset == 0 and end_offset == 0:
                # End of list - we're done.
                break
            elif begin_offset == self._max_addr:
                # Base address selection entry
                entry_length = self.stream.tell() - entry_offset
                lst.append(BaseAddressEntry(entry_offset=entry_offset, entry_length=entry_length, base_address=end_offset))
            else:
                # Location list entry
                expr_len = struct_parse(
                    self.structs.Dwarf_uint16(''), self.stream)
                loc_expr = [struct_parse(self.structs.Dwarf_uint8(''),
                                         self.stream)
                                for i in range(expr_len)]
                entry_length = self.stream.tell() - entry_offset
                lst.append(LocationEntry(
                    entry_offset=entry_offset,
                    entry_length=entry_length,
                    begin_offset=begin_offset,
                    end_offset=end_offset,
                    loc_expr=loc_expr,
                    is_absolute = False))
        return lst

    # Also returns an array with BaseAddressEntry and LocationEntry
    # Can't possibly support indexed values, since parsing those requires
    # knowing the DIE context it came from
    def _parse_location_list_from_stream_v5(self, die = None):
        # This won't contain the terminator entry
        lst = [self._translate_entry_v5(entry, die)
            for entry
            in struct_parse(self.structs.Dwarf_loclists_entries, self.stream)]
        return lst

    # From V5 style entries to a LocationEntry/BaseAddressEntry
    def _translate_entry_v5(self, entry, die):
        off = entry.entry_offset
        len = entry.entry_end_offset - off
        type = entry.entry_type
        if type == 'DW_LLE_base_address':
            return BaseAddressEntry(off, len, entry.address)
        elif type == 'DW_LLE_offset_pair':
            return LocationEntry(off, len, entry.start_offset, entry.end_offset, entry.loc_expr, False)
        elif type == 'DW_LLE_start_length':
            return LocationEntry(off, len, entry.start_address, entry.start_address + entry.length, entry.loc_expr, True)
        elif type == 'DW_LLE_start_end': # No test for this yet, but the format seems straightforward
            return LocationEntry(off, len, entry.start_address, entry.end_address, entry.loc_expr, True)
        elif type == 'DW_LLE_default_location': # No test for this either, and this is new in the API
            return LocationEntry(off, len, -1, -1, entry.loc_expr, True)
        elif type in ('DW_LLE_base_addressx', 'DW_LLE_startx_endx', 'DW_LLE_startx_length'):
            # We don't have sample binaries for those LLEs. Their proper parsing would
            # require knowing the CU context (so that indices can be resolved to code offsets)
            raise NotImplementedError("Location list entry type %s is not supported yet" % (type,))
        else:
            raise DWARFError(False, "Unknown DW_LLE code: %s" % (type,))

    # Locviews is the dict, mapping locview offsets to corresponding loclist offsets
    def _parse_locview_pairs(self, locviews):
        stream = self.stream
        list_offset = locviews.get(stream.tell(), None)
        pairs = []
        if list_offset is not None:
            while stream.tell() < list_offset:
                pair = struct_parse(self.structs.Dwarf_locview_pair, stream)
                pairs.append(LocationViewPair(pair.entry_offset, pair.begin, pair.end))
            assert(stream.tell() == list_offset)
        return pairs

class LocationParser(object):
    """ A parser for location information in DIEs.
        Handles both location information contained within the attribute
        itself (represented as a LocationExpr object) and references to
        location lists in the .debug_loc section (represented as a
        list).
    """
    def __init__(self, location_lists):
        self.location_lists = location_lists

    @staticmethod
    def attribute_has_location(attr, dwarf_version):
        """ Checks if a DIE attribute contains location information.
        """
        return (LocationParser._attribute_is_loclistptr_class(attr) and
                (LocationParser._attribute_has_loc_expr(attr, dwarf_version) or
                 LocationParser._attribute_has_loc_list(attr, dwarf_version)))

    def parse_from_attribute(self, attr, dwarf_version, die = None):
        """ Parses a DIE attribute and returns either a LocationExpr or
            a list.
        """
        if self.attribute_has_location(attr, dwarf_version):
            if self._attribute_has_loc_expr(attr, dwarf_version):
                return LocationExpr(attr.value)
            elif self._attribute_has_loc_list(attr, dwarf_version):
                return self.location_lists.get_location_list_at_offset(
                    attr.value, die)
                # We don't yet know if the DIE context will be needed.
                # We might get it without a full tree traversal using
                # attr.offset as a key, but we assume a good DWARF5
                # aware consumer would pass a DIE along.
        else:
            raise ValueError("Attribute does not have location information")

    #------ PRIVATE ------#

    @staticmethod
    def _attribute_has_loc_expr(attr, dwarf_version):
        return ((dwarf_version < 4 and attr.form.startswith('DW_FORM_block') and
            not attr.name == 'DW_AT_const_value') or
            attr.form == 'DW_FORM_exprloc')

    @staticmethod
    def _attribute_has_loc_list(attr, dwarf_version):
        return ((dwarf_version < 4 and
                 attr.form in ('DW_FORM_data4', 'DW_FORM_data8') and
                 not attr.name == 'DW_AT_const_value') or
                attr.form == 'DW_FORM_sec_offset')

    @staticmethod
    def _attribute_is_loclistptr_class(attr):
        return (attr.name in ( 'DW_AT_location', 'DW_AT_string_length',
                               'DW_AT_const_value', 'DW_AT_return_addr',
                               'DW_AT_data_member_location',
                               'DW_AT_frame_base', 'DW_AT_segment',
                               'DW_AT_static_link', 'DW_AT_use_location',
                               'DW_AT_vtable_elem_location',
                               'DW_AT_GNU_call_site_value',
                               'DW_AT_GNU_call_site_target',
                               'DW_AT_GNU_call_site_data_value'))
