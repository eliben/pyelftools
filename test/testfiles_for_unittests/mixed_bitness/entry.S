/* This code is in the public domain. */
.section .text
.global _start
.code64
_start:
    /* Keep the stack, code, and return addresses below 4 GiB. */
    lea stack_end(%rip), %rsp
    mov %cs, %ax
    cmp $0x33, %ax
    jne failed64
    mov $3, %edi
    call compute64
    cmp $77, %eax
    jne failed64
    mov $-3, %edi
    call compute64
    cmp $76, %eax
    jne failed64
    /* Linux x86-64 user compatibility code selector. */
    pushq $0x23
    lea enter32(%rip), %rax
    pushq %rax
    lretq
.code32
enter32:
    mov %cs, %ax
    cmp $0x23, %ax
    jne failed32
    /* Align ESP to 16 bytes before each i386 SysV call. */
    sub $12, %esp
    pushl $3
    call compute32
    add $16, %esp
    cmpl $77, %eax
    jne failed32
    sub $12, %esp
    pushl $-3
    call compute32
    add $16, %esp
    cmpl $76, %eax
    jne failed32
    xor %edi, %edi
    jmp return64
failed32:
    mov $2, %edi
return64:
    /* Linux x86-64 user long-mode code selector. */
    pushl $0x33
    pushl $exit64
    lret
.code64
failed64:
    mov $1, %edi
exit64:
    mov %cs, %ax
    cmp $0x33, %ax
    je exit
    mov $3, %edi
exit:
    mov $60, %eax
    syscall
.section .bss
.balign 16
stack:
    .skip 16384
stack_end:
.section .note.GNU-stack,"",@progbits
