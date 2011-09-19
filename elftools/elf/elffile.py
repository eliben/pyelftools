#-------------------------------------------------------------------------------
# elftools: elf/elffile.py
#
# ELFFile - main class for accessing ELF files
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.exceptions import ELFError
from ..common.utils import struct_parse, elf_assert
from ..construct import ConstructError
from .structs import ELFStructs
from .sections import (
        Section, StringTableSection, SymbolTableSection, NullSection,
        RelocationSection)
from .segments import Segment, InterpSegment


class ELFFile(object):
    """ Creation: the constructor accepts a stream (file-like object) with the
        contents of an ELF file.
    
        Accessible attributes:
        
            elfclass: 
                32 or 64 - specifies the word size of the target machine
            
            little_endian:
                boolean - specifies the target machine's endianness     

            header:
                the complete ELF file header

            e_ident_raw:
                the raw e_ident field of the header
    """
    def __init__(self, stream):
        self.stream = stream
        self._identify_file()
        self.structs = ELFStructs(
            little_endian=self.little_endian,
            elfclass=self.elfclass)
        self.header = self._parse_elf_header()

        self.stream.seek(0)
        self.e_ident_raw = self.stream.read(16)
        
        self._file_stringtable_section = self._get_file_stringtable()
        self._section_name_map = None
    
    def num_sections(self):
        """ Number of sections in the file
        """
        return self['e_shnum']
    
    def get_section(self, n):
        """ Get the section at index #n from the file (Section object or a
            subclass)
        """
        section_header = self._get_section_header(n)
        return self._make_section(section_header)
    
    def get_section_by_name(self, name):
        """ Get a section from the file, by name. Return None if no such 
            section exists.
        """
        # The first time this method is called, construct a name to number
        # mapping
        #
        if self._section_name_map is None:
            self._section_name_map = {}
            for i, sec in enumerate(self.iter_sections()):
                self._section_name_map[sec.name] = i
        secnum = self._section_name_map.get(name, None)
        return None if secnum is None else self.get_section(secnum)
    
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
        return self._make_segment(segment_header)
    
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
        elf_assert(magic == '\x7fELF', 'Magic number does not match')
        
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
    
    def _make_segment(self, segment_header):
        """ Create a Segment object of the appropriate type
        """
        segtype = segment_header['p_type']
        if segtype == 'PT_INTERP':
            return InterpSegment(segment_header, self.stream)
        else:
            return Segment(segment_header, self.stream)

    def _get_section_header(self, n):
        """ Find the header of section #n, parse it and return the struct 
        """
        return struct_parse(
            self.structs.Elf_Shdr,
            self.stream,
            stream_pos=self._section_offset(n))
    
    def _get_section_name(self, section_header):
        """ Given a section header, find this section's name in the file's
            string table
        """
        name_offset = section_header['sh_name']
        return self._file_stringtable_section.get_string(name_offset)

    def _make_section(self, section_header):
        """ Create a section object of the appropriate type
        """
        name = self._get_section_name(section_header)
        sectype = section_header['sh_type']
        
        if sectype == 'SHT_STRTAB':
            return StringTableSection(section_header, name, self.stream)
        elif sectype == 'SHT_NULL':
            return NullSection(section_header, name, self.stream)
        elif sectype in ('SHT_SYMTAB', 'SHT_DYNSYM'):
            return self._make_symbol_table_section(section_header, name)
        elif sectype in ('SHT_REL', 'SHT_RELA'):
            return RelocationSection(
                section_header, name, self.stream, self.structs)
        else:
            return Section(section_header, name, self.stream)

    def _make_symbol_table_section(self, section_header, name):
        """ Create a SymbolTableSection
        """
        linked_strtab_index = section_header['sh_link']
        strtab_section = self.get_section(linked_strtab_index)
        return SymbolTableSection(
            section_header, name, self.stream,
            elfstructs=self.structs,
            stringtable=strtab_section)

    def _get_segment_header(self, n):
        """ Find the header of segment #n, parse it and return the struct
        """
        return struct_parse(
            self.structs.Elf_Phdr,
            self.stream,
            stream_pos=self._segment_offset(n))
    
    def _get_file_stringtable(self):
        """ Find the file's string table section
        """
        stringtable_section_num = self['e_shstrndx']
        return StringTableSection(
                header=self._get_section_header(stringtable_section_num),
                name='',
                stream=self.stream)
    
    def _parse_elf_header(self):
        """ Parses the ELF file header and assigns the result to attributes
            of this object.
        """
        return struct_parse(self.structs.Elf_Ehdr, self.stream, stream_pos=0)

