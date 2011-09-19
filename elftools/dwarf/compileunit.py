#-------------------------------------------------------------------------------
# elftools: dwarf/compileunit.py
#
# DWARF compile unit
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------


class CompileUnit(object):
    def __init__(self, header, format_bits, cu_die):
        self.header = header
        self.format_bits = format_bits
        self.cu_die = cu_die
    
    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]
