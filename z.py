# Just a script for playing around with pyelftools during testing
# please ignore it!
#

import sys
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

# read a little-endian, 64-bit file
es = ELFStructs(True, 64)

stream = open('tests/testfiles/z.elf', 'rb')
#stream = open('binfiles/z32.elf', 'rb')

efile = ELFFile(stream)
print efile.elfclass, efile.little_endian
print '===> %s sections!' % efile.num_sections() 

print efile.has_dwarf_info()

print efile.get_dwarf_info()


#~ print efile.get_section_by_name('.debug_info').name

#~ print '===> %s segments!' % efile.num_segments()

#~ for sec in efile.iter_sections():
    #~ print type(sec), sec.name
    #~ if isinstance(sec, SymbolTableSection):
        #~ print '   linked string table:', sec.stringtable.name

#~ for seg in efile.iter_segments():
    #~ print type(seg), seg['p_type'], seg['p_offset']

#~ for sec in efile.iter_sections():
    #~ if isinstance(sec, SymbolTableSection):
        #~ print 'symbol table "%s ~~~"' % sec.name
        #~ for sym in sec.iter_symbols():
            #~ print '%-26s %s %s' % (sym.name, sym['st_info']['type'], sym['st_info']['bind'])

