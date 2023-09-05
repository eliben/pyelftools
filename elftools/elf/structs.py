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
    Struct, Array, Enum, Padding, BitStruct,
    BitsInteger, Computed, CString, Switch, Bytes
)
from ..common.construct_utils import ULEB128, CStringBytes
from ..common.utils import roundup
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
        self._create_gnu_property()
        self._create_note(e_type)
        self._create_stabs()
        self._create_attributes_subsection()
        self._create_arm_attributes()
        self._create_riscv_attributes()
        self._create_elf_hash()
        self._create_gnu_hash()

    #-------------------------------- PRIVATE --------------------------------#

    def _create_ehdr(self):
        self.Elf_Ehdr = Struct(
            'e_ident' / Struct(
                'EI_MAG' / Array(4, self.Elf_byte),
                'EI_CLASS' / Enum(self.Elf_byte, **ENUM_EI_CLASS),
                'EI_DATA' / Enum(self.Elf_byte, **ENUM_EI_DATA),
                'EI_VERSION' / Enum(self.Elf_byte, **ENUM_E_VERSION),
                'EI_OSABI' / Enum(self.Elf_byte, **ENUM_EI_OSABI),
                'EI_ABIVERSION' / self.Elf_byte,
                Padding(7)
            ),
            'e_type' / Enum(self.Elf_half, **ENUM_E_TYPE),
            'e_machine' / Enum(self.Elf_half, **ENUM_E_MACHINE),
            'e_version' / Enum(self.Elf_word, **ENUM_E_VERSION),
            'e_entry' / self.Elf_addr,
            'e_phoff' / self.Elf_offset,
            'e_shoff' / self.Elf_offset,
            'e_flags' / self.Elf_word,
            'e_ehsize' / self.Elf_half,
            'e_phentsize' / self.Elf_half,
            'e_phnum' / self.Elf_half,
            'e_shentsize' / self.Elf_half,
            'e_shnum' / self.Elf_half,
            'e_shstrndx' / self.Elf_half,
        )

    def _create_leb128(self):
        self.Elf_uleb128 = ULEB128

    def _create_ntbs(self):
        self.Elf_ntbs = CString('utf8')

    def _create_phdr(self):
        p_type_dict = ENUM_P_TYPE_BASE
        if self.e_machine == 'EM_ARM':
            p_type_dict = ENUM_P_TYPE_ARM
        elif self.e_machine == 'EM_AARCH64':
            p_type_dict = ENUM_P_TYPE_AARCH64
        elif self.e_machine == 'EM_MIPS':
            p_type_dict = ENUM_P_TYPE_MIPS
        elif self.e_machine == 'EM_RISCV':
            p_type_dict = ENUM_P_TYPE_RISCV

        if self.elfclass == 32:
            self.Elf_Phdr = Struct(
                'p_type' / Enum(self.Elf_word, **p_type_dict),
                'p_offset' / self.Elf_offset,
                'p_vaddr' / self.Elf_addr,
                'p_paddr' / self.Elf_addr,
                'p_filesz' / self.Elf_word,
                'p_memsz' / self.Elf_word,
                'p_flags' / self.Elf_word,
                'p_align' / self.Elf_word,
            )
        else: # 64
            self.Elf_Phdr = Struct(
                'p_type' / Enum(self.Elf_word, **p_type_dict),
                'p_flags' / self.Elf_word,
                'p_offset' / self.Elf_offset,
                'p_vaddr' / self.Elf_addr,
                'p_paddr' / self.Elf_addr,
                'p_filesz' / self.Elf_xword,
                'p_memsz' / self.Elf_xword,
                'p_align' / self.Elf_xword,
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
        if self.e_machine == 'EM_RISCV':
            sh_type_dict = ENUM_SH_TYPE_RISCV

        self.Elf_Shdr = Struct(
            'sh_name' / self.Elf_word,
            'sh_type' / Enum(self.Elf_word, **sh_type_dict),
            'sh_flags' / self.Elf_xword,
            'sh_addr' / self.Elf_addr,
            'sh_offset' / self.Elf_offset,
            'sh_size' / self.Elf_xword,
            'sh_link' / self.Elf_word,
            'sh_info' / self.Elf_word,
            'sh_addralign' / self.Elf_xword,
            'sh_entsize' / self.Elf_xword,
        )

    def _create_chdr(self):
        # Structure of compressed sections header. It is documented in Oracle
        # "Linker and Libraries Guide", Part IV ELF Application Binary
        # Interface, Chapter 13 Object File Format, Section Compression:
        # https://docs.oracle.com/cd/E53394_01/html/E54813/section_compression.html
        fields = [
            'ch_type' / Enum(self.Elf_word, **ENUM_ELFCOMPRESS_TYPE),
            'ch_size' / self.Elf_xword,
            'ch_addralign' / self.Elf_xword,
        ]

        if self.elfclass == 64:
            fields.insert(1, 'ch_reserved' / self.Elf_word)

        self.Elf_Chdr = Struct(*fields)

    def _create_rel(self):
        # r_info is also taken apart into r_info_sym and r_info_type. This is
        # done in Value to avoid endianity issues while parsing.
        if self.elfclass == 32:
            fields = [
                'r_info' / self.Elf_xword,
                'r_info_sym' / Computed(lambda ctx: (ctx['r_info'] >> 8) & 0xFFFFFF),
                'r_info_type' / Computed(lambda ctx: ctx['r_info'] & 0xFF)
            ]
        elif self.e_machine == 'EM_MIPS': # ELF64 MIPS
            fields = [
                # The MIPS ELF64 specification
                # (https://www.linux-mips.org/pub/linux/mips/doc/ABI/elf64-2.4.pdf)
                # provides a non-standard relocation structure definition.
                'r_sym' / self.Elf_word,
                'r_ssym' / self.Elf_byte,
                'r_type3' / self.Elf_byte,
                'r_type2' / self.Elf_byte,
                'r_type' / self.Elf_byte,

                # Synthetize usual fields for compatibility with other
                # architectures. This allows relocation consumers (including
                # our readelf tests) to work without worrying about MIPS64
                # oddities.
                'r_info_sym' / Computed(lambda ctx: ctx['r_sym']),
                'r_info_ssym' / Computed(lambda ctx: ctx['r_ssym']),
                'r_info_type' / Computed(lambda ctx: ctx['r_type']),
                'r_info_type2' / Computed(lambda ctx: ctx['r_type2']),
                'r_info_type3' / Computed(lambda ctx: ctx['r_type3']),
                'r_info' / Computed(lambda ctx: (ctx['r_sym'] << 32)
                                  | (ctx['r_ssym'] << 24)
                                  | (ctx['r_type3'] << 16)
                                  | (ctx['r_type2'] << 8)
                                  | ctx['r_type'])
            ]
        else: # Other 64 ELFs
            fields = [
                'r_info' / self.Elf_xword,
                'r_info_sym' / Computed(lambda ctx: (ctx['r_info'] >> 32) & 0xFFFFFFFF),
                'r_info_type' / Computed(lambda ctx: ctx['r_info'] & 0xFFFFFFFF)
            ]

        self.Elf_Rel = Struct(
            'r_offset' / self.Elf_addr,
            *fields
        )

        fields_and_addend = fields + ['r_addend' / self.Elf_sxword]
        self.Elf_Rela = Struct(
            'r_offset' / self.Elf_addr,
            *fields_and_addend
        )

        # Elf32_Relr is typedef'd as Elf32_Word, Elf64_Relr as Elf64_Xword
        # (see the glibc patch, for example:
        # https://sourceware.org/pipermail/libc-alpha/2021-October/132029.html)
        # For us, this is the same as self.Elf_addr (or self.Elf_xword).
        self.Elf_Relr = Struct('r_offset' / self.Elf_addr)

    def _create_dyn(self):
        d_tag_dict = dict(ENUM_D_TAG_COMMON)
        if self.e_machine in ENUMMAP_EXTRA_D_TAG_MACHINE:
            d_tag_dict.update(ENUMMAP_EXTRA_D_TAG_MACHINE[self.e_machine])
        elif self.e_ident_osabi == 'ELFOSABI_SOLARIS':
            d_tag_dict.update(ENUM_D_TAG_SOLARIS)

        self.Elf_Dyn = Struct(
            'd_tag' / Enum(self.Elf_sxword, **d_tag_dict),
            'd_val' / self.Elf_xword,
            'd_ptr' / Computed(lambda ctx: ctx['d_val']),
        )

    def _create_sym(self):
        # st_info is hierarchical. To access the type, use
        # container['st_info']['type']
        st_info_struct = BitStruct(
            'bind' / Enum(BitsInteger(4), **ENUM_ST_INFO_BIND),
            'type' / Enum(BitsInteger(4), **ENUM_ST_INFO_TYPE)
        )
        # st_other is hierarchical. To access the visibility,
        # use container['st_other']['visibility']
        st_other_struct = BitStruct(
            # https://openpowerfoundation.org/wp-content/uploads/2016/03/ABI64BitOpenPOWERv1.1_16July2015_pub4.pdf
            # See 3.4.1 Symbol Values.
            'local' / Enum(BitsInteger(3), **ENUM_ST_LOCAL),
            Padding(2),
            'visibility' / Enum(BitsInteger(3), **ENUM_ST_VISIBILITY)
        )
        if self.elfclass == 32:
            self.Elf_Sym = Struct(
                'st_name' / self.Elf_word,
                'st_value' / self.Elf_addr,
                'st_size' / self.Elf_word,
                'st_info' / st_info_struct,
                'st_other' / st_other_struct,
                'st_shndx' / Enum(self.Elf_half, **ENUM_ST_SHNDX),
            )
        else:
            self.Elf_Sym = Struct(
                'st_name' / self.Elf_word,
                'st_info' / st_info_struct,
                'st_other' / st_other_struct,
                'st_shndx' / Enum(self.Elf_half, **ENUM_ST_SHNDX),
                'st_value' / self.Elf_addr,
                'st_size' / self.Elf_xword,
            )

    def _create_sunw_syminfo(self):
        self.Elf_Sunw_Syminfo = Struct(
            'si_boundto' / Enum(self.Elf_half, **ENUM_SUNW_SYMINFO_BOUNDTO),
            'si_flags' / self.Elf_half,
        )

    def _create_gnu_verneed(self):
        # Structure of "version needed" entries is documented in
        # Oracle "Linker and Libraries Guide", Chapter 13 Object File Format
        self.Elf_Verneed = Struct(
            'vn_version' / self.Elf_half,
            'vn_cnt' / self.Elf_half,
            'vn_file' / self.Elf_word,
            'vn_aux' / self.Elf_word,
            'vn_next' / self.Elf_word,
        )
        self.Elf_Vernaux = Struct(
            'vna_hash' / self.Elf_word,
            'vna_flags' / self.Elf_half,
            'vna_other' / self.Elf_half,
            'vna_name' / self.Elf_word,
            'vna_next' / self.Elf_word,
        )

    def _create_gnu_verdef(self):
        # Structure of "version definition" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 13 Object File Format
        self.Elf_Verdef = Struct(
            'vd_version' / self.Elf_half,
            'vd_flags' / self.Elf_half,
            'vd_ndx' / self.Elf_half,
            'vd_cnt' / self.Elf_half,
            'vd_hash' / self.Elf_word,
            'vd_aux' / self.Elf_word,
            'vd_next' / self.Elf_word,
        )
        self.Elf_Verdaux = Struct(
            'vda_name' / self.Elf_word,
            'vda_next' / self.Elf_word,
        )

    def _create_gnu_versym(self):
        # Structure of "version symbol" entries are documented in
        # Oracle "Linker and Libraries Guide", Chapter 13 Object File Format
        self.Elf_Versym = Struct(
            'ndx' / Enum(self.Elf_half, **ENUM_VERSYM),
        )

    def _create_gnu_abi(self):
        # Structure of GNU ABI notes is documented in
        # https://code.woboq.org/userspace/glibc/csu/abi-note.S.html
        self.Elf_abi = Struct(
            'abi_os' / Enum(self.Elf_word, **ENUM_NOTE_ABI_TAG_OS),
            'abi_major' / self.Elf_word,
            'abi_minor' / self.Elf_word,
            'abi_tiny' / self.Elf_word,
        )

    def _create_gnu_debugaltlink(self):
        self.Elf_debugaltlink = Struct(
            'sup_filename' / CStringBytes,
            'sup_checksum' / Bytes(20),
        )

    def _create_gnu_property(self):
        # Structure of GNU property notes is documented in
        # https://github.com/hjl-tools/linux-abi/wiki/linux-abi-draft.pdf
        def roundup_padding(ctx):
            if self.elfclass == 32:
                return roundup(ctx.pr_datasz, 2) - ctx.pr_datasz
            return roundup(ctx.pr_datasz, 3) - ctx.pr_datasz

        def classify_pr_data(ctx):
            if not isinstance(ctx.pr_type, str):
                return None
            if ctx.pr_type.startswith('GNU_PROPERTY_X86_'):
                return ('GNU_PROPERTY_X86_*', 4, 0)
            return (ctx.pr_type, ctx.pr_datasz, self.elfclass)

        self.Elf_Prop = Struct(
            'pr_type' / Enum(self.Elf_word, **ENUM_NOTE_GNU_PROPERTY_TYPE),
            'pr_datasz' / self.Elf_word,
            'pr_data' / Switch(classify_pr_data, {
                    ('GNU_PROPERTY_STACK_SIZE', 4, 32): self.Elf_word,
                    ('GNU_PROPERTY_STACK_SIZE', 8, 64): self.Elf_word64,
                    ('GNU_PROPERTY_X86_*', 4, 0): self.Elf_word,
                },
                default=Bytes(lambda ctx: ctx.pr_datasz)
            ),
            Padding(roundup_padding)
        )

    def _create_note(self, e_type=None):
        # Structure of "PT_NOTE" section

        self.Elf_ugid = self.Elf_half if self.elfclass == 32 and self.e_machine in {
            'EM_MN10300',
            'EM_ARM',
            'EM_CRIS',
            'EM_CYGNUS_FRV',
            'EM_386',
            'EM_M32R',
            'EM_68K',
            'EM_S390',
            'EM_SH',
            'EM_SPARC',
        } else self.Elf_word

        self.Elf_Nhdr = Struct(
            'n_namesz' / self.Elf_word,
            'n_descsz' / self.Elf_word,
            'n_type' / Enum(self.Elf_word, **(ENUM_NOTE_N_TYPE if e_type != "ET_CORE" else ENUM_CORE_NOTE_N_TYPE)),
        )

        # A process psinfo structure according to
        # http://elixir.free-electrons.com/linux/v2.6.35/source/include/linux/elfcore.h#L84
        if self.elfclass == 32:
            self.Elf_Prpsinfo = Struct(
                'pr_state' / self.Elf_byte,
                'pr_sname' / Bytes(1),
                'pr_zomb' / self.Elf_byte,
                'pr_nice' / self.Elf_byte,
                'pr_flag' / self.Elf_xword,
                'pr_uid' / self.Elf_ugid,
                'pr_gid' / self.Elf_ugid,
                'pr_pid' / self.Elf_word,
                'pr_ppid' / self.Elf_word,
                'pr_pgrp' / self.Elf_word,
                'pr_sid' / self.Elf_word,
                'pr_fname' / Bytes(16),
                'pr_psargs' / Bytes(80),
            )
        else: # 64
            self.Elf_Prpsinfo = Struct(
                'pr_state' / self.Elf_byte,
                'pr_sname' / Bytes(1),
                'pr_zomb' / self.Elf_byte,
                'pr_nice' / self.Elf_byte,
                Padding(4),
                'pr_flag' / self.Elf_xword,
                'pr_uid' / self.Elf_ugid,
                'pr_gid' / self.Elf_ugid,
                'pr_pid' / self.Elf_word,
                'pr_ppid' / self.Elf_word,
                'pr_pgrp' / self.Elf_word,
                'pr_sid' / self.Elf_word,
                'pr_fname' / Bytes(16),
                'pr_psargs' / Bytes(80),
            )

        # A PT_NOTE of type NT_FILE matching the definition in
        # https://chromium.googlesource.com/
        # native_client/nacl-binutils/+/upstream/master/binutils/readelf.c
        # Line 15121
        self.Elf_Nt_File = Struct(
            'num_map_entries' / self.Elf_xword,
            'page_size' / self.Elf_xword,
            'Elf_Nt_File_Entry' / Array(lambda ctx: ctx.num_map_entries,
                Struct(
                    'vm_start' / self.Elf_addr,
                    'vm_end' / self.Elf_addr,
                    'page_offset' / self.Elf_offset
                )
            ),
            'filename' / Array(lambda ctx: ctx.num_map_entries,
                CStringBytes
            )
        )

    def _create_stabs(self):
        # Structure of one stabs entry, see binutils/bfd/stabs.c
        # Names taken from https://sourceware.org/gdb/current/onlinedocs/stabs.html#Overview
        self.Elf_Stabs = Struct(
            'n_strx' / self.Elf_word,
            'n_type' / self.Elf_byte,
            'n_other' / self.Elf_byte,
            'n_desc' / self.Elf_half,
            'n_value' / self.Elf_word,
        )

    def _create_attributes_subsection(self):
        # Structure of a build attributes subsection header. A subsection is
        # either public to all tools that process the ELF file or private to
        # the vendor's tools.
        self.Elf_Attr_Subsection_Header = Struct(
            'length' / self.Elf_word,
            'vendor_name' / self.Elf_ntbs
        )

    def _create_arm_attributes(self):
        # Structure of an ARM build attribute tag.
        self.Elf_Arm_Attribute_Tag = Struct(
            'tag' / Enum(self.Elf_uleb128, **ENUM_ATTR_TAG_ARM)
        )

    def _create_riscv_attributes(self):
        # Structure of a RISC-V build attribute tag.
        self.Elf_RiscV_Attribute_Tag = Struct(
            'tag' / Enum(self.Elf_uleb128, **ENUM_ATTR_TAG_RISCV)
        )

    def _create_elf_hash(self):
        # Structure of the old SYSV-style hash table header. It is documented
        # in the Oracle "Linker and Libraries Guide", Part IV ELF Application
        # Binary Interface, Chapter 14 Object File Format, Section Hash Table
        # Section:
        # https://docs.oracle.com/cd/E53394_01/html/E54813/chapter6-48031.html

        self.Elf_Hash = Struct(
            'nbuckets' / self.Elf_word,
            'nchains' / self.Elf_word,
            'buckets' / Array(lambda ctx: ctx['nbuckets'], self.Elf_word),
            'chains' / Array(lambda ctx: ctx['nchains'], self.Elf_word)
        )

    def _create_gnu_hash(self):
        # Structure of the GNU-style hash table header. Documentation for this
        # table is mostly in the GLIBC source code, a good explanation of the
        # format can be found in this blog post:
        # https://flapenguin.me/2017/05/10/elf-lookup-dt-gnu-hash/
        self.Gnu_Hash = Struct(
            'nbuckets' / self.Elf_word,
            'symoffset' / self.Elf_word,
            'bloom_size' / self.Elf_word,
            'bloom_shift' / self.Elf_word,
            'bloom' / Array(lambda ctx: ctx['bloom_size'], self.Elf_xword),
            'buckets' / Array(lambda ctx: ctx['nbuckets'], self.Elf_word)
        )
