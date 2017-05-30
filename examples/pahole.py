#-------------------------------------------------------------------------------
# elftools example: pahole.py
#
# In the .debug_info section, Dwarf Information Entries (DIEs) form a tree.
# pyelftools provides easy access to this tree, as demonstrated here.
# This can be used to inspect the structures just like the pahole tool.
#
# Damien Nozay (damien.nozay@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile

OFFSET = 0
def process_file(filename):
    global OFFSET
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()
        for CU in dwarfinfo.iter_CUs():
            # this offset is very important
            # because DW_AT_type is relative to that.
            OFFSET = CU.cu_offset
            for DIE in CU.iter_DIEs():
                die_parse_types(DIE)

        for CU in dwarfinfo.iter_CUs():
            OFFSET = CU.cu_offset
            top_DIE = CU.get_top_DIE()
            die_info_rec(top_DIE)


TYPES = {}
UNRESOLVED = {}

def register(name, offset):
    TYPES[offset] = name
    for unresolved_offset, pattern in UNRESOLVED.get(offset, set()):
        register(pattern % name, unresolved_offset)

def resolve_register(pattern, die):
    basetypeoffset = die.attributes.get(_.DW_AT_type, _.NO_TYPE).value
    if basetypeoffset:
        # offset is relative to the unit
        basetypeoffset += OFFSET
        basetype = TYPES.get(basetypeoffset, None)
        if basetype:
            name_attr = pattern % basetype
            register(name_attr, die.offset)
        else:
            UNRESOLVED.setdefault(basetypeoffset,set()).add((die.offset,pattern))
    else:
        # void
        name_attr = pattern % 'void'
        register(name_attr, die.offset)

class _:
    class NO_NAME:
        value = ''
    class NO_TYPE:
        value = 0
    DW_AT_name = 'DW_AT_name'
    DW_AT_type = 'DW_AT_type'
    DW_AT_const_value = 'DW_AT_const_value'

class DIE_type_handler:
    @staticmethod
    def DW_TAG_base_type(die):
        name_attr = get_name(die)
        register(name_attr, die.offset)
        for child in die.iter_children():
            print(child)
    @staticmethod
    def DW_TAG_typedef(die):
        name_attr = get_name(die)
        register(name_attr, die.offset)
    @staticmethod
    def DW_TAG_pointer_type(die):
        resolve_register('%s *', die)
    @staticmethod
    def DW_TAG_array_type(die):
        length = ''
        for child in die.iter_children():
            if child.tag == 'DW_TAG_subrange_type':
                upper = child.attributes.get('DW_AT_upper_bound', None)
                if upper:
                    length = upper.value + 1
        resolve_register('%%s [%s]' % length, die)
    @staticmethod
    def DW_TAG_const_type(die):
        resolve_register('const %s', die)
    @staticmethod
    def DW_TAG_volatile_type(die):
        resolve_register('volatile %s', die)
    @staticmethod
    def DW_TAG_structure_type(die):
        name_attr = get_name(die)
        register('struct %s' % name_attr, die.offset)
    @staticmethod
    def DW_TAG_union_type(die):
        name_attr = get_name(die)
        register('union %s' % name_attr, die.offset)
    @staticmethod
    def DW_TAG_enumeration_type(die):
        name_attr = get_name(die)
        register('enum %s' % name_attr, die.offset)

def die_parse_types(die):
    die_tag = die.tag
    if die.tag is None:
        return
    handler = getattr(DIE_type_handler, die_tag, None)
    if handler:
        handler(die)
        return
    for child in die.iter_children():
        die_parse_types(child)

def get_type(die):
    offset = die.attributes.get(_.DW_AT_type, _.NO_TYPE).value
    rel_offset = offset + OFFSET
    default = '__unresolved_%s' % str(rel_offset)
    return TYPES.get(rel_offset, TYPES.get(offset, default))

def get_name(die):
    name_attr = die.attributes.get(_.DW_AT_name, _.NO_NAME).value
    if not name_attr:
        name_attr = '__unknown_%s' % die.offset
    return name_attr

class DIE_info_handler:
    @staticmethod
    def DW_TAG_base_type(die, indent_level):
        name_attr = get_name(die)
        print("%s[%s]: type %s;" % (die.offset, die.offset - OFFSET, name_attr))
    @staticmethod
    def DW_TAG_typedef(die, indent_level):
        type_attr = get_type(die)
        name_attr = get_name(die)
        print("%s[%s]: typedef %s %s;" % (die.offset, die.offset - OFFSET, name_attr, type_attr))
    @staticmethod
    def DW_TAG_pointer_type(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_const_type(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_volatile_type(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_array_type(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_subrange_type(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_subroutine_type(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_subprogram(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_variable(die, indent_level):
        pass
    @staticmethod
    def DW_TAG_member(die, indent_level):
        type_attr = get_type(die)
        name_attr = get_name(die)
        print(indent_level + '%-20s %s;' % (type_attr, name_attr))
    @staticmethod
    def DW_TAG_union_type(die, indent_level):
        name_attr = get_name(die)
        print(indent_level + 'union %s {' % name_attr)
        child_indent = indent_level + '  '
        for child in die.iter_children():
            die_info_rec(child, child_indent)
        print(indent_level + '}')
    @staticmethod
    def DW_TAG_structure_type(die, indent_level):
        name_attr = get_name(die)
        print(indent_level + 'struct %s {' % name_attr)
        child_indent = indent_level + '  '
        for child in die.iter_children():
            die_info_rec(child, child_indent)
        print(indent_level + '}')
    @staticmethod
    def DW_TAG_enumerator(die, indent_level):
        name = die.attributes[_.DW_AT_name].value
        value = die.attributes[_.DW_AT_const_value].value
        print(indent_level + '%-20s = %#x' % (name, value))
    @staticmethod
    def DW_TAG_enumeration_type(die, indent_level):
        name_attr = get_name(die)
        print(indent_level + 'enum %s {' % name_attr)
        child_indent = indent_level + '  '
        for child in die.iter_children():
            die_info_rec(child, child_indent)
        print(indent_level + '}')
    @staticmethod
    def DW_TAG_compile_unit(die, indent_level):
        name_attr = get_name(die)
        print('#' * 80)
        print('Compile unit %s' % name_attr)
        print('#' * 80)
        child_indent = indent_level + '  '
        for child in die.iter_children():
            die_info_rec(child, child_indent)
    @staticmethod
    def default(die, indent_level):
        type_attr = get_type(die)
        name_attr = get_name(die)
        print(indent_level + 'DIE tag=%s %s (%s) %s' % (die.tag, type_attr, name_attr, die.offset))
        child_indent = indent_level + '  '
        for child in die.iter_children():
            die_info_rec(child, child_indent)


def die_info_rec(die, indent_level='    '):
    """ A recursive function for showing information about a DIE and its
        children.
    """
    die_tag = die.tag
    if die.tag is None:
        print(die)
        return
    handler = getattr(DIE_info_handler, die_tag, None)
    if handler:
        handler(die, indent_level)
    else:
        DIE_info_handler.default(die, indent_level)


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)


