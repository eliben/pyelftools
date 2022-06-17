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


RangeEntry = namedtuple('RangeEntry', 'entry_offset entry_length begin_offset end_offset is_absolute')
BaseAddressEntry = namedtuple('BaseAddressEntry', 'entry_offset base_address')

def not_implemented(e):
    raise NotImplementedError("Range list entry %s is not supported yet" % (e.entry_type,))

# Maps parsed entry types to RangeEntry/BaseAddressEntry objects
entry_translate = {
    'DW_RLE_base_address' : lambda e: BaseAddressEntry(e.entry_offset, e.address),
    'DW_RLE_offset_pair'  : lambda e: RangeEntry(e.entry_offset, e.entry_length, e.start_offset, e.end_offset, False),
    'DW_RLE_start_end'    : lambda e: RangeEntry(e.entry_offset, e.entry_length, e.start_address, e.end_address, True),
    'DW_RLE_start_length' : lambda e: RangeEntry(e.entry_offset, e.entry_length, e.start_address, e.start_address + e.length, True),
    'DW_RLE_base_addressx': not_implemented,
    'DW_RLE_startx_endx'  : not_implemented,
    'DW_RLE_startx_length': not_implemented
}

class RangeLists(object):
    """ A single range list is a Python list consisting of RangeEntry or
        BaseAddressEntry objects.

        Since v0.29, two new parameters - version and dwarfinfo

        version is used to distinguish DWARFv5 rnglists section from
        the DWARF<=4 ranges section. Only the 4/5 distinction matters.

        The dwarfinfo is needed for enumeration, because enumeration
        requires scanning the DIEs, because ranges may overlap, even on DWARF<=4
    """
    def __init__(self, stream, structs, version, dwarfinfo):
        self.stream = stream
        self.structs = structs
        self._max_addr = 2 ** (self.structs.address_size * 8) - 1
        self.version = version
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
        all_offsets = list(set(die.attributes['DW_AT_ranges'].value
            for cu in self._dwarfinfo.iter_CUs()
            for die in cu.iter_DIEs()
            if 'DW_AT_ranges' in die.attributes))
        all_offsets.sort()

        for offset in all_offsets:
            yield self.get_range_list_at_offset(offset)

    #------ PRIVATE ------#

    def _parse_range_list_from_stream(self):
        if self.version >= 5:
            return list(entry_translate[entry.entry_type](entry)
                for entry
                in struct_parse(self.structs.Dwarf_rnglists_entries, self.stream))
        else:
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
                        entry_length=self.stream.tell() - entry_offset,
                        begin_offset=begin_offset,
                        end_offset=end_offset,
                        is_absolute=False))
            return lst
