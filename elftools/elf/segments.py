#-------------------------------------------------------------------------------
# elftools: elf/segments.py
#
# ELF segments
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

class Segment(object):
    def __init__(self, header, stream):
        self.header = header
        self.stream = stream
    
    def data(self):
        """ The segment data from the file.
        """
        self.stream.seek(self['p_offset'])
        return self.stream.read(self['p_filesz'])

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

