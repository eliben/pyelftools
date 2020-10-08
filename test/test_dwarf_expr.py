#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest

from elftools.dwarf.descriptions import ExprDumper, set_global_machine_arch
from elftools.dwarf.dwarf_expr import DWARFExprParser, DWARFExprOp
from elftools.dwarf.structs import DWARFStructs


class TestExprDumper(unittest.TestCase):
    structs32 = DWARFStructs(
            little_endian=True,
            dwarf_format=32,
            address_size=4)

    def setUp(self):
        self.visitor = ExprDumper(self.structs32)
        set_global_machine_arch('x64')

    def test_basic_single(self):
        self.assertEqual(self.visitor.dump_expr([0x1b]),
            'DW_OP_div')

        self.assertEqual(self.visitor.dump_expr([0x74, 0x82, 0x01]),
            'DW_OP_breg4 (rsi): 130')

        self.assertEqual(self.visitor.dump_expr([0x91, 0x82, 0x01]),
            'DW_OP_fbreg: 130')

        self.assertEqual(self.visitor.dump_expr([0x51]),
            'DW_OP_reg1 (rdx)')

        self.assertEqual(self.visitor.dump_expr([0x90, 16]),
            'DW_OP_regx: 16 (rip)')

        self.assertEqual(self.visitor.dump_expr([0x9d, 0x8f, 0x0A, 0x90, 0x01]),
            'DW_OP_bit_piece: 1295 144')

    def test_basic_sequence(self):
        self.assertEqual(self.visitor.dump_expr([0x03, 0x01, 0x02, 0, 0, 0x06, 0x06]),
            'DW_OP_addr: 201; DW_OP_deref; DW_OP_deref')

        self.assertEqual(self.visitor.dump_expr([0x15, 0xFF, 0x0b, 0xf1, 0xff]),
            'DW_OP_pick: 255; DW_OP_const2s: -15')

        self.assertEqual(self.visitor.dump_expr([0x1d, 0x1e, 0x1d, 0x1e, 0x1d, 0x1e]),
            'DW_OP_mod; DW_OP_mul; DW_OP_mod; DW_OP_mul; DW_OP_mod; DW_OP_mul')


class TestParseExpr(unittest.TestCase):
    structs32 = DWARFStructs(
            little_endian=True,
            dwarf_format=32,
            address_size=4)

    def setUp(self):
        set_global_machine_arch('x64')

    def test_single(self):
        p = DWARFExprParser(self.structs32)
        lst = p.parse_expr([0x1b])
        self.assertEqual(lst, [DWARFExprOp(op=0x1B, op_name='DW_OP_div', args=[])])

        lst = p.parse_expr([0x90, 16])
        self.assertEqual(lst, [DWARFExprOp(op=0x90, op_name='DW_OP_regx', args=[16])])


if __name__ == '__main__':
    unittest.main()
