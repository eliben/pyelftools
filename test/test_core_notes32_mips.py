#------------------------------------------------------------------------------
# elftools tests
#
# Lukas Dresel (lukas.dresel@cs.ucsb.edu)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.segments import NoteSegment


class TestCoreNotes(unittest.TestCase):
    """ This test ensures that core dump specific notes
        are properly analyzed. Specifically, tests for a
        regression where MIPS PRPSINFO structures would be
        parsed incorrectly due to being treated as 16-bit
        fields instead of 32-bit fields.
    """
    @classmethod
    def setUpClass(cls):
       cls._core_file = open(os.path.join('test',
                             'testfiles_for_unittests', 'core_linux32_qemu_mips.elf'),
                             'rb')

    def test_core_prpsinfo(self):
        elf = ELFFile(self._core_file)
        for segment in elf.iter_segments():
            if not isinstance(segment, NoteSegment):
                continue
            for note in segment.iter_notes():
                if note['n_type'] != 'NT_PRPSINFO':
                    continue
                desc = note['n_desc']
                self.assertEqual(desc['pr_state'], 0)
                self.assertEqual(desc['pr_sname'], b'\0')
                self.assertEqual(desc['pr_zomb'], 0)
                self.assertEqual(desc['pr_nice'], 0)
                self.assertEqual(desc['pr_flag'], 0x0)
                self.assertEqual(desc['pr_uid'], 1000)
                self.assertEqual(desc['pr_gid'], 1000)
                self.assertEqual(desc['pr_pid'], 449015)
                self.assertEqual(desc['pr_ppid'], 4238)
                self.assertEqual(desc['pr_pgrp'], 449015)
                self.assertEqual(desc['pr_sid'], 4238)
                self.assertEqual(
                    desc['pr_fname'],
                    b'crash'.ljust(16, b'\0'))
                self.assertEqual(
                    desc['pr_psargs'],
                    b'./crash '.ljust(80, b'\x00'))

    @classmethod
    def tearDownClass(cls):
        cls._core_file.close()


if __name__ == '__main__':
    unittest.main()
