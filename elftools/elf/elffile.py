#-------------------------------------------------------------------------------
# elftools: elf/elffile.py
#
# ELFFile - main class for accessing ELF files
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

from .structs import ELFStructs
from ..exceptions import ELFError, ELFParseError
from ..construct import ConstructError


class ELFFile(object):
    """ Accessible attributes:
        
            elfclass: 
                32 or 64 - specifies the word size of the target machine
            
            little_endian:
                boolean - specifies the target machine's endianness     

            header:
                the complete ELF file header
    """
    def __init__(self, stream):
        self.stream = stream
        self._identify_file()
        self.structs = ELFStructs(
            little_endian=self.little_endian,
            elfclass=self.elfclass)
        self.header = self._parse_elf_header()
    
    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]
        
    def _identify_file(self):
        """ Verify the ELF file and identify its class and endianness.
        """
        # Note: this code reads the stream directly, without using ELFStructs,
        # since we don't yet know its exact format. ELF was designed to be 
        # read like this - its e_ident field is word-size and endian agnostic.
        #
        self.stream.seek(0)
        magic = self.stream.read(4)
        self._assert(magic == '\x7fELF', 'Magic number does not match')
        
        ei_class = self.stream.read(1)
        if ei_class == '\x01':
            self.elfclass = 32
        elif ei_class == '\x02':
            self.elfclass = 64
        else:
            raise ELFError('Invalid EI_CLASS %s' % repr(ei_class))
        
        ei_data = self.stream.read(1)
        if ei_data == '\x01':
            self.little_endian = True
        elif ei_data == '\x02':
            self.little_endian = False
        else:
            raise ELFError('Invalid EI_DATA %s' % repr(ei_data))
    
    def _parse_elf_header(self):
        """ Parses the ELF file header and assigns the result to attributes
            of this object.
        """
        self.stream.seek(0)
        return self._struct_parse(self.structs.Elf_Ehdr)
    
    def _struct_parse(self, struct):
        """ Convenience method for parsing at the current stream location with
            the given struct. Also wraps the error thrown by construct with our
            own error.
        """
        try:
            return struct.parse_stream(self.stream)
        except ConstructError as e:
            raise ELFParseError(e.message)
    
    def _assert(self, cond, msg=''):
        """ Assert that cond is True, otherwise raise ELFError(msg)
        """
        if not cond:
            raise ELFError(msg)

