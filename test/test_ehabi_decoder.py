# -------------------------------------------------------------------------------
# elftools: tests
#
# LeadroyaL (leadroyal@qq.com)
# This code is in the public domain
# -------------------------------------------------------------------------------

import unittest

from elftools.ehabi.decoder import EHABIBytecodeDecoder


class TestEHABIDecoder(unittest.TestCase):
    """ Tests for the EHABI decoder.
        TODO: This test only tests some split from `readelf -u`. It's not very completed.
    """

    def test1(self):
        mnemonic_array = EHABIBytecodeDecoder([0xb1, 0x08, 0x84, 0x00, 0xb0, 0xb0]).mnemonic_array
        self.assertEqual(4, len(mnemonic_array))
        self.assertEqual(mnemonic_array[0].mnemonic, "pop {r3}")
        self.assertEqual(mnemonic_array[1].mnemonic, "pop {lr}")
        self.assertEqual(mnemonic_array[2].mnemonic, "finish")
        self.assertEqual(mnemonic_array[3].mnemonic, "finish")

    def test2(self):
        mnemonic_array = EHABIBytecodeDecoder([0x1e, 0x3f, 0xaf]).mnemonic_array
        self.assertEqual(3, len(mnemonic_array))
        self.assertEqual(mnemonic_array[0].mnemonic, "vsp = vsp + 124")
        self.assertEqual(mnemonic_array[1].mnemonic, "vsp = vsp + 256")
        self.assertEqual(mnemonic_array[2].mnemonic, "pop {r4, r5, r6, r7, r8, r9, r10, fp, lr}")

    def test3(self):
        mnemonic_array = EHABIBytecodeDecoder([0xb2, 0xac, 0x08, 0xaf, 0xb0, 0xb0]).mnemonic_array
        self.assertEqual(4, len(mnemonic_array))
        self.assertEqual(mnemonic_array[0].mnemonic, "vsp = vsp + 4788")
        self.assertEqual(mnemonic_array[1].mnemonic, "pop {r4, r5, r6, r7, r8, r9, r10, fp, lr}")
        self.assertEqual(mnemonic_array[2].mnemonic, "finish")
        self.assertEqual(mnemonic_array[3].mnemonic, "finish")


if __name__ == '__main__':
    unittest.main()
