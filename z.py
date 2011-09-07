import sys
from elftools.elf.structs import ELFStructs

# read a little-endian, 64-bit file
es = ELFStructs(True, 64)

stream = open('binfiles/z.elf', 'rb')
eheader = es.Elf_Ehdr.parse_stream(stream)

print eheader

shtable_offset = eheader.e_shoff
strtable_section_offset = shtable_offset + eheader.e_shstrndx * eheader.e_shentsize

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
