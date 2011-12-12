import sys, unittest
from cStringIO import StringIO

sys.path.extend(['.', '..'])
from elftools.dwarf.callframe import (
    CallFrameInfo, CIE, FDE, instruction_name, CallFrameInstruction)
from elftools.dwarf.structs import DWARFStructs


class TestCallFrame(unittest.TestCase):
    def assertInstruction(self, instr, name, args):
        self.assertIsInstance(instr, CallFrameInstruction)
        self.assertEqual(instruction_name(instr.opcode), name)
        self.assertEqual(instr.args, args)
        
    def test_spec_sample_d6(self):
        # D.6 sample in DWARFv3
        s = StringIO()
        data = ('' +
            # first comes the CIE
            '\x20\x00\x00\x00' +        # length
            '\xff\xff\xff\xff' +        # CIE_id
            '\x03\x00\x04\x7c' +        # version, augmentation, caf, daf
            '\x08' +                    # return address
            '\x0c\x07\x00' +
            '\x08\x00' +
            '\x07\x01' +
            '\x07\x02' +
            '\x07\x03' +
            '\x08\x04' +
            '\x08\x05' +
            '\x08\x06' +
            '\x08\x07' +
            '\x09\x08\x01' +
            '\x00' +
            
            # then comes the FDE
            '\x28\x00\x00\x00' +        # length
            '\x00\x00\x00\x00' +        # CIE_pointer (to CIE at 0)
            '\x44\x33\x22\x11' +        # initial_location
            '\x54\x00\x00\x00' +        # address range
            '\x41' +
            '\x0e\x0c' + '\x41' +
            '\x88\x01' + '\x41' +
            '\x86\x02' + '\x41' +
            '\x0d\x06' + '\x41' +
            '\x84\x03' + '\x4b' +
            '\xc4' + '\x41' +
            '\xc6' +
            '\x0d\x07' + '\x41' +
            '\xc8' + '\x41' +
            '\x0e\x00' +
            '\x00\x00'
            )
        s.write(data)

        structs = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)
        cfi = CallFrameInfo(s, len(data), structs)
        entries = cfi.get_entries()

        self.assertEqual(len(entries), 2)
        self.assertIsInstance(entries[0], CIE)
        self.assertEqual(entries[0]['length'], 32)
        self.assertEqual(entries[0]['data_alignment_factor'], -4)
        self.assertEqual(entries[0]['return_address_register'], 8)
        self.assertEqual(len(entries[0].instructions), 11)
        self.assertInstruction(entries[0].instructions[0],
            'DW_CFA_def_cfa', [7, 0])
        self.assertInstruction(entries[0].instructions[8],
            'DW_CFA_same_value', [7])
        self.assertInstruction(entries[0].instructions[9],
            'DW_CFA_register', [8, 1])

        self.assertTrue(isinstance(entries[1], FDE))
        self.assertEqual(entries[1]['length'], 40)
        self.assertEqual(entries[1]['CIE_pointer'], 0)
        self.assertEqual(entries[1]['address_range'], 84)
        self.assertEqual(len(entries[1].instructions), 21)
        self.assertInstruction(entries[1].instructions[0],
            'DW_CFA_advance_loc', [1])
        self.assertInstruction(entries[1].instructions[1],
            'DW_CFA_def_cfa_offset', [12])
        self.assertInstruction(entries[1].instructions[9],
            'DW_CFA_offset', [4, 3])
        self.assertInstruction(entries[1].instructions[18],
            'DW_CFA_def_cfa_offset', [0])
        self.assertInstruction(entries[1].instructions[20],
            'DW_CFA_nop', [])

if __name__ == '__main__':
    unittest.main()


