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
    """

    def testLLVM(self):
        # Reference: https://github.com/llvm/llvm-project/blob/master/llvm/test/tools/llvm-readobj/ELF/ARM/unwind.s
        mnemonic_array = EHABIBytecodeDecoder([0xb1, 0x0f, 0xa7, 0x3f, 0xb0, 0xb0]).mnemonic_array
        self.assertEqual(mnemonic_array[0].mnemonic, "pop {r0, r1, r2, r3}")
        self.assertEqual(mnemonic_array[1].mnemonic, "pop {r4, r5, r6, r7, r8, r9, r10, fp}")
        self.assertEqual(mnemonic_array[2].mnemonic, "vsp = vsp + 256")
        self.assertEqual(mnemonic_array[3].mnemonic, "finish")
        self.assertEqual(mnemonic_array[4].mnemonic, "finish")

        mnemonic_array = EHABIBytecodeDecoder([0xc9, 0x84, 0xb0]).mnemonic_array
        self.assertEqual(mnemonic_array[0].mnemonic, "pop {d8, d9, d10, d11, d12}")
        self.assertEqual(mnemonic_array[1].mnemonic, "finish")

        mnemonic_array = EHABIBytecodeDecoder(
            [0xD7, 0xC9, 0x02, 0xC8, 0x02, 0xC7, 0x03, 0xC6,
             0x02, 0xC2, 0xBA, 0xB3, 0x12, 0xB2, 0x80, 0x04,
             0xB1, 0x01, 0xB0, 0xA9, 0xA1, 0x91, 0x84, 0xC0,
             0x80, 0xC0, 0x80, 0x01, 0x81, 0x00, 0x80, 0x00,
             0x42, 0x02, ]).mnemonic_array
        self.assertEqual(mnemonic_array[0].mnemonic, "pop {d8, d9, d10, d11, d12, d13, d14, d15}")
        self.assertEqual(mnemonic_array[1].mnemonic, "pop {d0, d1, d2}")
        self.assertEqual(mnemonic_array[2].mnemonic, "pop {d16, d17, d18}")
        self.assertEqual(mnemonic_array[3].mnemonic, "pop {wCGR0, wCGR1}")
        self.assertEqual(mnemonic_array[4].mnemonic, "pop {wR0, wR1, wR2}")
        self.assertEqual(mnemonic_array[5].mnemonic, "pop {wR10, wR11, wR12}")
        self.assertEqual(mnemonic_array[6].mnemonic, "pop {d8, d9, d10}")
        self.assertEqual(mnemonic_array[7].mnemonic, "pop {d1, d2, d3}")
        self.assertEqual(mnemonic_array[8].mnemonic, "vsp = vsp + 2564")
        self.assertEqual(mnemonic_array[9].mnemonic, "pop {r0}")
        self.assertEqual(mnemonic_array[10].mnemonic, "finish")
        self.assertEqual(mnemonic_array[11].mnemonic, "pop {r4, r5, lr}")
        self.assertEqual(mnemonic_array[12].mnemonic, "pop {r4, r5}")
        self.assertEqual(mnemonic_array[13].mnemonic, "vsp = r1")
        self.assertEqual(mnemonic_array[14].mnemonic, "pop {r10, fp, lr}")
        self.assertEqual(mnemonic_array[15].mnemonic, "pop {r10, fp}")
        self.assertEqual(mnemonic_array[16].mnemonic, "pop {r4}")
        self.assertEqual(mnemonic_array[17].mnemonic, "pop {ip}")
        self.assertEqual(mnemonic_array[18].mnemonic, "refuse to unwind")
        self.assertEqual(mnemonic_array[19].mnemonic, "vsp = vsp - 12")
        self.assertEqual(mnemonic_array[20].mnemonic, "vsp = vsp + 12")

        mnemonic_array = EHABIBytecodeDecoder(
            [0xD8, 0xD0, 0xCA, 0xC9, 0x00, 0xC8, 0x00, 0xC7,
             0x10, 0xC7, 0x01, 0xC7, 0x00, 0xC6, 0x00, 0xC0,
             0xB8, 0xB4, 0xB3, 0x00, 0xB2, 0x00, 0xB1, 0x10,
             0xB1, 0x01, 0xB1, 0x00, 0xB0, 0xA8, 0xA0, 0x9F,
             0x9D, 0x91, 0x88, 0x00, 0x80, 0x00, 0x40, 0x00,
             ]).mnemonic_array
        self.assertEqual(mnemonic_array[0].mnemonic, "spare")
        self.assertEqual(mnemonic_array[1].mnemonic, "pop {d8}")
        self.assertEqual(mnemonic_array[2].mnemonic, "spare")
        self.assertEqual(mnemonic_array[3].mnemonic, "pop {d0}")
        self.assertEqual(mnemonic_array[4].mnemonic, "pop {d16}")
        self.assertEqual(mnemonic_array[5].mnemonic, "spare")
        self.assertEqual(mnemonic_array[6].mnemonic, "pop {wCGR0}")
        self.assertEqual(mnemonic_array[7].mnemonic, "spare")
        self.assertEqual(mnemonic_array[8].mnemonic, "pop {wR0}")
        self.assertEqual(mnemonic_array[9].mnemonic, "pop {wR10}")
        self.assertEqual(mnemonic_array[10].mnemonic, "pop {d8}")
        self.assertEqual(mnemonic_array[11].mnemonic, "spare")
        self.assertEqual(mnemonic_array[12].mnemonic, "pop {d0}")
        self.assertEqual(mnemonic_array[13].mnemonic, "vsp = vsp + 516")
        self.assertEqual(mnemonic_array[14].mnemonic, "spare")
        self.assertEqual(mnemonic_array[15].mnemonic, "pop {r0}")
        self.assertEqual(mnemonic_array[16].mnemonic, "spare")
        self.assertEqual(mnemonic_array[17].mnemonic, "finish")
        self.assertEqual(mnemonic_array[18].mnemonic, "pop {r4, lr}")
        self.assertEqual(mnemonic_array[19].mnemonic, "pop {r4}")
        self.assertEqual(mnemonic_array[20].mnemonic, "reserved (WiMMX MOVrr)")
        self.assertEqual(mnemonic_array[21].mnemonic, "reserved (ARM MOVrr)")
        self.assertEqual(mnemonic_array[22].mnemonic, "vsp = r1")
        self.assertEqual(mnemonic_array[23].mnemonic, "pop {pc}")
        self.assertEqual(mnemonic_array[24].mnemonic, "refuse to unwind")
        self.assertEqual(mnemonic_array[25].mnemonic, "vsp = vsp - 4")
        self.assertEqual(mnemonic_array[26].mnemonic, "vsp = vsp + 4")


if __name__ == '__main__':
    unittest.main()
