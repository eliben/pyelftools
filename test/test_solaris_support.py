#-------------------------------------------------------------------------------
# elftools tests
#
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SYMINF0_FLAGS


class TestSolarisSupport(unittest.TestCase):

    def _test_SUNW_syminfo_section_generic(self, testfile):
        with open(os.path.join('test', 'testfiles',
                               testfile), 'rb') as f:
            elf = ELFFile(f)
            syminfo_section = elf.get_section_by_name('.SUNW_syminfo')
            self.assertIsNotNone(syminfo_section)

            exit_symbols = [s for s in syminfo_section.iter_symbols()
                            if 'exit' in s.name]
            self.assertNotEqual(len(exit_symbols), 0)

            for symbol in exit_symbols:
                self.assertEqual(symbol['si_boundto'], 0)
                self.assertEqual(symbol['si_flags'],
                                 SYMINF0_FLAGS.SYMINFO_FLG_DIRECT |
                                 SYMINF0_FLAGS.SYMINFO_FLG_DIRECTBIND)

    def test_SUNW_syminfo_section_x86(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris32_cc.elf')

    def test_SUNW_syminfo_section_x64(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris64_cc.elf')

    def test_SUNW_syminfo_section_sparc32(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris32_cc.elf.sparc')

    def test_SUNW_syminfo_section_sparc64(self):
        self._test_SUNW_syminfo_section_generic('exe_solaris64_cc.elf.sparc')

if __name__ == '__main__':
    unittest.main()
