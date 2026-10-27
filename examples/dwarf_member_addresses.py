#-------------------------------------------------------------------------------
# elftools example: dwarf_member_addresses.py
#
# Find addresses of direct data members in global class/struct objects.
# DW_AT_location describes the object's location, while DW_AT_type refers to
# its class/struct definition. For a DW_TAG_member with a constant
# DW_AT_data_member_location, that value is a byte offset within the object:
#     member address = object address + member byte offset
#
# For a small input, save this C++ code as members.cpp:
#     class TestClass { public: int a = 5; int b = 11; };
#     TestClass tester;
#     int main() { return tester.a + tester.b; }
# Build and run from the repository root:
#     g++ -g -O0 -no-pie members.cpp -o members.elf
#     PYTHONPATH=. python examples/dwarf_member_addresses.py members.elf
#
# Example output on x86-64 Linux:
#     Processing file: members.elf
#       tester at 0x404010
#         tester.a: offset 0, address 0x404010
#         tester.b: offset 4, address 0x404014
# The base address depends on the compiler and linker. With four-byte ints,
# a is at the start of tester and b is four bytes later. Multiple ELF paths
# may be supplied on the command line; each is processed independently.
#
# This example follows typedefs and type qualifiers, but only handles object
# locations expressed as a single DW_OP_addr and constant member byte offsets.
# Other object locations are skipped; bit-fields and members without constant
# byte offsets are reported as skipped. It does not dereference pointers or
# recurse into nested objects or base classes, and is not a general DWARF
# expression evaluator.
#
# These are linked virtual addresses, not file offsets. For PIE executables
# and shared libraries, add the runtime load bias to obtain runtime addresses.
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys

from elftools.common.utils import bytes2str
from elftools.dwarf.descriptions import describe_form_class
from elftools.dwarf.dwarf_expr import DWARFExprParser
from elftools.elf.elffile import ELFFile


def die_name(die):
    """Return a DIE's name as text, or '<unnamed>' if DW_AT_name is absent.

    Use die_name(variable_die) or die_name(member_die) when formatting output.
    DW_AT_name is stored as bytes, so decode it with bytes2str.
    """
    attr = die.attributes.get('DW_AT_name')
    return bytes2str(attr.value) if attr else '<unnamed>'


def process_file(filename):
    """Print supported objects and their direct member addresses in an ELF file.

    Call process_file('members.elf') with a path to a linked executable or
    shared library containing DWARF debug info. This function opens and closes
    the file, writes to stdout, and returns None.

    Object lines give linked addresses. Member lines give byte offsets and
    addresses computed by adding those offsets to the object's address.
    Unsupported member layouts are reported as skipped; objects without a
    single DW_OP_addr location are omitted entirely.
    """
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)
        if not elffile.has_dwarf_info(strict=True):
            print('  file has no DWARF info')
            return
        if elffile['e_type'] not in ('ET_EXEC', 'ET_DYN'):
            print('  expected a linked executable or shared library')
            return

        found = False
        for cu in elffile.get_dwarf_info().iter_CUs():
            parser = DWARFExprParser(cu.structs)
            for die in cu.iter_DIEs():
                if die.tag != 'DW_TAG_variable' or 'DW_AT_type' not in die.attributes:
                    continue

                # The reference form determines how to find the type DIE.
                # Follow aliases and qualifiers, but do not dereference pointers.
                type_die = die.get_DIE_from_attribute('DW_AT_type')
                while (type_die.tag in ('DW_TAG_typedef', 'DW_TAG_const_type',
                                       'DW_TAG_volatile_type', 'DW_TAG_restrict_type')
                       and 'DW_AT_type' in type_die.attributes):
                    type_die = type_die.get_DIE_from_attribute('DW_AT_type')
                if type_die.tag not in ('DW_TAG_class_type', 'DW_TAG_structure_type'):
                    continue

                # DW_AT_location is an expression, not the address itself.
                # A single DW_OP_addr gives a fixed address in the ELF;
                # more complex locations may require runtime context.
                location = die.attributes.get('DW_AT_location')
                if location is None or describe_form_class(location.form) not in ('exprloc', 'block'):
                    continue
                ops = parser.parse_expr(location.value)
                if len(ops) != 1 or ops[0].op_name != 'DW_OP_addr':
                    continue

                address = ops[0].args[0]
                name = die_name(die)
                print(f'  {name} at {address:#x}')
                found = True
                for member in type_die.iter_children():
                    if member.tag != 'DW_TAG_member':
                        continue
                    member_name = f'{name}.{die_name(member)}'
                    offset = member.attributes.get('DW_AT_data_member_location')
                    # Bit-fields have no independent byte address. Static
                    # members and expression-based layouts need other handling.
                    if 'DW_AT_bit_size' in member.attributes:
                        print(f'    {member_name}: skipped (bit-field)')
                    elif offset is None or describe_form_class(offset.form) != 'constant':
                        print(f'    {member_name}: skipped (no constant byte offset)')
                    else:
                        # DW_AT_data_member_location is relative to the start
                        # of the containing object, so add its base address.
                        print(f'    {member_name}: offset {offset.value}, '
                              f'address {address + offset.value:#x}')
        if not found:
            print('  No global class/struct objects with a supported location.')


if __name__ == '__main__':
    filenames = sys.argv[1:]
    if filenames[:1] == ['--test']:
        filenames = filenames[1:]
    if not filenames:
        sys.exit(f'Usage: {sys.argv[0]} <elf-file> [...]')
    for filename in filenames:
        process_file(filename)
