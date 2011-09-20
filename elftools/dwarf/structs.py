#-------------------------------------------------------------------------------
# elftools: dwarf/structs.py
#
# Encapsulation of Construct structs for parsing DWARF, adjusted for correct
# endianness and word-size.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct import (
    UBInt8, UBInt16, UBInt32, UBInt64,
    ULInt8, ULInt16, ULInt32, ULInt64,
    Adapter, Struct, ConstructError, If, RepeatUntil, Field, Rename,
    )


class DWARFStructs(object):
    """ Exposes Construct structs suitable for parsing information from DWARF 
        sections. Configurable with endianity and format (32 or 64-bit)
    
        Accessible attributes (mostly described by in chapter 7 of the DWARF
        spec v3):
    
            Dwarf_uint{8,16,32,64):
                Data chunks of the common sizes
            
            Dwarf_offset:
                32-bit or 64-bit word, depending on dwarf_format
            
            Dwarf_initial_length:
                "Initial length field" encoding
                section 7.4
            
            Dwarf_{u,s}leb128:
                ULEB128 and SLEB128 variable-length encoding
            
            Dwarf_CU_header:
                Compilation unit header
        
        See also the documentation of public methods.
    """
    def __init__(self, little_endian=True, dwarf_format=32):
        assert dwarf_format == 32 or dwarf_format == 64
        self.little_endian = little_endian
        self.dwarf_format = dwarf_format        
        self._create_structs()

    def initial_lenght_field_size(self):
        """ Size of an initial length field.
        """
        return 4 if self.dwarf_format == 32 else 12

    def _create_structs(self):
        if self.little_endian:
            self.Dwarf_uint8 = ULInt8
            self.Dwarf_uint16 = ULInt16
            self.Dwarf_uint32 = ULInt32
            self.Dwarf_uint64 = ULInt64
            self.Dwarf_offset = ULInt32 if self.dwarf_format == 32 else ULInt64
        else:
            self.Dwarf_uint8 = UBInt8
            self.Dwarf_uint16 = UBInt16
            self.Dwarf_uint32 = UBInt32
            self.Dwarf_uint64 = UBInt64
            self.Dwarf_offest = UBInt32 if self.dwarf_format == 32 else UBInt64

        self._create_initial_length()
        self._create_leb128()
        self._create_cu_header()

    def _create_initial_length(self):
        def _InitialLength(name):
            # Adapts a Struct that parses forward a full initial length field.
            # Only if the first word is the continuation value, the second 
            # word is parsed from the stream.
            #
            return _InitialLengthAdapter(
                Struct(name,
                    self.Dwarf_uint32('first'),
                    If(lambda ctx: ctx.first == 0xFFFFFFFF,
                        self.Dwarf_uint64('second'),
                        elsevalue=None)))
        self.Dwarf_initial_length = _InitialLength

    def _create_leb128(self):
        self.Dwarf_uleb128 = _ULEB128
        self.Dwarf_sleb128 = _SLEB128

    def _create_cu_header(self):
        self.Dwarf_CU_header = Struct('Dwarf_CU_header',
            self.Dwarf_initial_length('unit_length'),
            self.Dwarf_uint16('version'),
            self.Dwarf_offset('debug_abbrev_offset'),
            self.Dwarf_uint8('address_size'))


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
                Field(None, 1))


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
            #
            value |= - (1 << (7 * len(obj)))
        return value


def _ULEB128(name):
    """ A construct creator for ULEB128 encoding.
    """
    return Rename(name, _ULEB128Adapter(_LEB128_reader()))


def _SLEB128(name):
    """ A construct creator for SLEB128 encoding.
    """
    return Rename(name, _SLEB128Adapter(_LEB128_reader()))

