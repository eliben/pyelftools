/* This source was compiled with clang 23, which emits DWARF 5 by default:
   clang --target=x86_64-linux-gnu -c -O2 -g -fdebug-prefix-map=$PWD=/tmp \
       -o dwarf5-clang.o.elf dwarf5-clang.c
   Clang uses the indexed forms (strx, addrx, loclistx, rnglistx), and the
   inlined function from the header gives the line table a second file.
*/

#include "dwarf5-clang.h"

struct sample { const char *name; int value; };

int table[8];
struct sample samples[] = { { "low", 1 }, { "high", 9 } };

int scale(int n)
{
    int s = 0;
    for (int i = 0; i < n; i++)
        s += clamp(table[i & 7] * i, 0, 100);
    return s;
}

int pick(int i)
{
    return clamp(samples[i & 1].value + scale(i), 2, 50);
}
