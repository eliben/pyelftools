#-------------------------------------------------------------------------------
# elftools: dwarf/compileunit.py
#
# DWARF compile unit
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------


class CompileUnit(object):
    def __init__(self, dwarfinfo, header, structs):
        """ dwarfinfo:
                The DWARFInfo context object which created this one
            
            header:
                CU header for this compile unit
            
            structs:
                A DWARFStructs instance suitable for this compile unit
        """
        self.dwarfinfo = dwarfinfo
        self.header = header
        self.structs = structs
    
    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]




