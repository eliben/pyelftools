#-------------------------------------------------------------------------------
# elftools: dwarf/descriptions.py
#
# Textual descriptions of the various values and enums of DWARF
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import defaultdict


def describe_attr_value(attr, die, section_offset):
    """ Given an AttributeValue extracted, return the textual representation of
        its value, suitable for tools like readelf.
        
        To cover all cases, this function needs some extra arguments:

        die: the DIE this attribute was extracted from
        section_offset: offset in the stream of the section the DIE belongs to
    """
    descr_func = _ATTR_DESCRIPTION_MAP[attr.form]
    return descr_func(attr, die, section_offset)


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
    DW_FORM_flag_present=_describe_attr_value_passthrough,
    DW_FORM_flag=_describe_attr_value_passthrough,
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

