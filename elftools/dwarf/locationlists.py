#-------------------------------------------------------------------------------
# elftools: dwarf/locationlists.py
#
# DWARF location lists section decoding
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.utils import struct_parse


LocationEntry = namedtuple('LocationEntry', 'begin_offset end_offset loc_expr')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'base_address')


class LocationLists(object):
    def __init__(self, stream, structs):
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1
        
    def get_location_list_at_offset(self, offset):
        pass

    def iter_location_lists(self):
        pass

    def _parse_location_list_from_stream(self):
        lst = []
        while True:
            begin_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            end_offset = struct_parse(
                self.structs.Dwarf_target_addr(''), self.stream)
            if begin_offset == 0 and end_offset == 0:
                # End of list - we're done.
                break
            elif begin_offset == self._max_addr:
                # base
            else: 
                # entry...
        


