# as -o /tmp/t.o -gendebug -gdwarf-2 /tmp/t.s

	# readelf tests want a text section to dump
	.text
	nop



DW_LANG_C = 0x002
DW_TAG_compile_unit = 0x11
DW_TAG_partial_unit = 0x3c
DW_ATTR_language = 0x13
DW_ATTR_macro_info = 0x43
DW_ATTR_name = 0x03
DW_ATTR_stmt_list = 0x10
DW_FORM_data1 = 0x0b
DW_FORM_sec_offset = 0x17
DW_FORM_string = 0x08

	.section ".debug_macinfo"
mac_info:
        .byte 255, 43
        .ascii "hello\0"
        .byte 255, 128, 2
        .ascii "goodbye\0"
	.byte 0

mac_info2:
	.byte 255, 0
        .ascii "nice to meet you\0"
	.byte 0


	.section ".debug_info"

	.long 99f-1f		# unit_length
1:	.short 4		# dwarf version
	.long abbrev_table	# abrev table offset
	.byte 8			# addres size

	.byte 1                 # abbrev code
	.byte DW_LANG_C
	.ascii "one.s\0"	# str name
	.long mac_info		# macro section reference
	.long 0			# stmt_list section ref
99:

	# a partial unit , but this causes the line numbers to dump twice
	# if both have locations and crash if no location until fixed
	#.section ".not_debug_info"

	.long 99f-1f		# unit_length
1:	.short 4		# dwarf version
	.long abbrev_table	# abrev table offset
	.byte 8			# addres size

	.byte 2                 # abbrev code
	.byte DW_LANG_C
	.ascii "two.s\0"	# str name
	.long mac_info2		# macro section reference
	.byte 0                 # abbrev_code (padding)
	.byte 0                 # abbrev_code (padding)
	.byte 0                 # abbrev_code (padding)
99:

	.section ".debug_abbrev"
abbrev_table:
	.byte 1, DW_TAG_compile_unit, 0 # tag, has_children
	.byte DW_ATTR_language, DW_FORM_data1
	.byte DW_ATTR_name, DW_FORM_string
	.byte DW_ATTR_macro_info, DW_FORM_sec_offset
	.byte DW_ATTR_stmt_list, DW_FORM_sec_offset
	.byte 0, 0
	.byte 2, DW_TAG_partial_unit, 0 # tag, has_children
	.byte DW_ATTR_language, DW_FORM_data1
	.byte DW_ATTR_name, DW_FORM_string
	.byte DW_ATTR_macro_info, DW_FORM_sec_offset
	.byte 0, 0
	.byte 0
# as -o /tmp/t.o -gendebug -gdwarf-2 /tmp/t.s
