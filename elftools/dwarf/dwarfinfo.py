#-------------------------------------------------------------------------------
# elftools: dwarf/dwarfinfo.py
#
# DWARFInfo - Main class for accessing DWARF debug information
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.exceptions import DWARFError
from ..common.utils import struct_parse, dwarf_assert
from .structs import DWARFStructs
from .compileunit import CompileUnit


# Describes a debug section in a stream: offset and size
#
DebugSectionLocator = namedtuple('DebugSectionLocator', 'offset size')


class DWARFInfo(object):
    """ Creation: the constructor accepts a stream (file-like object) that
        contains debug sections, along with locators (DebugSectionLocator)
        of the required sections. In addition, little_endian is a boolean
        parameter specifying endianity.
    """
    def __init__(self, 
            stream,
            little_endian,
            debug_info_loc,
            debug_abbrev_loc,
            debug_str_loc,
            debug_line_loc):
        self.stream = stream
        self.debug_info_loc = debug_info_loc
        self.debug_abbrev_loc = debug_abbrev_loc
        self.debug_str_loc = debug_str_loc
        self.debug_line_loc = debug_line_loc
        
        self.little_endian = little_endian
        self.dwarf_format = 32
        self.structs = DWARFStructs(
            little_endian=self.little_endian,
            dwarf_format=self.dwarf_format)
        
        # Populate the list with CUs found in debug_info
        self._CU = self._parse_CUs()
    
    def _parse_CUs(self):
        """ Parse CU entries from debug_info.
        """
        offset = self.debug_info_loc.offset
        section_boundary = self.debug_info_loc.offset + self.debug_info_loc.size
        CUlist = []
        while offset < section_boundary:
            # Section 7.4 (32-bit and 64-bit DWARF Formats) of the DWARF spec v3
            # states that the first 32-bit word of the CU header determines 
            # whether the CU is represented with 32-bit or 64-bit DWARF format.
            # 
            # So we peek at the first byte in the CU header to determine its
            # dwarf format. Based on it, we then create a new DWARFStructs
            # instance suitable for this CU and use it to parse the rest.
            #
            initial_length = struct_parse(
                self.structs.Dwarf_uint32(''), self.stream, offset)
            if initial_length == 0xFFFFFFFF:
                self.dwarf_format = 64
            cu_structs = DWARFStructs(
                little_endian=self.little_endian,
                dwarf_format=self.dwarf_format)
            
            cu_header = struct_parse(
                self.structs.Dwarf_CU_header, self.stream, offset)
            dwarf_assert(
                self._is_supported_version(cu_header['version']),
                "Expected supported DWARF version. Got '%s'" % cu_header['version'])
            CUlist.append(CompileUnit(cu_header, cu_structs, None))
            # Compute the offset of the next CU in the section. The unit_length
            # field of the CU header contains its size not including the length
            # field itself.
            offset = (  offset + 
                        cu_header['unit_length'] + 
                        cu_structs.initial_lenght_field_size())
        return CUlist
        
    def _is_supported_version(self, version):
        """ DWARF version supported by this parser
        """
        return 2 <= version <= 3

