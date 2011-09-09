#-------------------------------------------------------------------------------
# elftools: elf/descriptions.py
#
# Textual descriptions of the various enums and flags of ELF
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .enums import ENUM_E_VERSION


def describe_ei_class(x):
    return _DESCR_EI_CLASS.get(x, _unknown())

def describe_ei_data(x):
    return _DESCR_EI_DATA.get(x, _unknown())

def describe_ei_version(x):
    s = '%d' % ENUM_E_VERSION[x]
    if x == 'EV_CURRENT':
        s += ' (current)'
    return s
    
def describe_ei_osabi(x):
    return _DESCR_EI_OSABI.get(x, _unknown())

def describe_e_type(x):
    return _DESCR_E_TYPE.get(x, _unknown())

def describe_e_machine(x):
    return _DESCR_E_MACHINE.get(x, _unknown())

def describe_e_version_numeric(x):
    return '0x%x' % ENUM_E_VERSION[x]


#-------------------------------------------------------------------------------
def _unknown():
    return '<unknown>'

    
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
