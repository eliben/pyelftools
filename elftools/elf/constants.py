#-------------------------------------------------------------------------------
# elftools: elf/constants.py
#
# Constants and flags, placed into classes for namespacing
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
class SHN_INDICES(object):
    """ Special section indices
    """
    SHN_UNDEF=0
    SHN_LORESERVE=0xff00
    SHN_LOPROC=0xff00
    SHN_HIPROC=0xff1f
    SHN_ABS=0xfff1
    SHN_COMMON=0xfff2
    SHN_HIRESERVE=0xffff


class SH_FLAGS(object):
    """ Flag values for the sh_flags field of section headers
    """
    SHF_WRITE=0x1
    SHF_ALLOC=0x2
    SHF_EXECINSTR=0x4
    SHF_MERGE=0x10
    SHF_STRINGS=0x20
    SHF_INFO_LINK=0x40
    SHF_LINK_ORDER=0x80
    SHF_OS_NONCONFORMING=0x100
    SHF_GROUP=0x200
    SHF_TLS=0x400
    SHF_MASKOS=0x0ff00000
    SHF_EXCLUDE=0x80000000
    SHF_MASKPROC=0xf0000000


class P_FLAGS(object):
    """ Flag values for the p_flags field of program headers
    """
    PF_X=0x1
    PF_W=0x2
    PF_R=0x4
    PF_MASKOS=0x00FF0000
    PF_MASKPROC=0xFF000000


# symbol info flags for entries
# in the .SUNW_syminfo section
class SUNW_SYMINFO_FLAGS(object):
    """ Flags for the si_flags field of entries
        in the .SUNW_syminfo section
    """
    SYMINFO_FLG_DIRECT=0x1
    SYMINFO_FLG_FILTER=0x2
    SYMINFO_FLG_COPY=0x4
    SYMINFO_FLG_LAZYLOAD=0x8
    SYMINFO_FLG_DIRECTBIND=0x10
    SYMINFO_FLG_NOEXTDIRECT=0x20
    SYMINFO_FLG_AUXILIARY=0x40
    SYMINFO_FLG_INTERPOSE=0x80
    SYMINFO_FLG_CAP=0x100
    SYMINFO_FLG_DEFERRED=0x200
