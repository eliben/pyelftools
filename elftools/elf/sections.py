#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import CString


class Section(object):
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
    def __init__(self, header, name, stream):
        super(StringTableSection, self).__init__(header, name, stream)
        
    def get_string(self, offset):
        """ Get the string stored at the given offset in this string table.
        """
        table_offset = self['sh_offset']
        self.stream.seek(table_offset + offset)
        return CString('').parse_stream(self.stream)


    
    
