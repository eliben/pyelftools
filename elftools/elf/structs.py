#-------------------------------------------------------------------------------
# elftools: elf/structs.py
#
# Encapsulation of Construct structs for parsing an ELF file, adjusted for
# correct endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from construct import (
    Int8ub, Int16ub, Int32ub, Int64ub,
    Int8ul, Int16ul, Int32ul, Int64ul,
    Int32sb, Int32sl, Int64sb, Int64sl,
    Struct, Array, Enum, Padding, BitStruct, BitsInteger, Computed,
    )

from .enums import *


class ELFStructs(object):
    """ Accessible attributes:

            Elf_{byte|half|word|word64|addr|offset|sword|xword|xsword}:
                Data chunks, as specified by the ELF standard, adjusted for
                correct endianness and word-size.

            Elf_Ehdr:
                ELF file header

            Elf_Phdr:
                Program header

            Elf_Shdr:
                Section header

            Elf_Sym:
                Symbol table entry

            Elf_Rel, Elf_Rela:
                Entries in relocation sections
    """
    def __init__(self, little_endian=True, elfclass=32):
        assert elfclass == 32 or elfclass == 64
        self.little_endian = little_endian
        self.elfclass = elfclass
        self._create_structs()

    def _create_structs(self):
        if self.little_endian:
            self.Elf_byte = Int8ul
            self.Elf_half = Int16ul
            self.Elf_word = Int32ul
            self.Elf_word64 = Int64ul
            self.Elf_addr = Int32ul if self.elfclass == 32 else Int64ul
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = Int32sl
            self.Elf_xword = Int32ul if self.elfclass == 32 else Int64ul
            self.Elf_sxword = Int32sl if self.elfclass == 32 else Int64sl
        else:
            self.Elf_byte = Int8ub
            self.Elf_half = Int16ub
            self.Elf_word = Int32ub
            self.Elf_word64 = Int64ub
            self.Elf_addr = Int32ub if self.elfclass == 32 else Int64ub
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = Int32sb
            self.Elf_xword = Int32ub if self.elfclass == 32 else Int64ub
            self.Elf_sxword = Int32sb if self.elfclass == 32 else Int64sb

        self._create_ehdr()
        self._create_phdr()
        self._create_shdr()
        self._create_sym()
        self._create_rel()
        self._create_dyn()
        self._create_sunw_syminfo()
        self._create_gnu_verneed()
        self._create_gnu_verdef()
        self._create_gnu_versym()
        self._create_note()
        self._create_stabs()

    def _create_ehdr(self):
        self.Elf_Ehdr = 'Elf_Ehdr'/Struct(
            'e_ident'/Struct(
                'EI_MAG'/Array(4, self.Elf_byte),
                Enum('EI_CLASS'/self.Elf_byte, Pass, **ENUM_EI_CLASS),
                Enum('EI_DATA'/self.Elf_byte, Pass, **ENUM_EI_DATA),
                Enum('EI_VERSION'/self.Elf_byte, Pass, **ENUM_E_VERSION),
                Enum('EI_OSABI'/self.Elf_byte, Pass, **ENUM_EI_OSABI),
                'EI_ABIVERSION'/self.Elf_byte,
                Padding(7)
            ),
            Enum('e_type'/self.Elf_half, Pass, **ENUM_E_TYPE),
            Enum('e_machine'/self.Elf_half, Pass, **ENUM_E_MACHINE),
            Enum('e_version'/self.Elf_word, Pass, **ENUM_E_VERSION),
            'e_entry'/self.Elf_addr,
            'e_phoff'/self.Elf_offset,
            'e_shoff'/self.Elf_offset,
            'e_flags'/self.Elf_word,
            'e_ehsize'/self.Elf_half,
            'e_phentsize'/self.Elf_half,
            'e_phnum'/self.Elf_half,
            'e_shentsize'/self.Elf_half,
            'e_shnum'/self.Elf_half,
            'e_shstrndx'/self.Elf_half,
        )

    def _create_phdr(self):
        if self.elfclass == 32:
            self.Elf_Phdr = 'Elf_Phdr'/Struct(
                Enum('p_type'/self.Elf_word, Pass, **ENUM_P_TYPE),
                'p_offset'/self.Elf_offset,
                'p_vaddr'/self.Elf_addr,
                'p_paddr'/self.Elf_addr,
                'p_filesz'/self.Elf_word,
                'p_memsz'/self.Elf_word,
                'p_flags'/self.Elf_word,
                'p_align'/self.Elf_word,
            )
        else: # 64
            self.Elf_Phdr = 'Elf_Phdr'/Struct(
                Enum('p_type'/self.Elf_word, Pass, **ENUM_P_TYPE),
                'p_flags'/self.Elf_word,
                'p_offset'/self.Elf_offset,
                'p_vaddr'/self.Elf_addr,
                'p_paddr'/self.Elf_addr,
                'p_filesz'/self.Elf_xword,
                'p_memsz'/self.Elf_xword,
                'p_align'/self.Elf_xword,
            )

    def _create_shdr(self):
        self.Elf_Shdr = 'Elf_Shdr'/Struct(
            'sh_name'/self.Elf_word,
            Enum('sh_type'/self.Elf_word, Pass, **ENUM_SH_TYPE),
            'sh_flags'/self.Elf_xword,
            'sh_addr'/self.Elf_addr,
            'sh_offset'/self.Elf_offset,
            'sh_size'/self.Elf_xword,
            'sh_link'/self.Elf_word,
            'sh_info'/self.Elf_word,
            'sh_addralign'/self.Elf_xword,
            'sh_entsize'/self.Elf_xword,
        )

    def _create_rel(self):
        # r_info is also taken apart into r_info_sym and r_info_type.
        # This is done in Computed to avoid endianity issues while parsing.
        if self.elfclass == 32:
            r_info_sym = 'r_info_sym'/Computed(
                lambda ctx: (ctx['r_info'] >> 8) & 0xFFFFFF)
            r_info_type = 'r_info_type'/Computed(
                lambda ctx: ctx['r_info'] & 0xFF)
        else: # 64
            r_info_sym = 'r_info_sym'/Computed(
                lambda ctx: (ctx['r_info'] >> 32) & 0xFFFFFFFF)
            r_info_type = 'r_info_type'/Computed(
                lambda ctx: ctx['r_info'] & 0xFFFFFFFF)

        self.Elf_Rel = 'Elf_Rel'/Struct(
            'r_offset'/self.Elf_addr,
            'r_info'/self.Elf_xword,
            r_info_sym,
            r_info_type,
        )
        self.Elf_Rela = 'Elf_Rela'/Struct(
            'r_offset'/self.Elf_addr,
            'r_info'/self.Elf_xword,
            r_info_sym,
            r_info_type,
            'r_addend'/self.Elf_sxword,
        )

    def _create_dyn(self):
        self.Elf_Dyn = 'Elf_Dyn'/Struct(
            Enum('d_tag'/self.Elf_sxword, Pass, **ENUM_D_TAG),
            'd_val'/self.Elf_xword,
            'd_ptr'/Computed(lambda ctx: ctx['d_val']),
        )

    def _create_sym(self):
        # st_info is hierarchical. To access the type, use
        # container['st_info']['type']
        st_info_struct = 'st_info'/BitStruct(
            Enum('bind'/BitsInteger(4), Pass, **ENUM_ST_INFO_BIND),
            Enum('type'/BitsInteger(4), Pass, **ENUM_ST_INFO_TYPE))
        # st_other is hierarchical. To access the visibility,
        # use container['st_other']['visibility']
        st_other_struct = 'st_other'/BitStruct(
            Padding(5),
            Enum('visibility'/BitsInteger(3), Pass, **ENUM_ST_VISIBILITY))
        if self.elfclass == 32:
            self.Elf_Sym = 'Elf_Sym'/Struct(
                'st_name'/self.Elf_word,
                'st_value'/self.Elf_addr,
                'st_size'/self.Elf_word,
                st_info_struct,
                st_other_struct,
                Enum('st_shndx'/self.Elf_half, Pass, **ENUM_ST_SHNDX),
            )
        else:
            self.Elf_Sym = 'Elf_Sym'/Struct(
                'st_name'/self.Elf_word,
                st_info_struct,
                st_other_struct,
                Enum('st_shndx'/self.Elf_half, Pass, **ENUM_ST_SHNDX),
                'st_value'/self.Elf_addr,
                'st_size'/self.Elf_xword,
            )

    def _create_sunw_syminfo(self):
        self.Elf_Sunw_Syminfo = 'Elf_Sunw_Syminfo'/Struct(
            Enum('si_boundto'/self.Elf_half, Pass, **ENUM_SUNW_SYMINFO_BOUNDTO),
            'si_flags'/self.Elf_half,
        )

    def _create_gnu_verneed(self):
        # Structure of "version needed" entries is documented in
        # Oracle "Linker and Libraries Guide", Chapter 7 Object File Format
        self.Elf_Verneed = 'Elf_Verneed'/Struct(
            'vn_version'/self.Elf_half,
            'vn_cnt'/self.Elf_half,
            'vn_file'/self.Elf_word,
            'vn_aux'/self.Elf_word,
            'vn_next'/self.Elf_word,
        )
        self.Elf_Vernaux = 'Elf_Vernaux'/Struct(
            'vna_hash'/self.Elf_word,
            'vna_flags'/self.Elf_half,
            'vna_other'/self.Elf_half,
            'vna_name'/self.Elf_word,
            'vna_next'/self.Elf_word,
        )

    def _create_gnu_verdef(self):
        # Structure off "version definition" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 7 Object File Format
        self.Elf_Verdef = 'Elf_Verdef'/Struct(
            'vd_version'/self.Elf_half,
            'vd_flags'/self.Elf_half,
            'vd_ndx'/self.Elf_half,
            'vd_cnt'/self.Elf_half,
            'vd_hash'/self.Elf_word,
            'vd_aux'/self.Elf_word,
            'vd_next'/self.Elf_word,
        )
        self.Elf_Verdaux = 'Elf_Verdaux'/Struct(
            'vda_name'/self.Elf_word,
            'vda_next'/self.Elf_word,
        )

    def _create_gnu_versym(self):
        # Structure off "version symbol" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 7 Object File Format
        self.Elf_Versym = 'Elf_Versym'/Struct(
            Enum('ndx'/self.Elf_half, Pass, **ENUM_VERSYM),
        )

    def _create_note(self):
        # Structure of "PT_NOTE" section
        self.Elf_Nhdr = 'Elf_Nhdr'/Struct(
            'n_namesz'/self.Elf_word,
            'n_descsz'/self.Elf_word,
            Enum('n_type'/self.Elf_word, Pass, **ENUM_NOTE_N_TYPE),
        )
        self.Elf_Nhdr_abi = 'Elf_Nhdr_abi'/Struct(
            'abi_os'/Enum(self.Elf_word, Pass, **ENUM_NOTE_ABI_TAG_OS),
            'abi_major'/self.Elf_word,
            'abi_minor'/self.Elf_word,
            'abi_tiny'/self.Elf_word,
        )

    def _create_stabs(self):
        # Structure of one stabs entry, see binutils/bfd/stabs.c
        # Names taken from https://sourceware.org/gdb/current/onlinedocs/stabs.html#Overview
        self.Elf_Stabs = 'Elf_Stabs'/Struct(
            'n_strx'/self.Elf_word,
            'n_type'/self.Elf_byte,
            'n_other'/self.Elf_byte,
            'n_desc'/self.Elf_half,
            'n_value'/self.Elf_word,
        )
