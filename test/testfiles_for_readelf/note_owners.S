/*
 * Notes with overlapping type numbers in different owner namespaces.
 * Build on x86-64 with:
 *     gcc -c note_owners.S -o note_owners.o.elf
 */

.macro note section_name, owner, type, data
.section .note.\section_name, "a", @note
.balign 4
.long 2f - 1f, 4, \type
1: .asciz "\owner"
2: .balign 4
.long \data
.balign 4
.endm

/* None of these Vendor notes should be interpreted as GNU notes. */
note vendor_build_id, Vendor, 3, 0x12345678
note vendor_property, Vendor, 5, 0x12345678

note gnu_build_id, GNU, 3, 0x12345678
note gnu_unknown, GNU, 0x1234, 0x12345678
note android_version, Android, 1, 35
note android_unknown, Android, 3, 0x12345678
