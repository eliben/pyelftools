import os
import sys
import unittest
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import StackSizeSection


class TestStackSizes(unittest.TestCase):
    def test_32bit_lsb_stack_sizes(self):
        test_dir = os.path.join('/scratch/daveb/benchmark/pyelftools/test', 'testfiles_for_unittests')

        encodings = ['lsb', 'msb']
        bits = ['32', '64']

        for encoding in encodings:
            for bit in bits:
                with open(os.path.join(test_dir,
                    'stack_sizes_' + encoding + '_' + bit + 'bit.elf'), 'rb') as f:
                    elf = ELFFile(f)
                    stack_section = None
                    for section in elf.iter_sections():
                        if isinstance(section, StackSizeSection):
                            stack_section = section
                            break
                    entries = []

                    for entry in stack_section.iter_stack_sizes():
                        entries.append(entry)

                    self.assertEqual(entries[0]['ss_symbol'], 16)
                    self.assertEqual(entries[0]['ss_size'], 32)
                    self.assertEqual(entries[1]['ss_symbol'], 48)
                    self.assertEqual(entries[1]['ss_size'], 64)

if __name__ == '__main__':
    unittest.main()
