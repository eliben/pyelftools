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
        parameter specifying endianity, and dwarfclass is 32 or 64, depending
        on the type of file the DWARF info was read from.
    """
    def __init__(self, 
            stream,
            little_endian,
            dwarfclass,
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
        self.dwarfclass = dwarfclass
        self.structs = DWARFStructs(
            little_endian=self.little_endian,
            dwarfclass=self.dwarfclass)
        
        self._CU = self._parse_CUs()
    
    def initial_lenght_field_size(self):
        """ Size of an initial length field.
        """
        return 4 if self.dwarfclass == 32 else 12

    def _parse_CUs(self):
        """ Parse CU entries from debug_info and return them as a list of
            containers.
        """
        offset = self.debug_info_loc.offset
        section_boundary = self.debug_info_loc.offset + self.debug_info_loc.length
        CUlist = []
        while offset < section_boundary:
            cu_header = struct_parse(
                self.structs.Dwarf_CU_header, self.stream, offset)
            dwarf_assert(self._is_supported_version(cu_header['version']))
            CUlist.append(CompileUnit(cu_header, None))
            # Compute the offset of the next CU in the section. The unit_length
            # field of the CU header contains its size not including the length
            # field itself.
            offset = (  offset + 
                        cu['unit_length'] + 
                        self.initial_lenght_field_size())
        return CUlist
        
    def _is_supported_version(self, version):
        """ DWARF version supported by this parser
        """
        return 2 <= version <= 3




