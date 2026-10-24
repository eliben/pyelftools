#-------------------------------------------------------------------------------
# elftools example: dwarf_type_references.py
#
# Follow DW_AT_type references from variables and typedefs to their underlying
# types. Show each reference's form and value alongside the resolved DIE offset.
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys

from elftools.common.utils import bytes2str
from elftools.elf.elffile import ELFFile


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)
        if not elffile.has_dwarf_info(strict=True):
            print('  file has no DWARF info')
            return

        dwarfinfo = elffile.get_dwarf_info()
        for cu in dwarfinfo.iter_CUs():
            print(f'  Compilation unit at offset {cu.cu_offset:#x}')
            for die in cu.iter_DIEs():
                if die.tag in ('DW_TAG_variable', 'DW_TAG_typedef'):
                    show_type_chain(die)


def describe_die(die):
    name_attr = die.attributes.get('DW_AT_name')
    name = bytes2str(name_attr.value) if name_attr else '<unnamed>'
    return f'{die.tag} {name} at {die.offset:#x}'


def show_type_chain(die):
    print(f'    {describe_die(die)}')
    seen = {die}
    while 'DW_AT_type' in die.attributes:
        attr = die.attributes['DW_AT_type']

        # DW_FORM_ref1/ref2/ref4/ref8/ref_udata values are relative to the
        # compilation unit, while DIE.offset is relative to its DWARF section.
        # For example, size_t in sample_exe64.elf has a DW_FORM_ref4 value of
        # 0x3f in the CU at 0x1a2, referring to the DIE at 0x1e1.
        # get_DIE_from_attribute handles the reference form, including references
        # to other units. Use it instead of comparing attr.value with DIE.offset
        # or adding the CU offset unconditionally.
        die = die.get_DIE_from_attribute('DW_AT_type')
        print(f'      DW_AT_type ({attr.form}, value={attr.value:#x}) -> {describe_die(die)}')

        # Type references form a graph; stop if the chain reaches a DIE again.
        if die in seen:
            print('      Cycle in type references')
            break
        seen.add(die)


if __name__ == '__main__':
    filenames = sys.argv[1:]
    if filenames[:1] == ['--test']:
        filenames = filenames[1:]
    if not filenames:
        sys.exit(f'Usage: {sys.argv[0]} <elf-file> [...]')
    for filename in filenames:
        process_file(filename)
