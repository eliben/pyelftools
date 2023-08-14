from elftools.elf.elffile import ELFFile
filepath = 'test\\testfiles_for_readelf\\dwarf_gnuops2.o.elf'

with open(filepath, 'rb') as f:
    elffile = ELFFile(f)
    dwarfinfo = elffile.get_dwarf_info()
    for CU in dwarfinfo.iter_CUs():
        cuname = CU.get_top_DIE().attributes['DW_AT_name'].value.decode('utf-8')
        print("Compile unit %s..." % cuname)
        for DIE in CU.iter_DIEs():
            pass
        pass


