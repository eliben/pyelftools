import sys
from elftools.elf.structs import ELFStructs
from elftools.elf.elffile import ELFFile

# read a little-endian, 64-bit file
es = ELFStructs(True, 64)

stream = open('binfiles/z.elf', 'rb')

efile = ELFFile(stream)

#~ print efile.header
#~ print dir(efile)
#~ print efile['e_type']

shtable_offset = efile['e_shoff']
strtable_section_offset = shtable_offset + efile['e_shstrndx'] * efile['e_shentsize']

# get to the section header for the sh string table
print strtable_section_offset
stream.seek(strtable_section_offset)
sheader = es.Elf_Shdr.parse_stream(stream)
print sheader

# yay, looks correct!!
stream.seek(sheader.sh_offset)
buf = stream.read(sheader.sh_size)
for c in buf:
    sys.stdout.write('%02X' % ord(c))




#~ print es.Elf_Ehdr
