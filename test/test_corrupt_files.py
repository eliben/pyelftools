"""
Test that elftools does not fail to load corrupted ELF files
"""
import os
import tempfile
import unittest

from elftools.common.exceptions import DWARFError, ELFParseError
from elftools.elf.elffile import ELFFile


class TestCorruptFile(unittest.TestCase):
    def test_elffile_init(self):
        """ Test that ELFFile does not crash when parsing an ELF file with corrupt e_shoff and/or e_shnum
        """
        filepath = os.path.join('test', 'testfiles_for_unittests', 'corrupt_sh.elf')
        with open(filepath, 'rb') as f:
            elf = None

            try:
                elf = ELFFile(f)
            except ELFParseError:
                pass

            self.assertIsInstance(elf, ELFFile, "ELFFile initialization should have detected the out of bounds read")


if __name__ == '__main__':
    unittest.main()


def _read_uleb(data, pos):
    """Read a ULEB128 value; return (value, length in bytes)."""
    value = 0
    shift = 0
    start = pos
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return value, pos - start


def _read_sleb(data, pos):
    """Read a SLEB128 value; return (value, length in bytes)."""
    shift = 0
    start = pos
    while True:
        byte = data[pos]
        pos += 1
        value = byte & 0x7F
        shift += 7
        if not (byte & 0x80):
            if byte & 0x40:
                value |= -(1 << shift)
            break
    return value, pos - start


def _abbrev_first_form_positions(abbrev_data):
    """Parse a .debug_abbrev section into {abbrev code: position of the
    first attribute's form byte, relative to the section start}."""
    entries = {}
    pos = 0
    while pos < len(abbrev_data):
        code, length = _read_uleb(abbrev_data, pos)
        pos += length
        if code == 0:
            break
        _, length = _read_uleb(abbrev_data, pos)  # tag
        pos += length
        pos += 1  # children byte
        first_form_pos = None
        while True:
            name, length = _read_uleb(abbrev_data, pos)
            pos += length
            form_pos = pos
            form, length = _read_uleb(abbrev_data, pos)
            pos += length
            if name == 0 and form == 0:
                break
            if first_form_pos is None:
                first_form_pos = form_pos
            if form == 0x21:  # DW_FORM_implicit_const: SLEB128 value follows
                _, length = _read_sleb(abbrev_data, pos)
                pos += length
        entries[code] = first_form_pos
    return entries


def _write_temp(data):
    with tempfile.NamedTemporaryFile(suffix='.elf', delete=False) as f:
        f.write(data)
        return f.name


class TestMutatedDwarfForms(unittest.TestCase):
    """Mutated DWARF inputs must raise DWARFError, not a raw KeyError.

    DW_FORM_null (code 0x00) is defined in the DW_FORM enum but has no
    parse construct in Dwarf_dw_form; both the direct and the
    DW_FORM_indirect lookup sites used to leak the raw KeyError.
    """

    fixture = os.path.join('test', 'testfiles_for_unittests', 'gmtime_r.o.elf')

    def _iter_all_dies(self, path):
        with open(path, 'rb') as f:
            elf = ELFFile(f)
            for cu in elf.get_dwarf_info().iter_CUs():
                list(cu.iter_DIEs())

    def test_direct_null_form_raises_dwarf_error(self):
        with open(self.fixture, 'rb') as f:
            data = bytearray(f.read())
            elf = ELFFile(f)
            abbrev = elf.get_section_by_name('.debug_abbrev')
        abbrev_data = bytes(
            data[abbrev['sh_offset']:abbrev['sh_offset'] + abbrev['sh_size']])
        # Abbrev code 4 is used by real DIEs in the first CU; patch the
        # form of its first attribute to DW_FORM_null.
        form_pos = _abbrev_first_form_positions(abbrev_data)[4]
        data[abbrev['sh_offset'] + form_pos] = 0x00
        tmp = _write_temp(data)
        try:
            with self.assertRaises(DWARFError):
                self._iter_all_dies(tmp)
        finally:
            os.unlink(tmp)

    def test_indirect_null_form_raises_dwarf_error(self):
        with open(self.fixture, 'rb') as f:
            elf = ELFFile(f)
            dwarfinfo = elf.get_dwarf_info(follow_links=False)
            cu = next(dwarfinfo.iter_CUs())
            # That DIE has an attribute with form DW_FORM_indirect.
            die = next(d for d in cu.iter_DIEs()
                       if d.tag == 'DW_TAG_pointer_type')
            attr = die.attributes['DW_AT_type']
            self.assertEqual(attr.form, 'DW_FORM_ref2')
            info = elf.get_section_by_name('.debug_info')
            # attr.offset points at the indirect form code byte itself.
            file_pos = info['sh_offset'] + attr.offset
        with open(self.fixture, 'rb') as f:
            data = bytearray(f.read())
        data[file_pos] = 0x00  # indirect form code -> DW_FORM_null
        tmp = _write_temp(data)
        try:
            with self.assertRaises(DWARFError):
                self._iter_all_dies(tmp)
        finally:
            os.unlink(tmp)

    def test_unmutated_fixture_iterates_dies(self):
        with open(self.fixture, 'rb') as f:
            elf = ELFFile(f)
            dies = [die for cu in elf.get_dwarf_info().iter_CUs()
                    for die in cu.iter_DIEs()]
        self.assertTrue(len(dies) > 0)
