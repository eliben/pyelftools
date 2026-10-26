/*
 * An inline function's static variable has STB_GNU_UNIQUE binding (issue #92).
 * Build on x86-64 Linux with GCC and GNU binutils, from this directory:
 *
 *   g++ -std=c++11 -fPIC -fgnu-unique -shared -nostdlib -Wl,--build-id=none \
 *       gnu_unique.cpp -o gnu_unique.so.elf
 *   cp gnu_unique.so.elf os_specific_symbol.so.elf
 *   elfedit --output-osabi none os_specific_symbol.so.elf
 *
 * Both .dynsym and .symtab contain the unique symbol. The second fixture
 * changes only EI_OSABI: binding 10 is OS-specific, not UNIQUE, under System V.
 */

inline int& counter()
{
    static int value;
    return value;
}

int* get_counter()
{
    return &counter();
}
