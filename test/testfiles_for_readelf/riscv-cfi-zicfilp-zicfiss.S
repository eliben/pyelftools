# Compile with
# riscv64-unknown-linux-gnu-gcc riscv-cfi-zicfilp-zicfiss.S -c -o riscv-cfi-zicfilp-zicfiss.elf
#define GNU_PROPERTY_RISCV_FEATURE_1_AND 0xc0000000
#define GNU_PROPERTY_RISCV_FEATURE_1_ZICFILP (1 << 0)
#define GNU_PROPERTY_RISCV_FEATURE_1_ZICFISS (1 << 1)

	.text
	.globl _start
	.type _start,@function
_start:
    ret	

.section ".note.gnu.property", "a", @note
	.p2align 3
	.long 1f - 0f		/* name length */
	.long 5f - 2f		/* data length */
	.long 5		/* note type */
0:	.asciz "GNU"		/* vendor name */
1:
	.p2align 3
2:	.long GNU_PROPERTY_RISCV_FEATURE_1_AND	/* pr_type.  */
	.long 4f - 3f		/* pr_datasz.  */
3:
	.long (GNU_PROPERTY_RISCV_FEATURE_1_ZICFILP | GNU_PROPERTY_RISCV_FEATURE_1_ZICFISS)
4:
	.p2align 3
5:
end:
