/*
To compile:
Linux x86-64
gcc version 8.3.0

gcc -gdwarf-2 -O2 -c llpaira.c
gcc -gdwarf-5 -O2 -o dwarf_llpair.elf llpair.c llpaira.o
*/
#include <stdlib.h>
#include <stdio.h>

extern void a(int n);

void b(int n)
{
    int i;
    for(i=0;i<n;i++)
        printf("%d\n", i*i);
    printf("%d\n", rand()*rand()*rand() + rand()*rand() + rand());
    for(i=0;i<10;i++)
        printf("%d\n", i*i+76543*i);
    printf("%d\n", n);
}

int main()
{
    b(rand());
    return 0;
}