#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest

from elftools.dwarf.locationlists import LocationParser
from elftools.dwarf.die import AttributeValue

class TestLocationAttrubute(unittest.TestCase):
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
        attr = AttributeValue(name='DW_AT_call_target', form='DW_FORM_exprloc', value=[80], raw_value=[80], offset=8509, indirection_length=0)
        self.assertTrue(LocationParser.attribute_has_location(attr, 5))

        # This attribute came from the binary in issue #508
        # DW_TAG_subrange_type at 0x45DEA
        attr = AttributeValue(name='DW_AT_upper_bound', form='DW_FORM_exprloc', value=[163, 1, 94, 49, 28], raw_value=[163, 1, 94, 49, 28], offset=286191, indirection_length=0)
        self.assertTrue(LocationParser.attribute_has_location(attr, 5))



if __name__ == '__main__':
    unittest.main()