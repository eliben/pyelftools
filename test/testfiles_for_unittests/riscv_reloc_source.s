# RISC-V relocation test object source
#
# Produces riscv_reloc.o: a RISC-V 64-bit relocatable object used to test
# pyelftools RISC-V relocation support.
#
# Build command:
#   riscv64-linux-gnu-gcc -c riscv_reloc_source.s -o riscv_reloc.o
#
# Tested with:
#   riscv64-linux-gnu-gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0
#   GNU Binutils 2.38
#
# Layout of the .text section (16 bytes) and applied relocations:
#
#   offset  type            sym     addend   initial   expected
#   ------  --------------  ------  -------  --------  --------
#        0  R_RISCV_32      sym_a       0    00000000  00100000  (sym_a=0x1000, LE)
#        4  R_RISCV_64      sym_b       2    00...00   0700..00  (sym_b+2=0x7, LE 8B)
#       12  R_RISCV_SET6    sym_a       3    C0        C3        (0x1003&0x3F | 0xC0)
#       13  R_RISCV_SUB6    sym_b       0    C7        C2        ((0xC7&0x3F)-0x5)&0x3F | 0xC0

    # Define two absolute symbols used as relocation targets.
    # sym_a and sym_b are global so they appear in the symbol table.
    .global sym_a
    .global sym_b
    sym_a = 0x1000
    sym_b = 0x0005

    .section .text

    # Bytes 0-3: R_RISCV_32 patches this 4-byte word with sym_a + 0
    .4byte  0x00000000
loc4:
    # Bytes 4-11: R_RISCV_64 patches this 8-byte quad with sym_b + 2
    .8byte  0x0000000000000000
loc12:
    # Byte 12: upper 2 bits (0xC0) must be preserved by R_RISCV_SET6
    .byte   0xC0
loc13:
    # Byte 13: upper 2 bits (0xC0) must be preserved by R_RISCV_SUB6; low 6 bits = 0x07
    .byte   0xC7
    # Bytes 14-15: unrelocated padding
    .byte   0x00
    .byte   0x00

    # Explicit relocation entries (GNU as .reloc directive).
    # Syntax: .reloc offset_expr, reloc_type, symbol+addend
    .reloc  0,     R_RISCV_32,   sym_a
    .reloc  loc4,  R_RISCV_64,   sym_b+2
    .reloc  loc12, R_RISCV_SET6, sym_a+3
    .reloc  loc13, R_RISCV_SUB6, sym_b
