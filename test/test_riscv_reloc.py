#-------------------------------------------------------------------------------
# elftools tests
#
# Test RISC-V relocation support.
# Verifies the RISC-V-specific relocation calculation functions, that the
# relocation recipe table has correct bytesizes and calc functions, and that
# end-to-end relocation via RelocationHandler produces correct bytes.
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import struct
import unittest
from io import BytesIO

from elftools.elf.elffile import ELFFile
from elftools.elf.enums import ENUM_RELOC_TYPE_RISCV
from elftools.elf.relocation import (
    RelocationHandler,
    _reloc_calc_sym_plus_addend,
    _reloc_calc_sym_plus_value,
    _reloc_calc_value_minus_sym_addend,
    _reloc_calc_value_plus_sym_6,
    _reloc_calc_value_minus_sym_addend_6,
)


class TestRISCVCalcFunctions(unittest.TestCase):
    """Test the two RISC-V-specific relocation calculation functions."""

    # _reloc_calc_value_plus_sym_6 is used for R_RISCV_SET6:
    #   result = ((sym_value + addend) & 0x3F) | (value & 0xC0)
    # It sets the low 6 bits of the byte to (sym + addend), preserving the
    # upper 2 bits of the original value.

    def test_set6_basic(self):
        result = _reloc_calc_value_plus_sym_6(value=0x00, sym_value=0x0A, offset=0, addend=0)
        self.assertEqual(result, 0x0A)

    def test_set6_preserves_upper_bits(self):
        result = _reloc_calc_value_plus_sym_6(value=0xC0, sym_value=0x0A, offset=0, addend=0)
        self.assertEqual(result, 0xCA)  # 0x0A | 0xC0

    def test_set6_sym_truncated_to_6bits(self):
        result = _reloc_calc_value_plus_sym_6(value=0x00, sym_value=0x7F, offset=0, addend=0)
        self.assertEqual(result, 0x3F)  # 0x7F & 0x3F

    def test_set6_with_addend(self):
        result = _reloc_calc_value_plus_sym_6(value=0x00, sym_value=0x02, offset=0, addend=0x03)
        self.assertEqual(result, 0x05)  # (2 + 3) & 0x3F

    def test_set6_addend_preserves_upper_bits(self):
        result = _reloc_calc_value_plus_sym_6(value=0x80, sym_value=0x01, offset=0, addend=0x02)
        self.assertEqual(result, 0x83)  # 0x03 | 0x80

    # _reloc_calc_value_minus_sym_addend_6 is used for R_RISCV_SUB6:
    #   result = (((value & 0x3F) - sym_value - addend) & 0x3F) | (value & 0xC0)
    # It subtracts (sym + addend) from the low 6 bits, preserving the upper 2 bits.

    def test_sub6_basic(self):
        result = _reloc_calc_value_minus_sym_addend_6(value=0x0A, sym_value=0x03, offset=0, addend=0)
        self.assertEqual(result, 0x07)  # 0x0A - 3

    def test_sub6_preserves_upper_bits(self):
        result = _reloc_calc_value_minus_sym_addend_6(value=0xCA, sym_value=0x03, offset=0, addend=0)
        # value & 0x3F = 0x0A, 0x0A - 3 = 7, | 0xC0 = 0xC7
        self.assertEqual(result, 0xC7)

    def test_sub6_wraps_within_6bits(self):
        # Underflow wraps within 6 bits: (2 - 5) & 0x3F = (-3) & 0x3F = 0x3D
        result = _reloc_calc_value_minus_sym_addend_6(value=0x02, sym_value=0x05, offset=0, addend=0)
        self.assertEqual(result, 0x3D)

    def test_sub6_with_addend(self):
        result = _reloc_calc_value_minus_sym_addend_6(value=0x0F, sym_value=0x02, offset=0, addend=0x03)
        # (0x0F - 2 - 3) & 0x3F = 0x0A
        self.assertEqual(result, 0x0A)

    def test_sub6_wrap_preserves_upper_bits(self):
        result = _reloc_calc_value_minus_sym_addend_6(value=0x42, sym_value=0x05, offset=0, addend=0)
        # value & 0x3F = 0x02, 0x02 - 5 = -3, & 0x3F = 0x3D, | (0x42 & 0xC0=0x40) = 0x7D
        self.assertEqual(result, 0x7D)

    def test_set6_sub6_inverse(self):
        # Applying SET6 then SUB6 with the same sym should restore original value's low 6 bits
        original = 0x2A  # arbitrary 6-bit value
        sym = 0x10
        set_result = _reloc_calc_value_plus_sym_6(value=0x00, sym_value=sym, offset=0, addend=0)
        sub_result = _reloc_calc_value_minus_sym_addend_6(value=set_result, sym_value=sym, offset=0, addend=0)
        self.assertEqual(sub_result & 0x3F, 0x00)


class TestRISCVRelocationRecipes(unittest.TestCase):
    """Verify the RISC-V relocation recipe table has correct entries."""

    def setUp(self):
        self.recipes = RelocationHandler._RELOCATION_RECIPES_RISCV

    def test_r_riscv_32(self):
        recipe = self.recipes[ENUM_RELOC_TYPE_RISCV['R_RISCV_32']]
        self.assertEqual(recipe.bytesize, 4)
        self.assertTrue(recipe.has_addend)
        self.assertEqual(recipe.calc_func, _reloc_calc_sym_plus_addend)

    def test_r_riscv_64(self):
        recipe = self.recipes[ENUM_RELOC_TYPE_RISCV['R_RISCV_64']]
        self.assertEqual(recipe.bytesize, 8)
        self.assertTrue(recipe.has_addend)
        self.assertEqual(recipe.calc_func, _reloc_calc_sym_plus_addend)

    def test_r_riscv_add_sub_bytesizes(self):
        for suffix, expected_size in [('8', 1), ('16', 2), ('32', 4), ('64', 8)]:
            with self.subTest(suffix=suffix):
                add_recipe = self.recipes[ENUM_RELOC_TYPE_RISCV[f'R_RISCV_ADD{suffix}']]
                sub_recipe = self.recipes[ENUM_RELOC_TYPE_RISCV[f'R_RISCV_SUB{suffix}']]
                self.assertEqual(add_recipe.bytesize, expected_size)
                self.assertEqual(sub_recipe.bytesize, expected_size)
                self.assertEqual(add_recipe.calc_func, _reloc_calc_sym_plus_value)
                self.assertEqual(sub_recipe.calc_func, _reloc_calc_value_minus_sym_addend)

    def test_r_riscv_set6(self):
        recipe = self.recipes[ENUM_RELOC_TYPE_RISCV['R_RISCV_SET6']]
        self.assertEqual(recipe.bytesize, 1)
        self.assertTrue(recipe.has_addend)
        self.assertEqual(recipe.calc_func, _reloc_calc_value_plus_sym_6)

    def test_r_riscv_sub6(self):
        recipe = self.recipes[ENUM_RELOC_TYPE_RISCV['R_RISCV_SUB6']]
        self.assertEqual(recipe.bytesize, 1)
        self.assertTrue(recipe.has_addend)
        self.assertEqual(recipe.calc_func, _reloc_calc_value_minus_sym_addend_6)

    def test_r_riscv_set8_set16_set32(self):
        for suffix, expected_size in [('8', 1), ('16', 2), ('32', 4)]:
            with self.subTest(suffix=suffix):
                recipe = self.recipes[ENUM_RELOC_TYPE_RISCV[f'R_RISCV_SET{suffix}']]
                self.assertEqual(recipe.bytesize, expected_size)
                self.assertEqual(recipe.calc_func, _reloc_calc_sym_plus_addend)


class TestRISCVRelocationEndToEnd(unittest.TestCase):
    """End-to-end tests using a real RISC-V ELF relocatable object.

    riscv_reloc.o is compiled from riscv_reloc_source.s using:
        riscv64-linux-gnu-gcc -c riscv_reloc_source.s -o riscv_reloc.o

    The assembler folds absolute symbol values into the RELA addend
    (sym_idx=0), so the effective computation uses sym_value=0 and the full
    symbol value as addend. All types in _RELOCATION_RECIPES_RISCV are covered.
    """

    def _apply_relocations(self, elf):
        text = elf.get_section_by_name('.text')
        rela = elf.get_section_by_name('.rela.text')
        stream = BytesIO(text.data())
        RelocationHandler(elf).apply_section_relocations(stream, rela)
        return stream.getvalue()

    def test_riscv_reloc_o(self):
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'riscv_reloc.o'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'RISC-V')
            result = self._apply_relocations(elf)

        # R_RISCV_32 at offset 0: sym_a(0x1000) + addend(0) = 0x1000 (4 bytes LE)
        self.assertEqual(result[0:4], b'\x00\x10\x00\x00')

        # R_RISCV_64 at offset 4: sym_b(0x0005) + addend(2) = 0x0007 (8 bytes LE)
        self.assertEqual(result[4:12], b'\x07\x00\x00\x00\x00\x00\x00\x00')

        # R_RISCV_SET6 at offset 12: (sym_a+3)&0x3F | (0xC0&0xC0) = 0x03|0xC0 = 0xC3
        self.assertEqual(result[12], 0xC3)

        # R_RISCV_SUB6 at offset 13: ((0xC7&0x3F)-sym_b-0)&0x3F | (0xC7&0xC0)
        #                            = (0x07-0x05)&0x3F | 0xC0 = 0x02|0xC0 = 0xC2
        self.assertEqual(result[13], 0xC2)

        # Unrelocated bytes remain zero
        self.assertEqual(result[14:16], b'\x00\x00')

    def test_riscv_set8_set16_set32(self):
        """R_RISCV_SET8/16/32: result = sym_value + addend, written as N bytes."""
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'riscv_reloc.o'), 'rb') as f:
            elf = ELFFile(f)
            by_type = {r['r_info_type']: r['r_offset']
                       for r in elf.get_section_by_name('.rela.text').iter_relocations()}
            result = self._apply_relocations(elf)

        R = ENUM_RELOC_TYPE_RISCV
        # SET8:  addend = sym_b(5) + 3 = 8
        off = by_type[R['R_RISCV_SET8']]
        self.assertEqual(result[off:off+1], struct.pack('<B', 8))
        # SET16: addend = sym_a(0x1000)
        off = by_type[R['R_RISCV_SET16']]
        self.assertEqual(result[off:off+2], struct.pack('<H', 0x1000))
        # SET32: addend = sym_b(5) + 7 = 12
        off = by_type[R['R_RISCV_SET32']]
        self.assertEqual(result[off:off+4], struct.pack('<I', 12))

    def test_riscv_add8_add16_add32_add64(self):
        """R_RISCV_ADD*: result = initial_value + sym_value + addend."""
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'riscv_reloc.o'), 'rb') as f:
            elf = ELFFile(f)
            by_type = {r['r_info_type']: r['r_offset']
                       for r in elf.get_section_by_name('.rela.text').iter_relocations()}
            result = self._apply_relocations(elf)

        R = ENUM_RELOC_TYPE_RISCV
        # ADD8:  initial=10,    sym_b(5) → 10 + 5 = 15
        off = by_type[R['R_RISCV_ADD8']]
        self.assertEqual(result[off:off+1], struct.pack('<B', 15))
        # ADD16: initial=100,   sym_b(5) → 100 + 5 = 105
        off = by_type[R['R_RISCV_ADD16']]
        self.assertEqual(result[off:off+2], struct.pack('<H', 105))
        # ADD32: initial=1000,  sym_b(5) → 1000 + 5 = 1005
        off = by_type[R['R_RISCV_ADD32']]
        self.assertEqual(result[off:off+4], struct.pack('<I', 1005))
        # ADD64: initial=10000, sym_b(5) → 10000 + 5 = 10005
        off = by_type[R['R_RISCV_ADD64']]
        self.assertEqual(result[off:off+8], struct.pack('<Q', 10005))

    def test_riscv_sub8_sub16_sub32_sub64(self):
        """R_RISCV_SUB*: result = initial_value - sym_value - addend."""
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'riscv_reloc.o'), 'rb') as f:
            elf = ELFFile(f)
            by_type = {r['r_info_type']: r['r_offset']
                       for r in elf.get_section_by_name('.rela.text').iter_relocations()}
            result = self._apply_relocations(elf)

        R = ENUM_RELOC_TYPE_RISCV
        # SUB8:  initial=20,    sym_b(5) → 20 - 5 = 15
        off = by_type[R['R_RISCV_SUB8']]
        self.assertEqual(result[off:off+1], struct.pack('<B', 15))
        # SUB16: initial=200,   sym_b(5) → 200 - 5 = 195
        off = by_type[R['R_RISCV_SUB16']]
        self.assertEqual(result[off:off+2], struct.pack('<H', 195))
        # SUB32: initial=2000,  sym_b(5) → 2000 - 5 = 1995
        off = by_type[R['R_RISCV_SUB32']]
        self.assertEqual(result[off:off+4], struct.pack('<I', 1995))
        # SUB64: initial=20000, sym_b(5) → 20000 - 5 = 19995
        off = by_type[R['R_RISCV_SUB64']]
        self.assertEqual(result[off:off+8], struct.pack('<Q', 19995))


if __name__ == '__main__':
    unittest.main()
