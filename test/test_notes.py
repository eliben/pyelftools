import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import NoteSection

class TestNotes(unittest.TestCase):
    def test_note_segment_with_8_byte_alignment(self):
        with ELFFile.load_from_path(os.path.join('test', 'testfiles_for_unittests', 'note_with_segment_padding', 'main.elf')) as elf:
            note_sections = [section for section in elf.iter_sections() if isinstance(section, NoteSection)]
            # There's only one note section in this file:
            self.assertEqual(len(note_sections), 1)
            notes = list(note_sections[0].iter_notes())
            # There's one note in this section:
            self.assertEqual(len(notes), 1)
