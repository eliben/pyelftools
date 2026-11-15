#-------------------------------------------------------------------------------
# elftools tests
#
# Attribute sections whose entries claim a zero size must be rejected rather
# than being re-parsed forever.
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import io
import itertools
import os
import struct
import unittest

from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile

# Upper bound on entries pulled from a generator, so that a regression shows up
# as a failed assertion instead of a hung test run.
LIMIT = 100


def _elf_with_attributes(attr_bytes):
    """ Return the 32-bit little-endian ARM sample with the contents of its
        .ARM.attributes section replaced by attr_bytes (appended to the file).
    """
    path = os.path.join('test', 'testfiles_for_unittests', 'simple_gcc.elf.arm')
    with open(path, 'rb') as f:
        data = bytearray(f.read())
        f.seek(0)
        elf = ELFFile(f)
        index = elf.get_section_index('.ARM.attributes')
        e_shoff, e_shentsize = elf['e_shoff'], elf['e_shentsize']
    hdr = e_shoff + index * e_shentsize
    # sh_offset and sh_size follow sh_name, sh_type, sh_flags, sh_addr
    struct.pack_into('<II', data, hdr + 16, len(data), len(attr_bytes))
    data += attr_bytes
    return ELFFile(io.BytesIO(bytes(data)))


def _subsection(subsubsection, length=None):
    body = b'aeabi\0' + subsubsection
    if length is None:
        length = 4 + len(body)
    return struct.pack('<I', length) + body


def _subsubsection(size=None):
    attrs = b'\x06\x02'  # Tag_CPU_arch = 2
    if size is None:
        size = 1 + 4 + len(attrs)
    return b'\x01' + struct.pack('<I', size) + attrs


class TestMalformedAttributes(unittest.TestCase):
    def test_valid_two_subsections(self):
        sub = _subsection(_subsubsection())
        sec = _elf_with_attributes(b'A' + sub + sub).get_section_by_name('.ARM.attributes')
        subsecs = list(itertools.islice(sec.iter_subsections(), LIMIT))
        self.assertEqual(len(subsecs), 2)

    def test_zero_length_subsection(self):
        data = b'A' + _subsection(_subsubsection(), length=0)
        sec = _elf_with_attributes(data).get_section_by_name('.ARM.attributes')
        with self.assertRaises(ELFError):
            list(itertools.islice(sec.iter_subsections(), LIMIT))

    def test_zero_size_subsubsection(self):
        data = b'A' + _subsection(_subsubsection(size=0))
        sec = _elf_with_attributes(data).get_section_by_name('.ARM.attributes')
        subsec = next(sec.iter_subsections())
        with self.assertRaises(ELFError):
            list(itertools.islice(subsec.iter_subsubsections(), LIMIT))


if __name__ == '__main__':
    unittest.main()
