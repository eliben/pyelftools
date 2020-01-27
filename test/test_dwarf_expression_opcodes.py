#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import os, sys

#sys.path.insert(1, os.getcwd())

from elftools.elf.elffile import ELFFile
from elftools.dwarf.locationlists import LocationParser, LocationExpr
from elftools.dwarf.dwarf_expr import DW_OP_opcode2name, GenericExprDumper, DW_OP_opcode2name

class TestDwarfExpressionOpcodes(unittest.TestCase):
    """ Parse all location expressions for every DIE with a location
        make sure all the opcodes are known to the expression parser
    """

    def _test_parse_expression(self, expr, dumper):
        for op in dumper.dump(expr):
            self.assertTrue(op[0] in DW_OP_opcode2name, "Unknown opcode 0x%x" % (op[0]))
            if  DW_OP_opcode2name[op[0]].startswith('DW_OP_GNU_') and not op[0] in self.ops:
                self.ops.add(op[0])
 
    def _test_file(self, filename):
        filepath = os.path.join('test', 'testfiles_for_unittests', filename)
        print('Reading %s...' % (filename))
        with open(filepath, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info()
            location_lists = dwarfinfo.location_lists()
            loc_parser = LocationParser(location_lists)

            self.ops = set()

            for CU in dwarfinfo.iter_CUs():
                ver = CU['version'];
                print("Compile unit %s..." % CU.get_top_DIE().attributes['DW_AT_name'].value.decode('utf-8'))
                dumper = GenericExprDumper(CU.structs)

                for DIE in CU.iter_DIEs():
                    if 'DW_AT_location' in DIE.attributes:
                        ll = loc_parser.parse_from_attribute(DIE.attributes['DW_AT_location'], ver)
                        if isinstance(ll, LocationExpr):
                            self._test_parse_expression(ll.loc_expr, dumper)
                        else: 
                            for loc in ll:
                                self._test_parse_expression(loc.loc_expr, dumper)
                for op in self.ops:
                    print(DW_OP_opcode2name[op])

    def test_main(self):
        self._test_file('dwarf_gnuops1.o')
        self._test_file('dwarf_gnuops2.o')

if __name__ == '__main__':
    unittest.main()