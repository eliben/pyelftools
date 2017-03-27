#-------------------------------------------------------------------------------
# elftools: dwarf/structs.py
#
# Encapsulation of Construct structs for parsing DWARF, adjusted for correct
# endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct28 import (
    Int8ub, Int16ub, Int32ub, Int64ub, Int8ul, Int16ul, Int32ul, Int64ul,
    Int8sb, Int16sb, Int32sb, Int64sb, Int8sl, Int16sl, Int32sl, Int64sl,
    Adapter, Struct, ConstructError, If, RepeatUntil, Bytes, Renamed, Enum,
    Array, PrefixedArray, CString, Embedded, Bytes, IfThenElse, Computed
    )
from ..common.construct_utils import RepeatUntilExcluding

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
    def __init__(self,
                 little_endian, dwarf_format, address_size, dwarf_version=2):
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
        assert dwarf_format == 32 or dwarf_format == 64
        assert address_size == 8 or address_size == 4
        self.little_endian = little_endian
        self.dwarf_format = dwarf_format
        self.address_size = address_size
        self.dwarf_version = dwarf_version
        self._create_structs()

    def initial_length_field_size(self):
        """ Size of an initial length field.
        """
        return 4 if self.dwarf_format == 32 else 12

    def _create_structs(self):
        if self.little_endian:
            self.Dwarf_uint8 = Int8ul
            self.Dwarf_uint16 = Int16ul
            self.Dwarf_uint32 = Int32ul
            self.Dwarf_uint64 = Int64ul
            self.Dwarf_offset = Int32ul if self.dwarf_format == 32 else Int64ul
            self.Dwarf_target_addr = (
                Int32ul if self.address_size == 4 else Int64ul)
            self.Dwarf_int8 = Int8sl
            self.Dwarf_int16 = Int16sl
            self.Dwarf_int32 = Int32sl
            self.Dwarf_int64 = Int64sl
        else:
            self.Dwarf_uint8 = Int8ub
            self.Dwarf_uint16 = Int16ub
            self.Dwarf_uint32 = Int32ub
            self.Dwarf_uint64 = Int64ub
            self.Dwarf_offset = Int32ub if self.dwarf_format == 32 else Int64ub
            self.Dwarf_target_addr = (
                Int32ub if self.address_size == 4 else Int64ub)
            self.Dwarf_int8 = Int8sb
            self.Dwarf_int16 = Int16sb
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

    def _create_initial_length(self):
        def _InitialLength(name):
            # Adapts a Struct that parses forward a full initial length field.
            # Only if the first word is the continuation value, the second
            # word is parsed from the stream.
            return Renamed(name, _InitialLengthAdapter(
                Struct(
                    'first'/self.Dwarf_uint32,
                    If(lambda ctx: ctx.first == 0xFFFFFFFF,
                        'second'/self.Dwarf_uint64))))
        self.Dwarf_initial_length = _InitialLength

    def _create_leb128(self):
        self.Dwarf_uleb128 = _ULEB128
        self.Dwarf_sleb128 = _SLEB128

    def _create_cu_header(self):
        self.Dwarf_CU_header = 'Dwarf_CU_header'/Struct(
            self.Dwarf_initial_length('unit_length'),
            'version'/self.Dwarf_uint16,
            'debug_abbrev_offset'/self.Dwarf_offset,
            'address_size'/self.Dwarf_uint8)

    def _create_abbrev_declaration(self):
        self.Dwarf_abbrev_declaration = 'Dwarf_abbrev_entry'/Struct(
            Enum(self.Dwarf_uleb128('tag'), Pass, **ENUM_DW_TAG),
            Enum('children_flag'/self.Dwarf_uint8, Pass, **ENUM_DW_CHILDREN),
            RepeatUntilExcluding(
                lambda obj, ctx:
                    obj.name == 'DW_AT_null' and obj.form == 'DW_FORM_null',
                'attr_spec'/Struct(
                    Enum(self.Dwarf_uleb128('name'), Pass, **ENUM_DW_AT),
                    Enum(self.Dwarf_uleb128('form'), Pass, **ENUM_DW_FORM))))

    def _create_dw_form(self):
        self.Dwarf_dw_form = dict(
            DW_FORM_addr = ''/self.Dwarf_target_addr,

            DW_FORM_block1 = self._make_block_struct(self.Dwarf_uint8),
            DW_FORM_block2 = self._make_block_struct(self.Dwarf_uint16),
            DW_FORM_block4 = self._make_block_struct(self.Dwarf_uint32),
            DW_FORM_block = self._make_block_struct(self.Dwarf_uleb128),

            # All DW_FORM_data<n> forms are assumed to be unsigned
            DW_FORM_data1 = ''/self.Dwarf_uint8,
            DW_FORM_data2 = ''/self.Dwarf_uint16,
            DW_FORM_data4 = ''/self.Dwarf_uint32,
            DW_FORM_data8 = ''/self.Dwarf_uint64,
            DW_FORM_sdata = self.Dwarf_sleb128(''),
            DW_FORM_udata = self.Dwarf_uleb128(''),

            DW_FORM_string = ''/CString(),
            DW_FORM_strp = ''/self.Dwarf_offset,
            DW_FORM_flag = ''/self.Dwarf_uint8,

            DW_FORM_ref1 = ''/self.Dwarf_uint8,
            DW_FORM_ref2 = ''/self.Dwarf_uint16,
            DW_FORM_ref4 = ''/self.Dwarf_uint32,
            DW_FORM_ref8 = ''/self.Dwarf_uint64,
            DW_FORM_ref_udata = self.Dwarf_uleb128(''),
            DW_FORM_ref_addr = ''/self.Dwarf_offset,

            DW_FORM_indirect = self.Dwarf_uleb128(''),

            # New forms in DWARFv4
            DW_FORM_flag_present = Bytes(0),
            DW_FORM_sec_offset = ''/ self.Dwarf_offset,
            DW_FORM_exprloc = self._make_block_struct(self.Dwarf_uleb128),
            DW_FORM_ref_sig8 = ''/ self.Dwarf_offset,

            DW_FORM_GNU_strp_alt = ''/self.Dwarf_offset,
            DW_FORM_GNU_ref_alt = ''/self.Dwarf_offset,
            DW_AT_GNU_all_call_sites = self.Dwarf_uleb128(''),
        )

    def _create_aranges_header(self):
        self.Dwarf_aranges_header = 'Dwarf_aranges_header'/Struct(
            self.Dwarf_initial_length('unit_length'),
            'version'/self.Dwarf_uint16,
            'debug_info_offset'/self.Dwarf_offset, # a little tbd
            'address_size'/self.Dwarf_uint8,
            'segment_size'/self.Dwarf_uint8
            )

    def _create_lineprog_header(self):
        # A file entry is terminated by a NULL byte, so we don't want to parse
        # past it. Therefore an If is used.
        self.Dwarf_lineprog_file_entry = 'file_entry'/Struct(
            'name'/CString(),
            Embedded(IfThenElse(lambda ctx: len(ctx.name) != 0,
                Struct(
                    self.Dwarf_uleb128('dir_index'),
                    self.Dwarf_uleb128('mtime'),
                    self.Dwarf_uleb128('length')),
                Struct())))

        self.Dwarf_lineprog_header = 'Dwarf_lineprog_header'/Struct(
            self.Dwarf_initial_length('unit_length'),
            'version'/self.Dwarf_uint16,
            'header_length'/self.Dwarf_offset,
            'minimum_instruction_length'/self.Dwarf_uint8,
            "maximum_operations_per_instruction"/IfThenElse(
                lambda ctx: ctx['version'] >= 4,
                self.Dwarf_uint8,
                Computed(1)),
            'default_is_stmt'/self.Dwarf_uint8,
            'line_base'/self.Dwarf_int8,
            'line_range'/self.Dwarf_uint8,
            'opcode_base'/self.Dwarf_uint8,
            Array(lambda ctx: ctx['opcode_base'] - 1,
                  'standard_opcode_lengths'/self.Dwarf_uint8),
            RepeatUntilExcluding(
                lambda obj, ctx: obj == b'',
                'include_directory'/CString()),
            RepeatUntilExcluding(
                lambda obj, ctx: len(obj.name) == 0,
                self.Dwarf_lineprog_file_entry),
            )

    def _create_callframe_entry_headers(self):
        # The CIE header was modified in DWARFv4.
        if self.dwarf_version == 4:
            self.Dwarf_CIE_header = 'Dwarf_CIE_header'/Struct(
                self.Dwarf_initial_length('length'),
                'CIE_id'/self.Dwarf_offset,
                'version'/self.Dwarf_uint8,
                'augmentation'/CString(),
                'address_size'/self.Dwarf_uint8,
                'segment_size'/self.Dwarf_uint8,
                self.Dwarf_uleb128('code_alignment_factor'),
                self.Dwarf_sleb128('data_alignment_factor'),
                self.Dwarf_uleb128('return_address_register'))
        else:
            self.Dwarf_CIE_header = 'Dwarf_CIE_header'/Struct(
                self.Dwarf_initial_length('length'),
                'CIE_id'/self.Dwarf_offset,
                'version'/self.Dwarf_uint8,
                'augmentation'/CString(),
                self.Dwarf_uleb128('code_alignment_factor'),
                self.Dwarf_sleb128('data_alignment_factor'),
                self.Dwarf_uleb128('return_address_register'))

        self.Dwarf_FDE_header = 'Dwarf_FDE_header'/Struct(
            self.Dwarf_initial_length('length'),
            'CIE_pointer'/self.Dwarf_offset,
            'initial_location'/self.Dwarf_target_addr,
            'address_range'/self.Dwarf_target_addr)

    def _make_block_struct(self, length_field):
        """ Create a struct for DW_FORM_block<size>
        """
        if length_field == self.Dwarf_uleb128:
            lfield = length_field('')
        else:
            lfield = ''/length_field 
        return PrefixedArray(
                    subcon='elem'/self.Dwarf_uint8,
                    lengthfield=lfield)


class _InitialLengthAdapter(Adapter):
    """ A standard Construct adapter that expects a sub-construct
        as a struct with one or two values (first, second).
    """
    def _decode(self, obj, context):
        if obj.first < 0xFFFFFF00:
            return obj.first
        else:
            if obj.first == 0xFFFFFFFF:
                return obj.second
            else:
                raise ConstructError("Failed decoding initial length for %X" % (
                    obj.first))


def _LEB128_reader():
    """ Read LEB128 variable-length data from the stream. The data is terminated
        by a byte with 0 in its highest bit.
    """
    return RepeatUntil(
                lambda obj, ctx: ord(obj) < 0x80,
                Bytes(1))


class _ULEB128Adapter(Adapter):
    """ An adapter for ULEB128, given a sequence of bytes in a sub-construct.
    """
    def _decode(self, obj, context):
        value = 0
        for b in reversed(obj):
            value = (value << 7) + (ord(b) & 0x7F)
        return value


class _SLEB128Adapter(Adapter):
    """ An adapter for SLEB128, given a sequence of bytes in a sub-construct.
    """
    def _decode(self, obj, context):
        value = 0
        for b in reversed(obj):
            value = (value << 7) + (ord(b) & 0x7F)
        if ord(obj[-1]) & 0x40:
            # negative -> sign extend
            value |= - (1 << (7 * len(obj)))
        return value


def _ULEB128(name):
    """ A construct creator for ULEB128 encoding.
    """
    return Renamed(name, _ULEB128Adapter(_LEB128_reader()))


def _SLEB128(name):
    """ A construct creator for SLEB128 encoding.
    """
    return Renamed(name, _SLEB128Adapter(_LEB128_reader()))
