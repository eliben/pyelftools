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
CUs = list(dwarfinfo.iter_CUs())
print 'num CUs:', len(CUs)
print 'CU:', CUs[2]

lp = dwarfinfo.line_program_for_CU(CUs[2])
print 'lp:', lp, lp.header
print 'linetable:', lp.get_line_table()
#for lp in dwarfinfo.iter_line_programs():
    #print lp
    #print lp.header

