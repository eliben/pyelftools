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
        attr = AttributeValue(name='DW_AT_data_member_location', form='DW_FORM_data1', value=0, raw_value=0, offset=402, indirection_length=0)
        self.assertFalse(LocationParser.attribute_has_location(attr, 3))


if __name__ == '__main__':
    unittest.main()