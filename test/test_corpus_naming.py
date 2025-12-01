#------------------------------------------------------------------------------
# Enforce consistency of test naming for some testfiles.
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.segments import NoteSegment

class TestCorpusNaming(unittest.TestCase):
    def scan_under(self, subdir):
        dir = os.path.join('test', subdir)
        for filename in os.listdir(dir):
            name, ext = os.path.splitext(filename)
            if ext == '.elf':
                with ELFFile.load_from_path(os.path.join(dir, filename)) as ef:
                    _, pre_ext = os.path.splitext(name)
                    if ef.header.e_type == 'ET_DYN':
                        self.assertEqual(pre_ext, '.so', f'{filename} is ET_DYN')
                    elif ef.header.e_type == 'ET_REL':
                        self.assertEqual(pre_ext, '.o', f'{filename} is ET_REL')

    def test_corpus_naming(self):
        self.scan_under('testfiles_for_readelf')
        self.scan_under('testfiles_for_unittests')
        self.scan_under('testfiles_for_dwarfdump')

if __name__ == '__main__':
    unittest.main()
