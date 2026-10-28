/*
 * Issue #364: do not reapply retained DWARF relocations in linked files.
 * Rebuild the three fixtures with Clang and LLD from this directory:
 *
 * clang --target=armv7-none-eabi -g -gdwarf-4 -O0 -fdebug-compilation-dir=. \
 *     -c arm_dwarf_reloc.c -o arm_dwarf_reloc.o.elf
 * ld.lld --emit-relocs --nmagic -Ttext=0x1000 -e main \
 *     arm_dwarf_reloc.o.elf -o arm_dwarf_reloc.elf
 * ld.lld --emit-relocs --nmagic -Ttext=0x1000 -shared \
 *     arm_dwarf_reloc.o.elf -o arm_dwarf_reloc.so.elf
 *
 * The linked executable and shared library retain R_ARM_ABS32 relocations
 * in .debug_info, .debug_line and .debug_frame, but the linker has already
 * applied them. Applying them again doubles the addresses in these sections.
 * In the relocatable object, second has a nonzero symbol value, so its DWARF
 * location also checks that R_ARM_ABS32 still adds the symbol value there.
 */

int first = 1;
int second = 2;

int main(void)
{
    return 0;
}
