# Just a script for playing around with pyelftools during testing
# please ignore it!
#

from elftools.dwarf.structs import DWARFStructs
from elftools.dwarf.dwarfinfo import DWARFInfo


ds = DWARFStructs(little_endian=True, dwarf_format=32)

print ds.Dwarf_offset('x').parse('\x04\x01\x00\x00')
print ds.Dwarf_initial_length('joe').parse('\xff\xff\xff\xff\x32\x00\x00\x00\x00\x00\x00\x00')


print ds.Dwarf_sleb128('kwa').parse('\x81\x7f')

s = ds.Dwarf_dw_form['DW_FORM_block']
#~ s = ds.Dwarf_dw_form['DW_FORM_addr']

print s.parse('\x04\x12\x13\x13\x16')
#~ print s.parse('\x04\x00\x12\x13')
