#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
from io import BytesIO

from elftools.construct import ConstructError
from elftools.dwarf.structs import DWARFStructs


class TestDWARFStructs(unittest.TestCase):
    def test_block_forms(self):
        # Include NUL/high-bit bytes and a multi-byte ULEB128 length.
        for little_endian in (True, False):
            ds = DWARFStructs(little_endian=little_endian, dwarf_format=32, address_size=4)
            byteorder = 'little' if little_endian else 'big'
            for payload, uleb_length in (
                (b'', b'\x00'),
                (b'\x00\x80\xff', b'\x03'),
                (bytes(range(129)), b'\x81\x01'),
            ):
                prefixes = {
                    'DW_FORM_block1': len(payload).to_bytes(1, byteorder),
                    'DW_FORM_block2': len(payload).to_bytes(2, byteorder),
                    'DW_FORM_block4': len(payload).to_bytes(4, byteorder),
                    'DW_FORM_block': uleb_length,
                    'DW_FORM_exprloc': uleb_length,
                }
                for form, prefix in prefixes.items():
                    with self.subTest(form=form, little_endian=little_endian, length=len(payload)):
                        parser = ds.Dwarf_dw_form[form]
                        stream = BytesIO(prefix + payload + b'\xaa')
                        value = parser.parse_stream(stream)
                        self.assertIsInstance(value, bytes)
                        self.assertEqual(value, payload)
                        self.assertEqual(stream.read(), b'\xaa')

                        # Reject incomplete lengths and short payloads.
                        with self.assertRaises(ConstructError):
                            parser.parse(prefix[:-1])
                        if payload:
                            with self.assertRaises(ConstructError):
                                parser.parse(prefix + payload[:-1])

    def test_lineprog_header(self):
        ds = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)

        c = ds.Dwarf_lineprog_header.parse(
            b'\x04\x10\x00\x00'    # initial length
            b'\x02\x00'            # version
            b'\x20\x00\x00\x00'    # header length
            b'\x05\x10\x40\x50'    # until and including line_range
            b'\x06'                # opcode_base
            b'\x00\x01\x04\x08\x0C' # standard_opcode_lengths
            # 2 dir names followed by a NULL
            b'\x61\x62\x00\x70\x00\x00'
            # a file entry
            b'\x61\x72\x00\x0C\x0D\x0F'
            # and another entry
            b'\x45\x50\x51\x00\x86\x12\x07\x08'
            # followed by NULL
            b'\x00')
        self.assertEqual(c.version, 2)
        self.assertEqual(c.opcode_base, 6)
        self.assertEqual(c.standard_opcode_lengths, [0, 1, 4, 8, 12])
        self.assertEqual(c.include_directory, [b'ab', b'p'])
        self.assertEqual(len(c.file_entry), 2)
        self.assertEqual(c.file_entry[0].name, b'ar')
        self.assertEqual(c.file_entry[1].name, b'EPQ')
        self.assertEqual(c.file_entry[1].dir_index, 0x12 * 128 + 6)


if __name__ == '__main__':
    unittest.main()
