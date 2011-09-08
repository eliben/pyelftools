#-------------------------------------------------------------------------------
# elftools: common/exceptions.py
#
# Exception classes for elftools
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
class ELFError(Exception): 
    pass

class ELFParseError(ELFError):
    pass

