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

from ..common.utils import struct_parse

LocationExpr = namedtuple('LocationExpr', 'loc_expr')
LocationEntry = namedtuple('LocationEntry', 'entry_offset begin_offset end_offset loc_expr')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'entry_offset base_address')

class LocationLists(object):
    """ A single location list is a Python list consisting of LocationEntry or
        BaseAddressEntry objects.
    """
    def __init__(self, stream, structs):
        self.stream = stream
        self.structs = structs
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1

    def get_location_list_at_offset(self, offset):
        """ Get a location list at the given offset in the section.
        """
        self.stream.seek(offset, os.SEEK_SET)
        return self._parse_location_list_from_stream()

    def iter_location_lists(self):
        """ Yield all location lists found in the section.
        """
        # Just call _parse_location_list_from_stream until the stream ends
        self.stream.seek(0, os.SEEK_END)
        endpos = self.stream.tell()

        self.stream.seek(0, os.SEEK_SET)
        while self.stream.tell() < endpos:
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
                lst.append(BaseAddressEntry(entry_offset=entry_offset, base_address=end_offset))
            else:
                # Location list entry
                expr_len = struct_parse(
                    self.structs.Dwarf_uint16(''), self.stream)
                loc_expr = [struct_parse(self.structs.Dwarf_uint8(''),
                                         self.stream)
                                for i in range(expr_len)]
                lst.append(LocationEntry(
                    entry_offset=entry_offset,
                    begin_offset=begin_offset,
                    end_offset=end_offset,
                    loc_expr=loc_expr))
        return lst

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

    def parse_from_attribute(self, attr, dwarf_version):
        """ Parses a DIE attribute and returns either a LocationExpr or
            a list.
        """
        if self.attribute_has_location(attr, dwarf_version):
            if self._attribute_has_loc_expr(attr, dwarf_version):
                return LocationExpr(attr.value)
            elif self._attribute_has_loc_list(attr, dwarf_version):
                return self.location_lists.get_location_list_at_offset(
                    attr.value)
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
