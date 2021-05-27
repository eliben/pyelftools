import os
import unittest

from elftools.elf.elffile import ELFFile


class TestDWARFv5(unittest.TestCase):
    def test_dwarfv5_parses(self):
        dwarfv5_basic = os.path.join('test', 'testfiles_for_unittests', 'dwarfv5_basic.elf')
        with open(dwarfv5_basic, 'rb') as f:
            elf = ELFFile(f)
            # DWARFv5 debugging information is detected.
            self.assertTrue(elf.has_dwarf_info())

            # Fetching DWARFInfo for DWARFv5 doesn't completely explode.
            dwarf = elf.get_dwarf_info()
            self.assertIsNotNone(dwarf)


if __name__ == '__main__':
    unittest.main()
