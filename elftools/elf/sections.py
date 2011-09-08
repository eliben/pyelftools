#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

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

