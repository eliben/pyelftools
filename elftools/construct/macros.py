from lib import BitStreamReader, BitStreamWriter, encode_bin, decode_bin
from core import *
from adapters import *


#===============================================================================
# fields
#===============================================================================
def Field(name, length):
    """a field
    * name - the name of the field
    * length - the length of the field. the length can be either an integer
      (StaticField), or a function that takes the context as an argument and 
      returns the length (MetaField)
    """
    if callable(length):
        return MetaField(name, length)
    else:
        return StaticField(name, length)

def BitField(name, length, swapped = False, signed = False, bytesize = 8):
    """a bit field; must be enclosed in a BitStruct
    * name - the name of the field
    * length - the length of the field in bits. the length can be either 
      an integer, or a function that takes the context as an argument and 
      returns the length
    * swapped - whether the value is byte-swapped (little endian). the 
      default is False.
    * signed - whether the value of the bitfield is a signed integer. the 
      default is False.
    * bytesize - the number of bits in a byte (used for byte-swapping). the
      default is 8.
    """
    return BitIntegerAdapter(Field(name, length), 
        length,
        swapped = swapped, 
        signed = signed,
        bytesize = bytesize
    )

def Padding(length, pattern = "\x00", strict = False):
    r"""a padding field (value is discarded)
    * length - the length of the field. the length can be either an integer,
      or a function that takes the context as an argument and returns the 
      length
    * pattern - the padding pattern (character) to use. default is "\x00"
    * strict - whether or not to raise an exception is the actual padding 
      pattern mismatches the desired pattern. default is False.
    """
    return PaddingAdapter(Field(None, length), 
        pattern = pattern, 
        strict = strict,
    )

def Flag(name, truth = 1, falsehood = 0, default = False):
    """a flag field (True or False)
    * name - the name of the field
    * truth - the numeric value of truth. the default is 1.
    * falsehood - the numeric value of falsehood. the default is 0.
    * default - the default value to assume, when the value is neither 
      `truth` nor `falsehood`. the default is False.
    """
    return SymmetricMapping(Field(name, 1), 
        {True : chr(truth), False : chr(falsehood)},
        default = default,
    )

#===============================================================================
# field shortcuts
#===============================================================================
def Bit(name):
    """a 1-bit BitField; must be enclosed in a BitStruct"""
    return BitField(name, 1)
def Nibble(name):
    """a 4-bit BitField; must be enclosed in a BitStruct"""
    return BitField(name, 4)
def Octet(name):
    """an 8-bit BitField; must be enclosed in a BitStruct"""
    return BitField(name, 8)

def UBInt8(name):
    """unsigned, big endian 8-bit integer"""
    return FormatField(name, ">", "B")
def UBInt16(name):
    """unsigned, big endian 16-bit integer"""
    return FormatField(name, ">", "H")
def UBInt32(name):
    """unsigned, big endian 32-bit integer"""
    return FormatField(name, ">", "L")
def UBInt64(name):
    """unsigned, big endian 64-bit integer"""
    return FormatField(name, ">", "Q")

def SBInt8(name):
    """signed, big endian 8-bit integer"""
    return FormatField(name, ">", "b")
def SBInt16(name):
    """signed, big endian 16-bit integer"""
    return FormatField(name, ">", "h")
def SBInt32(name):
    """signed, big endian 32-bit integer"""
    return FormatField(name, ">", "l")
def SBInt64(name):
    """signed, big endian 64-bit integer"""
    return FormatField(name, ">", "q")

def ULInt8(name):
    """unsigned, little endian 8-bit integer"""
    return FormatField(name, "<", "B")
def ULInt16(name):
    """unsigned, little endian 16-bit integer"""
    return FormatField(name, "<", "H")
def ULInt32(name):
    """unsigned, little endian 32-bit integer"""
    return FormatField(name, "<", "L")
def ULInt64(name):
    """unsigned, little endian 64-bit integer"""
    return FormatField(name, "<", "Q")

def SLInt8(name):
    """signed, little endian 8-bit integer"""
    return FormatField(name, "<", "b")
def SLInt16(name):
    """signed, little endian 16-bit integer"""
    return FormatField(name, "<", "h")
def SLInt32(name):
    """signed, little endian 32-bit integer"""
    return FormatField(name, "<", "l")
def SLInt64(name):
    """signed, little endian 64-bit integer"""
    return FormatField(name, "<", "q")

def UNInt8(name):
    """unsigned, native endianity 8-bit integer"""
    return FormatField(name, "=", "B")
def UNInt16(name):
    """unsigned, native endianity 16-bit integer"""
    return FormatField(name, "=", "H")
def UNInt32(name):
    """unsigned, native endianity 32-bit integer"""
    return FormatField(name, "=", "L")
def UNInt64(name):
    """unsigned, native endianity 64-bit integer"""
    return FormatField(name, "=", "Q")

def SNInt8(name):
    """signed, native endianity 8-bit integer"""
    return FormatField(name, "=", "b")
def SNInt16(name):
    """signed, native endianity 16-bit integer"""
    return FormatField(name, "=", "h")
def SNInt32(name):
    """signed, native endianity 32-bit integer"""
    return FormatField(name, "=", "l")
def SNInt64(name):
    """signed, native endianity 64-bit integer"""
    return FormatField(name, "=", "q")

def BFloat32(name):
    """big endian, 32-bit IEEE floating point number"""
    return FormatField(name, ">", "f")
def LFloat32(name):
    """little endian, 32-bit IEEE floating point number"""
    return FormatField(name, "<", "f")
def NFloat32(name):
    """native endianity, 32-bit IEEE floating point number"""
    return FormatField(name, "=", "f")

def BFloat64(name):
    """big endian, 64-bit IEEE floating point number"""
    return FormatField(name, ">", "d")
def LFloat64(name):
    """little endian, 64-bit IEEE floating point number"""
    return FormatField(name, "<", "d")
def NFloat64(name):
    """native endianity, 64-bit IEEE floating point number"""
    return FormatField(name, "=", "d")


#===============================================================================
# arrays
#===============================================================================
def Array(count, subcon):
    """array of subcon repeated count times.
    * subcon - the subcon.
    * count - an integer, or a function taking the context as an argument, 
      returning the count
    """
    if callable(count):
        con = MetaArray(count, subcon)
    else:
        con = MetaArray(lambda ctx: count, subcon)
        con._clear_flag(con.FLAG_DYNAMIC)
    return con

def PrefixedArray(subcon, length_field = UBInt8("length")):
    """an array prefixed by a length field.
    * subcon - the subcon to be repeated
    * length_field - an integer construct
    """
    return LengthValueAdapter(
        Sequence(subcon.name, 
            length_field, 
            Array(lambda ctx: ctx[length_field.name], subcon),
            nested = False
        )
    )

def OpenRange(mincount, subcon):
    from sys import maxint
    return Range(mincount, maxint, subcon)

def GreedyRange(subcon):
    """an open range (1 or more times) of repeated subcon.
    * subcon - the subcon to repeat"""
    return OpenRange(1, subcon)

def OptionalGreedyRange(subcon):
    """an open range (0 or more times) of repeated subcon.
    * subcon - the subcon to repeat"""
    return OpenRange(0, subcon)


#===============================================================================
# subconstructs
#===============================================================================
def Optional(subcon):
    """an optional construct. if parsing fails, returns None.
    * subcon - the subcon to optionally parse or build
    """
    return Select(subcon.name, subcon, Pass)

def Bitwise(subcon):
    """converts the stream to bits, and passes the bitstream to subcon
    * subcon - a bitwise construct (usually BitField)
    """
    # subcons larger than MAX_BUFFER will be wrapped by Restream instead 
    # of Buffered. implementation details, don't stick your nose :)
    MAX_BUFFER = 1024 * 8
    def resizer(length):
        if length & 7:
            raise SizeofError("size must be a multiple of 8", length)
        return length >> 3
    if not subcon._is_flag(subcon.FLAG_DYNAMIC) and subcon.sizeof() < MAX_BUFFER:
        con = Buffered(subcon, 
            encoder = decode_bin, 
            decoder = encode_bin, 
            resizer = resizer
        )
    else:
        con = Restream(subcon, 
            stream_reader = BitStreamReader, 
            stream_writer = BitStreamWriter, 
            resizer = resizer)
    return con

def Aligned(subcon, modulus = 4, pattern = "\x00"):
    r"""aligns subcon to modulus boundary using padding pattern
    * subcon - the subcon to align
    * modulus - the modulus boundary (default is 4)
    * pattern - the padding pattern (default is \x00)
    """
    if modulus < 2:
        raise ValueError("modulus must be >= 2", modulus)
    if modulus in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024):
        def padlength(ctx):
            m1 = modulus - 1
            return (modulus - (subcon._sizeof(ctx) & m1)) & m1
    else:
        def padlength(ctx):
            return (modulus - (subcon._sizeof(ctx) % modulus)) % modulus
    return IndexingAdapter(
        Sequence(subcon.name, 
            subcon, 
            Padding(padlength, pattern = pattern),
            nested = False,
        ),
        0
    )

def Embedded(subcon):
    """embeds a struct into the enclosing struct.
    * subcon - the struct to embed
    """
    return Reconfig(subcon.name, subcon, subcon.FLAG_EMBED)

def Rename(newname, subcon):
    """renames an existing construct
    * newname - the new name
    * subcon - the subcon to rename
    """
    return Reconfig(newname, subcon)

def Alias(newname, oldname):
    """creates an alias for an existing element in a struct
    * newname - the new name
    * oldname - the name of an existing element
    """
    return Value(newname, lambda ctx: ctx[oldname])


#===============================================================================
# mapping
#===============================================================================
def SymmetricMapping(subcon, mapping, default = NotImplemented):
    """defines a symmetrical mapping: a->b, b->a.
    * subcon - the subcon to map
    * mapping - the encoding mapping (a dict); the decoding mapping is 
      achieved by reversing this mapping
    * default - the default value to use when no mapping is found. if no 
      default value is given, and exception is raised. setting to Pass would
      return the value "as is" (unmapped)
    """
    reversed_mapping = dict((v, k) for k, v in mapping.iteritems())
    return MappingAdapter(subcon, 
        encoding = mapping, 
        decoding = reversed_mapping, 
        encdefault = default,
        decdefault = default, 
    )

def Enum(subcon, **kw):
    """a set of named values mapping. 
    * subcon - the subcon to map
    * kw - keyword arguments which serve as the encoding mapping
    * _default_ - an optional, keyword-only argument that specifies the 
      default value to use when the mapping is undefined. if not given,
      and exception is raised when the mapping is undefined. use `Pass` to
      pass the unmapped value as-is
    """
    return SymmetricMapping(subcon, kw, kw.pop("_default_", NotImplemented))

def FlagsEnum(subcon, **kw):
    """a set of flag values mapping.
    * subcon - the subcon to map
    * kw - keyword arguments which serve as the encoding mapping
    """
    return FlagsAdapter(subcon, kw)


#===============================================================================
# structs
#===============================================================================
def AlignedStruct(name, *subcons, **kw):
    """a struct of aligned fields
    * name - the name of the struct
    * subcons - the subcons that make up this structure
    * kw - keyword arguments to pass to Aligned: 'modulus' and 'pattern'
    """
    return Struct(name, *(Aligned(sc, **kw) for sc in subcons))

def BitStruct(name, *subcons):
    """a struct of bitwise fields
    * name - the name of the struct
    * subcons - the subcons that make up this structure
    """
    return Bitwise(Struct(name, *subcons))

def EmbeddedBitStruct(*subcons):
    """an embedded BitStruct. no name is necessary.
    * subcons - the subcons that make up this structure
    """
    return Bitwise(Embedded(Struct(None, *subcons)))

#===============================================================================
# strings
#===============================================================================
def String(name, length, encoding = None, padchar = None, 
           paddir = "right", trimdir = "right"):
    """a fixed-length, optionally padded string of characters
    * name - the name of the field
    * length - the length (integer)
    * encoding - the encoding to use (e.g., "utf8"), or None, for raw bytes.
      default is None
    * padchar - the padding character (commonly "\x00"), or None to 
      disable padding. default is None
    * paddir - the direction where padding is placed ("right", "left", or 
      "center"). the default is "right". this argument is meaningless if 
      padchar is None.
    * trimdir - the direction where trimming will take place ("right" or 
      "left"). the default is "right". trimming is only meaningful for
      building, when the given string is too long. this argument is 
      meaningless if padchar is None.
    """
    con = StringAdapter(Field(name, length), encoding = encoding)
    if padchar is not None:
        con = PaddedStringAdapter(con, 
            padchar = padchar, 
            paddir = paddir, 
            trimdir = trimdir
        )
    return con

def PascalString(name, length_field = UBInt8("length"), encoding = None):
    """a string prefixed with a length field. the data must directly follow 
    the length field.
    * name - the name of the 
    * length_field - a numeric construct (i.e., UBInt8) that holds the 
      length. default is an unsigned, 8-bit integer field. note that this
      argument must pass an instance of a construct, not a class 
      (`UBInt8("length")` rather than `UBInt8`)
    * encoding - the encoding to use (e.g., "utf8"), or None, for raw bytes.
      default is None
    """
    return StringAdapter(
        LengthValueAdapter(
            Sequence(name,
                length_field,
                Field("data", lambda ctx: ctx[length_field.name]),
            )
        ),
        encoding = encoding,
    )

def CString(name, terminators = "\x00", encoding = None, 
            char_field = Field(None, 1)):
    r"""a c-style string (string terminated by a terminator char)
    * name - the name fo the string
    * terminators - a sequence of terminator chars. default is "\x00".
    * encoding - the encoding to use (e.g., "utf8"), or None, for raw bytes.
      default is None
    * char_field - the construct that represents a single character. default
      is a one-byte character. note that this argument must be an instance
      of a construct, not a construct class (`Field("char", 1)` rather than
      `Field`)
    """
    return Rename(name,
        CStringAdapter(
            RepeatUntil(lambda obj, ctx: obj in terminators, 
                char_field,
            ),
            terminators = terminators,
            encoding = encoding,
        )
    )


#===============================================================================
# conditional
#===============================================================================
def IfThenElse(name, predicate, then_subcon, else_subcon):
    """an if-then-else conditional construct: if the predicate indicates True,
    `then_subcon` will be used; otherwise `else_subcon`
    * name - the name of the construct
    * predicate - a function taking the context as an argument and returning
      True or False
    * then_subcon - the subcon that will be used if the predicate returns True
    * else_subcon - the subcon that will be used if the predicate returns False
    """
    return Switch(name, lambda ctx: bool(predicate(ctx)),
        {
            True : then_subcon,
            False : else_subcon,
        }
    )

def If(predicate, subcon, elsevalue = None):
    """an if-then conditional construct: if the predicate indicates True,
    subcon will be used; otherwise, `elsevalue` will be returned instead.
    * predicate - a function taking the context as an argument and returning
      True or False
    * subcon - the subcon that will be used if the predicate returns True
    * elsevalue - the value that will be used should the predicate return False.
      by default this value is None.
    """
    return IfThenElse(subcon.name, 
        predicate, 
        subcon, 
        Value("elsevalue", lambda ctx: elsevalue)
    )


#===============================================================================
# misc
#===============================================================================
def OnDemandPointer(offsetfunc, subcon, force_build = True):
    """an on-demand pointer. 
    * offsetfunc - a function taking the context as an argument and returning 
      the absolute stream position
    * subcon - the subcon that will be parsed from the `offsetfunc()` stream 
      position on demand
    * force_build - see OnDemand. by default True.
    """
    return OnDemand(Pointer(offsetfunc, subcon), 
        advance_stream = False, 
        force_build = force_build
    )



























