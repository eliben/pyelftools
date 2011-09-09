import sys
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import *

# read a little-endian, 64-bit file
es = ELFStructs(True, 64)

stream = open('binfiles/z.elf', 'rb')
#stream = open('binfiles/z32.elf', 'rb')

efile = ELFFile(stream)

print '===> %s sections!' % efile.num_sections() 
print '===> %s segments!' % efile.num_segments()

for sec in efile.iter_sections():
    print type(sec), sec.name
    if isinstance(sec, SymbolTableSection):
        print '   linked string table:', sec.stringtable.name

for seg in efile.iter_segments():
    print seg['p_type'], seg['p_offset']

for sec in efile.iter_sections():
    if isinstance(sec, SymbolTableSection):
        print 'symbol table "%s ~~~"' % sec.name
        for sym in sec.iter_symbols():
            print '%-26s %s %s' % (sym.name, sym['st_info']['type'], sym['st_info']['bind'])


#~ print 'num', efile.num_sections()
#~ sec = efile.get_section(39)
#~ print sec.header
#~ print sec.name
#~ print sec['sh_type']
#~ print map(ord, sec.data())

#~ print sec.stream
#~ print map(ord, efile._stringtable)

#~ print efile.header
#~ print dir(efile)
#~ print efile['e_type']

#~ shtable_offset = efile['e_shoff']
#~ strtable_section_offset = shtable_offset + efile['e_shstrndx'] * efile['e_shentsize']

#~ # get to the section header for the sh string table
#~ print strtable_section_offset
#~ stream.seek(strtable_section_offset)
#~ sheader = es.Elf_Shdr.parse_stream(stream)
#~ print sheader

#~ # yay, looks correct!!
#~ stream.seek(sheader.sh_offset)
#~ buf = stream.read(sheader.sh_size)
#~ for c in buf:
    #~ sys.stdout.write('%02X' % ord(c))




#~ print es.Elf_Ehdr
