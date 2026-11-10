"""String and symbol lookup in compressed ELF string tables."""
import struct
import unittest
import zlib
from io import BytesIO

from elftools.elf.elffile import ELFFile


def string_table_elf(compressed):
    """An inert ELF64 object with a plain SYMTAB and optional compressed STRTAB."""
    strings = b'\0expected_symbol\0bad_\xff\0'
    names = b'\0.shstrtab\0.strtab\0.symtab\0'
    payload = strings
    if compressed:
        payload = struct.pack('<IIQQ', 1, 0, len(strings), 1) + zlib.compress(strings)
    symbols = bytes(24)
    for offset, value in ((1, 0x1234), (17, 0x5678)):
        symbols += struct.pack('<IBBHQQ', offset, 0x10, 0, 0xfff1, value, 0)
    data = bytearray(64)
    headers = [bytes(64)]
    for name, kind, flags, content, link, info, alignment, entrysize in (
            (1, 3, 0, names, 0, 0, 1, 0),
            (11, 3, 0x800 if compressed else 0, payload, 0, 0,
             8 if compressed else 1, 0),
            (19, 2, 0, symbols, 2, 1, 8, 24)):
        data.extend(bytes(-len(data) % alignment))
        offset = len(data)
        data.extend(content)
        headers.append(struct.pack('<IIQQQQIIQQ', name, kind, flags, 0,
                                   offset, len(content), link, info,
                                   alignment, entrysize))
    data.extend(bytes(-len(data) % 8))
    shoff = len(data)
    data.extend(b''.join(headers))
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    data[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 1, 62, 1, 0, 0,
                           shoff, 0, 64, 0, 0, 64, 4, 1)
    return BytesIO(data)


class TestCompressedStringTable(unittest.TestCase):
    def test_string_and_symbol_names(self):
        for compressed in (False, True):
            with string_table_elf(compressed) as stream:
                elf = ELFFile(stream)
                strings = elf.get_section_by_name('.strtab')
                symbols = elf.get_section_by_name('.symtab')
                for offset, expected in ((0, ''), (1, 'expected_symbol'),
                                         (17, 'bad_\ufffd'), (11, 'ymbol')):
                    with self.subTest(compressed=compressed, offset=offset):
                        self.assertEqual(strings.get_string(offset), expected)
                with self.subTest(compressed=compressed, lookup='symbol'):
                    symbol = symbols.get_symbol(1)
                    self.assertEqual(symbol.name, 'expected_symbol')
                    self.assertEqual(symbol['st_value'], 0x1234)
                with self.subTest(compressed=compressed, lookup='iteration'):
                    self.assertEqual([symbol.name for symbol in symbols.iter_symbols()],
                                     ['', 'expected_symbol', 'bad_\ufffd'])


if __name__ == '__main__':
    unittest.main()
