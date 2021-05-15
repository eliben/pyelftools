/* This source was compiled for ppc64le.
   clang --target=powerpc64le -c -o powerpc64-relocs-le.o.elf powerpc64-relocs.c -g
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
}
