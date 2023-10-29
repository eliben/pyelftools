/* This source was compiled for s390x.
   gcc -c -o s390x-relocs.o.elf s390x-relocs.c -g
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
