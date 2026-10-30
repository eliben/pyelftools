/* The locations of thread-local variables in the debug info of an object file
   are relocated with R_X86_64_DTPOFF32 (gcc), R_X86_64_DTPOFF64 (clang) or
   R_386_TLS_LDO_32 (gcc -m32):

   gcc -c -O1 -g -o tls_relocs_x64_gcc.o tls_relocs.c
   clang -c -O1 -g -o tls_relocs_x64_clang.o tls_relocs.c
   gcc -m32 -c -O1 -g -o tls_relocs_i386_gcc.o tls_relocs.c
*/
__thread int first = 1;
__thread int second = 2;
__thread char buffer[16];

int sum(int i)
{
  return first + second + buffer[i & 15];
}
