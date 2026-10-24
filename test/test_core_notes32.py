#------------------------------------------------------------------------------
# elftools tests
#
# Kyle Zeng (zengyhkyle@asu.edu)
# This code is in the public domain
#------------------------------------------------------------------------------
import io
import os
import unittest

from elftools.elf.elffile import ELFFile
from elftools.elf.segments import NoteSegment


class TestCoreNotes(unittest.TestCase):
    """ This test makes sure than core dump specific
        sections are properly analyzed.
    """
    @classmethod
    def setUpClass(cls):
        cls._core_file = open(os.path.join('test',  # noqa: SIM115
                              'testfiles_for_unittests', 'core_linux32.elf'),
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
                self.assertEqual(desc['pr_sname'], b'R')
                self.assertEqual(desc['pr_zomb'], 0)
                self.assertEqual(desc['pr_nice'], 0)
                self.assertEqual(desc['pr_flag'], 0x400600)
                self.assertEqual(desc['pr_uid'], 1000)
                self.assertEqual(desc['pr_gid'], 1000)
                self.assertEqual(desc['pr_pid'], 11038)
                self.assertEqual(desc['pr_ppid'], 10442)
                self.assertEqual(desc['pr_pgrp'], 11038)
                self.assertEqual(desc['pr_sid'], 10442)
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
        CORE                 0x0000018b	NT_FILE (mapped files)
        Page size: 4096
             Start         End Page Offset
        0x56624000  0x56625000  0x00000000
            /tmp/coredump
        0x56625000  0x56626000  0x00000000
            /tmp/coredump
        0x56626000  0x56627000  0x00000001
            /tmp/coredump
        0xf7d13000  0xf7ee8000  0x00000000
            /lib/i386-linux-gnu/libc-2.27.so
        0xf7ee8000  0xf7ee9000  0x000001d5
            /lib/i386-linux-gnu/libc-2.27.so
        0xf7ee9000  0xf7eeb000  0x000001d5
            /lib/i386-linux-gnu/libc-2.27.so
        0xf7eeb000  0xf7eec000  0x000001d7
            /lib/i386-linux-gnu/libc-2.27.so
        0xf7f39000  0xf7f5f000  0x00000000
            /lib/i386-linux-gnu/ld-2.27.so
        0xf7f5f000  0xf7f60000  0x00000025
            /lib/i386-linux-gnu/ld-2.27.so
        0xf7f60000  0xf7f61000  0x00000026
            /lib/i386-linux-gnu/ld-2.27.so
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
                                            0x56624000, 0x56625000, 0x00000000)
                self.assertEqual(desc['filename'][0],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][1],
                                            desc['page_size'],
                                            0x56625000, 0x56626000, 0x00000000)
                self.assertEqual(desc['filename'][1],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][2],
                                            desc['page_size'],
                                            0x56626000, 0x56627000, 0x00000001)
                self.assertEqual(desc['filename'][2],
                                 b"/tmp/coredump")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][3],
                                            desc['page_size'],
                                            0xf7d13000, 0xf7ee8000, 0x00000000)
                self.assertEqual(desc['filename'][3],
                                 b"/lib/i386-linux-gnu/libc-2.27.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][4],
                                            desc['page_size'],
                                            0xf7ee8000, 0xf7ee9000, 0x000001d5)
                self.assertEqual(desc['filename'][4],
                                 b"/lib/i386-linux-gnu/libc-2.27.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][5],
                                            desc['page_size'],
                                            0xf7ee9000, 0xf7eeb000, 0x000001d5)
                self.assertEqual(desc['filename'][5],
                                 b"/lib/i386-linux-gnu/libc-2.27.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][6],
                                            desc['page_size'],
                                            0xf7eeb000, 0xf7eec000, 0x000001d7)
                self.assertEqual(desc['filename'][6],
                                 b"/lib/i386-linux-gnu/libc-2.27.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][7],
                                            desc['page_size'],
                                            0xf7f39000, 0xf7f5f000, 0x00000000)
                self.assertEqual(desc['filename'][7],
                                 b"/lib/i386-linux-gnu/ld-2.27.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][8],
                                            desc['page_size'],
                                            0xf7f5f000, 0xf7f60000, 0x00000025)
                self.assertEqual(desc['filename'][8],
                                 b"/lib/i386-linux-gnu/ld-2.27.so")

                self.validate_nt_file_entry(desc['Elf_Nt_File_Entry'][9],
                                            desc['page_size'],
                                            0xf7f60000, 0xf7f61000, 0x00000026)
                self.assertEqual(desc['filename'][9],
                                 b"/lib/i386-linux-gnu/ld-2.27.so")

        self.assertTrue(nt_file_found)

    def validate_nt_file_entry(self,
                               entry,
                               page_size,
                               expected_vm_start,
                               expected_vm_end,
                               expected_page_offset):
        self.assertEqual(entry.vm_start, expected_vm_start)
        self.assertEqual(entry.vm_end, expected_vm_end)
        self.assertEqual(entry.page_offset, expected_page_offset)

    def test_core_gnu_build_id(self):
        # A core dump may contain standard GNU notes such as NT_GNU_BUILD_ID
        # (note type 3, name 'GNU'). Verify that iter_notes does not confuse
        # type 3 with NT_PRPSINFO (issue #656).
        data = bytearray()
        # ELF Header (32-bit little-endian ARM ET_CORE)
        data.extend(b'\x7fELF\x01\x01\x01\x00' + b'\x00' * 8)
        data.extend(b'\x04\x00')          # e_type = ET_CORE (4)
        data.extend(b'\x28\x00')          # e_machine = EM_ARM (40)
        data.extend(b'\x01\x00\x00\x00')  # e_version = 1
        data.extend(b'\x00\x00\x00\x00')  # e_entry = 0
        data.extend(b'\x34\x00\x00\x00')  # e_phoff = 52
        data.extend(b'\x00\x00\x00\x00')  # e_shoff = 0
        data.extend(b'\x00\x00\x00\x00')  # e_flags = 0
        data.extend(b'\x34\x00')          # e_ehsize = 52
        data.extend(b'\x20\x00')          # e_phentsize = 32
        data.extend(b'\x01\x00')          # e_phnum = 1
        data.extend(b'\x00\x00')          # e_shentsize = 0
        data.extend(b'\x00\x00')          # e_shnum = 0
        data.extend(b'\x00\x00')          # e_shstrndx = 0

        # Program Header (PT_NOTE Segment)
        data.extend(b'\x04\x00\x00\x00')  # p_type = PT_NOTE (4)
        data.extend(b'\x54\x00\x00\x00')  # p_offset = 84
        data.extend(b'\x54\x00\x00\x00')  # p_vaddr = 84
        data.extend(b'\x54\x00\x00\x00')  # p_paddr = 84
        data.extend(b'\x18\x00\x00\x00')  # p_filesz = 24
        data.extend(b'\x18\x00\x00\x00')  # p_memsz = 24
        data.extend(b'\x00\x00\x00\x00')  # p_flags = 0
        data.extend(b'\x04\x00\x00\x00')  # p_align = 4

        # Note Header (n_namesz=4, n_descsz=8, n_type=3)
        data.extend(b'\x04\x00\x00\x00')  # n_namesz = 4
        data.extend(b'\x08\x00\x00\x00')  # n_descsz = 8
        data.extend(b'\x03\x00\x00\x00')  # n_type = 3
        data.extend(b'GNU\x00')           # n_name = 'GNU'
        data.extend(b'\xde\xad\xc0\xde\xde\xad\xc0\xde')  # 8-byte build ID

        elf = ELFFile(io.BytesIO(data))
        notes = []
        for segment in elf.iter_segments():
            if isinstance(segment, NoteSegment):
                notes.extend(segment.iter_notes())

        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['n_type'], 'NT_GNU_BUILD_ID')
        self.assertEqual(notes[0]['n_name'], 'GNU')
        self.assertEqual(notes[0]['n_desc'], 'deadc0dedeadc0de')

    @classmethod
    def tearDownClass(cls):
        cls._core_file.close()
