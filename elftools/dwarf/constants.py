#-------------------------------------------------------------------------------
# elftools: dwarf/constants.py
#
# Constants and flags
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self  # 3.11+


class _IntEnum(int, Enum):  # Py3.11: enum.ReprEnum
    def __repr__(self) -> str:
        return int.__str__(self.value)

    @property  # Py3.11+: enum.property
    def FQN(self) -> str:
        return f"{self.__class__.__name__}_{self.name}"


class DW_INL(_IntEnum):
    """Inline codes."""
    not_inlined = 0
    inlined = 1
    declared_not_inlined = 2
    declared_inlined = 3


class DW_LANG(_IntEnum):
    """Source languages."""
    C89 = 0x0001
    C = 0x0002
    Ada83 = 0x0003
    C_plus_plus = 0x0004
    Cobol74 = 0x0005
    Cobol85 = 0x0006
    Fortran77 = 0x0007
    Fortran90 = 0x0008
    Pascal83 = 0x0009
    Modula2 = 0x000a
    Java = 0x000b
    C99 = 0x000c
    Ada95 = 0x000d
    Fortran95 = 0x000e
    PLI = 0x000f
    ObjC = 0x0010
    ObjC_plus_plus = 0x0011
    UPC = 0x0012
    D = 0x0013
    Python = 0x0014
    OpenCL = 0x0015
    Go = 0x0016
    Modula3 = 0x0017
    Haskell = 0x0018
    C_plus_plus_03 = 0x0019
    C_plus_plus_11 = 0x001a
    OCaml = 0x001b
    Rust = 0x001c
    C11 = 0x001d
    Swift = 0x001e
    Julia = 0x001f
    Dylan = 0x0020
    C_plus_plus_14 = 0x0021
    Fortran03 = 0x0022
    Fortran08 = 0x0023
    RenderScript = 0x0024
    BLISS = 0x0025
    Mips_Assembler = 0x8001
    Upc = 0x8765
    HP_Bliss = 0x8003
    HP_Basic91 = 0x8004
    HP_Pascal91 = 0x8005
    HP_IMacro = 0x8006
    HP_Assembler = 0x8007
    GOOGLE_RenderScript = 0x8e57
    BORLAND_Delphi = 0xb000


class DW_ATE(_IntEnum):
    """Encodings."""
    void = 0x0
    address = 0x1
    boolean = 0x2
    complex_float = 0x3
    float = 0x4
    signed = 0x5
    signed_char = 0x6
    unsigned = 0x7
    unsigned_char = 0x8
    imaginary_float = 0x9
    packed_decimal = 0xa
    numeric_string = 0xb
    edited = 0xc
    signed_fixed = 0xd
    unsigned_fixed = 0xe
    decimal_float = 0xf
    UTF = 0x10
    UCS = 0x11
    ASCII = 0x12
    lo_user = 0x80
    hi_user = 0xff
    HP_float80 = 0x80
    HP_complex_float80 = 0x81
    HP_float128 = 0x82
    HP_complex_float128 = 0x83
    HP_floathpintel = 0x84
    HP_imaginary_float80 = 0x85
    HP_imaginary_float128 = 0x86


class DW_ACCESS(_IntEnum):
    """Access."""
    public = 1
    protected = 2
    private = 3


class DW_VIS(_IntEnum):
    """Visibility."""
    local = 1
    exported = 2
    qualified = 3


class DW_VIRTUALITY(_IntEnum):
    """Virtuality."""
    none = 0
    virtual = 1
    pure_virtual = 2


class DW_ID(_IntEnum):
    """ID cases."""
    case_sensitive = 0
    up_case = 1
    down_case = 2
    case_insensitive = 3


class DW_CC(_IntEnum):
    """Calling conventions."""
    normal = 0x1
    program = 0x2
    nocall = 0x3
    pass_by_reference = 0x4
    pass_by_valuee = 0x5


class DW_ORD(_IntEnum):
    """Orderings."""
    row_major = 0
    col_major = 1


class DW_LNS(_IntEnum):
    """Line program opcodes."""
    copy = 0x01
    advance_pc = 0x02
    advance_line = 0x03
    set_file = 0x04
    set_column = 0x05
    negate_stmt = 0x06
    set_basic_block = 0x07
    const_add_pc = 0x08
    fixed_advance_pc = 0x09
    set_prologue_end = 0x0a
    set_epilogue_begin = 0x0b
    set_isa = 0x0c


class DW_LNE(_IntEnum):
    """Line program extended opcodes."""
    end_sequence = 0x01
    set_address = 0x02
    define_file = 0x03
    set_discriminator = 0x04
    lo_user = 0x80
    hi_user = 0xff


class DW_LNCT(_IntEnum):
    """Line program header content types."""
    path = 0x01
    directory_index = 0x02
    timestamp = 0x03
    size = 0x04
    MD5 = 0x05
    lo_user = 0x2000
    LLVM_source = 0x2001
    LLVM_is_MD5 = 0x2002
    hi_user = 0x3fff


class DW_CFA(_IntEnum):
    """
    Call frame instructions.

    Note that the first 3 instructions have the so-called "primary opcode"
    (as described in DWARFv3 7.23), so only their highest 2 bits take part
    in the opcode decoding. They are kept as constants with the low bits masked
    out, and the callframe module knows how to handle this.
    The other instructions use an "extended opcode" encoded just in the low 6
    bits, with the high 2 bits, so these constants are exactly as they would
    appear in an actual file.
    """
    advance_loc = 0b01000000
    offset = 0b10000000
    restore = 0b11000000

    nop = 0x00
    set_loc = 0x01
    advance_loc1 = 0x02
    advance_loc2 = 0x03
    advance_loc4 = 0x04
    offset_extended = 0x05
    restore_extended = 0x06
    undefined = 0x07
    same_value = 0x08
    register = 0x09
    remember_state = 0x0a
    restore_state = 0x0b
    def_cfa = 0x0c
    def_cfa_register = 0x0d
    def_cfa_offset = 0x0e
    def_cfa_expression = 0x0f
    expression = 0x10
    offset_extended_sf = 0x11
    def_cfa_sf = 0x12
    def_cfa_offset_sf = 0x13
    val_offset = 0x14
    val_offset_sf = 0x15
    val_expression = 0x16
    AARCH64_negate_ra_state = 0x2d
    GNU_window_save = 0x2d  # Used on SPARC, not in the corpus
    GNU_args_size = 0x2e

    @classmethod
    def parse_raw_opcode(cls, /, opcode: int, *, __MASK: int = 0b11_00_0000) -> tuple[Self, int] | tuple[Self]:
        """Extract primary or extended opcode from raw byte."""
        if primary := opcode & __MASK:
            return (cls(primary), opcode & ~__MASK)
        return (cls(opcode),)


class DW_UT(_IntEnum):
    """
    Compilation unit types.

    DWARFv5 introduces the "unit_type" field to each CU header, allowing
    individual CUs to indicate whether they're complete, partial, and so forth.
    See DWARFv5 3.1 ("Unit Entries") and 7.5.1 ("Unit Headers").
    """
    compile = 0x01
    type = 0x02
    partial = 0x03
    skeleton = 0x04
    split_compile = 0x05
    split_type = 0x06
    lo_user = 0x80
    hi_user = 0xff


# Add back legacy names `DW_UT_type = DW_UT.type` for `from .constants import *`.
# These are invisible to typing as the members are added dynamically by code!
# Use __members__ to also add aliases like DW_CFA.{AARCH64_negate_ra_state,GNU_window_save}.
globals().update({
    f"{enum_name}_{member_name}": member.value
    for enum_name, enum in globals().items()
    if enum_name.startswith("DW_") and issubclass(enum, _IntEnum)
    for member_name, member in enum.__members__.items()
})
