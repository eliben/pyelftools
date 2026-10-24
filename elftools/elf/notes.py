#-------------------------------------------------------------------------------
# elftools: elf/notes.py
#
# ELF notes
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from ..common.utils import bytes2str, roundup, struct_parse
from ..construct import CString
from .enums import ENUM_ANDROID_NOTE_N_TYPE, ENUM_CORE_NOTE_N_TYPE, ENUM_NOTE_N_TYPE

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..construct.lib.container import Container
    from .elffile import ELFFile


# Note type numbers have meaning only within their owner's namespace.
_NOTE_TYPE_NAMES = {
    owner: {value: name for name, value in enum.items() if name != '_default_'}
    for owner, enum in (
        ('GNU', ENUM_NOTE_N_TYPE),
        ('Android', ENUM_ANDROID_NOTE_N_TYPE),
    )
}
_CORE_NOTE_TYPE_NAMES = {
    value: name for name, value in ENUM_CORE_NOTE_N_TYPE.items() if name != '_default_'
}


def iter_notes(elffile: ELFFile, offset: int, size: int) -> Iterator[Container]:
    """ Yield complete notes within a section or segment.

        n_type is a symbolic name for known types in the owner's namespace,
        or the numeric type for unknown types and owners.
    """
    end = offset + size
    nhdr_size = elffile.structs.Elf_Nhdr.sizeof()
    # Note: a note's name and data are 4-byte aligned, but it's possible there's
    # additional padding at the end to satisfy the alignment requirement of the segment.
    while offset + nhdr_size <= end:
        note: Container = struct_parse(
            elffile.structs.Elf_Nhdr,
            elffile.stream,
            stream_pos=offset)
        disk_namesz = roundup(note['n_namesz'], 2)
        disk_descsz = roundup(note['n_descsz'], 2)
        note_end = offset + nhdr_size + disk_namesz + disk_descsz
        # Validate the whole note, including padding, before reading its body.
        if note_end > end:
            break

        name_data = elffile.stream.read(disk_namesz)
        if len(name_data) != disk_namesz:
            break
        if note['n_namesz']:
            note['n_name'] = bytes2str(CString('').parse(name_data))
        else:
            note['n_name'] = None

        note_types = _NOTE_TYPE_NAMES.get(note['n_name'], {})
        if note['n_name'] == 'CORE' and elffile['e_type'] == 'ET_CORE':
            note_types = _CORE_NOTE_TYPE_NAMES
        note['n_type'] = note_types.get(note['n_type'], note['n_type'])

        desc_data = elffile.stream.read(disk_descsz)
        if len(desc_data) != disk_descsz:
            break
        desc_data = desc_data[:note['n_descsz']]
        note['n_descdata'] = desc_data
        # Structured decoders must stay within this descriptor, even when its
        # contents are malformed and more bytes follow in the file.
        if note['n_type'] == 'NT_GNU_ABI_TAG':
            note['n_desc'] = struct_parse(elffile.structs.Elf_abi,
                                          BytesIO(desc_data))
        elif note['n_type'] == 'NT_GNU_BUILD_ID':
            note['n_desc'] = bytes(desc_data).hex()
        elif note['n_type'] == 'NT_GNU_GOLD_VERSION':
            note['n_desc'] = bytes2str(desc_data)
        elif note['n_type'] == 'NT_PRPSINFO':
            note['n_desc'] = struct_parse(elffile.structs.Elf_Prpsinfo,
                                          BytesIO(desc_data))
        elif note['n_type'] == 'NT_FILE':
            note['n_desc'] = struct_parse(elffile.structs.Elf_Nt_File,
                                          BytesIO(desc_data))
        elif note['n_type'] == 'NT_GNU_PROPERTY_TYPE_0':
            off = 0
            desc_stream = BytesIO(desc_data)
            props: list[Container] = []
            while off < len(desc_data):
                p: Container = struct_parse(elffile.structs.Elf_Prop, desc_stream, off)
                off += roundup(p.pr_datasz + 8, 2 if elffile.elfclass == 32 else 3)
                props.append(p)
            note['n_desc'] = props
        else:
            note['n_desc'] = desc_data
        note['n_offset'] = offset
        note['n_size'] = note_end - offset
        offset = note_end
        yield note
