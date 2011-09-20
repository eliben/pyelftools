#-------------------------------------------------------------------------------
# elftools: dwarf/abbrevtable.py
#
# DWARF abbreviation table
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------


class AbbrevTable(object):
    def __init__(self, structs, stream):
        self.structs = structs
        self.stream = stream


