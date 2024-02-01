import os
import unittest

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import NoteSection


class TestNotes(unittest.TestCase):
    def test_note_after_gnu_property_type_note(self):
        with ELFFile.load_from_path(os.path.join('test', 'testfiles_for_unittests', 'note_after_gnu_property', 'main.elf')) as elf:
            note_sections = [section for section in elf.iter_sections() if isinstance(section, NoteSection)]
            # There's only one note section in this file:
            self.assertEqual(len(note_sections), 1)
            notes = list(note_sections[0].iter_notes())
            # There are 2 notes in this section:
            self.assertEqual(len(notes), 2)
            # The first note is the GNU_PROPERTY_TYPE_0 note:
            self.assertEqual(notes[0].n_type, 'NT_GNU_PROPERTY_TYPE_0')
            # It should only have two Elf_Props (and not attempt to parse the note after it as Elf_Props):
            self.assertEqual(len(notes[0].n_desc), 2)

    def test_note_segment_with_8_byte_alignment(self):
        with ELFFile.load_from_path(os.path.join('test', 'testfiles_for_unittests', 'note_with_segment_padding', 'main.elf')) as elf:
            note_sections = [section for section in elf.iter_sections() if isinstance(section, NoteSection)]
            # There's only one note section in this file:
            self.assertEqual(len(note_sections), 1)
            notes = list(note_sections[0].iter_notes())
            # There's one note in this section:
            self.assertEqual(len(notes), 1)
