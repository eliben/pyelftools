#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import random
from io import BytesIO

from elftools.common.construct_utils import ULInt24, UBInt24
from elftools.common.utils import struct_parse

class TestInt24(unittest.TestCase):
    def test_main(self):
        # Testing parsing and building, both LE and BE
        b = random.randbytes(3)

        n = struct_parse(UBInt24(''), BytesIO(b))
        self.assertEqual(n, (b[0] << 16) | (b[1] << 8) | b[2])
        s = UBInt24('').build(n)
        self.assertEqual(s, b)
        
        n = struct_parse(ULInt24(''), BytesIO(b))
        self.assertEqual(n, b[0] | (b[1] << 8) | (b[2] << 16))
        s = ULInt24('').build(n)
        self.assertEqual(s, b)

if __name__ == '__main__':
    unittest.main()