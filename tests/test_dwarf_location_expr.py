import sys, unittest

sys.path.extend(('..', '.'))
from elftools.dwarf.location_expr import (
        GenericLocationExprVisitor, DW_OP_opcode2name)
from elftools.dwarf.structs import DWARFStructs


class MyTestVisitor(GenericLocationExprVisitor):
    def __init__(self, structs):
        super(MyTestVisitor, self).__init__(structs)
        self.results = []
        
    def _after_visit(self, opcode, opcode_name, *args):
        self.results.append((opcode_name, args))
        

class TestGenericLocationExprVisitor(unittest.TestCase):
    structs32 = DWARFStructs(
            little_endian=True,
            dwarf_format=32,
            address_size=4)

    def test_basic(self):
        visitor = MyTestVisitor(self.structs32)
        visitor.process_expr([0x03, 0x01, 0x02, 0, 0, 0x06, 0x06])
        print visitor.results


if __name__ == '__main__':
    unittest.main()

