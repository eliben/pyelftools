/*
 * Compiled using https://github.com/riscv-collab/riscv-gnu-toolchain with
 * multilib support enabled.
 *
 * riscv64-unknown-elf-gcc -march=rv64gcv_zba_zbb_zbc_zbs_zfh simple_gcc.riscv.c -o simple_gcc.elf.riscv
 */

int main()
{
    return 42;
}
