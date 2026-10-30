#-------------------------------------------------------------------------------
# elftools: tests for parsing DIEs with unsupported attribute forms
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import io
import struct
import unittest

from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import DWARFError


def _uleb128(n):
    out = b""
    while True:
        b7 = n & 0x7F
        n >>= 7
        if n:
            out += bytes([b7 | 0x80])
        else:
            return out + bytes([b7])


def _build_dwarf_elf(form_code):
    """Build a minimal ELF64 with a .debug_abbrev/.debug_info pair where the
    single DW_TAG_compile_unit DIE declares one DW_AT_name attribute with the
    given (raw) form code.
    """
    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\x00" * 7
    # abbrev code 1, DW_TAG_compile_unit, no children,
    # DW_AT_name with the requested form code, then the terminator pair
    # and the end-of-abbreviations marker.
    abbrev = (
        _uleb128(1) + _uleb128(0x11) + bytes([0])
        + _uleb128(0x03) + _uleb128(form_code)
        + _uleb128(0) + _uleb128(0)
        + _uleb128(0)
    )
    if form_code == 0x16:  # DW_FORM_indirect: the real form code follows
        die_body = _uleb128(1) + _uleb128(0x00)
    elif form_code == 0x08:  # DW_FORM_string: an inline (empty) string value
        die_body = _uleb128(1) + b"\x00"
    else:
        die_body = _uleb128(1)
    rest = struct.pack("<HI", 4, 0) + bytes([8]) + die_body
    info = struct.pack("<I", len(rest)) + rest

    shstr = b"\x00.debug_abbrev\x00.debug_info\x00.shstrtab\x00"
    NAME_ABBREV, NAME_INFO, NAME_SHSTR = 1, 15, 27

    layout = {}
    cur = 64
    for name, data in (
        (".debug_abbrev", abbrev),
        (".debug_info", info),
        (".shstrtab", shstr),
    ):
        layout[name] = (cur, len(data))
        cur += len(data)

    blob = bytearray(200 + 64 * 4)
    blob[0:64] = struct.pack(
        "<16sHHIQQQIHHHHHH", e_ident, 1, 0x3e, 1, 0x400000, 0, 200, 0,
        64, 56, 0, 64, 4, 3,
    )
    for name, data in (
        (".debug_abbrev", abbrev),
        (".debug_info", info),
        (".shstrtab", shstr),
    ):
        offset, _ = layout[name]
        blob[offset:offset + len(data)] = data

    def make_shdr(name_idx, offset, size):
        return struct.pack("<IIQQQQIIQQ", name_idx, 1, 0, 0, offset, size, 0, 0, 1, 0)

    headers = [
        b"\x00" * 64,
        make_shdr(NAME_ABBREV, *layout[".debug_abbrev"]),
        make_shdr(NAME_INFO, *layout[".debug_info"]),
        make_shdr(NAME_SHSTR, *layout[".shstrtab"]),
    ]
    for i, header in enumerate(headers):
        blob[200 + i * 64: 200 + (i + 1) * 64] = header
    return bytes(blob)


class TestUnknownDIEForm(unittest.TestCase):
    def _iter_dies(self, data):
        elf = ELFFile(io.BytesIO(data))
        for cu in elf.get_dwarf_info().iter_CUs():
            for die in cu.iter_DIEs():
                pass

    def test_unsupported_form_in_abbrev_raises_dwarverror(self):
        # DW_FORM_null (0x00) is a known DWARF form code with no parse
        # construct: the direct abbrev path must report it, not crash.
        data = _build_dwarf_elf(form_code=0x00)
        with self.assertRaises(DWARFError) as cm:
            self._iter_dies(data)
        self.assertIn("DW_FORM_null", str(cm.exception))

    def test_unsupported_form_via_indirect_raises_dwarverror(self):
        # DW_FORM_indirect (0x16) resolving to DW_FORM_null (0x00)
        data = _build_dwarf_elf(form_code=0x16)
        with self.assertRaises(DWARFError) as cm:
            self._iter_dies(data)
        self.assertIn("DW_FORM_null", str(cm.exception))

    def test_valid_dies_still_parse(self):
        # DW_FORM_string (0x08): a supported form; the DIE must parse
        # (the string value is empty, which is fine for this fixture).
        data = _build_dwarf_elf(form_code=0x08)
        self._iter_dies(data)


if __name__ == "__main__":
    unittest.main()
