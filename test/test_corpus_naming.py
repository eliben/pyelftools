#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.segments import NoteSegment

class TestCoreNotes(unittest.TestCase):
    def scan_under(self, subdir):
        dir = os.path.join('test', subdir)
        for filename in os.listdir(dir):
            name, ext = os.path.splitext(filename)
            if ext == '.elf':
                try:
                    ef = ELFFile.load_from_path(os.path.join(dir, filename))
                    
                    if ef.header.e_type == 'ET_DYN':
                        self.assertTrue('.so.' in filename)
                    elif ef.header.e_type == 'ET_REL':
                        self.assertTrue('.o.' in filename)
                except:
                    pass

    def test_corpus_naming(self):
        self.scan_under('testfiles_for_readelf')
        self.scan_under('testfiles_for_unittests')
        self.scan_under('testfiles_for_dwarfdump')

if __name__ == '__main__':
    unittest.main()