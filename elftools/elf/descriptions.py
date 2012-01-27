#-------------------------------------------------------------------------------
# elftools: elf/descriptions.py
#
# Textual descriptions of the various enums and flags of ELF
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .enums import ENUM_E_VERSION, ENUM_RELOC_TYPE_i386, ENUM_RELOC_TYPE_x64
from .constants import P_FLAGS, SH_FLAGS
from ..common.py3compat import iteritems


def describe_ei_class(x):
    return _DESCR_EI_CLASS.get(x, _unknown)

def describe_ei_data(x):
    return _DESCR_EI_DATA.get(x, _unknown)

def describe_ei_version(x):
    s = '%d' % ENUM_E_VERSION[x]
    if x == 'EV_CURRENT':
        s += ' (current)'
    return s
    
def describe_ei_osabi(x):
    return _DESCR_EI_OSABI.get(x, _unknown)

def describe_e_type(x):
    return _DESCR_E_TYPE.get(x, _unknown)

def describe_e_machine(x):
    return _DESCR_E_MACHINE.get(x, _unknown)

def describe_e_version_numeric(x):
    return '0x%x' % ENUM_E_VERSION[x]

def describe_p_type(x):
    return _DESCR_P_TYPE.get(x, _unknown)

def describe_p_flags(x):
    s = ''
    for flag in (P_FLAGS.PF_R, P_FLAGS.PF_W, P_FLAGS.PF_X):
        s += _DESCR_P_FLAGS[flag] if (x & flag) else ' ' 
    return s

def describe_sh_type(x):
    return _DESCR_SH_TYPE.get(x, _unknown)

def describe_sh_flags(x):
    s = ''
    for flag in (
            SH_FLAGS.SHF_WRITE, SH_FLAGS.SHF_ALLOC, SH_FLAGS.SHF_EXECINSTR,
            SH_FLAGS.SHF_MERGE, SH_FLAGS.SHF_STRINGS, SH_FLAGS.SHF_INFO_LINK,
            SH_FLAGS.SHF_LINK_ORDER, SH_FLAGS.SHF_OS_NONCONFORMING,
            SH_FLAGS.SHF_GROUP, SH_FLAGS.SHF_TLS, SH_FLAGS.SHF_EXCLUDE):
        s += _DESCR_SH_FLAGS[flag] if (x & flag) else ''
    return s

def describe_symbol_type(x):
    return _DESCR_ST_INFO_TYPE.get(x, _unknown)

def describe_symbol_bind(x):
    return _DESCR_ST_INFO_BIND.get(x, _unknown)

def describe_symbol_visibility(x):
    return _DESCR_ST_VISIBILITY.get(x, _unknown)

def describe_symbol_shndx(x):
    return _DESCR_ST_SHNDX.get(x, '%3s' % x)

def describe_reloc_type(x, elffile):
    arch = elffile.get_machine_arch()
    if arch == 'x86':
        return _DESCR_RELOC_TYPE_i386.get(x, _unknown)
    elif arch == 'x64':
        return _DESCR_RELOC_TYPE_x64.get(x, _unknown)
    else:
        return 'unrecognized: %-7x' % (x & 0xFFFFFFFF)


#-------------------------------------------------------------------------------
_unknown = '<unknown>'

    
_DESCR_EI_CLASS = dict(
    ELFCLASSNONE='none',
    ELFCLASS32='ELF32',
    ELFCLASS64='ELF64',
)

_DESCR_EI_DATA = dict(
    ELFDATANONE='none',
    ELFDATA2LSB="2's complement, little endian",
    ELFDATA2MSB="2's complement, big endian",
)

_DESCR_EI_OSABI = dict(
    ELFOSABI_SYSV='UNIX - System V',
    ELFOSABI_HPUX='UNIX - HP-UX',
    ELFOSABI_NETBSD='UNIX - NetBSD',
    ELFOSABI_LINUX='UNIX - Linux',
    ELFOSABI_HURD='UNIX - GNU/Hurd',
    ELFOSABI_SOLARIS='UNIX - Solaris',
    ELFOSABI_AIX='UNIX - AIX',
    ELFOSABI_IRIX='UNIX - IRIX',
    ELFOSABI_FREEBSD='UNIX - FreeBSD',
    ELFOSABI_TRU64='UNIX - TRU64',
    ELFOSABI_MODESTO='Novell - Modesto',
    ELFOSABI_OPENBSD='UNIX - OpenBSD',
    ELFOSABI_OPENVMS='VMS - OpenVMS',
    ELFOSABI_NSK='HP - Non-Stop Kernel',
    ELFOSABI_AROS='AROS',
    ELFOSABI_ARM='ARM',
    ELFOSABI_STANDALONE='Standalone App',
)

_DESCR_E_TYPE = dict(
    ET_NONE='NONE (None)',
    ET_REL='REL (Relocatable file)',
    ET_EXEC='EXEC (Executable file)',
    ET_DYN='DYN (Shared object file)',
    ET_CORE='CORE (Core file)',
    PROC_SPECIFIC='Processor Specific',
)

_DESCR_E_MACHINE = dict(
    EM_NONE='None',
    EM_M32='WE32100',
    EM_SPARC='Sparc',
    EM_386='Intel 80386',
    EM_68K='MC68000',
    EM_88K='MC88000',
    EM_860='Intel 80860',
    EM_MIPS='MIPS R3000',
    EM_S370='IBM System/370',
    EM_MIPS_RS4_BE='MIPS 4000 big-endian',
    EM_IA_64='Intel IA-64',
    EM_X86_64='Advanced Micro Devices X86-64',
    EM_AVR='Atmel AVR 8-bit microcontroller',
    RESERVED='RESERVED',
)

_DESCR_P_TYPE = dict(
    PT_NULL='NULL',
    PT_LOAD='LOAD',
    PT_DYNAMIC='DYNAMIC',
    PT_INTERP='INTERP',
    PT_NOTE='NOTE',
    PT_SHLIB='SHLIB',
    PT_PHDR='PHDR',
    PT_GNU_EH_FRAME='GNU_EH_FRAME',
    PT_GNU_STACK='GNU_STACK',
    PT_GNU_RELRO='GNU_RELRO',
)

_DESCR_P_FLAGS = {
    P_FLAGS.PF_X: 'E',
    P_FLAGS.PF_R: 'R',
    P_FLAGS.PF_W: 'W',
}

_DESCR_SH_TYPE = dict(
    SHT_NULL='NULL',
    SHT_PROGBITS='PROGBITS',
    SHT_SYMTAB='SYMTAB',
    SHT_STRTAB='STRTAB',
    SHT_RELA='RELA',
    SHT_HASH='HASH',
    SHT_DYNAMIC='DYNAMIC',
    SHT_NOTE='NOTE',
    SHT_NOBITS='NOBITS',
    SHT_REL='REL',
    SHT_SHLIB='SHLIB',
    SHT_DYNSYM='DYNSYM',
    SHT_INIT_ARRAY='INIT_ARRAY',
    SHT_FINI_ARRAY='FINI_ARRAY',
    SHT_PREINIT_ARRAY='PREINIT_ARRAY',
    SHT_GNU_HASH='GNU_HASH',
    SHT_GROUP='GROUP',
    SHT_SYMTAB_SHNDX='SYMTAB SECTION INDICIES',
    SHT_GNU_verdef='VERDEF',
    SHT_GNU_verneed='VERNEED',
    SHT_GNU_versym='VERSYM',
    SHT_GNU_LIBLIST='GNU_LIBLIST',
)

_DESCR_SH_FLAGS = {
    SH_FLAGS.SHF_WRITE: 'W',
    SH_FLAGS.SHF_ALLOC: 'A',
    SH_FLAGS.SHF_EXECINSTR: 'X',
    SH_FLAGS.SHF_MERGE: 'M',
    SH_FLAGS.SHF_STRINGS: 'S',
    SH_FLAGS.SHF_INFO_LINK: 'I',
    SH_FLAGS.SHF_LINK_ORDER: 'L',
    SH_FLAGS.SHF_OS_NONCONFORMING: 'O',
    SH_FLAGS.SHF_GROUP: 'G',
    SH_FLAGS.SHF_TLS: 'T',
    SH_FLAGS.SHF_EXCLUDE: 'E',
}

_DESCR_ST_INFO_TYPE = dict(
    STT_NOTYPE='NOTYPE',
    STT_OBJECT='OBJECT',
    STT_FUNC='FUNC',
    STT_SECTION='SECTION',
    STT_FILE='FILE',
    STT_COMMON='COMMON',
    STT_TLS='TLS',
    STT_NUM='NUM',
    STT_RELC='RELC',
    STT_SRELC='SRELC',
)

_DESCR_ST_INFO_BIND = dict(
    STB_LOCAL='LOCAL',
    STB_GLOBAL='GLOBAL',
    STB_WEAK='WEAK',
)

_DESCR_ST_VISIBILITY = dict(
    STV_DEFAULT='DEFAULT',
    STV_INTERNAL='INTERNAL',
    STV_HIDDEN='HIDDEN',
    STD_PROTECTED='PROTECTED',
)

_DESCR_ST_SHNDX = dict(
    SHN_UNDEF='UND',
    SHN_ABS='ABS',
    SHN_COMMON='COM',
)

_DESCR_RELOC_TYPE_i386 = dict(
        (v, k) for k, v in iteritems(ENUM_RELOC_TYPE_i386))

_DESCR_RELOC_TYPE_x64 = dict(
        (v, k) for k, v in iteritems(ENUM_RELOC_TYPE_x64))


