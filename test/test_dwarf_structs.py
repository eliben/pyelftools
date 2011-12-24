try:
    import unittest2 as unittest
except ImportError:
    import unittest
import sys

sys.path.extend(['.', '..'])
from elftools.dwarf.structs import DWARFStructs


class TestDWARFStructs(unittest.TestCase):
    def test_lineprog_header(self):
        ds = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)

        c = ds.Dwarf_lineprog_header.parse(
            '\x04\x10\x00\x00' +    # initial lenght
            '\x05\x02' +            # version
            '\x20\x00\x00\x00' +    # header length
            '\x05\x10\x40\x50' +    # until and including line_range
            '\x06' +                # opcode_base
            '\x00\x01\x04\x08\x0C' + # standard_opcode_lengths
            # 2 dir names followed by a NULL
            '\x61\x62\x00\x70\x00\x00' + 
            # a file entry
            '\x61\x72\x00\x0C\x0D\x0F' + 
            # and another entry
            '\x45\x50\x51\x00\x86\x12\x07\x08' +
            # followed by NULL
            '\x00')

        self.assertEqual(c.version, 0x205)
        self.assertEqual(c.opcode_base, 6)
        self.assertEqual(c.standard_opcode_lengths, [0, 1, 4, 8, 12])
        self.assertEqual(c.include_directory, ['ab', 'p'])
        self.assertEqual(len(c.file_entry), 2)
        self.assertEqual(c.file_entry[0].name, 'ar')
        self.assertEqual(c.file_entry[1].name, 'EPQ')
        self.assertEqual(c.file_entry[1].dir_index, 0x12 * 128 + 6)


if __name__ == '__main__':
    unittest.main()

