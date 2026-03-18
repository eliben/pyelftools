#-------------------------------------------------------------------------------
# elftools tests
#
# Test RISC-V relocation support.
# Verifies the RISC-V-specific relocation calculation functions and that the
# relocation recipe table has correct bytesizes and calc functions.
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest

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


if __name__ == '__main__':
    unittest.main()
