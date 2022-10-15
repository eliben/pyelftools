// Compile into tls.elf using:
// $ gcc -m32 -o tls.elf tls.c
// For tls64.elf, use:
// $ gcc -m64 -o tls64.elf tls.c

__thread int i;

int main(){}
