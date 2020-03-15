#-------------------------------------------------------------------------------
# elftools: elf/structs.py
#
# Encapsulation of Construct structs for parsing an ELF file, adjusted for
# correct endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import (
    UBInt8, UBInt16, UBInt32, UBInt64,
    ULInt8, ULInt16, ULInt32, ULInt64,
    SBInt32, SLInt32, SBInt64, SLInt64,
    Struct, Array, Enum, Padding, BitStruct, BitField, Value, String, CString
    )
from ..common.construct_utils import ULEB128
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
        self.e_type = None
        self.e_machine = None
        self.e_ident_osabi = None

    def __getstate__(self):
        return self.little_endian, self.elfclass, self.e_type, self.e_machine, self.e_ident_osabi

    def __setstate__(self, state):
        self.little_endian, self.elfclass, e_type, e_machine, e_osabi = state
        self.create_basic_structs()
        self.create_advanced_structs(e_type, e_machine, e_osabi)

    def create_basic_structs(self):
        """ Create word-size related structs and ehdr struct needed for
            initial determining of ELF type.
        """
        if self.little_endian:
            self.Elf_byte = ULInt8
            self.Elf_half = ULInt16
            self.Elf_word = ULInt32
            self.Elf_word64 = ULInt64
            self.Elf_addr = ULInt32 if self.elfclass == 32 else ULInt64
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = SLInt32
            self.Elf_xword = ULInt32 if self.elfclass == 32 else ULInt64
            self.Elf_sxword = SLInt32 if self.elfclass == 32 else SLInt64
        else:
            self.Elf_byte = UBInt8
            self.Elf_half = UBInt16
            self.Elf_word = UBInt32
            self.Elf_word64 = UBInt64
            self.Elf_addr = UBInt32 if self.elfclass == 32 else UBInt64
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = SBInt32
            self.Elf_xword = UBInt32 if self.elfclass == 32 else UBInt64
            self.Elf_sxword = SBInt32 if self.elfclass == 32 else SBInt64
        self._create_ehdr()
        self._create_leb128()
        self._create_ntbs()

    def create_advanced_structs(self, e_type=None, e_machine=None, e_ident_osabi=None):
        """ Create all ELF structs except the ehdr. They may possibly depend
            on provided e_type and/or e_machine parsed from ehdr.
        """
        self.e_type = e_type
        self.e_machine = e_machine
        self.e_ident_osabi = e_ident_osabi

        self._create_phdr()
        self._create_shdr()
        self._create_chdr()
        self._create_sym()
        self._create_rel()
        self._create_dyn()
        self._create_sunw_syminfo()
        self._create_gnu_verneed()
        self._create_gnu_verdef()
        self._create_gnu_versym()
        self._create_gnu_abi()
        self._create_note(e_type)
        self._create_stabs()
        self._create_arm_attributes()
        self._create_elf_hash()
        self._create_gnu_hash()

    #-------------------------------- PRIVATE --------------------------------#

    def _create_ehdr(self):
        self.Elf_Ehdr = Struct('Elf_Ehdr',
            Struct('e_ident',
                Array(4, self.Elf_byte('EI_MAG')),
                Enum(self.Elf_byte('EI_CLASS'), **ENUM_EI_CLASS),
                Enum(self.Elf_byte('EI_DATA'), **ENUM_EI_DATA),
                Enum(self.Elf_byte('EI_VERSION'), **ENUM_E_VERSION),
                Enum(self.Elf_byte('EI_OSABI'), **ENUM_EI_OSABI),
                self.Elf_byte('EI_ABIVERSION'),
                Padding(7)
            ),
            Enum(self.Elf_half('e_type'), **ENUM_E_TYPE),
            Enum(self.Elf_half('e_machine'), **ENUM_E_MACHINE),
            Enum(self.Elf_word('e_version'), **ENUM_E_VERSION),
            self.Elf_addr('e_entry'),
            self.Elf_offset('e_phoff'),
            self.Elf_offset('e_shoff'),
            self.Elf_word('e_flags'),
            self.Elf_half('e_ehsize'),
            self.Elf_half('e_phentsize'),
            self.Elf_half('e_phnum'),
            self.Elf_half('e_shentsize'),
            self.Elf_half('e_shnum'),
            self.Elf_half('e_shstrndx'),
        )

    def _create_leb128(self):
        self.Elf_uleb128 = ULEB128

    def _create_ntbs(self):
        self.Elf_ntbs = CString

    def _create_phdr(self):
        p_type_dict = ENUM_P_TYPE_BASE
        if self.e_machine == 'EM_ARM':
            p_type_dict = ENUM_P_TYPE_ARM
        elif self.e_machine == 'EM_AARCH64':
            p_type_dict = ENUM_P_TYPE_AARCH64
        elif self.e_machine == 'EM_MIPS':
            p_type_dict = ENUM_P_TYPE_MIPS

        if self.elfclass == 32:
            self.Elf_Phdr = Struct('Elf_Phdr',
                Enum(self.Elf_word('p_type'), **p_type_dict),
                self.Elf_offset('p_offset'),
                self.Elf_addr('p_vaddr'),
                self.Elf_addr('p_paddr'),
                self.Elf_word('p_filesz'),
                self.Elf_word('p_memsz'),
                self.Elf_word('p_flags'),
                self.Elf_word('p_align'),
            )
        else: # 64
            self.Elf_Phdr = Struct('Elf_Phdr',
                Enum(self.Elf_word('p_type'), **p_type_dict),
                self.Elf_word('p_flags'),
                self.Elf_offset('p_offset'),
                self.Elf_addr('p_vaddr'),
                self.Elf_addr('p_paddr'),
                self.Elf_xword('p_filesz'),
                self.Elf_xword('p_memsz'),
                self.Elf_xword('p_align'),
            )

    def _create_shdr(self):
        """Section header parsing.

        Depends on e_machine because of machine-specific values in sh_type.
        """
        sh_type_dict = ENUM_SH_TYPE_BASE
        if self.e_machine == 'EM_ARM':
            sh_type_dict = ENUM_SH_TYPE_ARM
        elif self.e_machine == 'EM_X86_64':
            sh_type_dict = ENUM_SH_TYPE_AMD64
        elif self.e_machine == 'EM_MIPS':
            sh_type_dict = ENUM_SH_TYPE_MIPS

        self.Elf_Shdr = Struct('Elf_Shdr',
            self.Elf_word('sh_name'),
            Enum(self.Elf_word('sh_type'), **sh_type_dict),
            self.Elf_xword('sh_flags'),
            self.Elf_addr('sh_addr'),
            self.Elf_offset('sh_offset'),
            self.Elf_xword('sh_size'),
            self.Elf_word('sh_link'),
            self.Elf_word('sh_info'),
            self.Elf_xword('sh_addralign'),
            self.Elf_xword('sh_entsize'),
        )

    def _create_chdr(self):
        # Structure of compressed sections header. It is documented in Oracle
        # "Linker and Libraries Guide", Part IV ELF Application Binary
        # Interface, Chapter 13 Object File Format, Section Compression:
        # https://docs.oracle.com/cd/E53394_01/html/E54813/section_compression.html
        fields = [
            Enum(self.Elf_word('ch_type'), **ENUM_ELFCOMPRESS_TYPE),
            self.Elf_xword('ch_size'),
            self.Elf_xword('ch_addralign'),
        ]
        if self.elfclass == 64:
            fields.insert(1, self.Elf_word('ch_reserved'))
        self.Elf_Chdr = Struct('Elf_Chdr', *fields)

    def _create_rel(self):
        # r_info is also taken apart into r_info_sym and r_info_type. This is
        # done in Value to avoid endianity issues while parsing.
        if self.elfclass == 32:
            fields = [self.Elf_xword('r_info'),
                      Value('r_info_sym',
                            lambda ctx: (ctx['r_info'] >> 8) & 0xFFFFFF),
                      Value('r_info_type',
                            lambda ctx: ctx['r_info'] & 0xFF)]
        elif self.e_machine == 'EM_MIPS': # ELF64 MIPS
            fields = [
                # The MIPS ELF64 specification
                # (https://www.linux-mips.org/pub/linux/mips/doc/ABI/elf64-2.4.pdf)
                # provides a non-standard relocation structure definition.
                self.Elf_word('r_sym'),
                self.Elf_byte('r_ssym'),
                self.Elf_byte('r_type3'),
                self.Elf_byte('r_type2'),
                self.Elf_byte('r_type'),

                # Synthetize usual fields for compatibility with other
                # architectures. This allows relocation consumers (including
                # our readelf tests) to work without worrying about MIPS64
                # oddities.
                Value('r_info_sym', lambda ctx: ctx['r_sym']),
                Value('r_info_ssym', lambda ctx: ctx['r_ssym']),
                Value('r_info_type', lambda ctx: ctx['r_type']),
                Value('r_info_type2', lambda ctx: ctx['r_type2']),
                Value('r_info_type3', lambda ctx: ctx['r_type3']),
                Value('r_info',
                      lambda ctx: (ctx['r_sym'] << 32)
                                  | (ctx['r_ssym'] << 24)
                                  | (ctx['r_type3'] << 16)
                                  | (ctx['r_type2'] << 8)
                                  | ctx['r_type']),
            ]
        else: # Other 64 ELFs
            fields = [self.Elf_xword('r_info'),
                      Value('r_info_sym',
                            lambda ctx: (ctx['r_info'] >> 32) & 0xFFFFFFFF),
                      Value('r_info_type',
                            lambda ctx: ctx['r_info'] & 0xFFFFFFFF)]

        self.Elf_Rel = Struct('Elf_Rel',
                              self.Elf_addr('r_offset'),
                              *fields)

        fields_and_addend = fields + [self.Elf_sxword('r_addend')]
        self.Elf_Rela = Struct('Elf_Rela',
                               self.Elf_addr('r_offset'),
                               *fields_and_addend
        )

    def _create_dyn(self):
        d_tag_dict = dict(ENUM_D_TAG_COMMON)
        if self.e_machine in ENUMMAP_EXTRA_D_TAG_MACHINE:
            d_tag_dict.update(ENUMMAP_EXTRA_D_TAG_MACHINE[self.e_machine])
        elif self.e_ident_osabi == 'ELFOSABI_SOLARIS':
            d_tag_dict.update(ENUM_D_TAG_SOLARIS)

        self.Elf_Dyn = Struct('Elf_Dyn',
            Enum(self.Elf_sxword('d_tag'), **d_tag_dict),
            self.Elf_xword('d_val'),
            Value('d_ptr', lambda ctx: ctx['d_val']),
        )

    def _create_sym(self):
        # st_info is hierarchical. To access the type, use
        # container['st_info']['type']
        st_info_struct = BitStruct('st_info',
            Enum(BitField('bind', 4), **ENUM_ST_INFO_BIND),
            Enum(BitField('type', 4), **ENUM_ST_INFO_TYPE))
        # st_other is hierarchical. To access the visibility,
        # use container['st_other']['visibility']
        st_other_struct = BitStruct('st_other',
            Padding(5),
            Enum(BitField('visibility', 3), **ENUM_ST_VISIBILITY))
        if self.elfclass == 32:
            self.Elf_Sym = Struct('Elf_Sym',
                self.Elf_word('st_name'),
                self.Elf_addr('st_value'),
                self.Elf_word('st_size'),
                st_info_struct,
                st_other_struct,
                Enum(self.Elf_half('st_shndx'), **ENUM_ST_SHNDX),
            )
        else:
            self.Elf_Sym = Struct('Elf_Sym',
                self.Elf_word('st_name'),
                st_info_struct,
                st_other_struct,
                Enum(self.Elf_half('st_shndx'), **ENUM_ST_SHNDX),
                self.Elf_addr('st_value'),
                self.Elf_xword('st_size'),
            )

    def _create_sunw_syminfo(self):
        self.Elf_Sunw_Syminfo = Struct('Elf_Sunw_Syminfo',
            Enum(self.Elf_half('si_boundto'), **ENUM_SUNW_SYMINFO_BOUNDTO),
            self.Elf_half('si_flags'),
        )

    def _create_gnu_verneed(self):
        # Structure of "version needed" entries is documented in
        # Oracle "Linker and Libraries Guide", Chapter 13 Object File Format
        self.Elf_Verneed = Struct('Elf_Verneed',
            self.Elf_half('vn_version'),
            self.Elf_half('vn_cnt'),
            self.Elf_word('vn_file'),
            self.Elf_word('vn_aux'),
            self.Elf_word('vn_next'),
        )
        self.Elf_Vernaux = Struct('Elf_Vernaux',
            self.Elf_word('vna_hash'),
            self.Elf_half('vna_flags'),
            self.Elf_half('vna_other'),
            self.Elf_word('vna_name'),
            self.Elf_word('vna_next'),
        )

    def _create_gnu_verdef(self):
        # Structure of "version definition" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 13 Object File Format
        self.Elf_Verdef = Struct('Elf_Verdef',
            self.Elf_half('vd_version'),
            self.Elf_half('vd_flags'),
            self.Elf_half('vd_ndx'),
            self.Elf_half('vd_cnt'),
            self.Elf_word('vd_hash'),
            self.Elf_word('vd_aux'),
            self.Elf_word('vd_next'),
        )
        self.Elf_Verdaux = Struct('Elf_Verdaux',
            self.Elf_word('vda_name'),
            self.Elf_word('vda_next'),
        )

    def _create_gnu_versym(self):
        # Structure of "version symbol" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 13 Object File Format
        self.Elf_Versym = Struct('Elf_Versym',
            Enum(self.Elf_half('ndx'), **ENUM_VERSYM),
        )

    def _create_gnu_abi(self):
        # Structure of GNU ABI notes is documented in
        # https://code.woboq.org/userspace/glibc/csu/abi-note.S.html
        self.Elf_abi = Struct('Elf_abi',
            Enum(self.Elf_word('abi_os'), **ENUM_NOTE_ABI_TAG_OS),
            self.Elf_word('abi_major'),
            self.Elf_word('abi_minor'),
            self.Elf_word('abi_tiny'),
        )

    def _create_note(self, e_type=None):
        # Structure of "PT_NOTE" section
        self.Elf_Nhdr = Struct('Elf_Nhdr',
            self.Elf_word('n_namesz'),
            self.Elf_word('n_descsz'),
            Enum(self.Elf_word('n_type'),
                 **(ENUM_NOTE_N_TYPE if e_type != "ET_CORE"
                    else ENUM_CORE_NOTE_N_TYPE)),
        )

        # A process psinfo structure according to
        # http://elixir.free-electrons.com/linux/v2.6.35/source/include/linux/elfcore.h#L84
        if self.elfclass == 32:
            self.Elf_Prpsinfo = Struct('Elf_Prpsinfo',
                self.Elf_byte('pr_state'),
                String('pr_sname', 1),
                self.Elf_byte('pr_zomb'),
                self.Elf_byte('pr_nice'),
                self.Elf_xword('pr_flag'),
                self.Elf_half('pr_uid'),
                self.Elf_half('pr_gid'),
                self.Elf_half('pr_pid'),
                self.Elf_half('pr_ppid'),
                self.Elf_half('pr_pgrp'),
                self.Elf_half('pr_sid'),
                String('pr_fname', 16),
                String('pr_psargs', 80),
            )
        else: # 64
            self.Elf_Prpsinfo = Struct('Elf_Prpsinfo',
                self.Elf_byte('pr_state'),
                String('pr_sname', 1),
                self.Elf_byte('pr_zomb'),
                self.Elf_byte('pr_nice'),
                Padding(4),
                self.Elf_xword('pr_flag'),
                self.Elf_word('pr_uid'),
                self.Elf_word('pr_gid'),
                self.Elf_word('pr_pid'),
                self.Elf_word('pr_ppid'),
                self.Elf_word('pr_pgrp'),
                self.Elf_word('pr_sid'),
                String('pr_fname', 16),
                String('pr_psargs', 80),
            )

        # A PT_NOTE of type NT_FILE matching the definition in
        # https://chromium.googlesource.com/
        # native_client/nacl-binutils/+/upstream/master/binutils/readelf.c
        # Line 15121
        self.Elf_Nt_File = Struct('Elf_Nt_File',
                                  self.Elf_xword("num_map_entries"),
                                  self.Elf_xword("page_size"),
                                  Array(lambda ctx: ctx.num_map_entries,
                                        Struct('Elf_Nt_File_Entry',
                                             self.Elf_addr('vm_start'),
                                             self.Elf_addr('vm_end'),
                                             self.Elf_offset('page_offset'))),
                                  Array(lambda ctx: ctx.num_map_entries,
                                        CString('filename')))

    def _create_stabs(self):
        # Structure of one stabs entry, see binutils/bfd/stabs.c
        # Names taken from https://sourceware.org/gdb/current/onlinedocs/stabs.html#Overview
        self.Elf_Stabs = Struct('Elf_Stabs',
            self.Elf_word('n_strx'),
            self.Elf_byte('n_type'),
            self.Elf_byte('n_other'),
            self.Elf_half('n_desc'),
            self.Elf_word('n_value'),
        )

    def _create_arm_attributes(self):
        # Structure of a build attributes subsection header. A subsection is
        # either public to all tools that process the ELF file or private to
        # the vendor's tools.
        self.Elf_Attr_Subsection_Header = Struct('Elf_Attr_Subsection',
                                                 self.Elf_word('length'),
                                                 self.Elf_ntbs('vendor_name',
                                                               encoding='utf-8')
        )

        # Structure of a build attribute tag.
        self.Elf_Attribute_Tag = Struct('Elf_Attribute_Tag',
                                        Enum(self.Elf_uleb128('tag'),
                                             **ENUM_ATTR_TAG_ARM)
        )

    def _create_elf_hash(self):
        # Structure of the old SYSV-style hash table header. It is documented
        # in the Oracle "Linker and Libraries Guide", Part IV ELF Application
        # Binary Interface, Chapter 14 Object File Format, Section Hash Table
        # Section:
        # https://docs.oracle.com/cd/E53394_01/html/E54813/chapter6-48031.html

        self.Elf_Hash = Struct('Elf_Hash',
                               self.Elf_word('nbuckets'),
                               self.Elf_word('nchains'),
                               Array(lambda ctx: ctx['nbuckets'], self.Elf_word('buckets')),
                               Array(lambda ctx: ctx['nchains'], self.Elf_word('chains')))

    def _create_gnu_hash(self):
        # Structure of the GNU-style hash table header. Documentation for this
        # table is mostly in the GLIBC source code, a good explanation of the
        # format can be found in this blog post:
        # https://flapenguin.me/2017/05/10/elf-lookup-dt-gnu-hash/
        self.Gnu_Hash = Struct('Gnu_Hash',
                               self.Elf_word('nbuckets'),
                               self.Elf_word('symoffset'),
                               self.Elf_word('bloom_size'),
                               self.Elf_word('bloom_shift'),
                               Array(lambda ctx: ctx['bloom_size'], self.Elf_xword('bloom')),
                               Array(lambda ctx: ctx['nbuckets'], self.Elf_word('buckets')))
