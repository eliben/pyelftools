@ Rebuild with GNU Arm assembler:
@ arm-none-eabi-as -o arm_none_reloc.o arm_none_reloc.S
@ NONE marks dependencies without touching data, including at its final byte.
.syntax unified
.section .text
.word 0
.global dependency
dependency:
.word 0

.section .data
.reloc 0, R_ARM_NONE, dependency
.word dependency + 17
.reloc 3, R_ARM_NONE, dependency
