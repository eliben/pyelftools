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

dinfo = efile.get_dwarf_info()
from elftools.dwarf.locationlists import LocationLists
from elftools.dwarf.descriptions import describe_DWARF_expr
llists = LocationLists(dinfo.debug_loc_sec.stream, dinfo.structs)
for li in  llists.get_location_list_at_offset(0):
    print li
    print describe_DWARF_expr(li.loc_expr, dinfo.structs)


