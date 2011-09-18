from elftools.dwarf.structs import DWARFStructs


ds = DWARFStructs(
    little_endian=True,
    dwarfclass=32)

print ds.Dwarf_xword('x').parse('\x04\x01\x00\x00')
print ds.Dwarf_initial_length('joe').parse('\xff\xff\xff\xff\x32\x00\x00\x00\x00\x00\x00\x00')


print ds.Dwarf_sleb128('kwa').parse('\x81\x7f')
