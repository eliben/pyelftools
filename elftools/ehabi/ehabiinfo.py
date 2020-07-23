# -------------------------------------------------------------------------------
# elftools: ehabi/ehabiinfo.py
#
# Decoder for ARM exception handler bytecode.
#
# LeadroyaL (leadroyal@qq.com)
# This code is in the public domain
# -------------------------------------------------------------------------------

from ..common.utils import struct_parse
from ..construct.core import Struct
from ..construct.macros import ULInt32

from .decoder import EHABIBytecodeDecoder
from .constants import EHABI_INDEX_ENTRY_SIZE


class EHABIInfo(object):
    """ ARM exception handler abi information class.

        Parameters:

            arm_idx_section:
                elf.sections.Section object, section which type is SHT_ARM_EXIDX.
    """

    def __init__(self, arm_idx_section):
        self._arm_idx_section = arm_idx_section
        self._num_entry = None

    def section_name(self):
        return self._arm_idx_section.name

    def num_entry(self):
        """ Number of exception handler entry in the section.
        """
        if self._num_entry is None:
            self._num_entry = self._arm_idx_section.header['sh_size'] // EHABI_INDEX_ENTRY_SIZE
        return self._num_entry

    def get_entry(self, n):
        """ Get the exception handler entry at index #n. (EHABIEntry object or a subclass)
        """
        if n >= self.num_entry():
            raise IndexError('Invalid entry %d/%d' % (n, self._num_entry))
        eh_index_entry_offset = self._arm_idx_section['sh_offset'] + n * EHABI_INDEX_ENTRY_SIZE
        eh_index_data = struct_parse(Struct(
            'EH_Index',
            ULInt32('Word0'),
            ULInt32('Word1')
        ), self._arm_idx_section.stream, eh_index_entry_offset)
        Word0, Word1 = eh_index_data['Word0'], eh_index_data['Word1']

        if Word0 & 0x80000000 != 0:
            return CorruptEHABIEntry()

        function_offset = arm_expand_prel31(Word0, self._arm_idx_section['sh_offset'] + n * EHABI_INDEX_ENTRY_SIZE)

        if Word1 == 1:
            # 0x1 means cannot unwind
            return CannotUnwindEHABIEntry(function_offset)
        elif Word1 & 0x80000000 == 0:
            # highest bit is zero, point to .ARM.extab data
            eh_table_offset = arm_expand_prel31(Word1, self._arm_idx_section['sh_offset'] + n * EHABI_INDEX_ENTRY_SIZE + 4)
            eh_index_data = struct_parse(Struct(
                'EH_Table',
                ULInt32('Word0'),
            ), self._arm_idx_section.stream, eh_table_offset)
            Word0 = eh_index_data['Word0']
            if Word0 & 0x80000000 == 0:
                # highest bit is one, generic model
                return GenericEHABIEntry(function_offset, arm_expand_prel31(Word0, eh_table_offset))
            else:
                # highest bit is one, arm compact model
                # highest half must be 0b1000 for compact model
                if Word0 & 0x70000000 != 0:
                    print ('Corrupt ARM compact model table entry: %x' % n)
                    return CorruptEHABIEntry()
                per_index = (Word0 >> 24) & 0x7f
                if per_index == 0:
                    # arm compact model 0
                    opcode = [(Word0 & 0xFF0000) >> 16, (Word0 & 0xFF00) >> 8, Word0 & 0xFF]
                    return EHABIEntry(function_offset, per_index, opcode)
                else:
                    # arm compact model 1/2
                    more_word = (Word0 >> 16) & 0xff
                    opcode = [(Word0 >> 8) & 0xff, (Word0 >> 0) & 0xff]
                    self._arm_idx_section.stream.seek(eh_table_offset + 4)
                    for i in range(more_word):
                        r = self._arm_idx_section.stream.read(4)
                        opcode.append((ord(r[3])))
                        opcode.append((ord(r[2])))
                        opcode.append((ord(r[1])))
                        opcode.append((ord(r[0])))
                    return EHABIEntry(function_offset, per_index, opcode, eh_table_offset=eh_table_offset)
        else:
            # highest bit is one, compact model must be 0
            if Word1 & 0x70000000 != 0:
                print('Corrupt ARM compact model table entry: %x' % n)
                return CorruptEHABIEntry()
            opcode = [(Word1 & 0xFF0000) >> 16, (Word1 & 0xFF00) >> 8, Word1 & 0xFF]
            return EHABIEntry(function_offset, 0, opcode)


class EHABIEntry(object):
    """ Exception handler abi entry.

        Accessible attributes:

            function_offset:
                Integer.
                Return None when corrupt.

            personality:
                Integer.
                Return None when corrupt or unwindable.
                0/1/2 for ARM personality compact format.
                Others for generic personality.

            bytecode_array:
                Integer array.
                Return None when corrupt or unwindable.

            eh_table_offset:
                Integer.
                Return None when corrupt or unwindable or ARM inline compact.

            unwindable:
                bool. Whether this function is unwindable.

            corrupt:
                bool. Whether this entry is corrupt.

    """

    def __init__(self,
                 function_offset,
                 personality,
                 bytecode_array,
                 eh_table_offset=None,
                 unwindable=True,
                 corrupt=False
                 ):
        self.function_offset = function_offset
        self.personality = personality
        self.bytecode_array = bytecode_array
        self.eh_table_offset = eh_table_offset
        self.unwindable = unwindable
        self.corrupt = corrupt

    def mnmemonic_array(self):
        if self.bytecode_array:
            return EHABIBytecodeDecoder(self.bytecode_array).mnemonic_array
        else:
            return None

    def __repr__(self):
        return "<EHABIEntry function_offset=0x%x, personality=%d, %sbytecode=%s>" % (
            self.function_offset,
            self.personality,
            "eh_table_offset=0x%x, " % self.eh_table_offset if self.eh_table_offset else "",
            self.bytecode_array)


class CorruptEHABIEntry(EHABIEntry):
    """ This entry is corrupt. Attribute #corrupt will be True.
    """

    def __init__(self):
        super(CorruptEHABIEntry, self).__init__(function_offset=None, personality=None, bytecode_array=None,
                                                corrupt=True)

    def __repr__(self):
        return "<CorruptEHABIEntry>"


class CannotUnwindEHABIEntry(EHABIEntry):
    """ This function cannot be unwind. Attribute #unwindable will be False.
    """

    def __init__(self, function_offset):
        super(CannotUnwindEHABIEntry, self).__init__(function_offset, personality=None, bytecode_array=None,
                                                     unwindable=False)

    def __repr__(self):
        return "<CannotUnwindEHABIEntry function_offset=0x%x>" % self.function_offset


class GenericEHABIEntry(EHABIEntry):
    """ This entry is generic model rather than ARM compact model.Attribute #bytecode_array will be None.
    """

    def __init__(self, function_offset, personality):
        super(GenericEHABIEntry, self).__init__(function_offset, personality, bytecode_array=None)

    def __repr__(self):
        return "<GenericEHABIEntry function_offset=0x%x, personality=0x%x>" % (self.function_offset, self.personality)


def arm_expand_prel31(address, place):
    """
       address: uint32
       place: uint32
       return: uint64
    """
    Location = address & 0x7fffffff
    if Location & 0x04000000:
        Location |= 0xffffffff80000000
    return Location + place & 0xffffffffffffffff
