#-------------------------------------------------------------------------------
# elftools: dwarf/ranges.py
#
# DWARF ranges section decoding (.debug_ranges)
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
from collections import namedtuple

from ..common.utils import struct_parse


RangeEntry = namedtuple('RangeEntry', 'entry_offset begin_offset end_offset')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'entry_offset base_address')


class RangeLists(object):
    """ A single range list is a Python list consisting of RangeEntry or
        BaseAddressEntry objects.

        The dwarfinfo is needed for enumeration, because it requires
        scanning the DIEs, because ranges may overlap.
    """
    # Since dwarfinfo is not a required parameter, there is fallback to the
    # broken enumeration logic, in case there is an old consumer
    def __init__(self, stream, structs, dwarfinfo = None):
        self.stream = stream
        self.structs = structs
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1
        self._dwarfinfo = dwarfinfo

    def get_range_list_at_offset(self, offset):
        """ Get a range list at the given offset in the section.
        """
        self.stream.seek(offset, os.SEEK_SET)
        return self._parse_range_list_from_stream()

    def iter_range_lists(self):
        """ Yield all range lists found in the section.
        """
        # Calling parse until the stream ends is wrong, because ranges can overlap.
        # Need to scan the DIEs to know all range locations
        if self._dwarfinfo:
            all_offsets = list(set(die.attributes['DW_AT_ranges'].value
                for cu in self._dwarfinfo.iter_CUs()
                for die in cu.iter_DIEs()
                if 'DW_AT_ranges' in die.attributes))
            all_offsets.sort()

            for offset in all_offsets:
                yield self.get_range_list_at_offset(offset)
        else: # Flawed logic for legacy consumers, if any
            self.stream.seek(0, os.SEEK_END)
            endpos = self.stream.tell()

            self.stream.seek(0, os.SEEK_SET)
            while self.stream.tell() < endpos:
                yield self._parse_range_list_from_stream()

    #------ PRIVATE ------#

    def _parse_range_list_from_stream(self):
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
                # Range entry
                lst.append(RangeEntry(
                    entry_offset=entry_offset,
                    begin_offset=begin_offset,
                    end_offset=end_offset))
        return lst
