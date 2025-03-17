#-------------------------------------------------------------------------------
# elftools: elf/sections.py
#
# ELF sections
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import annotations

from typing import IO, TYPE_CHECKING, Any, Literal, overload

from ..common.exceptions import ELFCompressionError
from ..common.utils import struct_parse, elf_assert, parse_cstring_from_stream
from collections import defaultdict
from .constants import SH_FLAGS
from .notes import iter_notes

import zlib
from elftools.construct.lib.container import Container

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..construct.lib.container import Container
    from .elffile import ELFFile
    from .structs import ELFStructs


class Section:
    """ Base class for ELF sections. Also used for all sections types that have
        no special functionality.

        Allows dictionary-like access to the section header. For example:
         > sec = Section(...)
         > sec['sh_type']  # section type
    """
    def __init__(self, header: Container, name: str, elffile: ELFFile) -> None:
        self.header = header
        self.name = name
        self.elffile = elffile
        self.stream: IO[bytes] = self.elffile.stream
        self.structs: ELFStructs = self.elffile.structs
        self._compressed: int = header['sh_flags'] & SH_FLAGS.SHF_COMPRESSED

        if self.compressed:
            # Read the compression header now to know about the size/alignment
            # of the decompressed data.
            header = struct_parse(self.structs.Elf_Chdr,
                                  self.stream,
                                  stream_pos=self['sh_offset'])
            self._compression_type: str = header['ch_type']
            self._decompressed_size: int = header['ch_size']
            self._decompressed_align: int = header['ch_addralign']
        else:
            self._decompressed_size = header['sh_size']
            self._decompressed_align = header['sh_addralign']

    @property
    def compressed(self) -> int:
        """ Is this section compressed?
        """
        return self._compressed

    @property
    def data_size(self) -> int:
        """ Return the logical size for this section's data.

        This can be different from the .sh_size header field when the section
        is compressed.
        """
        return self._decompressed_size

    @property
    def data_alignment(self) -> int:
        """ Return the logical alignment for this section's data.

        This can be different from the .sh_addralign header field when the
        section is compressed.
        """
        return self._decompressed_align

    def data(self) -> bytes:
        """ The section data from the file.

        Note that data is decompressed if the stored section data is
        compressed.
        """
        # If this section is NOBITS, there is no data. provide a dummy answer
        if self.header['sh_type'] == 'SHT_NOBITS':
            return b'\0'*self.data_size

        # If this section is compressed, deflate it
        if self.compressed:
            c_type = self._compression_type
            if c_type == 'ELFCOMPRESS_ZLIB':
                # Read the data to decompress starting right after the
                # compression header until the end of the section.
                hdr_size: int = self.structs.Elf_Chdr.sizeof()
                self.stream.seek(self['sh_offset'] + hdr_size)
                compressed: bytes = self.stream.read(self['sh_size'] - hdr_size)

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

    def is_null(self) -> bool:
        """ Is this a null section?
        """
        return False

    @overload
    def __getitem__(self, name: Literal["sh_addr", "sh_entsize", "sh_flags", "sh_offset", "sh_size"]) -> int: ...
    @overload
    def __getitem__(self, name: Literal["st_name", "sh_type"]) -> str: ...
    @overload
    def __getitem__(self, name: str) -> Any: ...
    def __getitem__(self, name: str) -> Any:
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def __eq__(self, other: object) -> bool:
        try:
            return self.header == other.header  # type: ignore[attr-defined]
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash(self.header)


class NullSection(Section):
    """ ELF NULL section
    """
    def is_null(self) -> bool:
        return True


class StringTableSection(Section):
    """ ELF string table section.
    """
    def get_string(self, offset: int) -> str:
        """ Get the string stored at the given offset in this string table.
        """
        table_offset = self['sh_offset']
        s = parse_cstring_from_stream(self.stream, table_offset + offset)
        return s.decode('utf-8', errors='replace') if s else ''


class SymbolTableIndexSection(Section):
    """ A section containing the section header table indices corresponding
        to symbols in the linked symbol table. This section has to exist if the
        symbol table contains an entry with a section header index set to
        SHN_XINDEX (0xffff). The format of the section is described at
        https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.sheader.html
    """
    def __init__(self, header: Container, name: str, elffile: ELFFile, symboltable: Container) -> None:
        super().__init__(header, name, elffile)
        self.symboltable = symboltable

    def get_section_index(self, n: int) -> int:
        """ Get the section header table index for the symbol with index #n.
            The section contains an array of Elf32_word values with one entry
            for every symbol in the associated symbol table.
        """
        return struct_parse(self.elffile.structs.Elf_word(''), self.stream,
                            self['sh_offset'] + n * self['sh_entsize'])


class SymbolTableSection(Section):
    """ ELF symbol table section. Has an associated StringTableSection that's
        passed in the constructor.
    """
    def __init__(self, header: Container, name: str, elffile: ELFFile, stringtable: StringTableSection) -> None:
        super().__init__(header, name, elffile)
        self.stringtable = stringtable
        elf_assert(self['sh_entsize'] > 0,
                'Expected entry size of section %r to be > 0' % name)
        elf_assert(self['sh_size'] % self['sh_entsize'] == 0,
                'Expected section size to be a multiple of entry size in section %r' % name)
        self._symbol_name_map: dict[str, list[int]] | None = None

    def num_symbols(self) -> int:
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize']

    def get_symbol(self, n: int) -> Symbol:
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

    def get_symbol_by_name(self, name: str) -> list[Symbol] | None:
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

    def iter_symbols(self) -> Iterator[Symbol]:
        """ Yield all the symbols in the table
        """
        for i in range(self.num_symbols()):
            yield self.get_symbol(i)


class Symbol:
    """ Symbol object - representing a single symbol entry from a symbol table
        section.

        Similarly to Section objects, allows dictionary-like access to the
        symbol entry.
    """
    def __init__(self, entry: Container, name: str) -> None:
        self.entry = entry
        self.name = name

    def __getitem__(self, name: str) -> Any:
        """ Implement dict-like access to entries
        """
        return self.entry[name]


class SUNWSyminfoTableSection(Section):
    """ ELF .SUNW Syminfo table section.
        Has an associated SymbolTableSection that's passed in the constructor.
    """
    def __init__(self, header: Container, name: str, elffile: ELFFile, symboltable: SymbolTableSection) -> None:
        super().__init__(header, name, elffile)
        self.symboltable = symboltable

    def num_symbols(self) -> int:
        """ Number of symbols in the table
        """
        return self['sh_size'] // self['sh_entsize'] - 1

    def get_symbol(self, n: int) -> Symbol:
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

    def iter_symbols(self) -> Iterator[Symbol]:
        """ Yield all the symbols in the table
        """
        for i in range(1, self.num_symbols() + 1):
            yield self.get_symbol(i)


class NoteSection(Section):
    """ ELF NOTE section. Knows how to parse notes.
    """
    def iter_notes(self) -> Iterator[Container]:
        """ Yield all the notes in the section.  Each result is a dictionary-
            like object with "n_name", "n_type", and "n_desc" fields, amongst
            others.
        """
        return iter_notes(self.elffile, self['sh_offset'], self['sh_size'])


class StabSection(Section):
    """ ELF stab section.
    """
    def iter_stabs(self) -> Iterator[Container]:
        """ Yield all stab entries.  Result type is ELFStructs.Elf_Stabs.
        """
        offset: int = self['sh_offset']
        size: int = self['sh_size']
        end = offset + size
        while offset < end:
            stabs = struct_parse(
                self.structs.Elf_Stabs,
                self.stream,
                stream_pos=offset)
            stabs['n_offset'] = offset
            offset += self.structs.Elf_Stabs.sizeof()
            self.stream.seek(offset)
            yield stabs

class Attribute:
    """ Attribute object - representing a build attribute of ELF files.
    """
    def __init__(self, tag):
        self._tag = tag
        self.extra = None

    @property
    def tag(self) -> str:
        return self._tag['tag']

    def __repr__(self) -> str:
        s = '<%s (%s): %r>' % \
            (self.__class__.__name__, self.tag, self.value)
        s += ' %s' % self.extra if self.extra is not None else ''
        return s


class AttributesSubsubsection(Section):
    """ Subsubsection of an ELF attribute section's subsection.
    """
    def __init__(self, stream, structs, offset, attribute):
        self.stream = stream
        self.offset = offset
        self.structs = structs
        self.attribute = attribute

        self.header = self.attribute(self.structs, self.stream)

        self.attr_start = self.stream.tell()

    def iter_attributes(self, tag: str | None = None) -> Iterator[Attribute]:
        """ Yield all attributes (limit to |tag| if specified).
        """
        for attribute in self._make_attributes():
            if tag is None or attribute.tag == tag:
                yield attribute

    @property
    def num_attributes(self) -> int:
        """ Number of attributes in the subsubsection.
        """
        return sum(1 for _ in self.iter_attributes()) + 1

    @property
    def attributes(self) -> list[Attribute]:
        """ List of all attributes in the subsubsection.
        """
        return [self.header, *(self.iter_attributes())]

    def _make_attributes(self) -> Iterator[Attribute]:
        """ Create all attributes for this subsubsection except the first one
            which is the header.
        """
        end = self.offset + self.header.value

        self.stream.seek(self.attr_start)

        while self.stream.tell() != end:
            yield self.attribute(self.structs, self.stream)

    def __repr__(self) -> str:
        s = "<%s (%s): %d bytes>"
        return s % (self.__class__.__name__,
                    self.header.tag[4:], self.header.value)


class AttributesSubsection(Section):
    """ Subsection of an ELF attributes section.
    """
    def __init__(self, stream, structs, offset, header, subsubsection):
        self.stream = stream
        self.offset = offset
        self.structs = structs
        self.subsubsection = subsubsection

        self.header = struct_parse(header, self.stream, self.offset)

        self.subsubsec_start = self.stream.tell()

    def iter_subsubsections(self, scope: str | None = None) -> Iterator[AttributesSubsubsection]:
        """ Yield all subsubsections (limit to |scope| if specified).
        """
        for subsubsec in self._make_subsubsections():
            if scope is None or subsubsec.header.tag == scope:
                yield subsubsec

    @property
    def num_subsubsections(self) -> int:
        """ Number of subsubsections in the subsection.
        """
        return sum(1 for _ in self.iter_subsubsections())

    @property
    def subsubsections(self) -> list[AttributesSubsubsection]:
        """ List of all subsubsections in the subsection.
        """
        return list(self.iter_subsubsections())

    def _make_subsubsections(self) -> Iterator[AttributesSubsubsection]:
        """ Create all subsubsections for this subsection.
        """
        end = self.offset + self['length']

        self.stream.seek(self.subsubsec_start)

        while self.stream.tell() != end:
            subsubsec = self.subsubsection(self.stream,
                                           self.structs,
                                           self.stream.tell())
            self.stream.seek(self.subsubsec_start + subsubsec.header.value)
            yield subsubsec

    def __getitem__(self, name: str) -> Any:
        """ Implement dict-like access to header entries.
        """
        return self.header[name]

    def __repr__(self) -> str:
        s = "<%s (%s): %d bytes>"
        return s  % (self.__class__.__name__,
                     self.header['vendor_name'], self.header['length'])


class AttributesSection(Section):
    """ ELF attributes section.
    """
    def __init__(self, header, name, elffile, subsection):
        super().__init__(header, name, elffile)
        self.subsection = subsection

        fv: int = struct_parse(self.structs.Elf_byte('format_version'),
                          self.stream,
                          self['sh_offset'])

        elf_assert(chr(fv) == 'A',
                   "Unknown attributes version %s, expecting 'A'." % chr(fv))

        self.subsec_start = self.stream.tell()

    def iter_subsections(self, vendor_name: str | None = None) -> Iterator[AttributesSubsection]:
        """ Yield all subsections (limit to |vendor_name| if specified).
        """
        for subsec in self._make_subsections():
            if vendor_name is None or subsec['vendor_name'] == vendor_name:
                yield subsec

    @property
    def num_subsections(self) -> int:
        """ Number of subsections in the section.
        """
        return sum(1 for _ in self.iter_subsections())

    @property
    def subsections(self) -> list[AttributesSubsection]:
        """ List of all subsections in the section.
        """
        return list(self.iter_subsections())

    def _make_subsections(self) -> Iterator[AttributesSubsection]:
        """ Create all subsections for this section.
        """
        end = self['sh_offset'] + self.data_size

        self.stream.seek(self.subsec_start)

        while self.stream.tell() != end:
            subsec = self.subsection(self.stream,
                                     self.structs,
                                     self.stream.tell())
            self.stream.seek(self.subsec_start + subsec['length'])
            yield subsec


class ARMAttribute(Attribute):
    """ ARM attribute object - representing a build attribute of ARM ELF files.
    """
    def __init__(self, structs: ELFStructs, stream: IO[bytes]) -> None:
        super().__init__(
            struct_parse(structs.Elf_Arm_Attribute_Tag, stream))

        if self.tag in ('TAG_FILE', 'TAG_SECTION', 'TAG_SYMBOL'):
            self.value = struct_parse(structs.Elf_word('value'), stream)

            if self.tag != 'TAG_FILE':
                self.extra: list[int] = []  # type: ignore[assignment]
                s_number: int = struct_parse(structs.Elf_uleb128('s_number'), stream)

                while s_number != 0:
                    self.extra.append(s_number)
                    s_number = struct_parse(structs.Elf_uleb128('s_number'),
                                            stream)

        elif self.tag in ('TAG_CPU_RAW_NAME', 'TAG_CPU_NAME', 'TAG_CONFORMANCE'):
            self.value = struct_parse(structs.Elf_ntbs('value',
                                                       encoding='utf-8'),
                                      stream)

        elif self.tag == 'TAG_COMPATIBILITY':
            self.value = struct_parse(structs.Elf_uleb128('value'), stream)
            self.extra = struct_parse(structs.Elf_ntbs('vendor_name',
                                                       encoding='utf-8'),
                                      stream)

        elif self.tag == 'TAG_ALSO_COMPATIBLE_WITH':
            self.value = ARMAttribute(structs, stream)

            if type(self.value.value) is not str:
                nul: int = struct_parse(structs.Elf_byte('nul'), stream)
                elf_assert(nul == 0,
                           "Invalid terminating byte %r, expecting NUL." % nul)

        else:
            self.value = struct_parse(structs.Elf_uleb128('value'), stream)


class ARMAttributesSubsubsection(AttributesSubsubsection):
    """ Subsubsection of an ELF .ARM.attributes section's subsection.
    """
    def __init__(self, stream, structs, offset):
        super().__init__(
            stream, structs, offset, ARMAttribute)


class ARMAttributesSubsection(AttributesSubsection):
    """ Subsection of an ELF .ARM.attributes section.
    """
    def __init__(self, stream, structs, offset):
        super().__init__(
            stream, structs, offset,
            structs.Elf_Attr_Subsection_Header,
            ARMAttributesSubsubsection)


class ARMAttributesSection(AttributesSection):
    """ ELF .ARM.attributes section.
    """
    def __init__(self, header, name, elffile):
        super().__init__(
            header, name, elffile, ARMAttributesSubsection)


class RISCVAttribute(Attribute):
    """ Attribute of an ELF .riscv.attributes section.
    """
    def __init__(self, structs: ELFStructs, stream: IO[bytes]) -> None:
        super().__init__(
            struct_parse(structs.Elf_RiscV_Attribute_Tag, stream))

        if self.tag in ('TAG_FILE', 'TAG_SECTION', 'TAG_SYMBOL'):
            self.value = struct_parse(structs.Elf_word('value'), stream)

            if self.tag != 'TAG_FILE':
                self.extra: list[int] = []  # type: ignore[assignment]
                s_number: int = struct_parse(structs.Elf_uleb128('s_number'), stream)

                while s_number != 0:
                    self.extra.append(s_number)
                    s_number = struct_parse(structs.Elf_uleb128('s_number'),
                                            stream)

        elif self.tag == 'TAG_ARCH':
            self.value = struct_parse(structs.Elf_ntbs('value',
                                                       encoding='utf-8'),
                                      stream)

        else:
            self.value = struct_parse(structs.Elf_uleb128('value'), stream)


class RISCVAttributesSubsubsection(AttributesSubsubsection):
    """ Subsubsection of an ELF .riscv.attributes subsection.
    """
    def __init__(self, stream, structs, offset):
        super().__init__(
            stream, structs, offset, RISCVAttribute)


class RISCVAttributesSubsection(AttributesSubsection):
    """ Subsection of an ELF .riscv.attributes section.
    """
    def __init__(self, stream, structs, offset):
        super().__init__(
            stream, structs, offset,
            structs.Elf_Attr_Subsection_Header,
            RISCVAttributesSubsubsection)


class RISCVAttributesSection(AttributesSection):
    """ ELF .riscv.attributes section.
    """
    def __init__(self, header, name, elffile):
        super().__init__(
            header, name, elffile, RISCVAttributesSubsection)
