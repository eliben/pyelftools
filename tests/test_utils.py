import sys, unittest
from cStringIO import StringIO
from random import randint

sys.path.extend(['.', '..'])
from elftools.common.utils import (parse_cstring_from_stream,
        preserve_stream_pos)


class Test_parse_cstring_from_stream(unittest.TestCase):
    def _make_random_string(self, n):
        return ''.join(chr(randint(32, 127)) for i in range(n))
        
    def test_small1(self):
        sio = StringIO('abcdefgh\x0012345')
        self.assertEqual(parse_cstring_from_stream(sio), 'abcdefgh')
        self.assertEqual(parse_cstring_from_stream(sio, 2), 'cdefgh')
        self.assertEqual(parse_cstring_from_stream(sio, 8), '')

    def test_small2(self):
        sio = StringIO('12345\x006789\x00abcdefg\x00iii')
        self.assertEqual(parse_cstring_from_stream(sio), '12345')
        self.assertEqual(parse_cstring_from_stream(sio, 5), '')
        self.assertEqual(parse_cstring_from_stream(sio, 6), '6789')

    def test_large1(self):
        text = 'i' * 400 + '\x00' + 'bb'
        sio = StringIO(text)
        self.assertEqual(parse_cstring_from_stream(sio), 'i' * 400)
        self.assertEqual(parse_cstring_from_stream(sio, 150), 'i' * 250)

    def test_large2(self):
        text = self._make_random_string(5000) + '\x00' + 'jujajaja'
        sio = StringIO(text)
        self.assertEqual(parse_cstring_from_stream(sio), text[:5000])
        self.assertEqual(parse_cstring_from_stream(sio, 2348), text[2348:5000])


class Test_preserve_stream_pos(object):
    def test_basic(self):
        sio = StringIO('abcdef')
        with preserve_stream_pos(sio):
            sio.seek(4)
        self.assertEqual(stream.tell(), 0)

        sio.seek(5)
        with preserve_stream_pos(sio):
            sio.seek(0)
        self.assertEqual(stream.tell(), 5)


if __name__ == '__main__':
    unittest.main()



