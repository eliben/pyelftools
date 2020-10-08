/*
clang -g -c aranges_partial_a.c
clang -g -gdwarf-aranges -c aranges_partial_b.c
clang -g aranges_partial_{a,b}.o -o aranges_partial.elf

clang -g -gdwarf-aranges -c aranges_partial_a.c
clang -g -gdwarf-aranges -c aranges_partial_b.c
clang -g aranges_partial_{a,b}.o -o aranges_complete.elf

clang -g -c aranges_partial_a.c
clang -g -c aranges_partial_b.c
clang -g aranges_partial_{a,b}.o -o aranges_absent.elf
*/

extern int test();

int main() {
    int a = test();
    return a;
}
