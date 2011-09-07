from elftools.elf.structs import ELFStructs

es = ELFStructs(True, 64)


stream = open('binfiles/z.elf', 'rb')
print es.Elf_Ehdr.parse_stream(stream)


#~ print es.Elf_Ehdr
