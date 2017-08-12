#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.exceptions import ELFCompressionError
from ..common.utils import struct_parse, elf_assert, parse_cstring_from_stream
from collections import defaultdict
from .constants import SH_FLAGS
from .notes import iter_notes
import zlib


class Section(object):
    """ Base class for ELF sections. Also used for all sections types that have
        no special functionality.

        Allows dictionary-like access to the section header. For example:
         > sec = Section(...)
         > sec['sh_type']  # section type
    """
    def __init__(self, header, name, elffile):
        self.header = header
        self.name = name
        self.elffile = elffile
        self.stream = self.elffile.stream
        self.structs = self.elffile.structs
        self._compressed = header['sh_flags'] & SH_FLAGS.SHF_COMPRESSED

        if self.compressed:
            # Read the compression header now to know about the size/alignment
            # of the decompressed data.
            header = struct_parse(self.structs.Elf_Chdr,
                                  self.stream,
                                  stream_pos=self['sh_offset'])
            self._compression_type = header['ch_type']
            self._decompressed_size = header['ch_size']
            self._decompressed_align = header['ch_addralign']
        else:
            self._decompressed_size = header['sh_size']
            self._decompressed_align = header['sh_addralign']

    @property
    def compressed(self):
        """ Is this section compressed?
        """
        return self._compressed

    @property
    def data_size(self):
        """ Return the logical size for this section's data.

        This can be different from the .sh_size header field when the section
        is compressed.
        """
        return self._decompressed_size

    @property
    def data_alignment(self):
        """ Return the logical alignment for this section's data.

        This can be different from the .sh_addralign header field when the
        section is compressed.
        """
        return self._decompressed_align

    def data(self):
        """ The section data from the file.

        Note that data is decompressed if the stored section data is
        compressed.
        """
        # If this section is compressed, deflate it
        if self.compressed:
            c_type = self._compression_type
            if c_type == 'ELFCOMPRESS_ZLIB':
                # Read the data to decompress starting right after the
                # compression header until the end of the section.
                hdr_size = self.structs.Elf_Chdr.sizeof()
                self.stream.seek(self['sh_offset'] + hdr_size)
                compressed = self.stream.read(self['sh_size'] - hdr_size)

                decomp = zlib.decompressobj()
                result = decomp.decompress(compressed, self.data_size)
            else:
                raise ELFCompressionError(
                    'Unknown compression type: {:#0x}'.format(c_type)
                )

            if len(result) != self._decompressed_size:
                raise ELFCompressionError(
                    'Decompressed data is {} bytes long, should be {} bytes'
                    ' long'.format(len(result), self._decompressed_size)
                )
        else:
            self.stream.seek(self['sh_offset'])
            result = self.stream.read(self._decompressed_size)

        return result

    def is_null(self):
        """ Is this a null section?
        """
        return False

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def __eq__(self, other):
        try:
            return self.header == other.header
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.header)


class NullSection(Section):
    """ ELF NULL section
    """
    def is_null(self):
        return True


class StringTableSection(Section):
    """ ELF string table section.
    """
    def get_string(self, offset):
        """ Get the string stored at the given offset in this string table.
        """
        table_offset = self['sh_offset']
        s = parse_cstring_from_stream(self.stream, table_offset + offset)
        return s.decode('ascii') if s else ''


class SymbolTableSection(Section):
    """ ELF symbol table section. Has an associated StringTableSection that's
        passed in the constructor.
    """
    def __init__(self, header, name, elffile, stringtable):
        super(SymbolTableSection, self).__init__(header, name, elffile)
        self.stringtable = stringtable
        elf_assert(self['sh_entsize'] > 0,
                'Expected entry size of section %r to be > 0' % name)
        elf_assert(self['sh_size'] % self['sh_entsize'] == 0,
                'Expected section size to be a multiple of entry size in section %r' % name)
        self._symbol_name_map = None

    def num_symbols(self):
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize']

    def get_symbol(self, n):
        """ Get the symbol at index #n from the table (Symbol object)
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.structs.Elf_Sym,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated string table
        name = self.stringtable.get_string(entry['st_name'])
        return Symbol(entry, name)

    def get_symbol_by_name(self, name):
        """ Get a symbol(s) by name. Return None if no symbol by the given name
            exists.
        """
        # The first time this method is called, construct a name to number
        # mapping
        #
        if self._symbol_name_map is None:
            self._symbol_name_map = defaultdict(list)
            for i, sym in enumerate(self.iter_symbols()):
                self._symbol_name_map[sym.name].append(i)
        symnums = self._symbol_name_map.get(name)
        return [self.get_symbol(i) for i in symnums] if symnums else None

    def iter_symbols(self):
        """ Yield all the symbols in the table
        """
        for i in range(self.num_symbols()):
            yield self.get_symbol(i)


class Symbol(object):
    """ Symbol object - representing a single symbol entry from a symbol table
        section.

        Similarly to Section objects, allows dictionary-like access to the
        symbol entry.
    """
    def __init__(self, entry, name):
        self.entry = entry
        self.name = name

    def __getitem__(self, name):
        """ Implement dict-like access to entries
        """
        return self.entry[name]


class SUNWSyminfoTableSection(Section):
    """ ELF .SUNW Syminfo table section.
        Has an associated SymbolTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, elffile, symboltable):
        super(SUNWSyminfoTableSection, self).__init__(header, name, elffile)
        self.symboltable = symboltable

    def num_symbols(self):
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize'] - 1

    def get_symbol(self, n):
        """ Get the symbol at index #n from the table (Symbol object).
            It begins at 1 and not 0 since the first entry is used to
            store the current version of the syminfo table.
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.structs.Elf_Sunw_Syminfo,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated symbol table
        name = self.symboltable.get_symbol(n).name
        return Symbol(entry, name)

    def iter_symbols(self):
        """ Yield all the symbols in the table
        """
        for i in range(1, self.num_symbols() + 1):
            yield self.get_symbol(i)


class NoteSection(Section):
    """ ELF NOTE section. Knows how to parse notes.
    """
    def iter_notes(self):
        """ Yield all the notes in the section.  Each result is a dictionary-
            like object with "n_name", "n_type", and "n_desc" fields, amongst
            others.
        """
        return iter_notes(self.elffile, self['sh_offset'], self['sh_size'])

class StabSection(Section):
    """ ELF stab section.
    """
    def iter_stabs(self):
        """ Yield all stab entries.  Result type is ELFStructs.Elf_Stabs.
        """
        offset = self['sh_offset']
        size = self['sh_size']
        end = offset + size
        while offset < end:
            stabs = struct_parse(
                self.structs.Elf_Stabs,
                self.elffile.stream,
                stream_pos=offset)
            stabs['n_offset'] = offset
            offset += self.structs.Elf_Stabs.sizeof()
            self.stream.seek(offset)
            yield stabs

