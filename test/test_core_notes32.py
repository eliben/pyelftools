#------------------------------------------------------------------------------
# elftools tests
#
# Kyle Zeng (zengyhkyle@asu.edu)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.segments import NoteSegment


class TestCoreNotes(unittest.TestCase):
    """ This test makes sure than core dump specific
        sections are properly analyzed.
    """
    @classmethod
    def setUpClass(cls):
        cls._core_file = open(os.path.join('test',
                              'testfiles_for_unittests', 'core_linux32.elf'),
                              'rb')

    def test_core_prpsinfo(self):
        elf = ELFFile(self._core_file)
        for segment in elf.iter_segments():
            if not isinstance(segment, NoteSegment):
                continue
            notes = list(segment.iter_notes())
            for note in segment.iter_notes():
                if note['n_type'] != 'NT_PRPSINFO':
                    continue
                desc = note['n_desc']
                self.assertEqual(desc['pr_state'], 0)
                self.assertEqual(desc['pr_sname'], b'R')
                self.assertEqual(desc['pr_zomb'], 0)
                self.assertEqual(desc['pr_nice'], 0)
                self.assertEqual(desc['pr_flag'], 0x404700)
                self.assertEqual(desc['pr_uid'], 1000)
                self.assertEqual(desc['pr_gid'], 1000)
                self.assertEqual(desc['pr_pid'], 131)
                self.assertEqual(desc['pr_ppid'], 108)
                self.assertEqual(desc['pr_pgrp'], 131)
                self.assertEqual(desc['pr_sid'], 108)
                self.assertEqual(
                    desc['pr_fname'],
                    b'coredump\x00\x00\x00\x00\x00\x00\x00\x00')
                self.assertEqual(
                    desc['pr_psargs'],
                    b'./coredump foo bar 42 '.ljust(80, b'\x00'))

    def test_core_nt_file(self):
        """
        Test that the parsing of the NT_FILE note within a core file is
        correct.
        The assertions are made against the output of eu-readelf.

        eu-readelf -n core_linux64.elf
        ...
        CORE                 0x0000029b	NT_FILE (mapped files)
        Page size: 4096
             Start         End Page Offset
        0x56610000  0x56611000  0x00000000
            /tmp/coredump
        0x56611000  0x56612000  0x00000001
            /tmp/coredump
        0x56612000  0x56613000  0x00000002
            /tmp/coredump
        0x56613000  0x56614000  0x00000002
            /tmp/coredump
        0x56614000  0x56615000  0x00000003
            /tmp/coredump
        0xf7dbe000  0xf7ddb000  0x00000000
            /usr/lib/i386-linux-gnu/libc-2.31.so
        0xf7ddb000  0xf7f36000  0x0000001d
            /usr/lib/i386-linux-gnu/libc-2.31.so
        0xf7f36000  0xf7fa6000  0x00000178
            /usr/lib/i386-linux-gnu/libc-2.31.so
        0xf7fa6000  0xf7fa7000  0x000001e8
            /usr/lib/i386-linux-gnu/libc-2.31.so
        0xf7fa7000  0xf7fa9000  0x000001e8
            /usr/lib/i386-linux-gnu/libc-2.31.so
        0xf7fa9000  0xf7fab000  0x000001ea
            /usr/lib/i386-linux-gnu/libc-2.31.so
        0xf7fbb000  0xf7fbc000  0x00000000
            /usr/lib/i386-linux-gnu/ld-2.31.so
        0xf7fbc000  0xf7fda000  0x00000001
            /usr/lib/i386-linux-gnu/ld-2.31.so
        0xf7fda000  0xf7fe5000  0x0000001f
            /usr/lib/i386-linux-gnu/ld-2.31.so
        0xf7fe6000  0xf7fe7000  0x0000002a
            /usr/lib/i386-linux-gnu/ld-2.31.so
        0xf7fe7000  0xf7fe8000  0x0000002b
            /usr/lib/i386-linux-gnu/ld-2.31.so
        ...
        """
        elf = ELFFile(self._core_file)
        nt_file_found = False
        for segment in elf.iter_segments():
            if not isinstance(segment, NoteSegment):
                continue
            for note in segment.iter_notes():
                if note['n_type'] != 'NT_FILE':
                    continue
                nt_file_found = True
                desc = note['n_desc']
                self.assertEqual(desc['num_map_entries'], 16)
                self.assertEqual(desc['page_size'], 4096)
                self.assertEqual(len(desc['Elf_Nt_File_Entry']), 16)
                self.assertEqual(len(desc['filename']), 16)

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][0],
                                            desc['page_size'],
                                            0x56610000, 0x56611000, 0x00000000)
                self.assertEqual(desc['filename'][0],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][1],
                                            desc['page_size'],
                                            0x56611000, 0x56612000, 0x00000001)
                self.assertEqual(desc['filename'][1],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][2],
                                            desc['page_size'],
                                            0x56612000, 0x56613000, 0x00000002)
                self.assertEqual(desc['filename'][2],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][3],
                                            desc['page_size'],
                                            0x56613000, 0x56614000, 0x00000002)
                self.assertEqual(desc['filename'][3],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][4],
                                            desc['page_size'],
                                            0x56614000, 0x56615000, 0x00000003)
                self.assertEqual(desc['filename'][4],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][5],
                                            desc['page_size'],
                                            0xf7dbe000, 0xf7ddb000, 0x00000000)
                self.assertEqual(desc['filename'][5],
                                 b"/usr/lib/i386-linux-gnu/libc-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][6],
                                            desc['page_size'],
                                            0xf7ddb000, 0xf7f36000, 0x0000001d)
                self.assertEqual(desc['filename'][6],
                                 b"/usr/lib/i386-linux-gnu/libc-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][7],
                                            desc['page_size'],
                                            0xf7f36000, 0xf7fa6000, 0x00000178)
                self.assertEqual(desc['filename'][7],
                                 b"/usr/lib/i386-linux-gnu/libc-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][8],
                                            desc['page_size'],
                                            0xf7fa6000, 0xf7fa7000, 0x000001e8)
                self.assertEqual(desc['filename'][8],
                                 b"/usr/lib/i386-linux-gnu/libc-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][9],
                                            desc['page_size'],
                                            0xf7fa7000, 0xf7fa9000, 0x000001e8)
                self.assertEqual(desc['filename'][9],
                                 b"/usr/lib/i386-linux-gnu/libc-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][10],
                                            desc['page_size'],
                                            0xf7fa9000, 0xf7fab000, 0x000001ea)
                self.assertEqual(desc['filename'][10],
                                 b"/usr/lib/i386-linux-gnu/libc-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][11],
                                            desc['page_size'],
                                            0xf7fbb000, 0xf7fbc000, 0x00000000)
                self.assertEqual(desc['filename'][11],
                                 b"/usr/lib/i386-linux-gnu/ld-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][12],
                                            desc['page_size'],
                                            0xf7fbc000, 0xf7fda000, 0x00000001)
                self.assertEqual(desc['filename'][12],
                                 b"/usr/lib/i386-linux-gnu/ld-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][13],
                                            desc['page_size'],
                                            0xf7fda000, 0xf7fe5000, 0x0000001f)
                self.assertEqual(desc['filename'][13],
                                 b"/usr/lib/i386-linux-gnu/ld-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][14],
                                            desc['page_size'],
                                            0xf7fe6000, 0xf7fe7000, 0x0000002a)
                self.assertEqual(desc['filename'][14],
                                 b"/usr/lib/i386-linux-gnu/ld-2.31.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][15],
                                            desc['page_size'],
                                            0xf7fe7000, 0xf7fe8000, 0x0000002b)
                self.assertEqual(desc['filename'][15],
                                 b"/usr/lib/i386-linux-gnu/ld-2.31.so")
        self.assertTrue(nt_file_found)

    def validate_nt_file_entry(self,
                               entry,
                               page_size,
                               expected_vm_start,
                               expected_vm_end,
                               expected_page_offset):
        self.assertEqual(entry.vm_start, expected_vm_start)
        self.assertEqual(entry.vm_end, expected_vm_end)
        print(entry.page_offset, page_size, expected_page_offset)
        self.assertEqual(entry.page_offset * page_size, expected_page_offset)

    @classmethod
    def tearDownClass(cls):
        cls._core_file.close()
