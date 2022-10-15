/**
 * Test ELF for .note.gnu.property, built on x86-64.
 *
 * Object file:
 *     gcc -c note_gnu_property.S -o note_gnu_property.o.elf
 *
 * ELF executable (to also have a PT_GNU_PROPERTY program header):
 *     gcc -DEXE -c note_gnu_property.S -o /tmp/x.o
 *     ld /tmp/x.o -o note_gnu_property.elf
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
#define GNU_PROPERTY_TEST_UNKNOWN_PROC    (GNU_PROPERTY_LOPROC + 0x1234567)
#define GNU_PROPERTY_TEST_UNKNOWN_USER    (GNU_PROPERTY_LOUSER + 0x1234567)

// https://gitlab.com/x86-psABIs/x86-64-ABI/
// https://gitlab.com/x86-psABIs/x86-64-ABI/-/wikis/x86-64-psABI
#define GNU_PROPERTY_X86_UINT32_AND_LO    0xc0000002
#define GNU_PROPERTY_X86_UINT32_AND_HI    0xc0007fff
#define GNU_PROPERTY_X86_UINT32_OR_LO     0xc0008000
#define GNU_PROPERTY_X86_UINT32_OR_HI     0xc000ffff
#define GNU_PROPERTY_X86_UINT32_OR_AND_LO 0xc0010000
#define GNU_PROPERTY_X86_UINT32_OR_AND_HI 0xc0017fff

#define GNU_PROPERTY_X86_FEATURE_1_AND     (GNU_PROPERTY_X86_UINT32_AND_LO + 0)
#define GNU_PROPERTY_X86_FEATURE_1_IBT     (1U << 0)
#define GNU_PROPERTY_X86_FEATURE_1_SHSTK   (1U << 1)
#define GNU_PROPERTY_X86_FEATURE_1_LAM_U48 (1U << 2)
#define GNU_PROPERTY_X86_FEATURE_1_LAM_U57 (1U << 3)

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

11:	.long GNU_PROPERTY_X86_FEATURE_1_AND // pr_type.
	.long 13f - 12f                      // pr_datasz
12:
	// Not sure if LAM_U48 and LAM_U57 make sense together, readelf does not
	// seem to complain and outputs both.
	.long GNU_PROPERTY_X86_FEATURE_1_IBT     \
		| GNU_PROPERTY_X86_FEATURE_1_SHSTK   \
		| GNU_PROPERTY_X86_FEATURE_1_LAM_U48 \
		| GNU_PROPERTY_X86_FEATURE_1_LAM_U57
13:
	ALIGN
end:
