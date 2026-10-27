#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
from pathlib import Path

from elftools.dwarf.die import AttributeValue
from elftools.dwarf.dwarf_expr import DWARFExprParser
from elftools.dwarf.locationlists import LocationParser
from elftools.elf.elffile import ELFFile


class TestLocationAttrubute(unittest.TestCase):
    def test_parsed_location_bytes(self):
        for filename, form in (
            ('sample_exe64.elf', 'DW_FORM_block1'),
            ('dwarf_gnuops1.o', 'DW_FORM_exprloc'),
        ):
            path = Path('test/testfiles_for_unittests') / filename
            with self.subTest(filename=filename), path.open('rb') as stream:
                dwarfinfo = ELFFile(stream).get_dwarf_info()
                cu, attr = next(
                    (cu, die.attributes['DW_AT_location'])
                    for cu in dwarfinfo.iter_CUs()
                    for die in cu.iter_DIEs()
                    if 'DW_AT_location' in die.attributes
                    and die.attributes['DW_AT_location'].form == form)
                self.assertIsInstance(attr.value, bytes)
                self.assertIsInstance(attr.raw_value, bytes)
                self.assertEqual(attr.value, attr.raw_value)
                location = LocationParser(None).parse_from_attribute(attr, cu['version'])
                self.assertIs(location.loc_expr, attr.value)
                self.assertTrue(DWARFExprParser(cu.structs).parse_expr(location.loc_expr))

    def test_has_location(self):
        # This attribute comes from a DWARFv3 binary that doesn't have a location lists
        # section. Before the patch, pyelftools would interpret it as an attribute with a
        # location, more specifically with a location list offset (as opposed to an expression).
        # Meanwhile, by the spec, DW_AT_data_member_location is not even capable
        # of storing a location list offset (since structure layout
        # can't vary by code location). DWARFv3 spec also provides that DW_AT_data_member_location
        # may be a small integer with an offset from the structure's base address, and that
        # seems to be the case here. Ergo, pyelftools should not claim this attribute a location.
        # Since the location/loclist parse function uses the same check, ths fix will
        # prevent such attribute values from being misparsed, also.
        #
        # The notion that member location in a structure had to be a DWARF expression
        # was a misnomer all along - how often does one see a compound datatype
        # with a static member set but a dynamic layout?
        attr = AttributeValue(name='DW_AT_data_member_location', form='DW_FORM_data1', value=0, raw_value=0, offset=402, indirection_length=0)
        self.assertFalse(LocationParser.attribute_has_location(attr, 3))

        # This attribute comes from a DWARFv5 binary. Its form unambiguously tells us it's a
        # location expression. Before the patch, pyelftools would not recognize it as one,
        # because it has a hard-coded list of attributes that may contain a location, and
        # DW_AT_call_target was not in that list.
        attr = AttributeValue(name='DW_AT_call_target', form='DW_FORM_exprloc', value=b'\x50', raw_value=b'\x50', offset=8509, indirection_length=0)
        self.assertTrue(LocationParser.attribute_has_location(attr, 5))

        # This attribute came from the binary in issue #508
        # DW_TAG_subrange_type at 0x45DEA
        attr = AttributeValue(name='DW_AT_upper_bound', form='DW_FORM_exprloc', value=b'\xa3\x01\x5e\x31\x1c', raw_value=b'\xa3\x01\x5e\x31\x1c', offset=286191, indirection_length=0)
        self.assertTrue(LocationParser.attribute_has_location(attr, 5))



if __name__ == '__main__':
    unittest.main()
