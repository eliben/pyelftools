
#include <stdio.h>

typedef struct namedFoo {
    int some_int;
    char some_character;
    volatile unsigned long some_volatile_unsigned_long_array[12];
    union {
        long * pointer_to_long;
        char * pointer_to_string;
        void *** triple_void_indirection;
    } some_union;
    int seven_bits: 7;
    int remaining_bit: 1;
    const struct namedFoo * self;
} namedFoo;

typedef struct {
    int member;
} anonymousStruct;

int main()
{
    namedFoo a;
    anonymousStruct b;
    return 0;
}
