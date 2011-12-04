import sys, unittest
from cStringIO import StringIO

sys.path.extend(['.', '..'])
from elftools.dwarf.lineprogram import LineProgram, LineState
from elftools.dwarf.structs import DWARFStructs


class TestLineProgram(unittest.TestCase):
    def _make_program_in_stream(self, stream):
        """ Create a LineProgram from the given program encoded in a stream
        """
        ds = DWARFStructs(little_endian=True, dwarf_format=32, address_size=4)
        header = ds.Dwarf_lineprog_header.parse(
            '\x04\x10\x00\x00' +    # initial lenght
            '\x03\x00' +            # version
            '\x20\x00\x00\x00' +    # header length
            '\x01\x01\x01\x0F' +    # flags
            '\x0A' +                # opcode_base
            '\x00\x01\x04\x08\x0C\x01\x01\x01\x00' + # standard_opcode_lengths
            # 2 dir names followed by a NULL
            '\x61\x62\x00\x70\x00\x00' + 
            # a file entry
            '\x61\x72\x00\x0C\x0D\x0F' + 
            # and another entry
            '\x45\x50\x51\x00\x86\x12\x07\x08' +
            # followed by NULL
            '\x00')

        lp = LineProgram(header, stream, ds, 0, len(stream.getvalue()))
        return lp
        
    def assertLineState(self, state, **kwargs):
        """ Assert that the state attributes specified in kwargs have the given
            values (the rest are default).
        """
        for k, v in kwargs.iteritems():
            self.assertEqual(getattr(state, k), v)
        
    def test_spec_sample_59(self):
        # Sample in figure 59 of DWARFv3
        s = StringIO()
        s.write(
            '\x02\xb9\x04' +
            '\x0b' +
            '\x38' +
            '\x82' +
            '\x73' +
            '\x02\x02' +
            '\x00\x01\x01')

        lp = self._make_program_in_stream(s)
        linetable = lp.get_line_table()

        self.assertLineState(linetable[0], address=0x239, line=3)
        self.assertLineState(linetable[1], address=0x23c, line=5)
        self.assertLineState(linetable[2], address=0x244, line=6)
        self.assertLineState(linetable[3], address=0x24b, line=7, end_sequence=False)
        self.assertLineState(linetable[4], address=0x24d, line=7, end_sequence=True)

    def test_spec_sample_60(self):
        # Sample in figure 60 of DWARFv3
        s = StringIO()
        s.write(
            '\x09\x39\x02' +
            '\x0b' +
            '\x09\x03\x00' +
            '\x0b' +
            '\x09\x08\x00' +
            '\x0a' +
            '\x09\x07\x00' +
            '\x0a' +
            '\x09\x02\x00' +
            '\x00\x01\x01')

        lp = self._make_program_in_stream(s)
        linetable = lp.get_line_table()

        self.assertLineState(linetable[0], address=0x239, line=3)
        self.assertLineState(linetable[1], address=0x23c, line=5)
        self.assertLineState(linetable[2], address=0x244, line=6)
        self.assertLineState(linetable[3], address=0x24b, line=7, end_sequence=False)
        self.assertLineState(linetable[4], address=0x24d, line=7, end_sequence=True)


if __name__ == '__main__':
    unittest.main()

