#-------------------------------------------------------------------------------
# elftools: dwarf/lineprogram.py
#
# DWARF line number program
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------


class LineProgram(object):
    def __init__(self, header, dwarfinfo, structs):
        self.dwarfinfo = dwarfinfo
        self.header = header
        pass

    #------ PRIVATE ------#
    
    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

