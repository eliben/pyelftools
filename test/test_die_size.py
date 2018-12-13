#------------------------------------------------------------------------------
# elftools tests
#
# Anders Dellien (anders@andersdellien.se)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile

class TestDieSize(unittest.TestCase):
    """ This test verifies that null DIEs are treated correctly - i.e.
        removed when we 'unflatten' the linear list and build a tree.
        The test file contains a CU with two non-null DIEs (both three bytes big),
        where the second one is followed by three null DIEs.
        We verify that the null DIEs are discarded and that the length of the second DIE
        does not include the null entries that follow it.
    """
    def test_die_size(self):
        with open(os.path.join('test',
                               'testfiles_for_unittests', 'trailing_null_dies.elf'),
                  'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())
            dwarfinfo = elffile.get_dwarf_info()
            for CU in dwarfinfo.iter_CUs():
                 for child in CU.get_top_DIE().iter_children():
                     self.assertEquals(child.size, 3)

if __name__ == '__main__':
    unittest.main()
