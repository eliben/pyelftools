#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import CString
from ..common.utils import struct_parse, elf_assert, parse_cstring_from_stream


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

    def is_null(self):
        """ Is this a null section?
        """
        return False

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def __eq__(self, other):
        return self.header == other.header


class NullSection(Section):
    """ ELF NULL section
    """
    def __init__(self, header, name, stream):
        super(NullSection, self).__init__(header, name, stream)

    def is_null(self):
        return True


class StringTableSection(Section):
    """ ELF string table section.
    """
    def __init__(self, header, name, stream):
        super(StringTableSection, self).__init__(header, name, stream)

    def get_string(self, offset):
        """ Get the string stored at the given offset in this string table.
        """
        table_offset = self['sh_offset']
        s = parse_cstring_from_stream(self.stream, table_offset + offset)
        return s


class SymbolTableSection(Section):
    """ ELF symbol table section. Has an associated StringTableSection that's
        passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, stringtable):
        super(SymbolTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.stringtable = stringtable
        elf_assert(self['sh_entsize'] > 0,
                'Expected entry size of section %s to be > 0' % name)
        elf_assert(self['sh_size'] % self['sh_entsize'] == 0,
                'Expected section size to be a multiple of entry size in section %s' % name)

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
            self.elfstructs.Elf_Sym,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated string table
        name = self.stringtable.get_string(entry['st_name'])
        return Symbol(entry, name)

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
    def __init__(self, header, name, stream, elffile, symboltable):
        super(SUNWSyminfoTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
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
            self.elfstructs.Elf_Sunw_Syminfo,
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


class Version(object):
    """ Version object - representing a version definition or dependency
        entry from a "Version Needed" or a "Version Dependency" table section.

        This kind of entry contains a pointer to an array of auxiliary entries
        that store the information about version names or dependencies. 
        These entries are not stored in this object and should be accessed
        through the appropriate method of a section object which will return
        an iterator of VersionAuxiliary objects.

        Similarly to Section objects, allows dictionary-like access to
        verdef/verneed entry
    """
    def __init__(self, entry, name=None):
        self.entry = entry
        self.name = name

    def __getitem__(self, name):
        """ Implement dict-like access to entry
        """
        return self.entry[name]


class VersionAuxiliary(object):
    """ Version Auxiliary object - representing an auxiliary entry of a version
        definition or dependency entry

        Similarly to Section objects, allows dictionary-like access to the
        verdaux/vernaux entry
    """
    def __init__(self, entry, name):
        self.entry = entry
        self.name = name

    def __getitem__(self, name):
        """ Implement dict-like access to entries
        """
        return self.entry[name]

class GNUVerNeedTableSection(Section):
    """ ELF SUNW or GNU Version Needed table section.
        Has an associated StringTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, stringtable):
        super(GNUVerNeedTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.stringtable = stringtable
        self._has_indexes = None

    def num_versions(self):
        """ Number of version dependency in the table
        """
        return self['sh_info']

    def has_indexes(self):
        """ Return True if at least one version definition entry has an index
            that is stored in the vna_other field.
            This information is used for symbol versioning
        """
        if self._has_indexes is None:
            self._has_indexes = False
            for _, vernaux_iter in self.iter_versions():
                for vernaux in vernaux_iter:
                    if vernaux['vna_other']:
                        self._has_indexes = True
                        break

        return self._has_indexes
        
    def get_version(self, index):
        """ Get the version information located at index #n in the table
            Return boths the verneed structure and the vernaux structure
            that contains the name of the version
        """
        for verneed, vernaux_iter in self.iter_versions():
            for vernaux in vernaux_iter:
                if vernaux['vna_other'] == index:
                    return verneed, vernaux

        return None


    def _iter_version_auxiliaries(self, entry_offset, count):
        """ Yield all auxiliary entries of a version dependency
        """
        for _ in range(count): 
            entry = struct_parse(
                        self.elfstructs.Elf_Vernaux,
                        self.stream,
                        stream_pos=entry_offset)

            name = self.stringtable.get_string(entry['vna_name'])
            version_aux = VersionAuxiliary(entry, name)
            yield version_aux

            if not entry['vna_next']:
                break

            entry_offset += entry['vna_next']
        

    def iter_versions(self):
        """ Yield all the version dependencies entries in the table 
            Each time it returns the main version dependency structure
            and an iterator to walk through its auxiliaries entries
        """
        entry_offset = self['sh_offset']
        for _ in range(self.num_versions()):
            entry = struct_parse(
                self.elfstructs.Elf_Verneed,
                self.stream,
                stream_pos=entry_offset)

            name = self.stringtable.get_string(entry['vn_file'])
            elf_assert(entry['vn_cnt'] > 0,
                'Expected number of version names to be > 0 for version definition %s' % name)

            verneed = Version(entry, name)
            aux_entries_offset = entry_offset + entry['vn_aux']
            vernaux_iter = self._iter_version_auxiliaries(aux_entries_offset,
                                                          entry['vn_cnt'])
            yield verneed, vernaux_iter

            if not entry['vn_next']:
                break

            entry_offset += entry['vn_next'] 


class GNUVerDefTableSection(Section):
    """ ELF SUNW or GNU Version Definition table section.
        Has an associated StringTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, stringtable):
        super(GNUVerDefTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.stringtable = stringtable

    def num_versions(self):
        """ Number of version definitions in the table
        """
        return self['sh_info']
        
    def get_version(self, index):
        """ Get the version information located at index #n in the table
            Return boths the verdef structure and an iterator to retrieve
            both the version names and dependencies in the form of 
            verdaux entries
        """
        for verdef, verdaux_iter in self.iter_versions():
            if verdef['vd_ndx'] == index:
                return verdef, verdaux_iter

        return None

    def _iter_version_auxiliaries(self, entry_offset, count):
        """ Yield all auxiliary entries of a version definition
        """
        for _ in range(count):
            entry = struct_parse(
                        self.elfstructs.Elf_Verdaux,
                        self.stream,
                        stream_pos=entry_offset)

            name = self.stringtable.get_string(entry['vda_name'])
            vernaux = VersionAuxiliary(entry, name)
            yield vernaux

            if not entry['vda_next']:
                break

            entry_offset += entry['vda_next']
        

    def iter_versions(self):
        """ Yield all the version definition entries in the table 
            Each time it returns the main version definition structure
            and an iterator to walk through its auxiliaries entries
        """
        entry_offset = self['sh_offset']
        for _ in range(self.num_versions()):
            entry = struct_parse(
                self.elfstructs.Elf_Verdef,
                self.stream,
                stream_pos=entry_offset)

            elf_assert(entry['vd_cnt'] > 0,
                'Expected number of version names to be > 0'
                'for version definition at index %i' % entry['vd_ndx'])

            verdef = Version(entry)
            aux_entries_offset = entry_offset + entry['vd_aux']
            verdaux_iter = self._iter_version_auxiliaries(aux_entries_offset,
                                                          entry['vd_cnt'])
            yield verdef, verdaux_iter

            if not entry['vd_next']:
                break

            entry_offset += entry['vd_next'] 


class GNUVerSymTableSection(Section):
    """ ELF SUNW or GNU Versym table section.
        Has an associated SymbolTableSection that's passed in the constructor.
    """
    def __init__(self, header, name, stream, elffile, symboltable):
        super(GNUVerSymTableSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        self.symboltable = symboltable

    def num_symbols(self):
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize']

    def get_symbol(self, n):
        """ Get the symbol at index #n from the table (Symbol object)
            It begins at 1 and not 0 since the first entry is used to
            store the current version of the syminfo table
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.elfstructs.Elf_Versym,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated symbol table
        name = self.symboltable.get_symbol(n).name
        return Symbol(entry, name)

    def iter_symbols(self):
        """ Yield all the symbols in the table
        """
        for i in range(self.num_symbols()):
            yield self.get_symbol(i)

