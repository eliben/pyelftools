# Just a script for playing around with pyelftools during testing
# please ignore it!
#

import sys, pprint
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

from elftools.elf.relocation import *


stream = open('test/testfiles/exe_simple64.elf', 'rb')

efile = ELFFile(stream)
print 'elfclass', efile.elfclass
print '===> %s sections!' % efile.num_sections() 
print efile.header
