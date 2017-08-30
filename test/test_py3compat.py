#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest

from elftools.common.py3compat import (iterbytes, iterkeys, itervalues,
                                       iteritems)


class TestPy3Compat(unittest.TestCase):
    def test_iterbytes(self):
        bi = iterbytes(b'fo1')
        self.assertEqual(next(bi), b'f')
        self.assertEqual(next(bi), b'o')
        self.assertEqual(next(bi), b'1')
        with self.assertRaises(StopIteration):
            next(bi)

    def test_iterdict(self):
        d = {1: 'foo', 2: 'bar'}
        self.assertEqual(list(sorted(iterkeys(d))), [1, 2])
        self.assertEqual(list(sorted(itervalues(d))), ['bar', 'foo'])
        self.assertEqual(list(sorted(iteritems(d))), [(1, 'foo'), (2, 'bar')])


if __name__ == '__main__':
    unittest.main()
