#-------------------------------------------------------------------------------
# elftools: dwarf/descriptions.py
#
# Textual descriptions of the various values and enums of DWARF
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import defaultdict

from .constants import *


def describe_attr_value(attrname, attr, die, section_offset):
    """ Given an attribute (attrname is the name, attr is the AttributeValue),
        return the textual representation of its value, suitable for tools like
        readelf.
        
        To cover all cases, this function needs some extra arguments:

        die: the DIE this attribute was extracted from
        section_offset: offset in the stream of the section the DIE belongs to
    """
    descr_func = _ATTR_DESCRIPTION_MAP[attr.form]
    val_description = descr_func(attr, die, section_offset)
    
    # For some attributes we can display further information
    extra_info_func = _EXTRA_INFO_DESCRIPTION_MAP[attrname]
    extra_info = extra_info_func(attr, die, section_offset)
    return str(val_description) + '\t' + extra_info    


#-------------------------------------------------------------------------------

def _describe_attr_ref(attr, die, section_offset):
    return '<0x%x>' % (attr.value + die.cu.cu_offset - section_offset)

def _describe_attr_value_passthrough(attr, die, section_offset):
    return attr.value

def _describe_attr_hex(attr, die, section_offset):
    return '0x%x' % (attr.value)

def _describe_attr_hex_addr(attr, die, section_offset):
    return '<0x%x>' % (attr.value)

def _describe_attr_split_64bit(attr, die, section_offset):
    low_word = attr.value & 0xFFFFFFFF
    high_word = (attr.value >> 32) & 0xFFFFFFFF
    return '0x%x 0x%x' % (low_word, high_word)

def _describe_attr_strp(attr, die, section_offset):
    return '(indirect string, offset: 0x%x): %s' % (attr.raw_value, attr.value)

def _describe_attr_debool(attr, die, section_offset):
    """ To be consistent with readelf, generate 1 for True flags, 0 for False
        flags.
    """
    return '1' if attr.value else '0'

def _describe_attr_block(attr, die, section_offset):
    s = '%s byte block: ' % len(attr.value)
    s += ' '.join('%x' % item for item in attr.value)
    return s
    

_ATTR_DESCRIPTION_MAP = defaultdict(
    lambda: _describe_attr_value_passthrough, # default_factory
    
    DW_FORM_ref1=_describe_attr_ref,
    DW_FORM_ref2=_describe_attr_ref,
    DW_FORM_ref4=_describe_attr_ref,
    DW_FORM_ref8=_describe_attr_split_64bit,
    DW_FORM_ref_udata=_describe_attr_ref,        
    DW_FORM_ref_addr=_describe_attr_hex_addr,
    DW_FORM_data4=_describe_attr_hex,
    DW_FORM_data8=_describe_attr_split_64bit,
    DW_FORM_addr=_describe_attr_hex,
    DW_FORM_sec_offset=_describe_attr_hex,
    DW_FORM_flag=_describe_attr_debool,
    DW_FORM_data1=_describe_attr_value_passthrough,
    DW_FORM_data2=_describe_attr_value_passthrough,
    DW_FORM_sdata=_describe_attr_value_passthrough,
    DW_FORM_udata=_describe_attr_value_passthrough,
    DW_FORM_string=_describe_attr_value_passthrough,
    DW_FORM_strp=_describe_attr_strp,
    DW_FORM_block1=_describe_attr_block,
    DW_FORM_block2=_describe_attr_block,
    DW_FORM_block4=_describe_attr_block,
    DW_FORM_block=_describe_attr_block,
)



def _describe_empty(attr, die, section_offset):
    return ''

def _describe_dw_inl_extra(attr, die, section_offset):
    return _DESCR_DW_INL.get(
        attr.value,
        '  (Unknown inline attribute value: %x)' % attr.value)

def _describe_dw_lang_extra(attr, die, section_offset):
    return _DESCR_DW_LANG.get(
        attr.value,
        '  (Unknown: %x)' % attr.value)

def _describe_dw_ate_extra(attr, die, section_offset):
    return _DESCR_DW_ATE.get(
        attr.value,
        '  (unknown type)')


_EXTRA_INFO_DESCRIPTION_MAP = defaultdict(
    lambda: _describe_empty, # default_factory
    
    DW_AT_inline=_describe_dw_inl_extra,
    DW_AT_language=_describe_dw_lang_extra,
    DW_AT_encoding=_describe_dw_ate_extra,
)


_DESCR_DW_INL = {
    DW_INL_not_inlined: '(not inlined)',
    DW_INL_inlined: '(inlined)',
    DW_INL_declared_not_inlined: '(declared as inline but ignored)',
    DW_INL_declared_inlined: '(declared as inline and inlined)',
}

_DESCR_DW_LANG = {
    DW_LANG_C89: '(ANSI C)',
    DW_LANG_C: '(non-ANSI C)',
    DW_LANG_Ada83: '(Ada)',
    DW_LANG_C_plus_plus: '(C++)',
    DW_LANG_Cobol74: '(Cobol 74)',
    DW_LANG_Cobol85: '(Cobol 85)',
    DW_LANG_Fortran77: '(FORTRAN 77)',
    DW_LANG_Fortran90: '(Fortran 90)',
    DW_LANG_Pascal83: '(ANSI Pascal)',
    DW_LANG_Modula2: '(Modula 2)',
    DW_LANG_Java: '(Java)',
    DW_LANG_C99: '(ANSI C99)',
    DW_LANG_Ada95: '(ADA 95)',
    DW_LANG_Fortran95: '(Fortran 95)',
    DW_LANG_PLI: '(PLI)',
    DW_LANG_ObjC: '(Objective C)',
    DW_LANG_ObjC_plus_plus: '(Objective C++)',
    DW_LANG_UPC: '(Unified Parallel C)',
    DW_LANG_D: '(D)',
    DW_LANG_Python: '(Python)',
    DW_LANG_Mips_Assembler: '(MIPS assembler)',
    DW_LANG_Upc: '(nified Parallel C)',
    DW_LANG_HP_Bliss: '(HP Bliss)',
    DW_LANG_HP_Basic91: '(HP Basic 91)',
    DW_LANG_HP_Pascal91: '(HP Pascal 91)',
    DW_LANG_HP_IMacro: '(HP IMacro)',
    DW_LANG_HP_Assembler: '(HP assembler)',
}

_DESCR_DW_ATE = {
    DW_ATE_void: '(void)',
    DW_ATE_address: '(machine address)',
    DW_ATE_boolean: '(boolean)',
    DW_ATE_complex_float: '(complex float)',
    DW_ATE_float: '(float)',
    DW_ATE_signed: '(signed)',
    DW_ATE_signed_char: '(signed char)',
    DW_ATE_unsigned: '(unsigned)',
    DW_ATE_unsigned_char: '(unsigned char)',
    DW_ATE_imaginary_float: '(imaginary float)',
    DW_ATE_decimal_float: '(decimal float)',
    DW_ATE_packed_decimal: '(packed_decimal)',
    DW_ATE_numeric_string: '(numeric_string)',
    DW_ATE_edited: '(edited)',
    DW_ATE_signed_fixed: '(signed_fixed)',
    DW_ATE_unsigned_fixed: '(unsigned_fixed)',
    DW_ATE_HP_float80: '(HP_float80)',
    DW_ATE_HP_complex_float80: '(HP_complex_float80)',
    DW_ATE_HP_float128: '(HP_float128)',
    DW_ATE_HP_complex_float128: '(HP_complex_float128)',
    DW_ATE_HP_floathpintel: '(HP_floathpintel)',
    DW_ATE_HP_imaginary_float80: '(HP_imaginary_float80)',
    DW_ATE_HP_imaginary_float128: '(HP_imaginary_float128)',
}

