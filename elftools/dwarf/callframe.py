#-------------------------------------------------------------------------------
# elftools: dwarf/callframe.py
#
# DWARF call frame information
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.utils import (struct_parse)
from .structs import DWARFStructs


class CallFrameInfo(object):
    def __init__(self, stream, size, base_structs):
        self.stream = stream
        self.size = size
        self.base_structs = base_structs

    def _parse_entries(self):
        offset = 0
        while offset < self.size:
            entry_length = struct_parse(
                self.base_structs.Dwarf_uint32(''), self.stream, offset)
            dwarf_format = 64 if entry_length == 0xFFFFFFFF else 32

            entry_structs = DWARFStructs(
                little_endian=self.base_structs.little_endian,
                dwarf_format=dwarf_format,
                address_size=self.base_structs.address_size)

            # ZZZ: it will be easier to split entry reading:
            # header: what comes before the instructions
            # the instructions are parsed separately (their length is computed
            # from the length and the tell() after parsing the header)

