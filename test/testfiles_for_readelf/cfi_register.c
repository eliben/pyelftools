/*
 * DW_CFA_register formatting regression for PR #689.
 * Build with GCC and GNU as on x86-64, from this directory:
 *     gcc -O2 -fasynchronous-unwind-tables -c cfi_register.c -o cfi_register.o.elf
 *
 * Inline assembly makes the register rules explicit: ordinary C does not
 * guarantee that the compiler emits DW_CFA_register. Generate both frame
 * sections for --debug-dump=frames and frames-interp comparisons.
 */

__asm__(".cfi_sections .eh_frame, .debug_frame");

void cfi_register(void)
{
    __asm__ volatile (
        "movq %%rbx, %%r10\n"
        "movq %%rbp, %%r11\n"
        /* Preserve the compiler's unwind rules around this assembly block. */
        ".cfi_remember_state\n"
        /* Consecutive register rules followed by a different instruction
         * make missing line breaks visible in the readelf comparison. */
        ".cfi_register %%rbx, %%r10\n"
        ".cfi_register %%rbp, %%r11\n"
        ".cfi_same_value %%r12\n"
        "nop\n"
        ".cfi_restore_state\n"
        :
        :
        : "r10", "r11");
}
