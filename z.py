# Just a script for playing around with pyelftools during testing
# please ignore it!
#

import sys, pprint
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

from elftools.elf.relocation import *

# read a little-endian, 64-bit file
es = ELFStructs(True, 64)

stream = open('tests/testfiles/exe_simple64.elf', 'rb')
#stream = open('binfiles/z32.elf', 'rb')

efile = ELFFile(stream)
print 'elfclass', efile.elfclass
print '===> %s sections!' % efile.num_sections() 

#~ print efile.has_dwarf_info()

dwarfinfo = efile.get_dwarf_info()

for lp in dwarfinfo.iter_line_programs():
    print lp
    print lp.header

