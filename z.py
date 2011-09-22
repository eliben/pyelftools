# Just a script for playing around with pyelftools during testing
# please ignore it!
#

import sys, pprint
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

dwarfinfo = efile.get_dwarf_info()
tt = dwarfinfo.structs.Dwarf_dw_form['DW_FORM_block1'].parse('\x03\x12\x34\x46')

cu = dwarfinfo.get_CU(1)
print 'CU header', cu.header
topdie = cu.get_top_DIE()

print topdie.size, topdie.attributes

#~ print dwarfinfo.structs.Dwarf_abbrev_entry.parse('\x13\x01\x01\x03\x50\x04\x00\x00')

#~ abbrevtable = dwarfinfo.get_abbrev_table(95)
#~ print id(abbrevtable)
#~ pprint.pprint(abbrevtable._abbrev_map)

#~ ab1 = abbrevtable.get_abbrev(2)
#~ print ab1.has_children()
#~ for name, form in ab1.iter_attr_specs():
    #~ print name, form

#~ print dwarfinfo.get_abbrev_table(0).get_abbrev(1).has_children()

#~ for cu in dwarfinfo._CU:
    #~ print cu, cu.header




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

