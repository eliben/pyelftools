#------------------------------------------------------------------------------
# elftools: elf/gnuversions.py
#
# ELF sections
#
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#------------------------------------------------------------------------------
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, TypedDict

from ..common.exceptions import ELFError
from ..common.utils import elf_assert, struct_parse
from .dynamic import DynamicSection
from .sections import Section, Symbol

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..construct.core import Struct
    from ..construct.lib.container import Container
    from .elffile import ELFFile
    from .sections import StringTableSection, SymbolTableSection


class SymbolVersion(TypedDict):
    index: str | int
    name: str | None
    filename: str | None
    hidden: bool


class Version:
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
    def __init__(self, entry: Container, name: str | None = None) -> None:
        self.entry = entry
        self.name = name

    def __getitem__(self, name: str) -> Any:
        """ Implement dict-like access to entry
        """
        return self.entry[name]


class VersionAuxiliary:
    """ Version Auxiliary object - representing an auxiliary entry of a version
        definition or dependency entry

        Similarly to Section objects, allows dictionary-like access to the
        verdaux/vernaux entry
    """
    def __init__(self, entry: Container, name: str) -> None:
        self.entry = entry
        self.name = name

    def __getitem__(self, name: str) -> Any:
        """ Implement dict-like access to entries
        """
        return self.entry[name]


class GNUVersionSection(Section):
    """ Common ancestor class for ELF SUNW|GNU Version Needed/Dependency
        sections class which contains shareable code
    """

    def __init__(
        self,
        header: Container,
        name: str,
        elffile: ELFFile,
        stringtable: StringTableSection,
        field_prefix: str,
        version_struct: Struct,
        version_auxiliaries_struct: Struct,
    ) -> None:
        super().__init__(header, name, elffile)
        self.stringtable = stringtable
        self.field_prefix = field_prefix
        self.version_struct = version_struct
        self.version_auxiliaries_struct = version_auxiliaries_struct

    def num_versions(self) -> int:
        """ Number of version entries in the section
        """
        return self['sh_info']

    def _field_name(self, name: str, auxiliary: bool = False) -> str:
        """ Return the real field's name of version or a version auxiliary
            entry
        """
        middle = 'a_' if auxiliary else '_'
        return self.field_prefix + middle + name

    def _iter_version_auxiliaries(
        self,
        entry_offset: int,
        count: int,
    ) -> Iterator[VersionAuxiliary]:
        """ Yield all auxiliary entries of a version entry
        """
        name_field = self._field_name('name', auxiliary=True)
        next_field = self._field_name('next', auxiliary=True)

        for _ in range(count):
            entry = struct_parse(
                        self.version_auxiliaries_struct,
                        self.stream,
                        stream_pos=entry_offset)

            name = self.stringtable.get_string(entry[name_field])
            version_aux = VersionAuxiliary(entry, name)
            yield version_aux

            entry_offset += entry[next_field]

    def iter_versions(self) -> Iterator[tuple[Version, Iterator[VersionAuxiliary]]]:
        """ Yield all the version entries in the section
            Each time it returns the main version structure
            and an iterator to walk through its auxiliaries entries
        """
        aux_field = self._field_name('aux')
        count_field = self._field_name('cnt')
        next_field = self._field_name('next')

        entry_offset = self['sh_offset']
        for _ in range(self.num_versions()):
            entry = struct_parse(
                self.version_struct,
                self.stream,
                stream_pos=entry_offset)

            elf_assert(entry[count_field] > 0,
                f'Expected number of version auxiliary entries ({count_field}) to be > 0'
                f'for the following version entry: {entry!s}')

            version = Version(entry)
            aux_entries_offset = entry_offset + entry[aux_field]
            version_auxiliaries_iter = self._iter_version_auxiliaries(
                    aux_entries_offset, entry[count_field])

            yield version, version_auxiliaries_iter

            entry_offset += entry[next_field]


class GNUVerNeedSection(GNUVersionSection):
    """ ELF SUNW or GNU Version Needed table section.
        Has an associated StringTableSection that's passed in the constructor.
    """
    def __init__(
        self,
        header: Container,
        name: str,
        elffile: ELFFile,
        stringtable: StringTableSection,
    ) -> None:
        super().__init__(
                header, name, elffile, stringtable, 'vn',
                elffile.structs.Elf_Verneed, elffile.structs.Elf_Vernaux)

    def has_indexes(self) -> bool:
        """ Return True if at least one version definition entry has an index
            that is stored in the vna_other field.
            This information is used for symbol versioning
        """
        return self._has_indexes

    @cached_property
    def _has_indexes(self) -> bool:
        return any(
            vernaux['vna_other']
            for _, vernaux_iter in self.iter_versions()
            for vernaux in vernaux_iter
        )

    def iter_versions(self) -> Iterator[tuple[Version, Iterator[VersionAuxiliary]]]:
        for verneed, vernaux in super().iter_versions():
            verneed.name = self.stringtable.get_string(verneed['vn_file'])
            yield verneed, vernaux

    def get_version(self, index: int) -> tuple[Version, VersionAuxiliary] | None:
        """ Get the version information located at index #n in the table
            Return boths the verneed structure and the vernaux structure
            that contains the name of the version
        """
        for verneed, vernaux_iter in self.iter_versions():
            for vernaux in vernaux_iter:
                if vernaux['vna_other'] == index:
                    return verneed, vernaux

        return None


class GNUVerDefSection(GNUVersionSection):
    """ ELF SUNW or GNU Version Definition table section.
        Has an associated StringTableSection that's passed in the constructor.
    """
    def __init__(
        self,
        header: Container,
        name: str,
        elffile: ELFFile,
        stringtable: StringTableSection,
    ) -> None:
        super().__init__(
                header, name, elffile, stringtable, 'vd',
                elffile.structs.Elf_Verdef, elffile.structs.Elf_Verdaux)

    def get_version(self, index: int) -> tuple[Version, Iterator[VersionAuxiliary]] | None:
        """ Get the version information located at index #n in the table
            Return boths the verdef structure and an iterator to retrieve
            both the version names and dependencies in the form of
            verdaux entries
        """
        for verdef, verdaux_iter in self.iter_versions():
            if verdef['vd_ndx'] == index:
                return verdef, verdaux_iter

        return None


class GNUVerSymSection(Section):
    """ ELF SUNW or GNU Versym table section.
        Has an associated SymbolTableSection that's passed in the constructor.
    """
    def __init__(
            self,
            header: Container,
            name: str,
            elffile: ELFFile,
            symboltable: SymbolTableSection,
    ) -> None:
        super().__init__(header, name, elffile)
        self.symboltable = symboltable

    def num_symbols(self) -> int:
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize']

    def get_symbol(self, n: int) -> Symbol:
        """ Get the symbol at index #n from the table (Symbol object)
            It begins at 1 and not 0 since the first entry is used to
            store the current version of the syminfo table
        """
        # Grab the symbol's entry from the stream
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.structs.Elf_Versym,
            self.stream,
            stream_pos=entry_offset)
        # Find the symbol name in the associated symbol table
        name = self.symboltable.get_symbol(n).name
        return Symbol(entry, name)

    @cached_property
    def is_gnu(self) -> bool:
        """ Whether this file uses GNU rather than Solaris versioning.
            GNU versioning is identified by the DT_VERSYM dynamic tag.
        """
        return any(
            tag['d_tag'] == 'DT_VERSYM'
            for section in self.elffile.iter_sections()
            if isinstance(section, DynamicSection)
            for tag in section.iter_tags())

    @cached_property
    def _version_sections(self) -> list[GNUVerDefSection | GNUVerNeedSection]:
        # Version definitions and requirements refer to the same string table
        # as the symbol table linked by this versym section.
        return [
            section for section in self.elffile.iter_sections()
            if isinstance(section, (GNUVerDefSection, GNUVerNeedSection))
            and section['sh_link'] == self.symboltable['sh_link']]

    def get_symbol_version(self, n: int) -> SymbolVersion | None:
        """ Resolve the version of symbol #n in this section's symboltable.

            Return a dict with index, name, filename, and hidden fields, or
            None if n is outside the table. Local and unversioned global
            symbols have indices 'VER_NDX_LOCAL' and 'VER_NDX_GLOBAL' and no
            name or filename. For named versions, filename identifies the
            dependency supplying the version, or is None for a definition
            in this file. hidden is the GNU version-hidden bit, not ELF symbol
            visibility; it is False for Solaris versioning.

            Raise ELFError if a version index has no matching definition or
            requirement. Resolving versions requires section headers.
        """
        if not 0 <= n < self.num_symbols():
            return None

        index = self.get_symbol(n)['ndx']
        hidden = False
        if isinstance(index, int) and self.is_gnu:
            # GNU uses the high bit as a flag; the remaining bits are the
            # index shared with the version definition/requirement tables.
            hidden = bool(index & 0x8000)
            index &= 0x7fff
            if index == 0:
                index = 'VER_NDX_LOCAL'
            elif index == 1:
                index = 'VER_NDX_GLOBAL'

        result: SymbolVersion = {
            'index': index, 'name': None, 'filename': None, 'hidden': hidden}
        if index in ('VER_NDX_LOCAL', 'VER_NDX_GLOBAL'):
            return result

        # Look up the recorded index, which need not be consecutive or bounded
        # by the number of definitions in the section.
        for section in self._version_sections:
            if isinstance(section, GNUVerDefSection):
                definition = section.get_version(index)
                if definition is None:
                    continue
                _, auxiliaries = definition
                result['name'] = next(auxiliaries).name
            else:
                needed = section.get_version(index)
                if needed is None:
                    continue
                requirement, auxiliary = needed
                result['name'] = auxiliary.name
                result['filename'] = requirement.name
            return result

        raise ELFError(f'No version definition or requirement for index {index}')

    def iter_symbols(self) -> Iterator[Symbol]:
        """ Yield all the symbols in the table
        """
        for i in range(self.num_symbols()):
            yield self.get_symbol(i)
