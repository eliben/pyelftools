/*
 * Compiled using https://github.com/riscv-collab/riscv-gnu-toolchain with
 * multilib support enabled.
 *
 * riscv64-unknown-linux-gnu-clang -march=rv64gcv_zba_zbb_zbc_zbs_zfh -static simple_clang.riscv.c -o simple_clang.elf.riscv
 */

int main()
{
    return 42;
}
