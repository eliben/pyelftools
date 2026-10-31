"""Bounds checks for file-backed section and segment data."""
import unittest
import zlib
from contextlib import contextmanager
from io import BytesIO
from tempfile import TemporaryFile
from types import SimpleNamespace
from unittest.mock import Mock, call

from elftools.common.exceptions import ELFCompressionError, ELFParseError
from elftools.construct import Container
from elftools.elf.constants import SH_FLAGS
from elftools.elf.sections import Section
from elftools.elf.segments import Segment
from elftools.elf.structs import ELFStructs


class TestDataBounds(unittest.TestCase):
    @contextmanager
    def stream(self, data, on_disk=False):
        with TemporaryFile() if on_disk else BytesIO() as stream:
            stream.write(data)
            stream.seek(0)
            yield stream

    def section(self, stream, offset, size, *, kind='SHT_PROGBITS',
                compressed=False, structs=None):
        if structs is None:
            structs = self.structs()
        pos = stream.tell()
        stream.seek(0, 2)
        elf = SimpleNamespace(stream=stream, stream_len=stream.tell(), structs=structs)
        stream.seek(pos)
        return Section(Container(
            sh_type=kind, sh_offset=offset, sh_size=size, sh_addralign=1,
            sh_flags=SH_FLAGS.SHF_COMPRESSED if compressed else 0), '', elf)

    def structs(self, elfclass=64, little_endian=True):
        structs = ELFStructs(elfclass=elfclass, little_endian=little_endian)
        structs.create_basic_structs()
        structs.create_advanced_structs()
        return structs

    def segment(self, stream, offset, size):
        return Segment(Container(p_offset=offset, p_filesz=size, p_memsz=1 << 32), stream)

    def test_invalid_ranges_rejected_before_read(self):
        cases = ((2**64 - 1, 1), (0, 2**64 - 1), (0, 2**32 - 1),
                 (7, 0), (5, 2), (-1, 1), (0, -1))
        for make in (self.section, self.segment):
            for on_disk in (False, True):
                for offset, size in cases:
                    with (self.subTest(kind=make.__name__, on_disk=on_disk,
                                       offset=offset, size=size),
                          self.stream(b'abcdef', on_disk) as raw):
                        stream = Mock(wraps=raw)
                        stream.read.side_effect = AssertionError('Must reject before reading')
                        obj = make(stream, offset, size)
                        with self.assertRaises(ELFParseError):
                            obj.data()
                        stream.read.assert_not_called()
                        if offset < 0 or offset > 6:
                            self.assertNotIn(call(offset), stream.seek.call_args_list)

    def test_valid_ranges(self):
        for make in (self.section, self.segment):
            for on_disk in (False, True):
                with (self.subTest(kind=make.__name__, on_disk=on_disk),
                      self.stream(b'abcdef', on_disk) as stream):
                    self.assertEqual(make(stream, 1, 2).data(), b'bc')
                    self.assertEqual(make(stream, 3, 3).data(), b'def')
                    self.assertEqual(make(stream, 6, 0).data(), b'')

    def test_short_read(self):
        for make in (self.section, self.segment):
            with self.subTest(kind=make.__name__):
                stream = Mock(wraps=BytesIO(b'abcdef'))
                obj = make(stream, 0, 6)
                stream.read.return_value = b'abc'
                with self.assertRaisesRegex(ELFParseError, 'Expected 6 bytes.*found 3'):
                    obj.data()

    def test_nobits_and_null_have_no_file_range(self):
        stream = Mock(wraps=BytesIO(b'x'))
        section = self.section(stream, 2**64 - 1, 4096, kind='SHT_NOBITS')
        self.assertEqual(section.data(), bytes(4096))
        # Section zero's size may contain the extended section count.
        section = self.section(stream, 0, 0x10000, kind='SHT_NULL')
        self.assertEqual(section.data(), b'')
        stream.read.assert_not_called()

    def test_compressed_header_bounds(self):
        for elfclass in (32, 64):
            structs = self.structs(elfclass)
            header_size = structs.Elf_Chdr.sizeof()
            for offset, size, error in (
                    (0, 0, ELFCompressionError),
                    (0, header_size - 1, ELFCompressionError),
                    (2**64 - 1, header_size, ELFParseError),
                    (0, 2**64 - 1, ELFParseError),
                    (1, header_size, ELFParseError)):
                with self.subTest(elfclass=elfclass, offset=offset, size=size):
                    stream = Mock(wraps=BytesIO(bytes(header_size)))
                    stream.read.side_effect = AssertionError('Must reject before parsing header')
                    with self.assertRaises(error):
                        self.section(stream, offset, size, compressed=True, structs=structs)
                    stream.read.assert_not_called()

    def test_compressed_data_larger_than_file(self):
        data = bytes(4096)
        for elfclass in (32, 64):
            for little_endian in (False, True):
                with self.subTest(elfclass=elfclass, little_endian=little_endian):
                    structs = self.structs(elfclass, little_endian)
                    header = structs.Elf_Chdr.build(Container(
                        ch_type='ELFCOMPRESS_ZLIB', ch_reserved=0,
                        ch_size=len(data), ch_addralign=1))
                    stored = header + zlib.compress(data)
                    stream = BytesIO(b'prefix' + stored)
                    section = self.section(stream, 6, len(stored), compressed=True, structs=structs)
                    self.assertGreater(section.data_size, section.elffile.stream_len)
                    self.assertEqual(section.data(), data)
                    # Check the current file length again when reading data.
                    stream.truncate(len(stream.getvalue()) - 1)
                    with self.assertRaises(ELFParseError):
                        section.data()


if __name__ == '__main__':
    unittest.main()
