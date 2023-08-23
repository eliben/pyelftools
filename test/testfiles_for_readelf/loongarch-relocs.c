/* This source was compiled for LoongArch64.
   loongarch64-unknown-linux-gnu-gcc -c -o loongarch64-relocs.o.elf loongarch-relocs.c -g
   Upstream support for LoongArch32 is not yet mature, so it is not covered.
*/

extern struct {
  int i, j;
} data;

extern int bar (void);

int
foo (int a)
{
  data.i += a;
  data.j -= bar();
  return 0;
}
