# -------------------------------------------------------------------------------
# elftools: ehabi/structs.py
#
# Encapsulation of Construct structs for parsing an EHABI, adjusted for
# correct endianness and word-size.
#
# LeadroyaL (leadroyal@qq.com)
# This code is in the public domain
# -------------------------------------------------------------------------------

from construct import Int32ub, Int32ul, Struct


class EHABIStructs(object):
    """ Accessible attributes:

            EH_index_struct:
                Struct of item in section .ARM.exidx.

            EH_table_struct:
                Struct of item in section .ARM.extab.
    """

    def __init__(self, little_endian):
        self._little_endian = little_endian
        self._create_structs()

    def _create_structs(self):
        if self._little_endian:
            self.EHABI_uint32 = Int32ul
        else:
            self.EHABI_uint32 = Int32ub
        self._create_exception_handler_index()
        self._create_exception_handler_table()

    def _create_exception_handler_index(self):
        self.EH_index_struct = Struct(
            'word0' / self.EHABI_uint32,
            'word1' / self.EHABI_uint32
        )

    def _create_exception_handler_table(self):
        self.EH_table_struct = Struct(
            'word0' / self.EHABI_uint32,
        )
