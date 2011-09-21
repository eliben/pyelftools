#-------------------------------------------------------------------------------
# elftools: dwarf/compileunit.py
#
# DWARF compile unit
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .die import DIE


class CompileUnit(object):
    def __init__(self, header, dwarfinfo, structs, cu_die_offset):
        """ header:
                CU header for this compile unit
            
            dwarfinfo:
                The DWARFInfo context object which created this one
                        
            structs:
                A DWARFStructs instance suitable for this compile unit
            
            cu_die_offset:
                Offset in the stream of the top DIE of this CU
        """
        self.dwarfinfo = dwarfinfo
        self.header = header
        self.structs = structs
        self.cu_die_offset = cu_die_offset
        
        # The abbreviation table for this CU. Filled lazily when DIEs are 
        # requested.
        self._abbrev_table = None
        
    def get_abbrev_table(self):
        """ Get the abbreviation table (AbbrevTable object) for this CU
        """
        if self._abbrev_table is None:
            self._abbrev_table = self.dwarfinfo.get_abbrev_table(
                self['debug_abbrev_offset'])
        return self._abbrev_table

    def get_top_DIE(self):
        """ Get the top DIE (which is either a DW_TAG_compile_unit or 
            DW_TAG_partial_unit) of this CU
        """
        return DIE(
            cu=self,
            stream=self.dwarfinfo.stream,
            offset=self.cu_die_offset)

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    