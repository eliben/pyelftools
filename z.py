# Just a script for playing around with pyelftools during testing
# please ignore it!
#

import sys, pprint
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

# read a little-endian, 64-bit file
es = ELFStructs(True, 64)

stream = open('tests/testfiles/exe_simple64.elf', 'rb')
#stream = open('binfiles/z32.elf', 'rb')

efile = ELFFile(stream)
print efile.elfclass, efile.little_endian
print '===> %s sections!' % efile.num_sections() 

#~ print efile.has_dwarf_info()

#~ dwarfinfo = efile.get_dwarf_info()

#~ cu = dwarfinfo.get_CU(3)
#~ print 'CU header', cu.header
#~ topdie = cu.get_top_DIE()

#~ c = topdie.iter_children().next()

#~ print c

#~ print 'siblings.....'

#~ for s in c.iter_siblings():
    #~ print s

from elftools.dwarf.location_expr import DW_OP_name2opcode, DW_OP_opcode2name

print hex(DW_OP_name2opcode['DW_OP_lit14'])
print DW_OP_opcode2name[0x0e]


