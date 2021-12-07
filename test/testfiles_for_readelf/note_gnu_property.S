/**
 * Test ELF for .note.gnu.property, built on x86-64.
 *
 * Object file:
 *     gcc -c note_gnu_property.S -o note_gnu_property.o.elf
 *
 * ELF executable (to also have a PT_GNU_PROPERTY program header):
 *     gcc -DEXE -c note_gnu_property.S -o /tmp/x.o
 *     ld /tmp/x.o -o note_gnu_property.elf
 *     strip
 */

// https://github.com/hjl-tools/linux-abi/wiki/linux-abi-draft.pdf
#define NT_GNU_PROPERTY_TYPE_0            5
#define GNU_PROPERTY_STACK_SIZE           1
#define GNU_PROPERTY_NO_COPY_ON_PROTECTED 2
#define GNU_PROPERTY_LOPROC               0xc0000000
#define GNU_PROPERTY_HIPROC               0xdfffffff
#define GNU_PROPERTY_LOUSER               0xe0000000
#define GNU_PROPERTY_HIUSER               0xffffffff

// Unknown property types for testing purposes
#define GNU_PROPERTY_TEST_UNKNOWN         0x12345678
#define GNU_PROPERTY_TEST_UNKNOWN_PROC    0xc1234567
#define GNU_PROPERTY_TEST_UNKNOWN_USER    0xe1234567

// https://gitlab.com/x86-psABIs/x86-64-ABI/-/wikis/x86-64-psABI
#define GNU_PROPERTY_X86_FEATURE_1_AND    0xc0000002
#define GNU_PROPERTY_X86_FEATURE_1_IBT    0x00000001
#define GNU_PROPERTY_X86_FEATURE_1_SHSTK  0x00000002

#ifdef __x86_64__
#define ALIGN .p2align 3
#else
#define ALIGN .p2align 2
#endif

.section ".text"
.global _start
_start:
	ud2

.section ".note.gnu.property", "a"
	ALIGN
	.long 1f - 0f                // n_namesz
	.long end - 2f               // n_descsz
	.long NT_GNU_PROPERTY_TYPE_0 // n_type
0:	.asciz "GNU"                 // n_name
1:
	ALIGN
2:	.long GNU_PROPERTY_STACK_SIZE // pr_type
	.long 4f - 3f                 // pr_datasz
3:
	.dc.a 0x123000
4:
	ALIGN
	.long GNU_PROPERTY_NO_COPY_ON_PROTECTED // pr_type
	.long 0                                 // pr_datasz
	ALIGN

// Avoid these if linking to executable, linkers may not recognize them
#ifndef EXE
	.long GNU_PROPERTY_TEST_UNKNOWN // pr_type
	.long 6f-5f                     // pr_datasz
5:
	.ascii "hello world"
6:
	ALIGN
	.long GNU_PROPERTY_TEST_UNKNOWN_PROC // pr_type
	.long 8f-7f                          // pr_datasz
7:
	.ascii "foobar"
8:
	ALIGN
	.long GNU_PROPERTY_TEST_UNKNOWN_USER // pr_type
	.long 10f-9f                         // pr_datasz
9:
	.ascii "bazquuz"
10:
	ALIGN
#endif

/* TODO: add support for these later...
6:	.long GNU_PROPERTY_X86_FEATURE_1_AND // pr_type.
	.long 8f - 7f                        // pr_datasz
7:
	.long GNU_PROPERTY_X86_FEATURE_1_IBT|GNU_PROPERTY_X86_FEATURE_1_SHSTK
8:
	ALIGN
*/
end:
