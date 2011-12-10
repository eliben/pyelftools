# Just a script for playing around with pyelftools during testing
# please ignore it!
#

import sys, pprint
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

from elftools.elf.relocation import *


stream = open('tests/testfiles/exe_simple64.elf', 'rb')
#stream = open('binfiles/z32.elf', 'rb')

efile = ELFFile(stream)
print 'elfclass', efile.elfclass
print '===> %s sections!' % efile.num_sections() 

#~ print efile.has_dwarf_info()

dwarfinfo = efile.get_dwarf_info()
cfi_entries = dwarfinfo.CFI_entries()
