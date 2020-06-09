/* This source was compiled for aarch64 (little endian).
   aarch64-linux-gnu-gcc -c -o aarch64-relocs-le.o.elf aarch64-relocs.c -g
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
