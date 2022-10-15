#------------------------------------------------------------------------------
# elftools tests
#
# Maxim Akhmedov (max42@yandex-team.ru)
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
                              'testfiles_for_unittests', 'core_linux64.elf'),
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
                self.assertEqual(desc['pr_flag'], 0x400600)
                self.assertEqual(desc['pr_uid'], 1000)
                self.assertEqual(desc['pr_gid'], 1000)
                self.assertEqual(desc['pr_pid'], 23395)
                self.assertEqual(desc['pr_ppid'], 23187)
                self.assertEqual(desc['pr_pgrp'], 23395)
                self.assertEqual(desc['pr_sid'], 23187)
                self.assertEqual(
                    desc['pr_fname'],
                    b'coredump_self\x00\x00\x00')
                self.assertEqual(
                    desc['pr_psargs'],
                    b'./coredump_self foo bar 42 ' + b'\x00' * (80 - 27))

    def test_core_nt_file(self):
        """
        Test that the parsing of the NT_FILE note within a core file is
        correct.
        The assertions are made against the output of eu-readelf.

        eu-readelf -n core_linux64.elf
        ...
        CORE                 621  FILE
        10 files:
        00400000-00401000 00000000 4096
          /home/max42/pyelftools/test/coredump_self
        00600000-00601000 00000000 4096
          /home/max42/pyelftools/test/coredump_self
        00601000-00602000 00001000 4096
          /home/max42/pyelftools/test/coredump_self
        7fa4593ae000-7fa45956d000 00000000 1830912
          /lib/x86_64-linux-gnu/libc-2.23.so
        7fa45956d000-7fa45976d000 001bf000 2097152
          /lib/x86_64-linux-gnu/libc-2.23.so
        7fa45976d000-7fa459771000 001bf000 16384
          /lib/x86_64-linux-gnu/libc-2.23.so
        7fa459771000-7fa459773000 001c3000 8192
          /lib/x86_64-linux-gnu/libc-2.23.so
        7fa459777000-7fa45979d000 00000000 155648
          /lib/x86_64-linux-gnu/ld-2.23.so
        7fa45999c000-7fa45999d000 00025000 4096
          /lib/x86_64-linux-gnu/ld-2.23.so
        7fa45999d000-7fa45999e000 00026000 4096
          /lib/x86_64-linux-gnu/ld-2.23.so
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
                self.assertEqual(desc['num_map_entries'], 10)
                self.assertEqual(desc['page_size'], 4096)
                self.assertEqual(len(desc['Elf_Nt_File_Entry']), 10)
                self.assertEqual(len(desc['filename']), 10)

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][0],
                                            desc['page_size'],
                                            0x00400000,
                                            0x00401000,
                                            0x00000000)
                self.assertEqual(desc['filename'][0],
                                 b"/home/max42/pyelftools/test/coredump_self")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][1],
                                            desc['page_size'],
                                            0x00600000,
                                            0x00601000,
                                            0x00000000)
                self.assertEqual(desc['filename'][1],
                                 b"/home/max42/pyelftools/test/coredump_self")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][2],
                                            desc['page_size'],
                                            0x00601000,
                                            0x00602000,
                                            0x00001000)
                self.assertEqual(desc['filename'][2],
                                 b"/home/max42/pyelftools/test/coredump_self")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][3],
                                            desc['page_size'],
                                            0x7fa4593ae000,
                                            0x7fa45956d000,
                                            0x00000000)
                self.assertEqual(desc['filename'][3],
                                 b"/lib/x86_64-linux-gnu/libc-2.23.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][4],
                                            desc['page_size'],
                                            0x7fa45956d000,
                                            0x7fa45976d000,
                                            0x001bf000)
                self.assertEqual(desc['filename'][4],
                                 b"/lib/x86_64-linux-gnu/libc-2.23.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][5],
                                            desc['page_size'],
                                            0x7fa45976d000,
                                            0x7fa459771000,
                                            0x001bf000)
                self.assertEqual(desc['filename'][5],
                                 b"/lib/x86_64-linux-gnu/libc-2.23.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][6],
                                            desc['page_size'],
                                            0x7fa459771000,
                                            0x7fa459773000,
                                            0x001c3000)
                self.assertEqual(desc['filename'][6],
                                 b"/lib/x86_64-linux-gnu/libc-2.23.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][7],
                                            desc['page_size'],
                                            0x7fa459777000,
                                            0x7fa45979d000,
                                            0x00000000)
                self.assertEqual(desc['filename'][7],
                                 b"/lib/x86_64-linux-gnu/ld-2.23.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][8],
                                            desc['page_size'],
                                            0x7fa45999c000,
                                            0x7fa45999d000,
                                            0x00025000)
                self.assertEqual(desc['filename'][8],
                                 b"/lib/x86_64-linux-gnu/ld-2.23.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][9],
                                            desc['page_size'],
                                            0x7fa45999d000,
                                            0x7fa45999e000,
                                            0x00026000)
                self.assertEqual(desc['filename'][9],
                                 b"/lib/x86_64-linux-gnu/ld-2.23.so")
        self.assertTrue(nt_file_found)

    def validate_nt_file_entry(self,
                               entry,
                               page_size,
                               expected_vm_start,
                               expected_vm_end,
                               expected_page_offset):
        self.assertEqual(entry.vm_start, expected_vm_start)
        self.assertEqual(entry.vm_end, expected_vm_end)
        self.assertEqual(entry.page_offset * page_size, expected_page_offset)

    @classmethod
    def tearDownClass(cls):
        cls._core_file.close()
