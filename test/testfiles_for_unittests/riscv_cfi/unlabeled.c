/*
 * riscv64-unknown-elf-gcc -c -march=rv64i_zicfilp_zicfiss -mabi=lp64 \
 *     -fcf-protection=full -mcf-branch-label-scheme=unlabeled \
 *     unlabeled.c -o unlabeled.o
 */

void f(void) {}
