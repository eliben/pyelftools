#-------------------------------------------------------------------------------
# elftools: elf/elffile.py
#
# ELFFile - main class for accessing ELF files
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

from cStringIO import StringIO

from ..exceptions import ELFError, ELFParseError
from ..construct import ConstructError, CString
from .structs import ELFStructs
from .sections import Section
from .segments import Segment


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
        self._stringtable = self._get_stringtable()
    
    def num_sections(self):
        """ Number of sections in the file
        """
        return self['e_shnum']
    
    def get_section(self, n):
        """ Get the section at index #n from the file (Section object)
        """
        section_header = self._get_section_header(n)
        name = self._get_section_name(section_header)
        return Section(section_header, name, self.stream)
    
    def iter_sections(self):
        """ Yield all the sections in the file
        """
        for i in range(self.num_sections()):
            yield self.get_section(i)
    
    def num_segments(self):
        """ Number of segments in the file
        """
        return self['e_phnum']
    
    def get_segment(self, n):
        """ Get the segment at index #n from the file (Segment object)
        """
        segment_header = self._get_segment_header(n)
        return Segment(segment_header, self.stream)
    
    def iter_segments(self):
        """ Yield all the segments in the file
        """
        for i in range(self.num_segments()):
            yield self.get_segment(i)
    
    #-------------------------------- PRIVATE --------------------------------#
    
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
    
    def _section_offset(self, n):
        """ Compute the offset of section #n in the file
        """
        return self['e_shoff'] + n * self['e_shentsize']
    
    def _segment_offset(self, n):
        """ Compute the offset of segment #n in the file
        """
        return self['e_phoff'] + n * self['e_phentsize']
    
    def _get_section_header(self, n):
        """ Find the header of section #n, parse it and return the struct 
        """
        self.stream.seek(self._section_offset(n))
        return self._struct_parse(self.structs.Elf_Shdr)
    
    def _get_segment_header(self, n):
        """ Find the header of segment #n, parse it and return the struct
        """
        self.stream.seek(self._segment_offset(n))
        return self._struct_parse(self.structs.Elf_Phdr)
    
    def _get_section_name(self, section_header):
        """ Given a section header, find this section's name in the file's
            string table, and return it as a normal Python string.
        """
        offset = section_header['sh_name']
        self._stringtable.seek(offset)
        return CString('').parse_stream(self._stringtable)
    
    def _get_stringtable(self):
        """ Find the file's string table section, read it and return the string
            table as a StringIO object pointing to the section's contents.
        """
        # Find the section header for the stringtable header, and read the 
        # section's contents from it
        #
        stringtable_section_num = self['e_shstrndx']
        stringtable_header = self._get_section_header(stringtable_section_num)
        self.stream.seek(stringtable_header['sh_offset'])
        return StringIO(self.stream.read(stringtable_header['sh_size']))
    
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

