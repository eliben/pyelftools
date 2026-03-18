#!/usr/bin/env python3
"""Generator for riscv_reloc.o - a minimal synthetic RISC-V 64-bit ELF
relocatable object used to test pyelftools RISC-V relocation support.

Run this script to regenerate the binary:
    python3 riscv_reloc_gen.py

Layout of the .text section (16 bytes) and applied relocations:

  offset  type            sym    addend   initial   expected
  ------  --------------  -----  -------  --------  --------
       0  R_RISCV_32      sym_a       0   00000000  00100000  (sym_a=0x1000, LE)
       4  R_RISCV_64      sym_b       2   00...00   07000000  (sym_b+2=0x7, LE 8B)
      12  R_RISCV_SET6    sym_a       3   C0        C3        (0x1003&0x3F | 0xC0)
      13  R_RISCV_SUB6    sym_b       0   C7        C2        ((0x7-5)&0x3F | 0xC0)
"""
import struct
import os


def build():
    # ELF constants
    ELFMAG       = b'\x7fELF'
    ELFCLASS64   = 2
    ELFDATA2LSB  = 1
    ET_REL       = 1
    EM_RISCV     = 243
    EV_CURRENT   = 1
    SHT_NULL     = 0
    SHT_PROGBITS = 1
    SHT_SYMTAB   = 2
    SHT_STRTAB   = 3
    SHT_RELA     = 4
    SHF_ALLOC    = 0x2
    SHF_EXECINSTR = 0x4
    SHF_INFO_LINK = 0x40
    STB_GLOBAL   = 1
    SHN_ABS      = 0xFFF1
    EF_RISCV_FLOAT_ABI_DOUBLE = 0x0004

    # RISC-V relocation types
    R_RISCV_32   = 1
    R_RISCV_64   = 2
    R_RISCV_SUB6 = 52
    R_RISCV_SET6 = 53

    # Symbol values
    SYM_A = 0x1000
    SYM_B = 0x0005

    # ------------------------------------------------------------------ #
    # Section data
    # ------------------------------------------------------------------ #

    # .text: 16 bytes; meaningful initial bytes only at offsets 12 and 13
    # (the upper 2 bits matter for SET6/SUB6 upper-bit-preservation tests)
    text_data = b'\x00' * 12 + b'\xC0\xC7' + b'\x00' * 2

    # Symbol string table: \0 sym_a \0 sym_b \0
    strtab_data = b'\x00sym_a\x00sym_b\x00'
    SYM_A_NAME = 1   # offset of "sym_a" in strtab
    SYM_B_NAME = 7   # offset of "sym_b" in strtab

    # Section name string table
    # offsets: NULL=0  .text=1  .rela.text=7  .symtab=18  .strtab=26  .shstrtab=34
    shstrtab_data = b'\x00.text\x00.rela.text\x00.symtab\x00.strtab\x00.shstrtab\x00'

    # Symbol table: NULL, sym_a (global abs 0x1000), sym_b (global abs 0x0005)
    # Elf64_Sym: st_name(4) st_info(1) st_other(1) st_shndx(2) st_value(8) st_size(8)
    def sym64(name, bind, shndx, value):
        return struct.pack('<IBBHQQ', name, (bind << 4), 0, shndx, value, 0)

    symtab_data = (sym64(0, 0, 0, 0) +
                   sym64(SYM_A_NAME, STB_GLOBAL, SHN_ABS, SYM_A) +
                   sym64(SYM_B_NAME, STB_GLOBAL, SHN_ABS, SYM_B))

    # Relocations (RELA): Elf64_Rela: r_offset(8) r_info(8) r_addend(8)
    def rela64(offset, sym_idx, rtype, addend):
        return struct.pack('<QQq', offset, (sym_idx << 32) | rtype, addend)

    # R_RISCV_32  @ 0:  sym_a + 0       = 0x1000
    # R_RISCV_64  @ 4:  sym_b + 2       = 0x0007
    # R_RISCV_SET6 @12: (sym_a+3)&0x3F | (0xC0&0xC0) = 0x03 | 0xC0 = 0xC3
    # R_RISCV_SUB6 @13: ((0xC7&0x3F)-sym_b-0)&0x3F | (0xC7&0xC0) = 0x02|0xC0 = 0xC2
    rela_data = (rela64(0,  1, R_RISCV_32,   0) +
                 rela64(4,  2, R_RISCV_64,   2) +
                 rela64(12, 1, R_RISCV_SET6, 3) +
                 rela64(13, 2, R_RISCV_SUB6, 0))

    # ------------------------------------------------------------------ #
    # File layout
    # ------------------------------------------------------------------ #
    ELF_HDR_SIZE = 64
    SHDR_SIZE    = 64

    text_off     = ELF_HDR_SIZE
    rela_off     = text_off     + len(text_data)
    symtab_off   = rela_off     + len(rela_data)
    strtab_off   = symtab_off   + len(symtab_data)
    shstrtab_off = strtab_off   + len(strtab_data)
    # align section headers to 8 bytes
    shdrs_off    = shstrtab_off + len(shstrtab_data)
    shdrs_off    = (shdrs_off + 7) & ~7
    padding      = shdrs_off - (shstrtab_off + len(shstrtab_data))

    NUM_SECTIONS = 6  # NULL .text .rela.text .symtab .strtab .shstrtab

    # ------------------------------------------------------------------ #
    # ELF header
    # ------------------------------------------------------------------ #
    e_ident = (ELFMAG +
               bytes([ELFCLASS64, ELFDATA2LSB, EV_CURRENT, 0]) +
               b'\x00' * 8)
    elf_hdr = struct.pack('<16sHHIQQQIHHHHHH',
        e_ident,
        ET_REL, EM_RISCV, EV_CURRENT,
        0,           # e_entry
        0,           # e_phoff
        shdrs_off,   # e_shoff
        EF_RISCV_FLOAT_ABI_DOUBLE,
        ELF_HDR_SIZE, 56, 0,   # ehsize, phentsize, phnum
        SHDR_SIZE, NUM_SECTIONS,
        5,           # e_shstrndx (.shstrtab)
    )

    # ------------------------------------------------------------------ #
    # Section headers
    # Elf64_Shdr: sh_name(4) sh_type(4) sh_flags(8) sh_addr(8)
    #             sh_offset(8) sh_size(8) sh_link(4) sh_info(4)
    #             sh_addralign(8) sh_entsize(8)
    # ------------------------------------------------------------------ #
    def shdr64(name, stype, flags, offset, size, link, info, align, entsize):
        return struct.pack('<IIQQQQIIQQ',
                           name, stype, flags, 0, offset, size,
                           link, info, align, entsize)

    shdrs = (
        shdr64(0,  SHT_NULL,     0,                          0,           0,              0, 0, 0, 0) +   # 0 NULL
        shdr64(1,  SHT_PROGBITS, SHF_ALLOC|SHF_EXECINSTR,   text_off,    len(text_data), 0, 0, 4, 0) +   # 1 .text
        shdr64(7,  SHT_RELA,     SHF_INFO_LINK,              rela_off,    len(rela_data), 3, 1, 8, 24) +  # 2 .rela.text  (link=.symtab=3, info=.text=1)
        shdr64(18, SHT_SYMTAB,   0,                          symtab_off,  len(symtab_data), 4, 1, 8, 24) + # 3 .symtab (link=.strtab=4, info=first global=1)
        shdr64(26, SHT_STRTAB,   0,                          strtab_off,  len(strtab_data), 0, 0, 1, 0) + # 4 .strtab
        shdr64(34, SHT_STRTAB,   0,                          shstrtab_off, len(shstrtab_data), 0, 0, 1, 0) # 5 .shstrtab
    )

    return (elf_hdr + text_data + rela_data + symtab_data +
            strtab_data + shstrtab_data + b'\x00' * padding + shdrs)


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(__file__), 'riscv_reloc.o')
    data = build()
    with open(out, 'wb') as f:
        f.write(data)
    print(f'Written {len(data)} bytes to {out}')
