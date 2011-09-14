#-------------------------------------------------------------------------------
# elftools: elf/segments.py
#
# ELF segments
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import CString
from ..common.utils import struct_parse


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


class InterpSegment(Segment):
    """ INTERP segment. Knows how to obtain the path to the interpreter used
        for this ELF file.
    """
    def __init__(self, header, stream):
        super(InterpSegment, self).__init__(header, stream)

    def get_interp_name(self):
        """ Obtain the interpreter path used for this ELF file.
        """
        path_offset = self['p_offset']
        return struct_parse(
            CString(''),
            self.stream,
            stream_pos=path_offset)


