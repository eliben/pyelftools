try:
    import unittest2 as unittest
except ImportError:
    import unittest
import sys
from random import randint

sys.path.extend(['.', '..'])
from elftools.common.py3compat import int2byte, BytesIO
from elftools.common.utils import (parse_cstring_from_stream,
        preserve_stream_pos)


class Test_parse_cstring_from_stream(unittest.TestCase):
    def _make_random_bytes(self, n):
        return b''.join(int2byte(randint(32, 127)) for i in range(n))
        
    def test_small1(self):
        sio = BytesIO(b'abcdefgh\x0012345')
        self.assertEqual(parse_cstring_from_stream(sio), b'abcdefgh')
        self.assertEqual(parse_cstring_from_stream(sio, 2), b'cdefgh')
        self.assertEqual(parse_cstring_from_stream(sio, 8), b'')

    def test_small2(self):
        sio = BytesIO(b'12345\x006789\x00abcdefg\x00iii')
        self.assertEqual(parse_cstring_from_stream(sio), b'12345')
        self.assertEqual(parse_cstring_from_stream(sio, 5), b'')
        self.assertEqual(parse_cstring_from_stream(sio, 6), b'6789')

    def test_large1(self):
        text = b'i' * 400 + b'\x00' + b'bb'
        sio = BytesIO(text)
        self.assertEqual(parse_cstring_from_stream(sio), b'i' * 400)
        self.assertEqual(parse_cstring_from_stream(sio, 150), b'i' * 250)

    def test_large2(self):
        text = self._make_random_bytes(5000) + b'\x00' + b'jujajaja'
        sio = BytesIO(text)
        self.assertEqual(parse_cstring_from_stream(sio), text[:5000])
        self.assertEqual(parse_cstring_from_stream(sio, 2348), text[2348:5000])


class Test_preserve_stream_pos(object):
    def test_basic(self):
        sio = BytesIO('abcdef')
        with preserve_stream_pos(sio):
            sio.seek(4)
        self.assertEqual(stream.tell(), 0)

        sio.seek(5)
        with preserve_stream_pos(sio):
            sio.seek(0)
        self.assertEqual(stream.tell(), 5)


if __name__ == '__main__':
    unittest.main()



