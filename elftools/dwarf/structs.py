#-------------------------------------------------------------------------------
# elftools: dwarf/structs.py
#
# Encapsulation of Construct structs for parsing DWARF, adjusted for correct
# endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from construct import (
    Int8ub, Int16ub, Int24ub, Int32ub, Int64ub, Int8ul, Int16ul, Int24ul, Int32ul, Int64ul,
    Int8sb, Int16sb, Int24sb, Int32sb, Int64sb, Int8sl, Int16sl, Int24sl, Int32sl, Int64sl,
    Adapter, ConstructError, If, Enum, Array, PrefixedArray, Bytes, IfThenElse, Construct,
    Struct, Switch, Computed, Padding, NullTerminated, GreedyBytes, Tell, RepeatUntil
)
from ..common.construct_utils import (
    ULEB128, SLEB128, EmbeddableStruct, Embed, CStringBytes, exclude_last_value
)
from .enums import *


class DWARFStructs(object):
    """ Exposes Construct structs suitable for parsing information from DWARF
        sections. Each compile unit in DWARF info can have its own structs
        object. Keep in mind that these structs have to be given a name (by
        calling them with a name) before being used for parsing (like other
        Construct structs). Those that should be used without a name are marked
        by (+).

        Accessible attributes (mostly as described in chapter 7 of the DWARF
        spec v3):

            Dwarf_[u]int{8,16,32,64):
                Data chunks of the common sizes

            Dwarf_offset:
                32-bit or 64-bit word, depending on dwarf_format

            Dwarf_length:
                32-bit or 64-bit word, depending on dwarf_format

            Dwarf_target_addr:
                32-bit or 64-bit word, depending on address size

            Dwarf_initial_length:
                "Initial length field" encoding
                section 7.4

            Dwarf_{u,s}leb128:
                ULEB128 and SLEB128 variable-length encoding

            Dwarf_CU_header (+):
                Compilation unit header

            Dwarf_abbrev_declaration (+):
                Abbreviation table declaration - doesn't include the initial
                code, only the contents.

            Dwarf_dw_form (+):
                A dictionary mapping 'DW_FORM_*' keys into construct Structs
                that parse such forms. These Structs have already been given
                dummy names.

            Dwarf_lineprog_header (+):
                Line program header

            Dwarf_lineprog_file_entry (+):
                A single file entry in a line program header or instruction

            Dwarf_CIE_header (+):
                A call-frame CIE

            Dwarf_FDE_header (+):
                A call-frame FDE

        See also the documentation of public methods.
    """

    # Cache for structs instances based on creation parameters. Structs
    # initialization is expensive and we don't won't to repeat it
    # unnecessarily.
    _structs_cache = {}

    def __new__(cls, little_endian, dwarf_format, address_size, dwarf_version=2):
        """ dwarf_version:
                Numeric DWARF version

            little_endian:
                True if the file is little endian, False if big

            dwarf_format:
                DWARF Format: 32 or 64-bit (see spec section 7.4)

            address_size:
                Target machine address size, in bytes (4 or 8). (See spec
                section 7.5.1)
        """
        key = (little_endian, dwarf_format, address_size, dwarf_version)

        if key in cls._structs_cache:
            return cls._structs_cache[key]

        self = super().__new__(cls)
        assert dwarf_format == 32 or dwarf_format == 64
        assert address_size == 8 or address_size == 4, str(address_size)
        self.little_endian = little_endian
        self.dwarf_format = dwarf_format
        self.address_size = address_size
        self.dwarf_version = dwarf_version
        self._create_structs()
        cls._structs_cache[key] = self
        return self

    def initial_length_field_size(self):
        """ Size of an initial length field.
        """
        return 4 if self.dwarf_format == 32 else 12

    def _create_structs(self):
        if self.little_endian:
            self.Dwarf_uint8 = Int8ul
            self.Dwarf_uint16 = Int16ul
            self.Dwarf_uint24 = Int24ul
            self.Dwarf_uint32 = Int32ul
            self.Dwarf_uint64 = Int64ul
            self.Dwarf_offset = Int32ul if self.dwarf_format == 32 else Int64ul
            self.Dwarf_length = Int32ul if self.dwarf_format == 32 else Int64ul
            self.Dwarf_target_addr = Int32ul if self.address_size == 4 else Int64ul
            self.Dwarf_int8 = Int8sl
            self.Dwarf_int16 = Int16sl
            self.Dwarf_int24 = Int24sl
            self.Dwarf_int32 = Int32sl
            self.Dwarf_int64 = Int64sl
        else:
            self.Dwarf_uint8 = Int8ub
            self.Dwarf_uint16 = Int16ub
            self.Dwarf_uint24 = Int24ub
            self.Dwarf_uint32 = Int32ub
            self.Dwarf_uint64 = Int64ub
            self.Dwarf_offset = Int32ub if self.dwarf_format == 32 else Int64ub
            self.Dwarf_length = Int32ub if self.dwarf_format == 32 else Int64ub
            self.Dwarf_target_addr = Int32ub if self.address_size == 4 else Int64ub
            self.Dwarf_int8 = Int8sb
            self.Dwarf_int16 = Int16sb
            self.Dwarf_int24 = Int24sb
            self.Dwarf_int32 = Int32sb
            self.Dwarf_int64 = Int64sb

        self._create_initial_length()
        self._create_leb128()
        self._create_cu_header()
        self._create_abbrev_declaration()
        self._create_dw_form()
        self._create_lineprog_header()
        self._create_callframe_entry_headers()
        self._create_aranges_header()
        self._create_nameLUT_header()
        self._create_string_offsets_table_header()
        self._create_address_table_header()
        self._create_loclists_parsers()
        self._create_rnglists_parsers()

        self._create_debugsup()
        self._create_gnu_debugaltlink()

    def _create_initial_length(self):
        def _InitialLength():
            # Adapts a Struct that parses forward a full initial length field.
            # Only if the first word is the continuation value, the second
            # word is parsed from the stream.
            return _InitialLengthAdapter(
                Struct(
                    'first' / self.Dwarf_uint32,
                    'second' / If(lambda ctx: ctx.first == 0xFFFFFFFF,
                        self.Dwarf_uint64
                    )
                )
            )
        self.Dwarf_initial_length = _InitialLength()

    def _create_leb128(self):
        self.Dwarf_uleb128 = ULEB128
        self.Dwarf_sleb128 = SLEB128

    def _create_cu_header(self):
        dwarfv4_CU_header = Struct(
            'debug_abbrev_offset' / self.Dwarf_offset,
            'address_size' / self.Dwarf_uint8
        )
        # DWARFv5 reverses the order of address_size and debug_abbrev_offset.
        # DWARFv5 7.5.1.1
        dwarfv5_CP_CU_header = Struct(
            'address_size' / self.Dwarf_uint8,
            'debug_abbrev_offset' / self.Dwarf_offset
        )
        # DWARFv5 7.5.1.2
        dwarfv5_SS_CU_header = Struct(
            'address_size' / self.Dwarf_uint8,
            'debug_abbrev_offset' / self.Dwarf_offset,
            'dwo_id' / self.Dwarf_uint64
        )
        # DWARFv5 7.5.1.3
        dwarfv5_TS_CU_header = Struct(
            'address_size' / self.Dwarf_uint8,
            'debug_abbrev_offset' / self.Dwarf_offset,
            'type_signature' / self.Dwarf_uint64,
            'type_offset' / self.Dwarf_offset
        )
        dwarfv5_CU_header = EmbeddableStruct(
            'unit_type' / Enum(self.Dwarf_uint8, **ENUM_DW_UT),
            Embed(Switch(lambda ctx: ctx.unit_type,
            {
                'DW_UT_compile'       : dwarfv5_CP_CU_header,
                'DW_UT_partial'       : dwarfv5_CP_CU_header,
                'DW_UT_skeleton'      : dwarfv5_SS_CU_header,
                'DW_UT_split_compile' : dwarfv5_SS_CU_header,
                'DW_UT_type'          : dwarfv5_TS_CU_header,
                'DW_UT_split_type'    : dwarfv5_TS_CU_header,
            }))
        )
        self.Dwarf_CU_header = EmbeddableStruct(
            'unit_length' / self.Dwarf_initial_length,
            'version' / self.Dwarf_uint16,
            Embed(IfThenElse(lambda ctx: ctx['version'] >= 5,
                dwarfv5_CU_header,
                dwarfv4_CU_header,
            ))
        )

    def _create_abbrev_declaration(self):
        self.Dwarf_abbrev_declaration = Struct(  # Dwarf_abbrev_entry
            'tag' / Enum(self.Dwarf_uleb128, **ENUM_DW_TAG),
            'children_flag' / Enum(self.Dwarf_uint8, **ENUM_DW_CHILDREN),
            'attr_spec' / RepeatUntil(
                exclude_last_value(lambda obj, lst, ctx: obj.name == 'DW_AT_null' and obj.form == 'DW_FORM_null'),
                Struct(
                    'name' / Enum(self.Dwarf_uleb128, **ENUM_DW_AT),
                    'form' / Enum(self.Dwarf_uleb128, **ENUM_DW_FORM),
                    'value' / If(lambda ctx: ctx['form'] == 'DW_FORM_implicit_const',
                        self.Dwarf_sleb128
                    )
                )
            )
        )

    def _create_debugsup(self):
        # We don't care about checksums, for now.
        self.Dwarf_debugsup = Struct(
            'version' / self.Dwarf_int16,
            'is_supplementary' / self.Dwarf_uint8,
            'sup_filename' / CStringBytes
        )

    def _create_gnu_debugaltlink(self):
        self.Dwarf_debugaltlink = Struct(
            'sup_filename' / CStringBytes,
            'sup_checksum' / Bytes(20)
        )

    def _create_dw_form(self):
        self.Dwarf_dw_form = dict(
            DW_FORM_addr=self.Dwarf_target_addr,
            DW_FORM_addrx=self.Dwarf_uleb128,
            DW_FORM_addrx1=self.Dwarf_uint8,
            DW_FORM_addrx2=self.Dwarf_uint16,
            DW_FORM_addrx3=self.Dwarf_uint24,
            DW_FORM_addrx4=self.Dwarf_uint32,

            DW_FORM_block1=self._make_block_struct(self.Dwarf_uint8),
            DW_FORM_block2=self._make_block_struct(self.Dwarf_uint16),
            DW_FORM_block4=self._make_block_struct(self.Dwarf_uint32),
            DW_FORM_block=self._make_block_struct(self.Dwarf_uleb128),

            # All DW_FORM_data<n> forms are assumed to be unsigned
            DW_FORM_data1=self.Dwarf_uint8,
            DW_FORM_data2=self.Dwarf_uint16,
            DW_FORM_data4=self.Dwarf_uint32,
            DW_FORM_data8=self.Dwarf_uint64,
            DW_FORM_data16=Array(16, self.Dwarf_uint8),  # Used for hashes and such, not for integers
            DW_FORM_sdata=self.Dwarf_sleb128,
            DW_FORM_udata=self.Dwarf_uleb128,

            DW_FORM_string=CStringBytes,
            DW_FORM_strp=self.Dwarf_offset,
            DW_FORM_strp_sup=self.Dwarf_offset,
            DW_FORM_line_strp=self.Dwarf_offset,
            DW_FORM_strx1=self.Dwarf_uint8,
            DW_FORM_strx2=self.Dwarf_uint16,
            DW_FORM_strx3=self.Dwarf_uint24,
            DW_FORM_strx4=self.Dwarf_uint64,
            DW_FORM_flag=self.Dwarf_uint8,

            DW_FORM_ref=self.Dwarf_uint32,
            DW_FORM_ref1=self.Dwarf_uint8,
            DW_FORM_ref2=self.Dwarf_uint16,
            DW_FORM_ref4=self.Dwarf_uint32,
            DW_FORM_ref_sup4=self.Dwarf_uint32,
            DW_FORM_ref8=self.Dwarf_uint64,
            DW_FORM_ref_sup8=self.Dwarf_uint64,
            DW_FORM_ref_udata=self.Dwarf_uleb128,
            DW_FORM_ref_addr=self.Dwarf_target_addr if self.dwarf_version == 2 else self.Dwarf_offset,

            DW_FORM_indirect=self.Dwarf_uleb128,

            # New forms in DWARFv4
            DW_FORM_flag_present=Bytes(0),
            DW_FORM_sec_offset=self.Dwarf_offset,
            DW_FORM_exprloc=self._make_block_struct(self.Dwarf_uleb128),
            DW_FORM_ref_sig8=self.Dwarf_uint64,

            DW_FORM_GNU_strp_alt=self.Dwarf_offset,
            DW_FORM_GNU_ref_alt=self.Dwarf_offset,
            DW_AT_GNU_all_call_sites=self.Dwarf_uleb128,

            # New forms in DWARFv5
            DW_FORM_loclistx=self.Dwarf_uleb128,
            DW_FORM_rnglistx=self.Dwarf_uleb128
        )

    def _create_aranges_header(self):
        self.Dwarf_aranges_header = Struct(
            'unit_length' / self.Dwarf_initial_length,
            'version' / self.Dwarf_uint16,
            'debug_info_offset' / self.Dwarf_offset, # a little tbd
            'address_size' / self.Dwarf_uint8,
            'segment_size' / self.Dwarf_uint8
            )

    def _create_nameLUT_header(self):
        self.Dwarf_nameLUT_header = Struct(
            'unit_length' / self.Dwarf_initial_length,
            'version' / self.Dwarf_uint16,
            'debug_info_offset' / self.Dwarf_offset,
            'debug_info_length' / self.Dwarf_length
            )

    def _create_string_offsets_table_header(self):
        self.Dwarf_string_offsets_table_header = Struct(
            'unit_length' / self.Dwarf_initial_length,
            'version' / self.Dwarf_uint16,
            Padding(2)
            )

    def _create_address_table_header(self):
        self.Dwarf_address_table_header = Struct(
            'unit_length' /self.Dwarf_initial_length,
            'version' / self.Dwarf_uint16,
            'address_size' / self.Dwarf_uint8,
            'segment_selector_size' / self.Dwarf_uint8,
            )

    def _create_lineprog_header(self):
        # A file entry is terminated by a NULL byte, so we don't want to parse
        # past it. Therefore an If is used.
        self.Dwarf_lineprog_file_entry = EmbeddableStruct(
            'name' / CStringBytes,
            Embed(If(lambda ctx: len(ctx.name) != 0,
                Struct(
                    'dir_index' / self.Dwarf_uleb128,
                    'mtime' / self.Dwarf_uleb128,
                    'length' / self.Dwarf_uleb128
                )
            ))
        )

        class FormattedEntry(Construct):
            # Generates a parser based on a previously parsed piece,
            # similar to deprecated Dynamic.
            # Strings are resolved later, since it potentially requires
            # looking at another section.
            def __init__(self, structs, format_field):
                Construct.__init__(self)
                self.structs = structs
                self.format_field = format_field

            def _parse(self, stream, context, path):
                fields = []
                for f in context['_'][self.format_field]:
                    fields.append(f.content_type / self.structs.Dwarf_dw_form[f.form])
                parser = Struct(*fields)
                return parser._parse(stream, context, path)

        ver5 = lambda ctx: ctx.version >= 5

        self.Dwarf_lineprog_header = EmbeddableStruct(
            'unit_length' / self.Dwarf_initial_length,
            'version' / self.Dwarf_uint16,
            'address_size' / If(ver5, self.Dwarf_uint8),
            'segment_selector_size' / If(ver5, self.Dwarf_uint8),
            'header_length' / self.Dwarf_offset,
            'minimum_instruction_length' / self.Dwarf_uint8,
            'maximum_operations_per_instruction' / IfThenElse(lambda ctx: ctx.version >= 4,
                self.Dwarf_uint8,
                Computed(1)
            ),
            'default_is_stmt' / self.Dwarf_uint8,
            'line_base' / self.Dwarf_int8,
            'line_range' / self.Dwarf_uint8,
            'opcode_base' / self.Dwarf_uint8,
            'standard_opcode_lengths' / Array(lambda ctx: ctx.opcode_base - 1, self.Dwarf_uint8),
            Embed(IfThenElse(ver5,
                Struct(  # Names deliberately don't match the legacy objects, since the format can't be made compatible
                    'directory_entry_format' / PrefixedArray(
                        self.Dwarf_uint8,
                        Struct(
                            'content_type' / Enum(self.Dwarf_uleb128, **ENUM_DW_LNCT),
                            'form' / Enum(self.Dwarf_uleb128, **ENUM_DW_FORM)
                        )
                    ),
                    'directories' / PrefixedArray(
                        self.Dwarf_uleb128,
                        FormattedEntry(self, 'directory_entry_format'),
                    ),
                    'file_name_entry_format' / PrefixedArray(
                        self.Dwarf_uint8,
                        Struct(
                            'content_type' / Enum(self.Dwarf_uleb128, **ENUM_DW_LNCT),
                            'form' / Enum(self.Dwarf_uleb128, **ENUM_DW_FORM)
                        )
                    ),
                    'file_names' / PrefixedArray(
                        self.Dwarf_uleb128,
                        FormattedEntry(self, 'file_name_entry_format')
                    )
                ),
                # Legacy  directories/files - DWARF < 5 only
                Struct(
                    'include_directory' / RepeatUntil(
                        exclude_last_value(lambda obj, lst, ctx: obj == b''),
                        NullTerminated(GreedyBytes)
                    ),
                    'file_entry' / RepeatUntil(
                        exclude_last_value(lambda obj, lst, ctx: len(obj.name) == 0),
                        self.Dwarf_lineprog_file_entry
                    )
                )
            )),
        )

    def _create_callframe_entry_headers(self):
        self.Dwarf_CIE_header = Struct(
            'length' / self.Dwarf_initial_length,
            'CIE_id' / self.Dwarf_offset,
            'version' / self.Dwarf_uint8,
            'augmentation' / CStringBytes,
            'code_alignment_factor' / self.Dwarf_uleb128,
            'data_alignment_factor' / self.Dwarf_sleb128,
            'return_address_register' / self.Dwarf_uleb128)
        self.EH_CIE_header = self.Dwarf_CIE_header

        # The CIE header was modified in DWARFv4.
        if self.dwarf_version == 4:
            self.Dwarf_CIE_header = Struct(
                'length' / self.Dwarf_initial_length,
                'CIE_id' / self.Dwarf_offset,
                'version' / self.Dwarf_uint8,
                'augmentation' / CStringBytes,
                'address_size' / self.Dwarf_uint8,
                'segment_size' / self.Dwarf_uint8,
                'code_alignment_factor' / self.Dwarf_uleb128,
                'data_alignment_factor' / self.Dwarf_sleb128,
                'return_address_register' / self.Dwarf_uleb128
            )

        self.Dwarf_FDE_header = Struct(
            'length' / self.Dwarf_initial_length,
            'CIE_pointer' / self.Dwarf_offset,
            'initial_location' / self.Dwarf_target_addr,
            'address_range' / self.Dwarf_target_addr
        )

    def _make_block_struct(self, length_field):
        """ Create a struct for DW_FORM_block<size>
        """
        return PrefixedArray(
            length_field,
            self.Dwarf_uint8,
        )

    def _create_loclists_parsers(self):
        """ Create a struct for debug_loclists CU header, DWARFv5, 7,29
        """
        self.Dwarf_loclists_CU_header = Struct(
            'cu_offset' / Tell,
            'unit_length' / self.Dwarf_initial_length,
            'is64' / Computed(lambda ctx: ctx.is64),
            'offset_after_length' / Tell,
            'version' / self.Dwarf_uint16,
            'address_size' / self.Dwarf_uint8,
            'segment_selector_size' / self.Dwarf_uint8,
            'offset_count' / self.Dwarf_uint32,
            'offset_table_offset' / Tell
        )

        cld = self.Dwarf_loclists_counted_location_description = PrefixedArray(self.Dwarf_uleb128, self.Dwarf_uint8)

        self.Dwarf_loclists_entries = RepeatUntil(
            exclude_last_value(lambda obj, list, ctx: obj.entry_type == 'DW_LLE_end_of_list'),
            EmbeddableStruct(
                'entry_offset' / Tell,
                'entry_type' / Enum(self.Dwarf_uint8, **ENUM_DW_LLE),
                Embed(Switch(lambda ctx: ctx.entry_type,
                {
                    'DW_LLE_end_of_list'      : Struct(),
                    'DW_LLE_base_addressx'    : Struct('index' / self.Dwarf_uleb128),
                    'DW_LLE_startx_endx'      : Struct('start_index' / self.Dwarf_uleb128, 'end_index' / self.Dwarf_uleb128, 'loc_expr' / cld),
                    'DW_LLE_startx_length'    : Struct('start_index' / self.Dwarf_uleb128, 'length' / self.Dwarf_uleb128, 'loc_expr' / cld),
                    'DW_LLE_offset_pair'      : Struct('start_offset' / self.Dwarf_uleb128, 'end_offset' / self.Dwarf_uleb128, 'loc_expr' / cld),
                    'DW_LLE_default_location' : Struct('loc_expr' / cld),
                    'DW_LLE_base_address'     : Struct('address' / self.Dwarf_target_addr),
                    'DW_LLE_start_end'        : Struct('start_address' / self.Dwarf_target_addr, 'end_address' / self.Dwarf_target_addr, 'loc_expr' / cld),
                    'DW_LLE_start_length'     : Struct('start_address' / self.Dwarf_target_addr, 'length' / self.Dwarf_uleb128, 'loc_expr' / cld),
                })),
                'entry_end_offset' / Tell,
                'entry_length' / Computed(lambda ctx: ctx.entry_end_offset - ctx.entry_offset)
            )
        )

        self.Dwarf_locview_pair = Struct(
            'entry_offset' / Tell,
            'begin' / self.Dwarf_uleb128,
            'end' / self.Dwarf_uleb128
        )

    def _create_rnglists_parsers(self):
        self.Dwarf_rnglists_CU_header = Struct(
            'cu_offset' / Tell,
            'unit_length' / self.Dwarf_initial_length,
            'is64' / Computed(lambda ctx: ctx.is64),
            'offset_after_length' / Tell,
            'version' / self.Dwarf_uint16,
            'address_size' / self.Dwarf_uint8,
            'segment_selector_size' / self.Dwarf_uint8,
            'offset_count' / self.Dwarf_uint32,
            'offset_table_offset' / Tell
        )

        self.Dwarf_rnglists_entries = RepeatUntil(
            exclude_last_value(lambda obj, list, ctx: obj.entry_type == 'DW_RLE_end_of_list'),
            EmbeddableStruct(
                'entry_offset' / Tell,
                'entry_type' / Enum(self.Dwarf_uint8, **ENUM_DW_RLE),
                Embed(Switch(lambda ctx: ctx.entry_type,
                {
                    'DW_RLE_end_of_list'      : Struct(),
                    'DW_RLE_base_addressx'    : Struct('index' / self.Dwarf_uleb128),
                    'DW_RLE_startx_endx'      : Struct('start_index' / self.Dwarf_uleb128, 'end_index' / self.Dwarf_uleb128),
                    'DW_RLE_startx_length'    : Struct('start_index' / self.Dwarf_uleb128, 'length' / self.Dwarf_uleb128),
                    'DW_RLE_offset_pair'      : Struct('start_offset' / self.Dwarf_uleb128, 'end_offset' / self.Dwarf_uleb128),
                    'DW_RLE_base_address'     : Struct('address' / self.Dwarf_target_addr),
                    'DW_RLE_start_end'        : Struct('start_address' / self.Dwarf_target_addr, 'end_address' / self.Dwarf_target_addr),
                    'DW_RLE_start_length'     : Struct('start_address' / self.Dwarf_target_addr, 'length' / self.Dwarf_uleb128)
                })),
                'entry_end_offset' / Tell,
                'entry_length' / Computed(lambda ctx: ctx.entry_end_offset - ctx.entry_offset)))


class _InitialLengthAdapter(Adapter):
    """ A standard Construct adapter that expects a sub-construct
        as a struct with one or two values (first, second).
    """
    def _decode(self, obj, context, path):
        if obj.first < 0xFFFFFF00:
            context['is64'] = False
            return obj.first
        else:
            if obj.first == 0xFFFFFFFF:
                context['is64'] = True
                return obj.second
            else:
                raise ConstructError("Failed decoding initial length for %X" % (
                    obj.first))
