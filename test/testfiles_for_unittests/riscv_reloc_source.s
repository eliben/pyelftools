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
# .text section layout and relocations:
#
#   Bytes 0-15  (R_RISCV_32, R_RISCV_64, R_RISCV_SET6, R_RISCV_SUB6)
#   offset  type            sym     addend   initial   expected
#   ------  --------------  ------  -------  --------  --------
#        0  R_RISCV_32      sym_a       0    00000000  00100000  (sym_a=0x1000, LE)
#        4  R_RISCV_64      sym_b       2    00...00   0700..00  (sym_b+2=0x7, LE 8B)
#       12  R_RISCV_SET6    sym_a       3    C0        C3        (0x1003&0x3F | 0xC0)
#       13  R_RISCV_SUB6    sym_b       0    C7        C2        ((0xC7&0x3F)-0x5)&0x3F | 0xC0
#
#   Bytes 16-22 (SET8, SET16, SET32)
#   offset  type            sym     addend   initial   expected
#   ------  --------------  ------  -------  --------  --------
#       16  R_RISCV_SET8    sym_b       3    00        08        (sym_b+3 = 5+3 = 8)
#       17  R_RISCV_SET16   sym_a       0    0000      0010      (sym_a = 0x1000, LE)
#       19  R_RISCV_SET32   sym_b       7    00000000  0c000000  (sym_b+7 = 12, LE)
#
#   Bytes 23-37 (ADD8, ADD16, ADD32, ADD64)
#   offset  type            sym     addend   initial   expected
#   ------  --------------  ------  -------  --------  --------
#       23  R_RISCV_ADD8    sym_b       0    0a        0f        (10 + 5 = 15)
#       24  R_RISCV_ADD16   sym_b       0    6400      6900      (100 + 5 = 105, LE)
#       26  R_RISCV_ADD32   sym_b       0    e8030000  ed030000  (1000 + 5 = 1005, LE)
#       30  R_RISCV_ADD64   sym_b       0    1027...   1527...   (10000 + 5 = 10005, LE)
#
#   Bytes 38-52 (SUB8, SUB16, SUB32, SUB64)
#   offset  type            sym     addend   initial   expected
#   ------  --------------  ------  -------  --------  --------
#       38  R_RISCV_SUB8    sym_b       0    14        0f        (20 - 5 = 15)
#       39  R_RISCV_SUB16   sym_b       0    c800      c300      (200 - 5 = 195, LE)
#       41  R_RISCV_SUB32   sym_b       0    d0070000  cb070000  (2000 - 5 = 1995, LE)
#       45  R_RISCV_SUB64   sym_b       0    204e...   1b4e...   (20000 - 5 = 19995, LE)

    # Define two absolute symbols used as relocation targets.
    # sym_a and sym_b are global so they appear in the symbol table.
    .global sym_a
    .global sym_b
    sym_a = 0x1000
    sym_b = 0x0005

    .section .text

    # --- Bytes 0-15: R_RISCV_32, R_RISCV_64, R_RISCV_SET6, R_RISCV_SUB6 ---

    # Bytes 0-3: R_RISCV_32 patches this 4-byte word with sym_a + 0
    .byte 0x00, 0x00, 0x00, 0x00
loc4:
    # Bytes 4-11: R_RISCV_64 patches this 8-byte quad with sym_b + 2
    .byte 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
loc12:
    # Byte 12: upper 2 bits (0xC0) must be preserved by R_RISCV_SET6
    .byte 0xC0
loc13:
    # Byte 13: upper 2 bits (0xC0) must be preserved by R_RISCV_SUB6; low 6 bits = 0x07
    .byte 0xC7
    # Bytes 14-15: unrelocated padding
    .byte 0x00, 0x00

    # --- Bytes 16-22: R_RISCV_SET8, R_RISCV_SET16, R_RISCV_SET32 ---

loc16:
    # Byte 16: R_RISCV_SET8 → sym_b(5) + 3 = 8
    .byte 0x00
loc17:
    # Bytes 17-18: R_RISCV_SET16 → sym_a(0x1000) + 0 = 0x1000 (LE: 0x00, 0x10)
    .byte 0x00, 0x00
loc19:
    # Bytes 19-22: R_RISCV_SET32 → sym_b(5) + 7 = 12 (LE: 0x0C, 0x00, 0x00, 0x00)
    .byte 0x00, 0x00, 0x00, 0x00

    # --- Bytes 23-37: R_RISCV_ADD8, ADD16, ADD32, ADD64 ---

loc23:
    # Byte 23: ADD8 initial=10, sym_b(5) → 10 + 5 = 15
    .byte 0x0A
loc24:
    # Bytes 24-25: ADD16 initial=100, sym_b(5) → 100 + 5 = 105 (LE: 0x64, 0x00)
    .byte 0x64, 0x00
loc26:
    # Bytes 26-29: ADD32 initial=1000, sym_b(5) → 1000 + 5 = 1005 (LE: 0xE8, 0x03, ...)
    .byte 0xE8, 0x03, 0x00, 0x00
loc30:
    # Bytes 30-37: ADD64 initial=10000, sym_b(5) → 10000 + 5 = 10005 (LE: 0x10, 0x27, ...)
    .byte 0x10, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00

    # --- Bytes 38-52: R_RISCV_SUB8, SUB16, SUB32, SUB64 ---

loc38:
    # Byte 38: SUB8 initial=20, sym_b(5) → 20 - 5 = 15
    .byte 0x14
loc39:
    # Bytes 39-40: SUB16 initial=200, sym_b(5) → 200 - 5 = 195 (LE: 0xC8, 0x00)
    .byte 0xC8, 0x00
loc41:
    # Bytes 41-44: SUB32 initial=2000, sym_b(5) → 2000 - 5 = 1995 (LE: 0xD0, 0x07, ...)
    .byte 0xD0, 0x07, 0x00, 0x00
loc45:
    # Bytes 45-52: SUB64 initial=20000, sym_b(5) → 20000 - 5 = 19995 (LE: 0x20, 0x4E, ...)
    .byte 0x20, 0x4E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00

    # Explicit relocation entries (GNU as .reloc directive).
    # Syntax: .reloc offset_expr, reloc_type, symbol+addend
    .reloc  0,     R_RISCV_32,   sym_a
    .reloc  loc4,  R_RISCV_64,   sym_b+2
    .reloc  loc12, R_RISCV_SET6, sym_a+3
    .reloc  loc13, R_RISCV_SUB6, sym_b

    .reloc  loc16, R_RISCV_SET8,  sym_b+3
    .reloc  loc17, R_RISCV_SET16, sym_a
    .reloc  loc19, R_RISCV_SET32, sym_b+7

    .reloc  loc23, R_RISCV_ADD8,  sym_b
    .reloc  loc24, R_RISCV_ADD16, sym_b
    .reloc  loc26, R_RISCV_ADD32, sym_b
    .reloc  loc30, R_RISCV_ADD64, sym_b

    .reloc  loc38, R_RISCV_SUB8,  sym_b
    .reloc  loc39, R_RISCV_SUB16, sym_b
    .reloc  loc41, R_RISCV_SUB32, sym_b
    .reloc  loc45, R_RISCV_SUB64, sym_b
