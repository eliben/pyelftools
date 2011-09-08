#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import CString
from ..common.utils import struct_parse


class Section(object):
    """ Base class for ELF sections. Also used for all sections types that have
        no special functionality.
        
        Allows dictionary-like access to the section header. For example:
         > sec = Section(...)
         > sec['sh_type']  # section type
    """
    def __init__(self, header, name, stream):
        self.header = header
        self.name = name
        self.stream = stream
    
    def data(self):
        """ The section data from the file.
        """
        self.stream.seek(self['sh_offset'])
        return self.stream.read(self['sh_size'])

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]


class StringTableSection(Section):
    """ ELF string table section.
    """
    def __init__(self, header, name, stream):
        super(StringTableSection, self).__init__(header, name, stream)
        
    def get_string(self, offset):
        """ Get the string stored at the given offset in this string table.
        """
        table_offset = self['sh_offset']
        return struct_parse(
            CString(''),
            self.stream,
            stream_pos=table_offset + offset)


class SymbolTableSection(Section):
    """ ELF symbol table section. Has an associated StringTableSection that's
        passed in the constructor.
    """
    def __init__(self, header, name, stream, stringtable):
        super(SymbolTableSection, self).__init__(header, name, stream)
        self.stringtable = stringtable
    

