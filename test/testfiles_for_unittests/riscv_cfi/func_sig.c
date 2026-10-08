/*
 * riscv64-unknown-elf-gcc -c -march=rv64i_zicfilp_zicfiss -mabi=lp64 \
 *     -fcf-protection=full -mcf-branch-label-scheme=func-sig \
 *     func_sig.c -o func_sig.o
 */

void f(void) {}
