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

    def test_core_prpsinfo(self):
        with open(os.path.join('test',
                               'testfiles_for_unittests', 'core_linux64.elf'),
                  'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if not isinstance(segment, NoteSegment):
                    continue
                notes = list(segment.iter_notes())
                for note in segment.iter_notes():
                    if note['n_type'] != 'NT_PRPSINFO':
                        continue
                    desc = note['n_desc']
                    self.assertEquals(desc['pr_state'], 0)
                    self.assertEquals(desc['pr_sname'], b'R')
                    self.assertEquals(desc['pr_zomb'], 0)
                    self.assertEquals(desc['pr_nice'], 0)
                    self.assertEquals(desc['pr_flag'], 0x400600)
                    self.assertEquals(desc['pr_uid'], 1000)
                    self.assertEquals(desc['pr_gid'], 1000)
                    self.assertEquals(desc['pr_pid'], 23395)
                    self.assertEquals(desc['pr_ppid'], 23187)
                    self.assertEquals(desc['pr_pgrp'], 23395)
                    self.assertEquals(desc['pr_sid'], 23187)
                    self.assertEquals(
                        desc['pr_fname'],
                        b'coredump_self\x00\x00\x00')
                    self.assertEquals(
                        desc['pr_psargs'],
                        b'./coredump_self foo bar 42 ' + b'\x00' * (80 - 27))
