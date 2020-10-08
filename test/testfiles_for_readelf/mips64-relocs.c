/* This source was compiled for MIPS64 (big endian) and MIPS64EL (little
   endial):

   mips64-unknown-linux-gnu-gcc   -c mips64-relocs.c -o mips64-relocs-be.o.elf -mabi=64
   mips64el-unknown-linux-gnu-gcc -c mips64-relocs.c -o mips64-relocs-le.o.elf -mabi=64
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
