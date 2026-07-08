import io
import os
import struct
import unittest

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import NoteSection
from elftools.elf.segments import NoteSegment


def _build_core_with_gnu_note(n_type, desc):
    """ Build a minimal 32-bit LE ARM ET_CORE ELF with a single PT_NOTE segment
        holding one note named 'GNU' with the given type and descriptor.
    """
    name = b'GNU\x00'
    note = struct.pack('<III', len(b'GNU') + 1, len(desc), n_type) + name + desc
    ehsize, phentsize = 52, 32
    p_offset = ehsize + phentsize
    ehdr = (b'\x7fELF\x01\x01\x01\x00' + b'\x00' * 8 +
            struct.pack('<HHIIIIIHHHHHH',
                        4, 40, 1, 0, ehsize, 0, 0,
                        ehsize, phentsize, 1, 0, 0, 0))
    phdr = struct.pack('<IIIIIIII',
                       4, p_offset, p_offset, p_offset, len(note), len(note), 0, 4)
    return io.BytesIO(ehdr + phdr + note)


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

    def test_gnu_build_id_note_in_core(self):
        # A GNU build ID note (type 3, name 'GNU') can appear inside an ET_CORE
        # file, where type 3 otherwise means NT_PRPSINFO. It must be decoded as
        # NT_GNU_BUILD_ID rather than parsed as a prpsinfo struct (issue #656).
        stream = _build_core_with_gnu_note(3, b'\xde\xad\xc0\xde\xde\xad\xc0\xde')
        elf = ELFFile(stream)
        segments = [s for s in elf.iter_segments() if isinstance(s, NoteSegment)]
        self.assertEqual(len(segments), 1)
        notes = list(segments[0].iter_notes())
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['n_name'], 'GNU')
        self.assertEqual(notes[0]['n_type'], 'NT_GNU_BUILD_ID')
        self.assertEqual(notes[0]['n_desc'], 'deadc0dedeadc0de')

    def test_note_tc3xx_blinky(self):
        with ELFFile.load_from_path(os.path.join('test', 'testfiles_for_unittests', 'note_tc3xxx_blinky.elf')) as elf:
            note_sections = [section for section in elf.iter_sections() if isinstance(section, NoteSection)]
            # There's only one note section in this file:
            self.assertEqual(len(note_sections), 1)
            notes = list(note_sections[0].iter_notes())
            # There's one note in this section:
            self.assertEqual(len(notes), 522)
