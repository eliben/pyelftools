#------------------------------------------------------------------------------
# elftools tests
#
# This code is in the public domain
#------------------------------------------------------------------------------
import os
import unittest

from elftools.elf.elffile import ELFFile
from elftools.elf.segments import NoteSegment


class TestCoreNotesX32(unittest.TestCase):
    """
    All expected values are from eu-readelf -n core_linux_x32.elf.
    """
    @classmethod
    def setUpClass(cls):
        cls._core_file = open(os.path.join('test',  # noqa: SIM115
                              'testfiles_for_unittests', 'core_linux_x32.elf'),
                              'rb')

    def notes(self, n_type):
        elf = ELFFile(self._core_file)
        return [note['n_desc']
                for segment in elf.iter_segments()
                if isinstance(segment, NoteSegment)
                for note in segment.iter_notes()
                if note['n_type'] == n_type]

    def test_core_prpsinfo(self):
        (desc,) = self.notes('NT_PRPSINFO')
        self.assertEqual(desc['pr_state'], 0)
        self.assertEqual(desc['pr_sname'], b'R')
        self.assertEqual(desc['pr_zomb'], 0)
        self.assertEqual(desc['pr_nice'], 0)
        self.assertEqual(desc['pr_flag'], 0x400700)
        self.assertEqual(desc['pr_uid'], 1000)
        self.assertEqual(desc['pr_gid'], 1001)
        self.assertEqual(desc['pr_pid'], 79)
        self.assertEqual(desc['pr_ppid'], 1)
        self.assertEqual(desc['pr_pgrp'], 79)
        self.assertEqual(desc['pr_sid'], 79)
        self.assertEqual(desc['pr_fname'], b'x32crash'.ljust(16, b'\0'))
        self.assertEqual(desc['pr_psargs'],
                         b'./x32crash foo bar '.ljust(80, b'\0'))

    def test_core_nt_file(self):
        (desc,) = self.notes('NT_FILE')
        self.assertEqual(desc['num_map_entries'], 15)
        self.assertEqual(desc['page_size'], 4096)
        self.assertEqual(len(desc['filename']), 15)
        expected = {
            0: (0x5660c000, 0x5660d000, 0x00000000, b'/work/x32crash'),
            4: (0x56610000, 0x56611000, 0x00003000, b'/work/x32crash'),
            5: (0xf7db8000, 0xf7dd7000, 0x00000000, b'/libx32/libc.so.6'),
            9: (0xf7f83000, 0xf7f84000, 0x001cb000, b'/libx32/libc.so.6'),
            14: (0xf7fc2000, 0xf7fc3000, 0x00032000,
                 b'/libx32/ld-linux-x32.so.2'),
        }
        for index, (start, end, offset, filename) in expected.items():
            entry = desc['Elf_Nt_File_Entry'][index]
            self.assertEqual(entry['vm_start'], start)
            self.assertEqual(entry['vm_end'], end)
            self.assertEqual(entry['page_offset'] * desc['page_size'], offset)
            self.assertEqual(desc['filename'][index], filename)

    @classmethod
    def tearDownClass(cls):
        cls._core_file.close()


if __name__ == '__main__':
    unittest.main()
