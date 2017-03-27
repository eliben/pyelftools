# -*- coding: utf-8 -*-

import struct as packer
from struct import Struct as Packer
from struct import error as PackerError
from io import BytesIO, StringIO
from binascii import hexlify, unhexlify
import sys
import collections

from construct.lib import *


#===============================================================================
# exceptions
#===============================================================================
class ConstructError(Exception):
    pass
class FieldError(ConstructError):
    pass
class SizeofError(ConstructError):
    pass
class AdaptationError(ConstructError):
    pass
class RangeError(ConstructError):
    pass
class SwitchError(ConstructError):
    pass
class SelectError(ConstructError):
    pass
class UnionError(ConstructError):
    pass
class FocusedError(ConstructError):
    pass
class TerminatedError(ConstructError):
    pass
class OverwriteError(ConstructError):
    pass
class PaddingError(ConstructError):
    pass
class ConstError(ConstructError):
    pass
class StringError(ConstructError):
    pass
class ChecksumError(ConstructError):
    pass
class ValidationError(ConstructError):
    pass
class BitIntegerError(ConstructError):
    pass
class MappingError(AdaptationError):
    pass
class ExplicitError(Exception):
    pass


#===============================================================================
# internal code
#===============================================================================
def singleton(cls):
    return cls()

def singletonfunction(func):
    return func()

def _read_stream(stream, length):
    # if not isinstance(length, int):
    #     raise TypeError("expected length to be int")
    if length < 0:
        raise ValueError("length must be >= 0", length)
    data = stream.read(length)
    if len(data) != length:
        raise FieldError("could not read enough bytes, expected %d, found %d" % (length, len(data)))
    return data

def _write_stream(stream, length, data):
    # if not isinstance(data, bytes):
    #     raise TypeError("expected data to be a bytes")
    if length < 0:
        raise ValueError("length must be >= 0", length)
    if len(data) != length:
        raise FieldError("could not write bytes, expected %d, found %d" % (length, len(data)))
    written = stream.write(data)
    if written is not None and written != length:
        raise FieldError("could not write bytes, written %d, should %d" % (written, length))


#===============================================================================
# abstract constructs
#===============================================================================
class Construct(object):
    r"""
    The mother of all constructs.

    This object is generally not directly instantiated, and it does not directly implement parsing and building, so it is largely only of interest to subclass implementors. There are also other abstract classes.

    The external user API:

     * ``parse()``
     * ``parse_stream()``
     * ``build()``
     * ``build_stream()``
     * ``sizeof()``

    Subclass authors should not override the external methods. Instead, another API is available:

     * ``_parse()``
     * ``_build()``
     * ``_sizeof()``

    There is also a flag API:

     * ``_inherit_flags()``

    And stateful copying:

     * ``__getstate__()``
     * ``__setstate__()``

    Attributes and Inheritance
    ==========================

    All constructs have a name and flags. The name is used for naming struct members and context dictionaries. Note that the name can either be a string, or None if the name is not needed. A single underscore ("_") is a reserved name, and so are names starting with a less-than character ("<"). The name should be descriptive, short, and valid as a Python identifier, although these rules are not enforced.

    The flags specify additional behavioral information about this construct. Flags are used by enclosing constructs to determine a proper course of action. Flags are inherited by default, from inner subconstructs to outer constructs. The enclosing construct may set new flags or clear existing ones, as necessary.
    """

    __slots__ = ["name", "flagbuildnone", "flagembedded"]
    def __init__(self):
        self.name = None
        self.flagbuildnone = False
        self.flagembedded = False

    def __repr__(self):
        return "<%s: %s%s%s>" % (self.__class__.__name__, self.name, " +nonbuild" if self.flagbuildnone else "", " +embedded" if self.flagembedded else "")

    def _inherit_flags(self, *subcons):
        for sc in subcons:
            self.flagbuildnone |= sc.flagbuildnone
            self.flagembedded |= sc.flagembedded

    def __getstate__(self):
        # Obtain a dictionary representing this construct's state.
        attrs = {}
        if hasattr(self, "__dict__"):
            attrs.update(self.__dict__)
        slots = []
        c = self.__class__
        while c is not None:
            if hasattr(c, "__slots__"):
                slots.extend(c.__slots__)
            c = c.__base__
        for name in slots:
            if hasattr(self, name):
                attrs[name] = getattr(self, name)
        return attrs

    def __setstate__(self, attrs):
        # Set this construct's state to a given state.
        for name, value in attrs.items():
            setattr(self, name, value)

    def __copy__(self):
        # Returns a copy of this construct.
        self2 = object.__new__(self.__class__)
        self2.__setstate__(self, self.__getstate__())
        return self2

    def parse(self, data, context=None, **kw):
        """
        Parse an in-memory buffer.

        Strings, buffers, memoryviews, and other complete buffers can be parsed with this method.
        """
        return self.parse_stream(BytesIO(data), context, **kw)

    def parse_stream(self, stream, context=None, **kw):
        """
        Parse a stream.

        Files, pipes, sockets, and other streaming sources of data are handled by this method.
        """
        if context is None:
            context = Container()
        context.update(kw)
        return self._parse(stream, context, "parsing")

    def _parse(self, stream, context, path):
        """
        Override in your subclass.

        :returns: some value, usually based on bytes read from the stream but sometimes it is computed from nothing or context
        """
        raise NotImplementedError()

    def build(self, obj, context=None, **kw):
        """
        Build an object in memory.

        :returns: bytes
        """
        stream = BytesIO()
        self.build_stream(obj, stream, context, **kw)
        return stream.getvalue()

    def build_stream(self, obj, stream, context=None, **kw):
        """
        Build an object directly into a stream.

        :returns: None
        """
        if context is None:
            context = Container()
        context.update(kw)
        self._build(obj, stream, context, "building")

    def _build(self, obj, stream, context, path):
        """
        Override in your subclass.

        :returns: None or a new value to put into context, few fields use this
        """
        raise NotImplementedError()

    def sizeof(self, context=None, **kw):
        """
        Calculate the size of this object, optionally using a context.

        Some constructs have no fixed size and can only know their size for a given hunk of data. These constructs will raise an error if they are not passed a context.

        :param context: a container

        :returns: int of the length of this construct
        :raises SizeofError: the size could not be determined
        """
        if context is None:
            context = Container()
        context.update(kw)
        return self._sizeof(context, "sizeof")

    def _sizeof(self, context, path):
        """
        Override in your subclass.

        :returns: an int for a fixed size field
        :raises SizeofError: the size could not be determined
        """
        raise SizeofError("cannot calculate size")

    def __getitem__(self, count):
        if isinstance(count, slice):
            if count.step is not None:
                raise ValueError("slice must not contain a step: %r" % count)
            min = 0 if count.start is None else count.start
            max = sys.maxsize if count.stop is None else count.stop
            return Range(min, max, self)
        elif isinstance(count, int) or callable(count):
            return Range(count, count, self)
        else:
            raise TypeError("expected an int, a context lambda, or a slice thereof, but found %r" % count)

    def __rshift__(self, other):
        lhs = self.subcons  if isinstance(self,  Sequence) else [self]
        rhs = other.subcons if isinstance(other, Sequence) else [other]
        return Sequence(*(lhs + rhs))

    def __rtruediv__(self, name):
        if name is not None:
            if not isinstance(name, stringtypes):
                raise TypeError("name must be b-string or u-string or None", name)
        return Renamed(name, self)
    __rdiv__ = __rtruediv__

    def __add__(self, other):
        lhs = self.subcons  if isinstance(self,  Struct) else [self]
        rhs = other.subcons if isinstance(other, Struct) else [other]
        return Struct(*(lhs + rhs))


class Subconstruct(Construct):
    r"""
    Abstract subconstruct (wraps an inner construct, inheriting its name and flags). Parsing and building is by default deferred to subcon, so it sizeof.

    Subconstructs wrap an inner Construct, inheriting its name and flags.

    :param subcon: the construct to wrap
    """
    __slots__ = ["subcon"]
    def __init__(self, subcon):
        if not isinstance(subcon, Construct):
            raise TypeError("subcon should be a Construct field")
        super(Subconstruct, self).__init__()
        self.name = subcon.name
        self.subcon = subcon
        self._inherit_flags(subcon)
    def _parse(self, stream, context, path):
        return self.subcon._parse(stream, context, path)
    def _build(self, obj, stream, context, path):
        return self.subcon._build(obj, stream, context, path)
    def _sizeof(self, context, path):
        return self.subcon._sizeof(context, path)


class Adapter(Subconstruct):
    r"""
    Abstract adapter parent class.

    Needs to implement ``_decode()`` and ``_encode()``.

    :param subcon: the construct to wrap
    """
    def _parse(self, stream, context, path):
        return self._decode(self.subcon._parse(stream, context, path), context)
    def _build(self, obj, stream, context, path):
        return self.subcon._build(self._encode(obj, context), stream, context, path)
    def _decode(self, obj, context):
        raise NotImplementedError()
    def _encode(self, obj, context):
        raise NotImplementedError()


class SymmetricAdapter(Adapter):
    r"""
    Abstract adapter parent class.

    Needs to implement ``_decode()`` only. Encoding is done by same method.

    :param subcon: the construct to wrap
    """
    def _encode(self, obj, context):
        return self._decode(obj, context)


class Validator(SymmetricAdapter):
    r"""
    Abstract class: validates a condition on the encoded/decoded object.

    Needs to implement ``_validate()`` that returns bool.

    :param subcon: the subcon to validate
    """
    def _decode(self, obj, context):
        if not self._validate(obj, context):
            raise ValidationError("object failed validation", obj)
        return obj
    def _validate(self, obj, context):
        raise NotImplementedError()


class Tunnel(Subconstruct):
    def _parse(self, stream, context, path):
        data = stream.read()  # reads entire stream
        data = self._decode(data, context)
        return self.subcon.parse(data, context)
    def _build(self, obj, stream, context, path):
        data = self.subcon.build(obj, context)
        data = self._encode(data, context)
        _write_stream(stream, len(data), data)
    def _sizeof(self, context, path):
        raise SizeofError("cannot calculate size")
    def _decode(self, data, context):
        raise NotImplementedError()
    def _encode(self, data, context):
        raise NotImplementedError()
    def _sizeof(self, context, path):
        raise SizeofError("cannot calculate size")


#===============================================================================
# bytes and bits
#===============================================================================
class Bytes(Construct):
    r"""
    A field consisting of a specified number of bytes. Builds from a b-string, or an integer (although deprecated and BytesInteger should be used).

    .. seealso:: Analog :func:`~construct.core.BytesInteger` that parses and builds from integers.

    :param length: an int or a function that takes context and returns int

    Example::

        >>> Bytes(4).parse(b"beef")
        b'beef'
        >>> Bytes(4).build(_)
        b'beef'
        >>> Bytes(4).build(255)
        b'\x00\x00\x00\xff'
        >>> Bytes(4).sizeof()
        4
    """
    __slots__ = ["length"]
    def __init__(self, length):
        super(Bytes, self).__init__()
        self.length = length
    def _parse(self, stream, context, path):
        length = self.length(context) if callable(self.length) else self.length
        return _read_stream(stream, length)
    def _build(self, obj, stream, context, path):
        length = self.length(context) if callable(self.length) else self.length
        data = integer2bytes(obj, length) if isinstance(obj, int) else obj
        _write_stream(stream, length, data)
        return data
    def _sizeof(self, context, path):
        try:
            return self.length(context) if callable(self.length) else self.length
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


@singleton
class GreedyBytes(Construct):
    r"""
    A byte field, that parses the stream to the end and builds into the stream as-is.

    This is an analog to `Bytes(infinity)`, pun intended.

    .. seealso:: Analog :func:`~construct.core.GreedyString` that parses and builds from strings using an encoding.

    Example::

        >>> GreedyBytes.parse(b"helloworld")
        b'helloworld'
        >>> GreedyBytes.build(b"asis")
        b'asis'
    """
    def _parse(self, stream, context, path):
        return stream.read()
    def _build(self, obj, stream, context, path):
        stream.write(obj)


class FormatField(Bytes):
    r"""
    A field that uses ``struct`` module to pack and unpack data. This is used to implement basic Int* fields.

    See ``struct`` documentation for instructions on crafting format strings.

    :param endianity: format endianness string as one of: < > =
    :param format: single format character like: f d B H L Q b h l q

    Example::

        >>> FormatField(">","H").parse(b"\x01\x00")
        256
        >>> FormatField(">","H").build(18)
        b'\x00\x12'
        >>> FormatField(">","H").sizeof()
        2
    """
    __slots__ = ["fmtstr"]
    def __init__(self, endianity, format):
        if endianity not in (">", "<", "="):
            raise ValueError("endianity must be one of: = < >", endianity)
        if len(format) != 1:
            raise ValueError("must specify one and only one format character")
        super(FormatField, self).__init__(packer.calcsize(endianity + format))
        self.fmtstr = endianity + format
    def _parse(self, stream, context, path):
        try:
            return packer.unpack(self.fmtstr, _read_stream(stream, self.sizeof()))[0]
        except Exception:
            raise FieldError("packer %r error during parsing" % self.fmtstr)
    def _build(self, obj, stream, context, path):
        try:
            _write_stream(stream, self.sizeof(), packer.pack(self.fmtstr, obj))
        except Exception:
            raise FieldError("packer %r error during building, given value %s" % (self.fmtstr, obj))


def Bitwise(subcon):
    r"""
    Converts the stream from bytes to bits, and passes the bitstream to underlying subcon.

    .. seealso:: Analog :func:`~construct.core.Bytewise` that transforms subset of bits back to bytes.

    .. warning:: Do not use pointers inside.

    :param subcon: any field that works with bits like: BitStruct BitsNumber Bit Nibble Octet

    Example::

        >>> Bitwise(Octet).parse(b"\xff")
        255
        >>> Bitwise(Octet).build(1)
        b'\x01'
        >>> Bitwise(Octet).sizeof()
        1
    """
    return Restreamed(subcon, bits2bytes, 8, bytes2bits, 1, lambda n: n//8)


def Bytewise(subcon):
    r"""
    Converts the stream from bits back to bytes. Needs to be used within Bitwise.

    :param subcon: any field that works with bytes like: Bytes BytesInteger Int* Struct

    Example::

        >>> Bitwise(Bytewise(Byte)).parse(b"\xff")
        255
        >>> Bitwise(Bytewise(Byte)).build(63)
        b'?'
        >>> Bitwise(Bytewise(Byte)).sizeof()
        1
    """
    return Restreamed(subcon, bytes2bits, 1, bits2bytes, 8, lambda n: n*8)


class BytesInteger(Construct):
    r"""
    A byte field, that parses into and builds from integers as opposed to b-strings. This is similar to Int* fields but can be much longer than 4 or 8 bytes.

    .. seealso:: Analog :func:`~construct.core.BitsInteger` that operatoes on bits.

    :param length: number of bytes in the field, or a function that takes context and returns int
    :param signed: whether the value is signed (two's complement), default is False (unsigned)
    :param swapped: whether to swap byte order (little endian), default is False (big endian)
    :param bytesize: size of byte as used for byte swapping (if swapped), default is 1

    Example::

        >>> BytesInteger(4).parse(b"abcd")
        1633837924
        >>> BytesInteger(4).build(1)
        b'\x00\x00\x00\x01'
        >>> BytesInteger(4).sizeof()
        4
    """
    __slots__ = ["length", "signed", "swapped", "bytesize"]
    def __init__(self, length, signed=False, swapped=False, bytesize=1):
        super(BytesInteger, self).__init__()
        self.length = length
        self.signed = signed
        self.swapped = swapped
        self.bytesize = bytesize
    def _parse(self, stream, context, path):
        length = self.length(context) if callable(self.length) else self.length
        data = _read_stream(stream, length)
        if self.swapped:
            data = swapbytes(data, self.bytesize)
        return bytes2integer(data, self.signed)
    def _build(self, obj, stream, context, path):
        if obj < 0 and not self.signed:
            raise BitIntegerError("object is negative, but field is not signed", obj)
        length = self.length(context) if callable(self.length) else self.length
        data = integer2bytes(obj, length)
        if self.swapped:
            data = swapbytes(data, self.bytesize)
        _write_stream(stream, len(data), data)
    def _sizeof(self, context, path):
        try:
            return self.length(context) if callable(self.length) else self.length
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


class BitsInteger(Construct):
    r"""
    A byte field, that parses into and builds from integers as opposed to b-strings. This is similar to Bit/Nibble/Octet fields but can be much longer than 1/4/8 bits. This must be encosed in Bitwise.

    :param length: number of bits in the field, or a function that takes context and returns int
    :param signed: whether the value is signed (two's complement), default is False (unsigned)
    :param swapped: whether to swap byte order (little endian), default is False (big endian)
    :param bytesize: size of byte as used for byte swapping (if swapped), default is 8

    Example::

        >>> Bitwise(BitsInteger(8)).parse(b"\x10")
        16
        >>> Bitwise(BitsInteger(8)).build(255)
        b'\xff'
        >>> Bitwise(BitsInteger(8)).sizeof()
        1
    """
    __slots__ = ["length", "signed", "swapped", "bytesize"]
    def __init__(self, length, signed=False, swapped=False, bytesize=8):
        super(BitsInteger, self).__init__()
        self.length = length
        self.signed = signed
        self.swapped = swapped
        self.bytesize = bytesize
    def _parse(self, stream, context, path):
        length = self.length(context) if callable(self.length) else self.length
        data = _read_stream(stream, length)
        if self.swapped:
            data = swapbytes(data, self.bytesize)
        return bits2integer(data, self.signed)
    def _build(self, obj, stream, context, path):
        if obj < 0 and not self.signed:
            raise BitIntegerError("object is negative, but field is not signed", obj)
        length = self.length(context) if callable(self.length) else self.length
        data = integer2bits(obj, length)
        if self.swapped:
            data = swapbytes(data, self.bytesize)
        _write_stream(stream, len(data), data)
    def _sizeof(self, context, path):
        try:
            return self.length(context) if callable(self.length) else self.length
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


#===============================================================================
# integers and floats
#===============================================================================
@singletonfunction
def Bit():
    """A 1-bit integer; must be enclosed in a BitStruct or similar"""
    return BitsInteger(1)
@singletonfunction
def Nibble():
    """A 4-bit integer; must be enclosed in a BitStruct or similar"""
    return BitsInteger(4)
@singletonfunction
def Octet():
    """An 8-bit integer; must be enclosed in a BitStruct or similar"""
    return BitsInteger(8)

@singletonfunction
def Int8ub():
    """Unsigned, big endian 8-bit integer"""
    return FormatField(">", "B")
@singletonfunction
def Int16ub():
    """Unsigned, big endian 16-bit integer"""
    return FormatField(">", "H")
@singletonfunction
def Int32ub():
    """Unsigned, big endian 32-bit integer"""
    return FormatField(">", "L")
@singletonfunction
def Int64ub():
    """Unsigned, big endian 64-bit integer"""
    return FormatField(">", "Q")

@singletonfunction
def Int8sb():
    """Signed, big endian 8-bit integer"""
    return FormatField(">", "b")
@singletonfunction
def Int16sb():
    """Signed, big endian 16-bit integer"""
    return FormatField(">", "h")
@singletonfunction
def Int32sb():
    """Signed, big endian 32-bit integer"""
    return FormatField(">", "l")
@singletonfunction
def Int64sb():
    """Signed, big endian 64-bit integer"""
    return FormatField(">", "q")

@singletonfunction
def Int8ul():
    """Unsigned, little endian 8-bit integer"""
    return FormatField("<", "B")
@singletonfunction
def Int16ul():
    """Unsigned, little endian 16-bit integer"""
    return FormatField("<", "H")
@singletonfunction
def Int32ul():
    """Unsigned, little endian 32-bit integer"""
    return FormatField("<", "L")
@singletonfunction
def Int64ul():
    """Unsigned, little endian 64-bit integer"""
    return FormatField("<", "Q")

@singletonfunction
def Int8sl():
    """Signed, little endian 8-bit integer"""
    return FormatField("<", "b")
@singletonfunction
def Int16sl():
    """Signed, little endian 16-bit integer"""
    return FormatField("<", "h")
@singletonfunction
def Int32sl():
    """Signed, little endian 32-bit integer"""
    return FormatField("<", "l")
@singletonfunction
def Int64sl():
    """Signed, little endian 64-bit integer"""
    return FormatField("<", "q")

@singletonfunction
def Int8un():
    """Unsigned, native endianity 8-bit integer"""
    return FormatField("=", "B")
@singletonfunction
def Int16un():
    """Unsigned, native endianity 16-bit integer"""
    return FormatField("=", "H")
@singletonfunction
def Int32un():
    """Unsigned, native endianity 32-bit integer"""
    return FormatField("=", "L")
@singletonfunction
def Int64un():
    """Unsigned, native endianity 64-bit integer"""
    return FormatField("=", "Q")

@singletonfunction
def Int8sn():
    """Signed, native endianity 8-bit integer"""
    return FormatField("=", "b")
@singletonfunction
def Int16sn():
    """Signed, native endianity 16-bit integer"""
    return FormatField("=", "h")
@singletonfunction
def Int32sn():
    """Signed, native endianity 32-bit integer"""
    return FormatField("=", "l")
@singletonfunction
def Int64sn():
    """Signed, native endianity 64-bit integer"""
    return FormatField("=", "q")

Byte = Int8ub

@singletonfunction
def Float32b():
    """Big endian, 32-bit IEEE floating point number"""
    return FormatField(">", "f")
@singletonfunction
def Float32l():
    """Little endian, 32-bit IEEE floating point number"""
    return FormatField("<", "f")
@singletonfunction
def Float32n():
    """Native endianity, 32-bit IEEE floating point number"""
    return FormatField("=", "f")

@singletonfunction
def Float64b():
    """Big endian, 64-bit IEEE floating point number"""
    return FormatField(">", "d")
@singletonfunction
def Float64l():
    """Little endian, 64-bit IEEE floating point number"""
    return FormatField("<", "d")
@singletonfunction
def Float64n():
    """Native endianity, 64-bit IEEE floating point number"""
    return FormatField("=", "d")

Single = Float32b
Double = Float64b

@singletonfunction
def Int24ub():
    """A 3-byte big-endian unsigned integer, as used in ancient file formats."""
    return BytesInteger(3)
@singletonfunction
def Int24ul():
    """A 3-byte little-endian unsigned integer, as used in ancient file formats."""
    return BytesInteger(3, swapped=True)
@singletonfunction
def Int24sb():
    """A 3-byte big-endian signed integer, as used in ancient file formats."""
    return BytesInteger(3, signed=True)
@singletonfunction
def Int24sl():
    """A 3-byte little-endian signed integer, as used in ancient file formats."""
    return BytesInteger(3, signed=True, swapped=True)


@singleton
class VarInt(Construct):
    r"""
    Varint encoded integer. Each 7 bits of the number are encoded in one byte in the stream, having leftmost bit not set when byte is terminal.

    Scheme defined at Google's site:
    https://developers.google.com/protocol-buffers/docs/encoding
    https://techoverflow.net/blog/2013/01/25/efficiently-encoding-variable-length-integers-in-cc/

    Example::

        >>> VarInt.build(16)
        b'\x10'
        >>> VarInt.parse(_)
        16
        >>> VarInt.build(2**100)
        b'\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80\x04'
        >>> VarInt.parse(_)
        1267650600228229401496703205376
    """
    def _parse(self, stream, context, path):
        acc = []
        while True:
            b = byte2int(_read_stream(stream, 1))
            acc.append(b & 0b01111111)
            if not b & 0b10000000:
                break
        num = 0
        for b in reversed(acc):
            num = (num << 7) | b
        return num
    def _build(self, obj, stream, context, path):
        if obj < 0:
            raise ValueError("varint cannot build from negative number")
        while obj > 0b01111111:
            _write_stream(stream, 1, int2byte(0b10000000 | (obj & 0b01111111)))
            obj >>= 7
        _write_stream(stream, 1, int2byte(obj))


#===============================================================================
# structures and sequences
#===============================================================================
class Struct(Construct):
    r"""
    A sequence of usually named constructs, similar to structs in C. The elements are parsed and built in the order they are defined.

    Some fields do not need to be named, since they are built from None anyway. See Const Padding Pass Terminated.

    .. seealso:: Can be nested easily, and embedded using :func:`~construct.core.Embedded` wrapper that merges members into parent's members.

    :param subcons: a sequence of subconstructs that make up this structure

    Example::

        >>> Struct("a"/Int8ul, "data"/Bytes(2), "data2"/Bytes(this.a)).parse(b"\x01abc")
        Container(a=1)(data=b'ab')(data2=b'c')
        >>> Struct("a"/Int8ul, "data"/Bytes(2), "data2"/Bytes(this.a)).build(_)
        b'\x01abc'
        >>> Struct("a"/Int8ul, "data"/Bytes(2), "data2"/Bytes(this.a)).build(dict(a=5, data=b"??", data2=b"hello"))
        b'\x05??hello'

        >>> Struct(Const(b"MZ"), Padding(2), Pass, Terminated).build({})
        b'MZ\x00\x00'
        >>> Struct(Const(b"MZ"), Padding(2), Pass, Terminated).parse(_)
        Container()
        >>> Struct(Const(b"MZ"), Padding(2), Pass, Terminated).sizeof()
        4

        Note that this syntax works ONLY on python 3.6 and pypy due to unordered keyword arguments:
        >>> Struct(a=Byte, b=Byte, c=Byte, d=Byte)
    """
    __slots__ = ["subcons"]
    def __init__(self, *subcons, **kw):
        subcons = list(subcons)
        for k,v in kw.items():
            subcons.append(k / v)
        super(Struct, self).__init__()
        self.subcons = subcons
    def _parse(self, stream, context, path):
        obj = Container()
        context = Container(_ = context)
        for i,sc in enumerate(self.subcons):
            if sc.flagembedded:
                subobj = list(sc._parse(stream, context, path).items())
                obj.update(subobj)
                context.update(subobj)
            else:
                subobj = sc._parse(stream, context, path)
                if sc.name is not None:
                    obj[sc.name] = subobj
                    context[sc.name] = subobj
        return obj
    def _build(self, obj, stream, context, path):
        context = Container(_ = context)
        context.update(obj)
        for i,sc in enumerate(self.subcons):
            if sc.flagembedded:
                subobj = obj
            elif sc.flagbuildnone:
                subobj = obj.get(sc.name, None)
            else:
                subobj = obj[sc.name]
            buildret = sc._build(subobj, stream, context, path)
            if buildret is not None:
                if sc.flagembedded:
                    context.update(buildret)
                if sc.name is not None:
                    context[sc.name] = buildret
        return context
    def _sizeof(self, context, path):
        try:
        #     def isStruct(sc):
        #         return isStruct(sc.subcon) if isinstance(sc, Renamed) else isinstance(sc.subcon, Struct)
        #     def nest(context, sc):
        #         if isStruct(sc) and sc.name in context:
        #         # if isinstance(sc, Renamed) and isinstance(sc.subcon, Struct) and sc.name in context:
        #         # if isinstance(sc, Struct) and sc.name in context:
        #             context2 = context[sc.name]
        #             context2._ = context
        #             return context2
        #         else:
        #             return Container()
        #     return sum(sc._sizeof(nest(context, sc), path) for sc in self.subcons)
            return sum(sc._sizeof(context, path) for sc in self.subcons)
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


class Sequence(Struct):
    r"""
    A sequence of unnamed constructs. The elements are parsed and built in the order they are defined.

    .. seealso:: Can be nested easily, and embedded using :func:`~construct.core.Embedded` wrapper that merges entries into parent's entries.

    :param subcons: a sequence of subconstructs that make up this sequence

    Example::

        >>> (Byte >> Byte).build([1, 2])
        b'\x01\x02'
        >>> (Byte >> Byte).parse(_)
        [1, 2]
        >>> (Byte >> Byte).sizeof()
        2

        >>> Sequence(Byte, CString(), Float32b).build([255, b"hello", 123])
        b'\xffhello\x00B\xf6\x00\x00'
        >>> Sequence(Byte, CString(), Float32b).parse(_)
        [255, b'hello', 123.0]
    """
    def _parse(self, stream, context, path):
        obj = ListContainer()
        context = Container(_ = context)
        for i,sc in enumerate(self.subcons):
            subobj = sc._parse(stream, context, path)
            if sc.flagembedded:
                obj.extend(subobj)
                context[i] = subobj
            else:
                obj.append(subobj)
                if sc.name is not None:
                    context[sc.name] = subobj
                context[i] = subobj
        return obj
    def _build(self, obj, stream, context, path):
        context = Container(_ = context)
        objiter = iter(obj)
        for i,sc in enumerate(self.subcons):
            if sc.flagembedded:
                subobj = objiter
            else:
                subobj = next(objiter)
                if sc.name is not None:
                    context[sc.name] = subobj
            context[i] = subobj
            buildret = sc._build(subobj, stream, context, path)
            if buildret is not None:
                if sc.flagembedded:
                    context.update(buildret)
                if sc.name is not None:
                    context[sc.name] = buildret
                context[i] = buildret


#===============================================================================
# arrays and repeaters
#===============================================================================
class Range(Subconstruct):
    r"""
    A homogenous array of elements. The array will iterate through between ``min`` to ``max`` times. If an exception occurs (EOF, validation error), the repeater exits cleanly. If less than ``min`` units have been successfully parsed, a RangeError is raised.

    .. seealso:: Analog :func:`~construct.core.GreedyRange` that parses until end of stream.

    .. note:: This object requires a seekable stream for parsing.

    :param min: the minimal count
    :param max: the maximal count
    :param subcon: the subcon to process individual elements

    Example::

        >>> Range(3, 5, Byte).build([1,2,3,4])
        b'\x01\x02\x03\x04'
        >>> Range(3, 5, Byte).parse(_)
        [1, 2, 3, 4]

        >>> Range(3, 5, Byte).build([1,2])
        construct.core.RangeError: expected from 3 to 5 elements, found 2
        >>> Range(3, 5, Byte).build([1,2,3,4,5,6])
        construct.core.RangeError: expected from 3 to 5 elements, found 6
    """
    __slots__ = ["min", "max"]
    def __init__(self, min, max, subcon):
        super(Range, self).__init__(subcon)
        self.min = min
        self.max = max
    def _parse(self, stream, context, path):
        min = self.min(context) if callable(self.min) else self.min
        max = self.max(context) if callable(self.max) else self.max
        if not 0 <= min <= max <= sys.maxsize:
            raise RangeError("unsane min %s and max %s" % (min, max))
        obj = ListContainer()
        context = Container(_ = context)
        try:
            while len(obj) < max:
                fallback = stream.tell()
                obj.append(self.subcon._parse(stream, context._, path))
                context[len(obj)-1] = obj[-1]
        except ExplicitError:
            raise
        except Exception:
            if len(obj) < min:
                raise RangeError("expected %d to %d, found %d" % (min, max, len(obj)))
            stream.seek(fallback)
        return obj
    def _build(self, obj, stream, context, path):
        min = self.min(context) if callable(self.min) else self.min
        max = self.max(context) if callable(self.max) else self.max
        if not 0 <= min <= max <= sys.maxsize:
            raise RangeError("unsane min %s and max %s" % (min, max))
        if not isinstance(obj, collections.Sequence):
            raise RangeError("expected sequence type, found %s" % type(obj))
        if not min <= len(obj) <= max:
            raise RangeError("expected from %d to %d elements, found %d" % (min, max, len(obj)))
        context = Container(_ = context)
        try:
            for i,subobj in enumerate(obj):
                context[i] = subobj
                self.subcon._build(subobj, stream, context._, path)
        except ExplicitError:
            raise
        except Exception:
            if len(obj) < min:
                raise RangeError("expected %d to %d, found %d" % (min, max, len(obj)))
            else:
                raise
    def _sizeof(self, context, path):
        try:
            min = self.min(context) if callable(self.min) else self.min
            max = self.max(context) if callable(self.max) else self.max
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")
        if min == max:
            return min * self.subcon._sizeof(context, path)
        else:
            raise SizeofError("cannot calculate size")


def GreedyRange(subcon):
    r"""
    A homogenous array of elements that parses until end of stream and builds from all elements.

    :param subcon: the subcon to process individual elements

    Example::

        >>> GreedyRange(Byte).build(range(10))
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t'
        >>> GreedyRange(Byte).parse(_)
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    return Range(0, sys.maxsize, subcon)


def Array(count, subcon):
    r"""
    A homogenous array of elements. The array will iterate through exactly ``count`` elements. Will raise RangeError if less elements are found.

    .. seealso:: Base :func:`~construct.core.Range` construct.

    :param count: int or a function that takes context and returns the number of elements
    :param subcon: the subcon to process individual elements

    Example::

        >>> Byte[5].build(range(5))
        b'\x00\x01\x02\x03\x04'
        >>> Byte[5].parse(_)
        [0, 1, 2, 3, 4]

        >>> Array(5, Byte).build(range(5))
        b'\x00\x01\x02\x03\x04'
        >>> Array(5, Byte).parse(_)
        [0, 1, 2, 3, 4]
    """
    return Range(count, count, subcon)


class PrefixedArray(Construct):
    r"""
    An array prefixed by a length field.

    .. seealso:: Analog :func:`~construct.core.Array` construct.

    :param lengthfield: a field parsing and building an integer
    :param subcon: the subcon to process individual elements

    Example::

        >>> PrefixedArray(Byte, Byte).build(range(5))
        b'\x05\x00\x01\x02\x03\x04'
        >>> PrefixedArray(Byte, Byte).parse(_)
        [0, 1, 2, 3, 4]
    """
    def __init__(self, lengthfield, subcon):
        super(PrefixedArray, self).__init__()
        self.lengthfield = lengthfield
        self.subcon = subcon
    def _parse(self, stream, context, path):
        try:
            count = self.lengthfield._parse(stream, context, path)
            return list(self.subcon._parse(stream, context, path) for i in range(count))
        except ExplicitError:
            raise
        except Exception:
            raise RangeError("could not read prefix or enough elements, stream too short?")
    def _build(self, obj, stream, context, path):
        self.lengthfield._build(len(obj), stream, context, path)
        for element in obj:
            self.subcon._build(element, stream, context, path)


class RepeatUntil(Subconstruct):
    r"""
    An array that repeats until the predicate indicates it to stop. Note that the last element (which caused the repeat to exit) is included in the return value.

    :param predicate: a predicate function that takes (obj, context) and returns True to break, or False to continue
    :param subcon: the subcon used to parse and build each element

    Example::

        >>> RepeatUntil(lambda x,ctx: x>7, Byte).build(range(20))
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08'
        >>> RepeatUntil(lambda x,ctx: x>7, Byte).parse(b"\x01\xff\x02")
        [1, 255]
    """
    __slots__ = ["predicate"]
    def __init__(self, predicate, subcon):
        super(RepeatUntil, self).__init__(subcon)
        self.predicate = predicate
    def _parse(self, stream, context, path):
        try:
            obj = ListContainer()
            while True:
                subobj = self.subcon._parse(stream, context, path)
                obj.append(subobj)
                if self.predicate(subobj, context):
                    return obj
        except ExplicitError:
            raise
        except ConstructError:
            raise RangeError("missing terminator when parsing")
    def _build(self, obj, stream, context, path):
        for subobj in obj:
            self.subcon._build(subobj, stream, context, path)
            if self.predicate(subobj, context):
                break
        else:
            raise RangeError("missing terminator when building")
    def _sizeof(self, context, path):
        raise SizeofError("cannot calculate size")


#===============================================================================
# subconstructs
#===============================================================================
class Padded(Subconstruct):
    r"""
    Appends additional null bytes to achieve a fixed length.

    Example::

        >>> Padded(4, Byte).build(255)
        b'\xff\x00\x00\x00'
        >>> Padded(4, Byte).parse(_)
        255
        >>> Padded(4, Byte).sizeof()
        4

        >>> Padded(4, VarInt).build(1)
        b'\x01\x00\x00\x00'
        >>> Padded(4, VarInt).build(70000)
        b'\xf0\xa2\x04\x00'
    """
    __slots__ = ["length", "pattern", "strict"]
    def __init__(self, length, subcon, pattern=b"\x00", strict=False):
        if not isinstance(pattern, bytes) or len(pattern) != 1:
            raise PaddingError("pattern expected to be b-string character")
        super(Padded, self).__init__(subcon)
        self.length = length
        self.pattern = pattern
        self.strict = strict
    def _parse(self, stream, context, path):
        length = self.length(context) if callable(self.length) else self.length
        position1 = stream.tell()
        obj = self.subcon._parse(stream, context, path)
        position2 = stream.tell()
        padlen = length - (position2 - position1)
        if padlen < 0:
            raise PaddingError("subcon parsed more bytes than was allowed by length")
        pad = _read_stream(stream, padlen)
        if self.strict:
            if pad != self.pattern * padlen:
                raise PaddingError("expected %r times %r, found %r" % (self.pattern, padlen, pad))
        return obj
    def _build(self, obj, stream, context, path):
        length = self.length(context) if callable(self.length) else self.length
        position1 = stream.tell()
        subobj = self.subcon._build(obj, stream, context, path)
        position2 = stream.tell()
        padlen = length - (position2 - position1)
        if padlen < 0:
            raise PaddingError("subcon parsed more bytes than was allowed by length")
        _write_stream(stream, padlen, self.pattern * padlen)
        return subobj
    def _sizeof(self, context, path):
        try:
            return self.length(context) if callable(self.length) else self.length
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


class Aligned(Subconstruct):
    r"""
    Appends additional null bytes to achieve a length that is shortest multiple of a modulus.

    :param modulus: the modulus to final length, an int or a context->int function
    :param subcon: the subcon to align
    :param pattern: optional, the padding pattern (default is \x00)

    Example::

        >>> Aligned(4, Int16ub).build(1)
        b'\x00\x01\x00\x00'
        >>> Aligned(4, Int16ub).parse(_)
        1
        >>> Aligned(4, Int16ub).sizeof()
        4
    """
    __slots__ = ["subcon", "modulus", "pattern"]
    def __init__(self, modulus, subcon, pattern=b"\x00"):
        if not isinstance(pattern, bytes) or len(pattern) != 1:
            raise PaddingError("pattern expected to be b-string character")
        super(Aligned, self).__init__(subcon)
        self.modulus = modulus
        self.pattern = pattern
    def _parse(self, stream, context, path):
        modulus = self.modulus(context) if callable(self.modulus) else self.modulus
        position1 = stream.tell()
        obj = self.subcon._parse(stream, context, path)
        position2 = stream.tell()
        pad = -(position2 - position1) % modulus
        _read_stream(stream, pad)
        return obj
    def _build(self, obj, stream, context, path):
        modulus = self.modulus(context) if callable(self.modulus) else self.modulus
        position1 = stream.tell()
        subobj = self.subcon._build(obj, stream, context, path)
        position2 = stream.tell()
        pad = -(position2 - position1) % modulus
        _write_stream(stream, pad, self.pattern * pad)
        return subobj
    def _sizeof(self, context, path):
        try:
            modulus = self.modulus(context) if callable(self.modulus) else self.modulus
            sublen = self.subcon._sizeof(context, path)
            return sublen + (-sublen % modulus)
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


def AlignedStruct(modulus, *subcons, **kw):
    r"""
    Makes a structure where each field is aligned to the same modulus.

    .. seealso:: Uses :func:`~construct.core.Aligned` and `~construct.core.Struct`.

    :param modulus: passed to each member
    :param \*subcons: the subcons that make up this structure
    :param pattern: optional, keyword parameter passed to each member

    Example::

        >>> AlignedStruct(4, "a"/Int8ub, "b"/Int16ub).build(dict(a=1,b=5))
        b'\x01\x00\x00\x00\x00\x05\x00\x00'
        >>> AlignedStruct(4, "a"/Int8ub, "b"/Int16ub).parse(_)
        Container(a=1)(b=5)
        >>> AlignedStruct(4, "a"/Int8ub, "b"/Int16ub).sizeof()
        8
    """
    return Struct(*[Aligned(modulus, sc, **kw) for sc in subcons])


def BitStruct(*subcons):
    r"""
    Makes a structure inside a Bitwise.

    .. seealso:: Uses :func:`~construct.core.Bitwise` and :func:`~construct.core.Struct`.

    :param \*subcons: the subcons that make up this structure

    Example::

        >>> BitStruct("field"/Octet).build(dict(field=5))
        b'\x05'
        >>> BitStruct("field"/Octet).parse(_)
        Container(field=5)
        >>> BitStruct("field"/Octet).sizeof()
        1

        >>> format = BitStruct(
        ...     "a" / Flag,
        ...     "b" / Nibble,
        ...     "c" / BitsInteger(10),
        ...     "d" / Padding(1),
        ... )
        >>> format.parse(b"\xbe\xef")
        Container(a=True)(b=7)(c=887)(d=None)
        >>> format.sizeof()
        2
    """
    return Bitwise(Struct(*subcons))


def EmbeddedBitStruct(*subcons):
    r"""
    Makes an embedded BitStruct.

    .. seealso:: Uses :func:`~construct.core.Bitwise` and :func:`~construct.core.Embedded` and :func:`~construct.core.Struct`.

    :param \*subcons: the subcons that make up this structure
    """
    return Bitwise(Embedded(Struct(*subcons)))


#===============================================================================
# conditional
#===============================================================================
class Union(Construct):
    r"""
    Treats the same data as multiple constructs (similar to C union statement) so you can "look" at the data in multiple views.

    When parsing, all fields read the same data bytes, but stream remains at same offset by default, unless buildfrom selects a subcon. When building, either the first subcon that can find an entry in given dict is allowed to put into the stream, or the subcon is selected by index or name, or builds nothing.

    :param subcons: subconstructs (order and name sensitive)
    :param buildfrom: optional, how to build, the subcon used for building and calculating size, can be integer index or string name selecting a subcon, None (then tries each subcon in sequence, the default), Pass (builds nothing), a context lambda returning either of previously mentioned

    Example::

        >>> Union("raw"/Bytes(8), "ints"/Int32ub[2], "shorts"/Int16ub[4], "chars"/Byte[8]).parse(b"12345678")
        Container(raw=b'12345678')(ints=[825373492, 892745528])(shorts=[12594, 13108, 13622, 14136])(chars=[49, 50, 51, 52, 53, 54, 55, 56])

        >>> Union("raw"/Bytes(8), "ints"/Int32ub[2], "shorts"/Int16ub[4], "chars"/Byte[8], buildfrom=3).build(dict(chars=range(8)))
        b'\x00\x01\x02\x03\x04\x05\x06\x07'
        >>> Union("raw"/Bytes(8), "ints"/Int32ub[2], "shorts"/Int16ub[4], "chars"/Byte[8], buildfrom="chars").build(dict(chars=range(8)))
        b'\x00\x01\x02\x03\x04\x05\x06\x07'

        Note that this syntax works ONLY on python 3.6 and pypy due to unordered keyword arguments:
        >>> Union(raw=Bytes(8), ints=Int32ub[2], shorts=Int16ub[4], chars=Byte[8], buildfrom=3)
    """
    __slots__ = ["subcons","buildfrom"]
    def __init__(self, *subcons, **kw):
        subcons = list(subcons)
        for k,v in kw.items():
            if k not in ["buildfrom"]:
                subcons.append(k / v)
        super(Union, self).__init__()
        self.subcons = [Peek(sc) for sc in subcons]
        self.buildfrom = kw.get("buildfrom")
    def _parse(self, stream, context, path):
        obj = Container()
        context = Container(_ = context)
        for i,sc in enumerate(self.subcons):
            if sc.flagembedded:
                subobj = list(sc._parse(stream, context, path).items())
                obj.update(subobj)
                context.update(subobj)
            else:
                subobj = sc._parse(stream, context, path)
                if sc.name is not None:
                    obj[sc.name] = subobj
                    context[sc.name] = subobj
        if callable(self.buildfrom):
            self.buildfrom = self.buildfrom(context)
        if isinstance(self.buildfrom, int):
            jump = self.subcons[self.buildfrom].subcon._sizeof(context, path)
            stream.seek(jump, 1)
        if isinstance(self.buildfrom, str):
            index = [i for i,sc in enumerate(self.subcons) if sc.name == self.buildfrom][0]
            jump = self.subcons[index].subcon._sizeof(context, path)
            stream.seek(jump, 1)
        return obj
    def _build(self, obj, stream, context, path):
        context = Container(_ = context)
        context.update(obj)
        if callable(self.buildfrom):
            self.buildfrom = self.buildfrom(context)
        if self.buildfrom is Pass:
            return
        if self.buildfrom is None:
            for i,sc in enumerate(self.subcons):
                if sc.subcon.flagbuildnone:
                    subobj = obj.get(sc.name, None)
                    buildret = sc.subcon._build(subobj, stream, context, path)
                    if buildret is not None:
                        if sc.flagembedded:
                            context.update(buildret)
                        if sc.name is not None:
                            context[sc.name] = buildret
                    return buildret
                elif sc.name in obj:
                    context[sc.name] = obj[sc.name]
                    buildret = sc.subcon._build(obj[sc.name], stream, context, path)
                    if buildret is not None:
                        if sc.flagembedded:
                            context.update(buildret)
                        if sc.name is not None:
                            context[sc.name] = buildret
                    return buildret
            else:
                raise UnionError("none of subcons %s were found in the dictionary %s" % (self.subcons, obj))
        if isinstance(self.buildfrom, int):
            sc = self.subcons[self.buildfrom]
            # pass the full object if building an embedded union member
            obj2 = obj if sc.flagembedded else obj[sc.name]
            return sc.subcon._build(obj2, stream, context, path)
        if isinstance(self.buildfrom, str):
            index = [i for i,sc in enumerate(self.subcons) if sc.name == self.buildfrom][0]
            sc = self.subcons[index]
            return sc.subcon._build(obj[sc.name], stream, context, path)
        raise UnionError("buildfrom should be either: None, Pass, an int, a str")
    def _sizeof(self, context, path):
        try:
            if callable(self.buildfrom):
                self.buildfrom = self.buildfrom(context)
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")
        if self.buildfrom is Pass:
            return 0
        if self.buildfrom is None:
            raise SizeofError("cannot calculate size")
        if isinstance(self.buildfrom, int):
            return self.subcons[self.buildfrom].subcon._sizeof(context, path)
        if isinstance(self.buildfrom, str):
            index = [i for i,sc in enumerate(self.subcons) if sc.name == self.buildfrom][0]
            return self.subcons[index].subcon._sizeof(context, path)
        raise UnionError("buildfrom should be either: None, Pass, an int, a str")


class Select(Construct):
    r"""
    Selects the first matching subconstruct. It will literally try each of the subconstructs, until one matches.

    :param subcons: the subcons to try (order sensitive)
    :param includename: indicates whether to include the name of the selected subcon in the return value of parsing, default is false

    Example::

        >>> Select(Int32ub, CString(encoding="utf8")).build(1)
        b'\x00\x00\x00\x01'
        >>> Select(Int32ub, CString(encoding="utf8")).build("Афон")
        b'\xd0\x90\xd1\x84\xd0\xbe\xd0\xbd\x00'

        Note that this syntax works ONLY on python 3.6 and pypy due to unordered keyword arguments:
        >>> Select(num=Int32ub, text=CString(encoding="utf8"))
    """
    __slots__ = ["subcons", "includename"]
    def __init__(self, *subcons, **kw):
        subcons = list(subcons)
        for k,v in kw.items():
            if k not in ("includename",):
                subcons.append(k / v)
        super(Select, self).__init__()
        self.subcons = subcons
        self._inherit_flags(*subcons)
        self.includename = kw.pop("includename", False)
    def _parse(self, stream, context, path):
        for sc in self.subcons:
            fallback = stream.tell()
            try:
                obj = sc._parse(stream, context, path)
            except ExplicitError:
                raise
            except ConstructError:
                stream.seek(fallback)
            else:
                return (sc.name,obj) if self.includename else obj
        raise SelectError("no subconstruct matched")
    def _build(self, obj, stream, context, path):
        if self.includename:
            name, obj = obj
            for sc in self.subcons:
                if sc.name == name:
                    return sc._build(obj, stream, context, path)
        else:
            for sc in self.subcons:
                try:
                    data = sc.build(obj, context)
                except ExplicitError:
                    raise
                except Exception:
                    pass
                else:
                    _write_stream(stream, len(data), data)
                    return
        raise SelectError("no subconstruct matched", obj)


def Optional(subcon):
    r"""
    Makes an optional construct, that tries to parse the subcon. If parsing fails, returns None. If building fails, writes nothing.

    Note: sizeof returns subcon size, although no bytes could be consumed or produced. Just something to consider.

    :param subcon: the subcon to optionally parse or build

    Example::

        >>> Optional(Int64ul).parse(b"1234")
        >>> Optional(Int64ul).parse(b"12345678")
        4050765991979987505

        >>> Optional(Int64ul).build(1)
        b'\x01\x00\x00\x00\x00\x00\x00\x00'
        >>> Optional(Int64ul).build("1")
        b''
    """
    return Select(subcon, Pass)


class Switch(Construct):
    r"""
    A conditional branch. Switch will choose the case to follow based on the return value of keyfunc. If no case is matched, and no default value is given, SwitchError will be raised.

    .. seealso:: The :class:`~construct.core.Pass` singleton.

    :param keyfunc: a function that takes the context and returns a key, which will be used to choose the relevant case
    :param cases: a dictionary mapping keys to constructs. the keys can be any values that may be returned by keyfunc
    :param default: a default field to use when the key is not found in the cases. if not supplied, an exception will be raised when the key is not found. Pass can be used for do-nothing
    :param includekey: whether to include the key in the return value of parsing, defualt is False

    Example::

        >>> Switch(this.n, { 1:Byte, 2:Int32ub }).build(5, dict(n=1))
        b'\x05'
        >>> Switch(this.n, { 1:Byte, 2:Int32ub }).build(5, dict(n=2))
        b'\x00\x00\x00\x05'
    """
    @singleton
    class NoDefault(Construct):
        def __init__(self):
            self.flagbuildnone = True
        def _parse(self, stream, context, path):
            raise SwitchError("no default case defined")
        def _build(self, obj, stream, context, path):
            raise SwitchError("no default case defined")
        def _sizeof(self, context, path):
            raise SwitchError("no default case defined")

    __slots__ = ["subcons", "keyfunc", "cases", "default", "includekey"]
    def __init__(self, keyfunc, cases, default=NoDefault, includekey=False):
        super(Switch, self).__init__()
        self.keyfunc = keyfunc
        self.cases = cases
        self.default = default
        self.includekey = includekey
        if all(sc.flagbuildnone for sc in cases.values()) and default.flagbuildnone:
            self.flagbuildnone = True
    def _parse(self, stream, context, path):
        key = self.keyfunc(context) if callable(self.keyfunc) else self.keyfunc
        obj = self.cases.get(key, self.default)._parse(stream, context, path)
        if self.includekey:
            return key, obj
        else:
            return obj
    def _build(self, obj, stream, context, path):
        if self.includekey:
            key, obj = obj
        else:
            key = self.keyfunc(context) if callable(self.keyfunc) else self.keyfunc
        case = self.cases.get(key, self.default)
        case._build(obj, stream, context, path)
    def _sizeof(self, context, path):
        try:
            key = self.keyfunc(context) if callable(self.keyfunc) else self.keyfunc
            sc = self.cases.get(key, self.default)
            return sc._sizeof(context, path)
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


def IfThenElse(predicate, thensubcon, elsesubcon):
    r"""
    An if-then-else conditional construct. If the predicate indicates True, `thensubcon` will be used, otherwise `elsesubcon` will be used.

    :param predicate: a function taking context and returning a bool
    :param thensubcon: the subcon that will be used if the predicate indicates True
    :param elsesubcon: the subcon that will be used if the predicate indicates False

    Example::

        >>> IfThenElse(this.x > 0, VarInt, Byte).build(255, dict(x=1))
        b'\xff\x01'
        >>> IfThenElse(this.x > 0, VarInt, Byte).build(255, dict(x=0))
        b'\xff'
    """
    return Switch(
        lambda ctx: bool(predicate(ctx)),
        {
            True : thensubcon,
            False : elsesubcon,
        },
    )


def If(predicate, subcon):
    r"""
    An if-then conditional construct. If the predicate indicates True, the `subcon` will be used for parsing and building, otherwise parsing returns None and building is no-op.

    :param predicate: a function taking context and returning a bool
    :param subcon: the subcon that will be used if the predicate returns True

    Example::

        >>> If(this.x > 0, Byte).build(255, dict(x=1))
        b'\xff'
        >>> If(this.x > 0, Byte).build(255, dict(x=0))
        b''
    """
    return IfThenElse(predicate, subcon, Pass)


#===============================================================================
# stream manipulation
#===============================================================================
class Pointer(Subconstruct):
    r"""
    Changes the stream position to a given offset, where the construction should take place, and restores the stream position when finished.

    .. seealso:: Analog :func:`~construct.core.OnDemandPointer` field, which also seeks to a given offset.

    :param offset: an int or a function that takes context and returns absolute stream position, where the construction would take place, can return negative integer as position from the end backwards
    :param subcon: the subcon to use at the offset

    Example::

        >>> Pointer(8, Bytes(1)).parse(b"abcdefghijkl")
        b'i'
        >>> Pointer(8, Bytes(1)).build(b"x")
        b'\x00\x00\x00\x00\x00\x00\x00\x00x'
        >>> Pointer(8, Bytes(1)).sizeof()
        0
    """
    __slots__ = ["offset"]
    def __init__(self, offset, subcon):
        super(Pointer, self).__init__(subcon)
        self.offset = offset
    def _parse(self, stream, context, path):
        offset = self.offset(context) if callable(self.offset) else self.offset
        fallback = stream.tell()
        stream.seek(offset, 2 if offset < 0 else 0)
        obj = self.subcon._parse(stream, context, path)
        stream.seek(fallback)
        return obj
    def _build(self, obj, stream, context, path):
        offset = self.offset(context) if callable(self.offset) else self.offset
        fallback = stream.tell()
        stream.seek(offset, 2 if offset < 0 else 0)
        buildret = self.subcon._build(obj, stream, context, path)
        stream.seek(fallback)
        return buildret
    def _sizeof(self, context, path):
        return 0


class Peek(Subconstruct):
    r"""
    Peeks at the stream. Parses without changing the stream position. If the end of the stream is reached when peeking, returns None. Sizeof returns 0 by design because build does not put anything into the stream. Building is no-op.

    .. seealso:: The :func:`~construct.core.Union` class.

    :param subcon: the subcon to peek at

    Example::

        >>> Sequence(Peek(Byte), Peek(Int16ub)).parse(b"\x01\x02")
        [1, 258]
        >>> Sequence(Peek(Byte), Peek(Int16ub)).sizeof()
        0
    """
    def __init__(self, subcon):
        super(Peek, self).__init__(subcon)
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        fallback = stream.tell()
        try:
            return self.subcon._parse(stream, context, path)
        except ExplicitError:
            raise
        except FieldError:
            pass
        finally:
            stream.seek(fallback)
    def _build(self, obj, stream, context, path):
        pass
    def _sizeof(self, context, path):
        return 0


@singleton
class Tell(Construct):
    r"""
    Gets the stream position when parsing or building.

    Tells are useful for adjusting relative offsets to absolute positions, or to measure sizes of Constructs. To get an absolute pointer, use a Tell plus a relative offset. To get a size, place two Tells and measure their difference using a Compute.

    .. seealso:: Better to use :func:`~construct.core.CopyRaw` wrapper in almost any case.

    Example::

        >>> Struct("num"/VarInt, "offset"/Tell).build(dict(num=88))
        b'X'
        >>> Struct("num"/VarInt, "offset"/Tell).parse(_)
        Container(num=88)(offset=1)
    """
    def __init__(self):
        super(self.__class__, self).__init__()
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        return stream.tell()
    def _build(self, obj, stream, context, path):
        return stream.tell()
    def _sizeof(self, context, path):
        return 0


class Seek(Construct):
    r"""
    Sets a new stream position when parsing or building. Seeks are useful when many other fields follow the jump. Pointer works when there is only one field to look at, but when there is more to be done, Seek may come useful.

    .. seealso:: Analog :func:`~construct.core.Pointer` wrapper that has same side effect but also processed a subcon.

    :param at: where to jump to, can ne an int or a context lambda
    :param whence: is the offset from beginning (0) or from current position (1) or from ending (2), can be an int or a context lambda, default is 0

    Example::

        >>> (Seek(5) >> Byte).parse(b"01234x")
        [5, 120]
        >>> (Bytes(10) >> Seek(5) >> Byte).build([b"0123456789", None, 255])
        b'01234\xff6789'
    """
    __slots__ = ["at","whence"]
    def __init__(self, at, whence=0):
        super(Seek, self).__init__()
        self.at = at
        self.whence = whence
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        at = self.at(context) if callable(self.at) else self.at
        whence = self.whence(context) if callable(self.whence) else self.whence
        return stream.seek(at, whence)
    def _build(self, obj, stream, context, path):
        at = self.at(context) if callable(self.at) else self.at
        whence = self.whence(context) if callable(self.whence) else self.whence
        return stream.seek(at, whence)
    def _sizeof(self, context, path):
        raise SizeofError("Seek seeks the stream, sizeof is not meaningful")


class Restreamed(Subconstruct):
    r"""
    Transforms bytes between the underlying stream and the subcon.

    When the parsing or building is done, the wrapper stream is closed. If read buffer or write buffer is not empty, error is raised.

    .. seealso:: Both :func:`~construct.core.Bitwise` and :func:`~construct.core.Bytewise` are implemented using Restreamed.

    .. warning:: Remember that subcon must consume or produce an amount of bytes that is a multiple of encoding or decoding units. For example, in a Bitwise context you should process a multiple of 8 bits or the stream will fail after parsing/building. Also do NOT use pointers inside.

    :param subcon: the subcon which will operate on the buffer
    :param encoder: a function that takes a b-string and returns a b-string (used when building)
    :param encoderunit: ratio as int, encoder takes that many bytes at once
    :param decoder: a function that takes a b-string and returns a b-string (used when parsing)
    :param decoderunit: ratio as int, decoder takes that many bytes at once

    Example::

        Bitwise is implemented as
        Restreamed(subcon, bits2bytes, 8, bytes2bits, 1, lambda n: n//8)

        Bytewise is implemented as
        Restreamed(subcon, bytes2bits, 1, bits2bytes, 8, lambda n: n*8)
    """
    __slots__ = ["stream2", "sizecomputer"]
    def __init__(self, subcon, encoder, encoderunit, decoder, decoderunit, sizecomputer):
        super(Restreamed, self).__init__(subcon)
        self.stream2 = RestreamedBytesIO(None, encoder, encoderunit, decoder, decoderunit)
        self.sizecomputer = sizecomputer
    def _parse(self, stream, context, path):
        self.stream2.substream = stream
        obj = self.subcon._parse(self.stream2, context, path)
        self.stream2.close()
        return obj
    def _build(self, obj, stream, context, path):
        self.stream2.substream = stream
        buildret = self.subcon._build(obj, self.stream2, context, path)
        self.stream2.close()
        return buildret
    def _sizeof(self, context, path):
        if self.sizecomputer is None:
            raise SizeofError("cannot calculate size")
        return self.sizecomputer(self.subcon._sizeof(context, path))


class Rebuffered(Subconstruct):
    r"""
    Caches bytes from the underlying stream, so it becomes seekable and tellable. Also makes the stream blocking, in case it came from a socket or a pipe. Optionally, stream can forget bytes that went a certain amount of bytes beyond the current offset, allowing only a limited seeking capability while allowing to process an endless stream.

    .. warning:: Experimental implementation. May not be mature enough.

    :param subcon: the subcon which will operate on the buffered stream

    Example::

        Rebuffered(RepeatUntil(lambda obj,ctx: ?,Byte), tailcutoff=1024).parse_stream(endless_nonblocking_stream)
    """
    __slots__ = ["stream2", "tailcutoff"]
    def __init__(self, subcon, tailcutoff=None):
        super(Rebuffered, self).__init__(subcon)
        self.stream2 = RebufferedBytesIO(None, tailcutoff=tailcutoff)
    def _parse(self, stream, context, path):
        self.stream2.substream = stream
        return self.subcon._parse(self.stream2, context, path)
    def _build(self, obj, stream, context, path):
        self.stream2.substream = stream
        return self.subcon._build(obj, self.stream2, context, path)


#===============================================================================
# miscellaneous
#===============================================================================
def Padding(length, pattern=b"\x00", strict=False):
    r"""
    A padding field that adds bytes when building, discards bytes when parsing.

    :param length: length of the padding, an int or a function taking context and returning an int
    :param pattern: padding pattern as b-string character, default is b"\x00" null character
    :param strict: whether to verify during parsing that the stream contains the pattern, raises an exception if actual padding differs from the pattern, default is False

    Example::

        >>> (Padding(4) >> Bytes(4)).parse(b"????abcd")
        [None, b'abcd']
        >>> (Padding(4) >> Bytes(4)).build(_)
        b'\x00\x00\x00\x00abcd'
        >>> (Padding(4) >> Bytes(4)).sizeof()
        8

        >>> Padding(4).build(None)
        b'\x00\x00\x00\x00'
        >>> Padding(4, strict=True).parse(b"****")
        construct.core.PaddingError: expected b'\x00\x00\x00\x00', found b'****'
    """
    return Padded(length, Pass, pattern=pattern, strict=strict)


class Const(Subconstruct):
    r"""
    Constant field enforcing a constant value. It is used for file signatures, to validate that the given pattern exists. When parsed, the value must match.

    Note that a variable length subcon may still provide positive verification. Const does not consume a precomputed amount of bytes, but depends on the subcon to read the appropriate amount. Consider for example, a field that eats null bytes and returns following byte. When parsing, both b"\x00\x00\x01" and b"\x01" will be parsed and checked OK.

    :param subcon: the subcon used to build value from, or a b-string value itself
    :param value: optional, the expected value

    :raises ConstError: when parsed data does not match specified value, or building from wrong value

    Example::

        >>> Const(b"MZ").parse(b"MZ")
        b'MZ'
        >>> Const(b"MZ").parse(b"??")
        construct.core.ConstError: expected b'MZ' but parsed b'??'
        >>> Const(b"MZ").build(None)
        b'MZ'
        >>> Const(b"MZ").sizeof()
        2

        >>> Const(Int32ul, 16).build(None)
        b'\x10\x00\x00\x00'
        >>> Const(Int32ul, 16).parse(_)
        16
        >>> Const(Int32ul, 16).sizeof()
        4
    """
    __slots__ = ["value"]
    def __init__(self, subcon, value=None):
        if value is None:
            subcon, value = Bytes(len(subcon)), subcon
        if isinstance(subcon, str):
            subcon, value = Bytes(len(value)), value
        super(Const, self).__init__(subcon)
        self.value = value
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        obj = self.subcon._parse(stream, context, path)
        if obj != self.value:
            raise ConstError("expected %r but parsed %r" % (self.value, obj))
        return obj
    def _build(self, obj, stream, context, path):
        if obj not in (None, self.value):
            raise ConstError("expected None or the value specified earlier")
        return self.subcon._build(self.value, stream, context, path)
    def _sizeof(self, context, path):
        return self.subcon._sizeof(context, path)


class Computed(Construct):
    r"""
    A computed value. Underlying byte stream is unaffected. When parsing `func(context)` provides the value.

    :param func: a function that takes context and returns the computed value

    Example::
        >>> st = Struct(
        ...     "width" / Byte,
        ...     "height" / Byte,
        ...     "total" / Computed(this.width * this.height),
        ... )
        >>> st.parse(b"12")
        Container(width=49)(height=50)(total=2450)
        >>> st.build(dict(width=4,height=5))
        b'\x04\x05'

        >>> Computed(lambda ctx: os.urandom(10)).parse(b"")
        b'[\x86\xcc\xf1b\xd9\x10\x0f?\x1a'
    """
    __slots__ = ["func"]
    def __init__(self, func):
        super(Computed, self).__init__()
        self.func = func
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        return self.func(context) if callable(self.func) else self.func
    def _build(self, obj, stream, context, path):
        return self.func(context) if callable(self.func) else self.func
    def _sizeof(self, context, path):
        return 0


@singleton
class Pass(Construct):
    r"""
    A do-nothing construct, useful as the default case for Switch. Returns None on parsing, puts nothing on building.

    Example::

        >>> Pass.parse(b"")
        >>> Pass.build(None)
        b''
        >>> Pass.sizeof()
        0
    """
    def __init__(self):
        super(self.__class__, self).__init__()
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        return None
    def _build(self, obj, stream, context, path):
        pass
    def _sizeof(self, context, path):
        return 0


@singleton
class Terminated(Construct):
    r"""
    Asserts the end of the stream has been reached at the point it was placed. You can use this to ensure no more unparsed data follows.

    This construct is only meaningful for parsing. For building, it's a no-op.

    Example::

        >>> Terminated.parse(b"")
        >>> Terminated.parse(b"remaining")
        construct.core.TerminatedError: expected end of stream
    """
    def __init__(self):
        super(self.__class__, self).__init__()
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        if stream.read(1):
            raise TerminatedError("expected end of stream")
    def _build(self, obj, stream, context, path):
        pass
    def _sizeof(self, context, path):
        return 0


@singleton
class Error(Construct):
    r"""
    Raises an exception when triggered by parse or build. Can be used as a sentinel that blows a whistle when a conditional branch goes the wrong way, or to raise an error explicitly the declarative way.

    Example::

        >>> d = "x"/Int8sb >> IfThenElse(this.x > 0, Int8sb, Error)
        >>> d.parse(b"\xff\x05")
        construct.core.ExplicitError: Error field was activated during parsing
    """
    def __init__(self):
        super(self.__class__, self).__init__()
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        raise ExplicitError("Error field was activated during parsing")
    def _build(self, obj, stream, context, path):
        raise ExplicitError("Error field was activated during building")


@singleton
class Numpy(Construct):
    r"""
    Preserves numpy arrays (both shape, dtype and values).

    Example::

        >>> import numpy
        >>> a = numpy.asarray([1,2,3])
        >>> Numpy.build(a)
        b"\x93NUMPY\x01\x00F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3,), }            \n\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00"
        >>> Numpy.parse(_)
        array([1, 2, 3])
    """
    def __init__(self):
        super(self.__class__, self).__init__()
        try:
            import numpy
            self.lib = numpy
        except ImportError:
            pass
    def _parse(self, stream, context, path):
        return self.lib.load(stream)
    def _build(self, obj, stream, context, path):
        self.lib.save(stream, obj)


class NamedTuple(Adapter):
    r"""
    Both arrays, structs and sequences can be mapped to a namedtuple from collections module. To create a named tuple, you need to provide a name and a sequence of fields, either a string with space-separated names or a list of strings. Just like the std library namedtuple does.

    Example::

        >>> NamedTuple("coord", "x y z", Byte[3]).parse(b"123")
        coord(x=49, y=50, z=51)
        >>> NamedTuple("coord", "x y z", Byte >> Byte >> Byte).parse(b"123")
        coord(x=49, y=50, z=51)
        >>> NamedTuple("coord", "x y z", Struct("x"/Byte, "y"/Byte, "z"/Byte)).parse(b"123")
        coord(x=49, y=50, z=51)
    """
    def __init__(self, tuplename, tuplefields, subcon):
        super(NamedTuple, self).__init__(subcon)
        self.factory = collections.namedtuple(tuplename, tuplefields)
    def _decode(self, obj, context):
        if isinstance(obj, list):
            return self.factory(*obj)
        if isinstance(obj, dict):
            return self.factory(**obj)
        raise AdaptationError("can only decode and encode from lists and dicts")
    def _encode(self, obj, context):
        if isinstance(self.subcon, (Sequence,Range)):
            return list(obj)
        if isinstance(self.subcon, (Struct)):
            return {sc.name:getattr(obj,sc.name) for sc in self.subcon.subcons if sc.name is not None}
        raise AdaptationError("can only decode and encode from lists and dicts")


class Rebuild(Subconstruct):
    r"""
    Parses the field like normal, but computes the value for building from a function. Useful for length and count fields when Prefixed and PrefixedArray cannot be used.

    Example::

        >>> st = Struct(
        ...     "count" / Rebuild(Byte, len_(this.items)),
        ...     "items" / Byte[this.count],
        ... )
        >>> st.build(dict(items=[1,2,3]))
        b'\x03\x01\x02\x03'
    """
    __slots__ = ["func"]
    def __init__(self, subcon, func):
        super(Rebuild, self).__init__(subcon)
        self.func = func
        self.flagbuildnone = True
    def _build(self, obj, stream, context, path):
        obj = self.func(context)
        self.subcon._build(obj, stream, context, path)
        return obj


class Default(Subconstruct):
    r"""
    Allows to make a field have a default value, which comes handly when building a Struct from a dict with missing keys.

    Example::

        >>> Struct("a"/Default(Byte,0), "b"/Default(Byte,0)).build(dict(a=1))
        b'\x01\x00'
    """
    __slots__ = ["value"]
    def __init__(self, subcon, value):
        super(Default, self).__init__(subcon)
        self.value = value
        self.flagbuildnone = True
    def _build(self, obj, stream, context, path):
        if obj is None:
            obj = self.value
        self.subcon._build(obj, stream, context, path)
        return obj


#===============================================================================
# tunneling and swapping
#===============================================================================
class RawCopy(Subconstruct):
    r"""
    Returns a dict containing both parsed subcon, the raw bytes that were consumed by it, starting and ending offset in the stream, and the amount of bytes. Builds either from raw bytes or a value used by subcon.

    Context does contain a dict with data (if built from raw bytes) or with both (if built from value) during building.

    Example::

        >>>> RawCopy(Byte).parse(b"\xff")
        Container(data='\xff')(value=255)(offset1=0L)(offset2=1L)(length=1L)
        ...
        >>>> RawCopy(Byte).build(dict(data=b"\xff"))
        '\xff'
        >>>> RawCopy(Byte).build(dict(value=255))
        '\xff'
    """
    def __init__(self, subcon):
        super(RawCopy, self).__init__(subcon)
    def _parse(self, stream, context, path):
        offset1 = stream.tell()
        obj = self.subcon._parse(stream, context, path)
        offset2 = stream.tell()
        stream.seek(offset1)
        data = _read_stream(stream, offset2-offset1)
        return Container(data=data, value=obj, offset1=offset1, offset2=offset2, length=(offset2-offset1))
    def _build(self, obj, stream, context, path):
        if 'data' in obj:
            data = obj['data']
            _write_stream(stream, len(data), data)
            return Container(obj, data=data, length=len(data))
        elif 'value' in obj:
            value = obj['value']
            data = self.subcon.build(value, context)
            _write_stream(stream, len(data), data)
            return Container(obj, data=data, value=value, length=len(data))
        else:
            raise ConstructError('both data and value keys are missing')


def ByteSwapped(subcon):
    r"""
    Swap the byte order within boundaries of the given subcon.

    :param subcon: the subcon on top of byte swapped bytes

    Example::

        Int24ul <--> ByteSwapped(Int24ub)
    """
    return Restreamed(subcon,
        lambda s: s[::-1], subcon.sizeof(),
        lambda s: s[::-1], subcon.sizeof(),
        lambda n: n)


def BitsSwapped(subcon):
    r"""
    Swap the bit order within each byte within boundaries of the given subcon.

    :param subcon: the subcon on top of byte swapped bytes

    Example::

        >>>> Bitwise(Bytes(8)).parse(b"\x01")
        '\x00\x00\x00\x00\x00\x00\x00\x01'
        >>>> BitsSwapped(Bitwise(Bytes(8))).parse(b"\x01")
        '\x01\x00\x00\x00\x00\x00\x00\x00'
    """
    return Restreamed(subcon,
        lambda s: bits2bytes(bytes2bits(s)[::-1]), 1,
        lambda s: bits2bytes(bytes2bits(s)[::-1]), 1,
        lambda n: n)


class Prefixed(Subconstruct):
    r"""
    Parses the length field. Then reads that amount of bytes and parses the subcon using only those bytes. Constructs that consume entire remaining stream are constrained to consuming only the specified amount of bytes. When building, data is prefixed by its length.

    .. seealso:: The :class:`~construct.core.VarInt` encoding should be preferred over :class:`~construct.core.Byte` and fixed size fields. VarInt is more compact and does never overflow.

    .. note:: If lengthfield is fixed size, Prefixed will seek back to write the length afterwards, which will break on non-seekable streams.

    :param lengthfield: a subcon used for storing the length
    :param subcon: the subcon used for storing the value

    Example::

        >>> Prefixed(VarInt, GreedyBytes).parse(b"\x05hello????remainins")
        b'hello'

        >>>> Prefixed(VarInt, Byte[:]).parse(b"\x03\x01\x02\x03????following")
        [1, 2, 3]
    """
    __slots__ = ["name", "lengthfield", "subcon"]
    def __init__(self, lengthfield, subcon):
        super(Prefixed, self).__init__(subcon)
        self.lengthfield = lengthfield
    def _parse(self, stream, context, path):
        length = self.lengthfield._parse(stream, context, path)
        stream2 = BoundBytesIO(stream, length)
        return self.subcon._parse(stream2, context, path)
    def _build(self, obj, stream, context, path):
        try:
            # needs to be both fixed size, seekable and tellable (third not checked)
            self.lengthfield.sizeof()
            if not stream.seekable:
                raise SizeofError
            offset1 = stream.tell()
            self.lengthfield._build(0, stream, context, path)
            offset2 = stream.tell()
            self.subcon._build(obj, stream, context, path)
            offset3 = stream.tell()
            stream.seek(offset1)
            self.lengthfield._build(offset3-offset2, stream, context, path)
            stream.seek(offset3)
        except SizeofError:
            data = self.subcon.build(obj, context)
            self.lengthfield._build(len(data), stream, context, path)
            _write_stream(stream, len(data), data)
    def _sizeof(self, context, path):
        return self.lengthfield._sizeof(context, path) + self.subcon._sizeof(context, path)


class Checksum(Construct):
    r"""
    A field that is build or validated by a hash of a given byte range.

    :param checksumfield: a subcon field that reads the checksum, usually Bytes(int)
    :param hashfunc: a function taking bytes and returning whatever checksumfield takes when building
    :param bytesfunc: a function taking context and returning the bytes to be hashed, usually this.rawcopy1.data alike

    Example::

        import hashlib
        d = Struct(
            "fields" / RawCopy(Struct(
                "a" / Byte,
                "b" / Byte,
            )),
            "checksum" / Checksum(Bytes(64), lambda data: hashlib.sha512(data).digest(), this.fields.data),
        )
        data = d.build(dict(fields=dict(value=dict(a=1,b=2))))
        # returned b'\x01\x02\xbd\xd8\x1a\xb23\xbc\xebj\xd23\xcd\x18qP\x93 \xa1\x8d\x035\xa8\x91\xcf\x98s\t\x90\xe8\x92>\x1d\xda\x04\xf35\x8e\x9c~\x1c=\x16\xb1o@\x8c\xfa\xfbj\xf52T\xef0#\xed$6S8\x08\xb6\xca\x993'
    """
    __slots__ = ["checksumfield", "hashfunc", "bytesfunc"]
    def __init__(self, checksumfield, hashfunc, bytesfunc):
        super(Checksum, self).__init__()
        self.checksumfield = checksumfield
        self.hashfunc = hashfunc
        self.bytesfunc = bytesfunc
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        hash1 = self.checksumfield._parse(stream, context, path)
        hash2 = self.hashfunc(self.bytesfunc(context))
        if hash1 != hash2:
            raise ChecksumError("wrong checksum, read %r, computed %r" % (hexlify(hash1), hexlify(hash2)))
        return hash1
    def _build(self, obj, stream, context, path):
        hash2 = self.hashfunc(self.bytesfunc(context))
        self.checksumfield._build(hash2, stream, context, path)
    def _sizeof(self, context, path):
        return self.checksumfield._sizeof(context, path)


class Compressed(Tunnel):
    r"""
    Compresses or decompresses underlying stream when processing the subcon. When parsing, entire stream is consumed. When building, puts compressed bytes without marking the end.

    .. seealso:: This construct should either be used with :func:`~construct.core.Prefixed` or on entire stream.

    :param subcon: the subcon used for storing the value
    :param encoding: any of the module names like zlib/gzip/bzip2/lzma, otherwise any of codecs module bytes<->bytes encodings
    :param level: optinal, an int between 0..9, lzma discards that

    Example::

        Compressed(GreedyBytes, "zlib")

        Prefixed(VarInt, Compressed(GreedyBytes, "zlib"))
        Struct("inner"/above)

        Compressed(Struct(...), "zlib")
   """
    __slots__ = ["encoding", "level", "lib"]
    def __init__(self, subcon, encoding, level=None):
        super(Compressed, self).__init__(subcon)
        self.encoding = encoding
        self.level = level
        if self.encoding == "zlib":
            import zlib
            self.lib = zlib
        elif self.encoding == "gzip":
            import gzip
            self.lib = gzip
        elif self.encoding == "bzip2":
            import bz2
            self.lib = bz2
        elif self.encoding == "lzma":
            import lzma
            self.lib = lzma
        else:
            import codecs
            self.lib = codecs
    def _decode(self, data, context):
        if self.encoding in ("zlib", "gzip", "bzip2", "lzma"):
            return self.lib.decompress(data)
        return self.lib.decode(data, self.encoding)
    def _encode(self, data, context):
        if self.encoding in ("zlib", "gzip", "bzip2", "lzma"):
            if self.level is None or self.encoding == "lzma":
                return self.lib.compress(data)
            else:
                return self.lib.compress(data, self.level)
        return self.lib.encode(data, self.encoding)


#===============================================================================
# lazy equivalents
#===============================================================================
class LazyStruct(Construct):
    r"""
    Equivalent to Struct construct, however fixed size members are parsed on demend, others are parsed immediately. If entire struct is fixed size then entire parse is essentially one seek.

    .. seealso:: Equivalent to :func:`~construct.core.Struct`.

    """
    __slots__ = ["subcons", "offsetmap", "totalsize", "subsizes", "keys"]
    def __init__(self, *subcons, **kw):
        super(LazyStruct, self).__init__()
        self.subcons = subcons

        try:
            keys = Container()
            self.offsetmap = {}
            at = 0
            for sc in self.subcons:
                if sc.flagembedded:
                    raise SizeofError
                if sc.name is not None:
                    keys[sc.name] = None
                    self.offsetmap[sc.name] = (at, sc)
                at += sc.sizeof()
            self.totalsize = at
            self.keys = list(keys.keys())
        except SizeofError:
            self.offsetmap = None
            self.totalsize = None

        self.subsizes = []
        for sc in self.subcons:
            try:
                self.subsizes.append(sc.sizeof())
            except SizeofError:
                self.subsizes.append(None)

    def _parse(self, stream, context, path):
        if self.offsetmap is not None:
            position = stream.tell()
            stream.seek(self.totalsize, 1)
            return LazyContainer(self.keys, self.offsetmap, {}, stream, position, context)
        context = Container(_ = context)
        offsetmap = {}
        keys = Container()
        values = {}
        position = stream.tell()
        for i,(sc,size) in enumerate(zip(self.subcons, self.subsizes)):
            if sc.flagembedded:
                subobj = list(sc._parse(stream, context, path).items())
                keys.update(subobj)
                values.update(subobj)
                context.update(subobj)
            elif size is None:
                subobj = sc._parse(stream, context, path)
                if sc.name is not None:
                    keys[sc.name] = None
                    values[sc.name] = subobj
                    context[sc.name] = subobj
            else:
                if sc.name is not None:
                    keys[sc.name] = None
                    offsetmap[sc.name] = (stream.tell(), sc)
                stream.seek(size, 1)
        return LazyContainer(list(keys.keys()), offsetmap, values, stream, 0, context)

    def _build(self, obj, stream, context, path):
        context = Container(_ = context)
        context.update(obj)
        for i,sc in enumerate(self.subcons):
            if sc.flagembedded:
                subobj = obj
            elif sc.flagbuildnone:
                subobj = obj.get(sc.name, None)
            else:
                subobj = obj[sc.name]
            buildret = sc._build(subobj, stream, context, path)
            if buildret is not None:
                if sc.flagembedded:
                    context.update(buildret)
                if sc.name is not None:
                    context[sc.name] = buildret
        return context

    def _sizeof(self, context, path):
        if self.totalsize is not None:
            return self.totalsize
        else:
            raise SizeofError("cannot calculate size, not all members are fixed size")


class LazyRange(Construct):
    r"""
    Equivalent to Range construct, but members are parsed on demand. Works only with fixed size subcon.

    .. seealso:: Equivalent to :func:`~construct.core.Range`.

    """
    __slots__ = ["subcon", "min", "max", "subsize"]
    def __init__(self, min, max, subcon):
        super(LazyRange, self).__init__()
        self.subcon = subcon
        self.min = min
        self.max = max
        self.subsize = subcon.sizeof()

    def _parse(self, stream, context, path):
        currentmin = self.min(context) if callable(self.min) else self.min
        currentmax = self.max(context) if callable(self.max) else self.max
        if not 0 <= currentmin <= currentmax <= sys.maxsize:
            raise RangeError("unsane min %s and max %s" % (currentmin, currentmax))
        starts = stream.tell()
        ends = stream.seek(0,2)
        remaining = ends - starts
        objcount = min(remaining//self.subsize, currentmax)
        if objcount < currentmin:
            raise RangeError("not enough bytes %d to read the min %d of %d bytes each" % (remaining, currentmin, self.subsize))
        stream.seek(starts + objcount*self.subsize, 0)
        return LazyRangeContainer(self.subcon, self.subsize, objcount, stream, starts, context)

    def _build(self, obj, stream, context, path):
        currentmin = self.min(context) if callable(self.min) else self.min
        currentmax = self.max(context) if callable(self.max) else self.max
        if not 0 <= currentmin <= currentmax <= sys.maxsize:
            raise RangeError("unsane min %s and max %s" % (currentmin, currentmax))
        if not isinstance(obj, collections.Sequence):
            raise RangeError("expected sequence type, found %s" % type(obj))
        if not currentmin <= len(obj) <= currentmax:
            raise RangeError("expected from %d to %d elements, found %d" % (currentmin, currentmax, len(obj)))
        try:
            for i,subobj in enumerate(obj):
                context[i] = subobj
                self.subcon._build(subobj, stream, context, path)
        except ConstructError:
            if len(obj) < currentmin:
                raise RangeError("expected %d to %d, found %d" % (currentmin, currentmax, len(obj)))

    def _sizeof(self, context, path):
        try:
            currentmin = self.min(context) if callable(self.min) else self.min
            currentmax = self.max(context) if callable(self.max) else self.max
            if not 0 <= currentmin <= currentmax <= sys.maxsize:
                raise RangeError("unsane min %s and max %s" % (currentmin, currentmax))
            if currentmin == currentmax:
                return self.min * self.subsize
            else:
                raise SizeofError("cannot calculate size, min not equal to max")
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


class LazySequence(Construct):
    r"""
    Equivalent to Sequence construct, however fixed size members are parsed on demand, others are parsed immediately. If entire sequence is fixed size then entire parse is essentially one seek.

    .. seealso:: Equivalent to :func:`~construct.core.Sequence`.

    """
    __slots__ = ["subcons", "offsetmap", "totalsize", "subsizes"]
    def __init__(self, *subcons, **kw):
        super(LazySequence, self).__init__()
        self.subcons = subcons

        try:
            self.offsetmap = {}
            at = 0
            for i,sc in enumerate(self.subcons):
                if sc.flagembedded:
                    raise SizeofError
                self.offsetmap[i] = (at, sc)
                at += sc.sizeof()
            self.totalsize = at
        except SizeofError:
            self.offsetmap = None
            self.totalsize = None

        self.subsizes = []
        for sc in self.subcons:
            try:
                self.subsizes.append(sc.sizeof())
            except SizeofError:
                self.subsizes.append(None)

    def _parse(self, stream, context, path):
        context = Container(_ = context)
        if self.totalsize is not None:
            position = stream.tell()
            stream.seek(self.totalsize, 1)
            return LazySequenceContainer(len(self.subcons), self.offsetmap, {}, stream, position, context)
        offsetmap = {}
        values = {}
        i = 0
        for sc,size in zip(self.subcons, self.subsizes):
            if sc.flagembedded:
                subobj = list(sc._parse(stream, context, path))
                for e in subobj:
                    values[i] = e
                    context[i] = e
                    i += 1
            elif size is None:
                obj = sc._parse(stream, context, path)
                values[i] = obj
                context[i] = obj
                i += 1
            else:
                offsetmap[i] = (stream.tell(), sc)
                stream.seek(size, 1)
                i += 1
        return LazySequenceContainer(i, offsetmap, values, stream, 0, context)

    def _build(self, obj, stream, context, path):
        context = Container(_ = context)
        objiter = iter(obj)
        for i,sc in enumerate(self.subcons):
            if sc.flagembedded:
                subobj = objiter
            else:
                subobj = next(objiter)
                if sc.name is not None:
                    context[sc.name] = subobj
            context[i] = subobj
            buildret = sc._build(subobj, stream, context, path)
            if buildret is not None:
                if sc.flagembedded:
                    context.update(buildret)
                if sc.name is not None:
                    context[sc.name] = buildret
                context[i] = buildret

    def _sizeof(self, context, path):
        if self.totalsize is not None:
            return self.totalsize
        else:
            raise SizeofError("cannot calculate size, not all members are fixed size")


class OnDemand(Subconstruct):
    r"""
    Allows for on-demand (lazy) parsing. When parsing, it will return a parameterless function that when called, will return the parsed value. Object is cached after first parsing, so non-deterministic subcons will be affected. Works only with fixed size subcon.

    :param subcon: the subcon to read/write on demand, must be fixed size

    Example::

        >>> OnDemand(Byte).parse(b"\xff")
        <function OnDemand._parse.<locals>.<lambda> at 0x7fdc241cfc80>
        >>> _()
        255
        >>> OnDemand(Byte).build(16)
        b'\x10'

        Can also re-build from the lambda returned at parsing.

        >>> OnDemand(Byte).parse(b"\xff")
        <function OnDemand._parse.<locals>.<lambda> at 0x7fcbd9855f28>
        >>> OnDemand(Byte).build(_)
        b'\xff'
    """
    def __init__(self, subcon):
        super(OnDemand, self).__init__(subcon)
    def _parse(self, stream, context, path):
        offset = stream.tell()
        stream.seek(self.subcon._sizeof(context, path), 1)
        cache = {}
        def effectuate():
            if not cache:
                fallback = stream.tell()
                stream.seek(offset)
                obj = self.subcon._parse(stream, context, path)
                stream.seek(fallback)
                cache["parsed"] = obj
            return cache["parsed"]
        return effectuate
    def _build(self, obj, stream, context, path):
        obj = obj() if callable(obj) else obj
        return self.subcon._build(obj, stream, context, path)


def OnDemandPointer(offset, subcon):
    r"""
    An on-demand pointer. Is both lazy and jumps to a position before reading.

    .. seealso:: Base :func:`~construct.core.OnDemand` and :func:`~construct.core.Pointer` construct.

    :param offset: an int or a context function that returns absolute stream position, where the construction would take place, can return negative integer as position from the end backwards
    :param subcon: the subcon that will be parsed or built at the `offset` stream position

    Example::

        >>> OnDemandPointer(lambda ctx: 2, Byte).parse(b"\x01\x02\x03garbage")
        <function OnDemand._parse.<locals>.effectuate at 0x7f6f011ad510>
        >>> _()
        3
    """
    return OnDemand(Pointer(offset, subcon))


class LazyBound(Construct):
    r"""
    A lazy-bound construct that binds to the construct only at runtime. Useful for recursive data structures (like linked lists or trees), where a construct needs to refer to itself (while it doesn't exist yet).

    :param subconfunc: a context function returning a Construct (derived) instance, can also return Pass or itself

    Example::

        >>> st = Struct(
        ...     "value"/Byte,
        ...     "next"/If(this.value > 0, LazyBound(lambda ctx: st)),
        ... )
        ...
        >>> st.parse(b"\x05\x09\x00")
        Container(value=5)(next=Container(value=9)(next=Container(value=0)(next=None)))
        ...
        >>> print(st.parse(b"\x05\x09\x00"))
        Container:
            value = 5
            next = Container:
                value = 9
                next = Container:
                    value = 0
                    next = None
    """
    __slots__ = ["subconfunc"]
    def __init__(self, subconfunc):
        super(LazyBound, self).__init__()
        self.subconfunc = subconfunc
    def _parse(self, stream, context, path):
        return self.subconfunc(context)._parse(stream, context, path)
    def _build(self, obj, stream, context, path):
        return self.subconfunc(context)._build(obj, stream, context, path)
    def _sizeof(self, context, path):
        try:
            return self.subconfunc(context)._sizeof(context, path)
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")


#===============================================================================
# special
#===============================================================================
class Embedded(Subconstruct):
    r"""
    Embeds a struct into the enclosing struct, merging fields. Can also embed sequences into sequences. Name is also inherited.

    :param subcon: the struct to embed

    Example::

        >>> Struct("a"/Byte, Embedded(Struct("b"/Byte)), "c"/Byte).parse(b"abc")
        Container(a=97)(b=98)(c=99)
        >>> Struct("a"/Byte, Embedded(Struct("b"/Byte)), "c"/Byte).build(_)
        b'abc'
    """
    def __init__(self, subcon):
        super(Embedded, self).__init__(subcon)
        self.flagembedded = True


class Renamed(Subconstruct):
    r"""
    Renames an existing construct. This creates a wrapper so underlying subcon retains it's original name, which in general means just a None. Can be used to give same construct few different names. Used internally by / operator.

    Also this wrapper is responsible for building a path (a chain of names) that gets attached to error message when parsing, building, or sizeof fails. A field that is not named does not appear on the path.

    :param newname: the new name
    :param subcon: the subcon to rename

    Example::

        >>> "name" / Int32ul
        <Renamed: name>
        >>> Renamed("name", Int32ul)
        <Renamed: name>
    """
    def __init__(self, newname, subcon):
        super(Renamed, self).__init__(subcon)
        self.name = newname
    def _parse(self, stream, context, path):
        try:
            path += " -> %s" % (self.name)
            return self.subcon._parse(stream, context, path)
        except ConstructError as e:
            if "\n" in str(e):
                raise
            raise e.__class__("%s\n    %s" % (e, path))
    def _build(self, obj, stream, context, path):
        try:
            path += " -> %s" % (self.name)
            return self.subcon._build(obj, stream, context, path)
        except ConstructError as e:
            if "\n" in str(e):
                raise
            raise e.__class__("%s\n    %s" % (e, path))
    def _sizeof(self, context, path):
        try:
            path += " -> %s" % (self.name)
            return self.subcon._sizeof(context, path)
        except ConstructError as e:
            if "\n" in str(e):
                raise
            raise e.__class__("%s\n    %s" % (e, path))


def Alias(newname, oldname):
    r"""
    Creates an alias for an existing element in a struct. When parsing, value is available under both keys. Building does nothing. Deprecated meaning there is no real use for it.

    .. seealso:: Note that :func:`~construct.core.Computed` is more powerful.

    :param newname: the new name
    :param oldname: the name of an existing element, must be on same context level
    """
    return Renamed(newname, Computed(lambda ctx: ctx[oldname]))


#===============================================================================
# mappings
#===============================================================================
class Mapping(Adapter):
    r"""
    Adapter that maps objects to other objects. Translates objects before parsing and before

    :param subcon: the subcon to map
    :param decoding: the decoding (parsing) mapping as a dict
    :param encoding: the encoding (building) mapping as a dict
    :param decdefault: the default return value when object is not found in the mapping, if no object is given an exception is raised, if ``Pass`` is used, the unmapped object will be passed as-is
    :param encdefault: the default return value when object is not found in the mapping, if no object is given an exception is raised, if ``Pass`` is used, the unmapped object will be passed as-is

    Example::

        ???
    """
    __slots__ = ["encoding", "decoding", "encdefault", "decdefault"]
    def __init__(self, subcon, decoding, encoding, decdefault=NotImplemented, encdefault=NotImplemented):
        super(Mapping, self).__init__(subcon)
        self.decoding = decoding
        self.encoding = encoding
        self.decdefault = decdefault
        self.encdefault = encdefault
    def _encode(self, obj, context):
        try:
            return self.encoding[obj]
        except ExplicitError:
            raise
        except (KeyError, TypeError):
            if self.encdefault is NotImplemented:
                raise MappingError("no encoding mapping for %r" % (obj,))
            if self.encdefault is Pass:
                return obj
            return self.encdefault
    def _decode(self, obj, context):
        try:
            return self.decoding[obj]
        except ExplicitError:
            raise
        except (KeyError, TypeError):
            if self.decdefault is NotImplemented:
                raise MappingError("no decoding mapping for %r" % (obj,))
            if self.decdefault is Pass:
                return obj
            return self.decdefault


def SymmetricMapping(subcon, mapping, default=NotImplemented):
    r"""
    Defines a symmetrical mapping, same mapping is used on parsing and building.

    .. seealso:: Based on :func:`~construct.core.Mapping`.

    :param subcon: the subcon to map
    :param encoding: the mapping as a dict
    :param decdefault: the default return value when object is not found in the mapping, if no object is given an exception is raised, if ``Pass`` is used, the unmapped object will be passed as-is

    Example::

        ???
    """
    return Mapping(subcon,
        encoding = mapping,
        decoding = dict((v,k) for k, v in mapping.items()),
        encdefault = default,
        decdefault = default,
    )


@singletonfunction
def Flag():
    r"""
    A one byte (or one bit) field that maps to True or False bool. Non-zero bytes are consifered True.

    Example::

        >>> Flag.parse(b"\x01")
        True
        >>> Flag.build(True)
        b'\x01'
    """
    return SymmetricMapping(Byte, {True : 1, False : 0}, default=True)


def Enum(subcon, default=NotImplemented, **mapping):
    r"""
    A set of named values mapping. Can build both from names and values.

    :param subcon: the subcon to map
    :param \*\*mapping: keyword arguments which serve as the encoding mapping
    :param default: an optional, keyword-only argument that specifies the default value to use when the mapping is undefined. if not given, and exception is raised when the mapping is undefined. use `Pass` topass the unmapped value as-is

    Example::

        >>> Enum(Byte,a=1,b=2).parse(b"\x01")
        'a'
        >>> Enum(Byte,a=1,b=2).parse(b"\x08")
        construct.core.MappingError: no decoding mapping for 8

        >>> Enum(Byte,a=1,b=2).build("a")
        b'\x01'
        >>> Enum(Byte,a=1,b=2).build(1)
        b'\x01'
    """
    encmapping = mapping.copy()
    for k,v in mapping.items():
        encmapping[v] = v
    return Mapping(subcon,
        encoding = encmapping,
        decoding = dict((v,k) for k, v in mapping.items()),
        encdefault = default,
        decdefault = default,
    )


class FlagsEnum(Adapter):
    r"""
    A set of flag values mapping. Each flag is extracted from the number, resulting in a FlagsContainer dict that has each key assigned True or False.

    :param subcon: the subcon to extract
    :param \*\*flags: a dictionary mapping flag-names to their value

    Example::

        >>> FlagsEnum(Byte,a=1,b=2,c=4,d=8).parse(b"\x03")
        Container(c=False)(b=True)(a=True)(d=False)
        >>> FlagsEnum(Byte,a=1,b=2,c=4,d=8).build(_)
        b'\x03'
    """
    __slots__ = ["flags"]
    def __init__(self, subcon, **flags):
        super(FlagsEnum, self).__init__(subcon)
        self.flags = flags
    def _encode(self, obj, context):
        flags = 0
        try:
            for name, value in obj.items():
                if value:
                    flags |= self.flags[name]
        except ExplicitError:
            raise
        except AttributeError:
            raise MappingError("not a mapping type: %r" % (obj,))
        except KeyError:
            raise MappingError("unknown flag: %s" % name)
        return flags
    def _decode(self, obj, context):
        obj2 = FlagsContainer()
        for name, value in self.flags.items():
            obj2[name] = bool(obj & value)
        return obj2


#===============================================================================
# adapters and validators
#===============================================================================
class ExprAdapter(Adapter):
    r"""
    A generic adapter that takes ``encoder`` and ``decoder`` as parameters. You can use ExprAdapter instead of writing a full-blown class when only a simple expression is needed.

    :param subcon: the subcon to adapt
    :param encoder: a function that takes (obj, context) and returns an encoded version of obj, or None for identity
    :param decoder: a function that takes (obj, context) and returns an decoded version of obj, or None for identity

    Example::

        Ident = ExprAdapter(Byte,
            encoder = lambda obj,ctx: obj+1,
            decoder = lambda obj,ctx: obj-1, )
    """
    __slots__ = ["_encode", "_decode"]
    def __init__(self, subcon, encoder, decoder):
        super(ExprAdapter, self).__init__(subcon)
        ident = lambda obj,ctx: obj
        self._encode = encoder if callable(encoder) else ident
        self._decode = decoder if callable(decoder) else ident


class ExprSymmetricAdapter(ExprAdapter):
    def __init__(self, subcon, encoder):
        super(ExprAdapter, self).__init__(subcon)
        ident = lambda obj,ctx: obj
        self._encode = encoder if callable(encoder) else ident
        self._decode = self._encode


class ExprValidator(Validator):
    r"""
    A generic adapter that takes ``validator`` as parameter. You can use ExprValidator instead of writing a full-blown class when only a simple expression is needed.

    :param subcon: the subcon to adapt
    :param encoder: a function that takes (obj, context) and returns a bool

    Example::

        OneOf = ExprValidator(Byte,
            validator = lambda obj,ctx: obj in [1,3,5])
    """
    def __init__(self, subcon, validator):
        super(ExprValidator, self).__init__(subcon)
        self._validate = validator


def Hex(subcon):
    r"""
    Adapter for hex-dumping b-strings. It returns a hex dump when parsing, and un-dumps when building.

    Example::

        >>> Hex(GreedyBytes).parse(b"abcd")
        b'61626364'
        >>> Hex(GreedyBytes).build("01020304")
        b'\x01\x02\x03\x04'
    """
    return ExprAdapter(subcon,
        encoder = lambda obj,ctx: None if subcon.flagbuildnone else unhexlify(obj),
        decoder = lambda obj,ctx: hexlify(obj),)


def HexDump(subcon, linesize=16):
    r"""
    Adapter for hex-dumping b-strings. It returns a hex dump when parsing, and un-dumps when building.

    :param linesize: default 16 bytes per line
    :param buildraw: by default build takes the same format that parse returns, set to build from a b-string directly

    Example::

        >>> HexDump(Bytes(10)).parse(b"12345abc;/")
        '0000   31 32 33 34 35 61 62 63 3b 2f                     12345abc;/       \n'
    """
    return ExprAdapter(subcon,
        encoder = lambda obj,ctx: None if subcon.flagbuildnone else hexundump(obj, linesize=linesize),
        decoder = lambda obj,ctx: hexdump(obj, linesize=linesize),)


class Slicing(Adapter):
    r"""
    Adapter for slicing a list (getting a slice from that list). Works with Range and Sequence and their lazy equivalents.

    :param subcon: the subcon to slice
    :param count: expected number of elements, needed during building
    :param start: start index (or None for entire list)
    :param stop: stop index (or None for up-to-end)
    :param step: step (or 1 for every element)
    :param empty: value to fill the list with during building

    Example::

        ???
    """
    __slots__ = ["count", "start", "stop", "step", "empty"]
    def __init__(self, subcon, count, start, stop, step=1, empty=None):
        super(Slicing, self).__init__(subcon)
        self.count = count
        self.start = start
        self.stop = stop
        self.step = step
        self.empty = empty
    def _encode(self, obj, context):
        if self.start is None:
            return obj
        elif self.stop is None:
            output = [self.empty] * self.count
            output[self.start::self.step] = obj
        else:
            output = [self.empty] * self.count
            output[self.start:self.stop:self.step] = obj
        return output
    def _decode(self, obj, context):
        return obj[self.start:self.stop:self.step]


class Indexing(Adapter):
    r"""
    Adapter for indexing a list (getting a single item from that list). Works with Range and Sequence and their lazy equivalents.

    :param subcon: the subcon to index
    :param count: expected number of elements, needed during building
    :param index: the index of the list to get
    :param empty: value to fill the list with during building

    Example::

        ???
    """
    __slots__ = ["count", "index", "empty"]
    def __init__(self, subcon, count, index, empty=None):
        super(Indexing, self).__init__(subcon)
        self.count = count
        self.index = index
        self.empty = empty
    def _encode(self, obj, context):
        output = [self.empty] * self.count
        output[self.index] = obj
        return output
    def _decode(self, obj, context):
        return obj[self.index]


class FocusedSeq(Construct):
    r"""
    Parses and builds a sequence where only one subcon value is returned from parsing or taken into building, other fields are parsed and discarded or built from nothing. This is a replacement for SeqOfOne.

    :param parsebuildfrom: which subcon to use, an int or str, or a context lambda returning an int or str
    :param \*subcons: a list of members
    :param \*\*kw: a list of members (works ONLY on python 3.6 and pypy)

    Excample::

        >>> d = FocusedSeq("num", Const(b"MZ"), "num"/Byte, Terminated)
        >>> d = FocusedSeq(1, Const(b"MZ"), "num"/Byte, Terminated)

        >>> d.parse(b"MZ\xff")
        255
        >>> d.build(255)
        b'MZ\xff'
    """
    def __init__(self, parsebuildfrom, *subcons, **kw):
        subcons = list(subcons)
        for k,v in kw.items():
            subcons.append(k / v)
        super(FocusedSeq, self).__init__()
        self.parsebuildfrom = parsebuildfrom
        self.subcons = subcons
    def _parse(self, stream, context, path):
        if callable(self.parsebuildfrom):
            self.parsebuildfrom = self.parsebuildfrom(context)
        if isinstance(self.parsebuildfrom, int):
            index = self.parsebuildfrom
            self.subcons[index]  #IndexError check
        if isinstance(self.parsebuildfrom, str):
            index = [i for i,sc in enumerate(self.subcons) if sc.name == self.parsebuildfrom][0]
        for i,sc in enumerate(self.subcons):
            parseret = sc._parse(stream, context, path)
            context[i] = parseret
            if sc.name is not None:
                context[sc.name] = parseret
            if i == index:
                finalobj = parseret
        return finalobj
    def _build(self, obj, stream, context, path):
        if callable(self.parsebuildfrom):
            self.parsebuildfrom = self.parsebuildfrom(context)
        if isinstance(self.parsebuildfrom, int):
            index = self.parsebuildfrom
            self.subcons[index]  #IndexError check
        if isinstance(self.parsebuildfrom, str):
            index = [i for i,sc in enumerate(self.subcons) if sc.name == self.parsebuildfrom][0]
        for i,sc in enumerate(self.subcons):
            if i == index:
                context[i] = obj
                if sc.name is not None:
                    context[sc.name] = obj
        for i,sc in enumerate(self.subcons):
            buildret = sc._build(obj if i==index else None, stream, context, path)
            if buildret is not None:
                if sc.name is not None:
                    context[sc.name] = buildret
                context[i] = buildret
            if i == index:
                finalobj = buildret
        return finalobj
    def _sizeof(self, context, path):
        try:
            if callable(self.parsebuildfrom):
                self.parsebuildfrom = self.parsebuildfrom(context)
        except (KeyError, AttributeError):
            raise SizeofError("cannot calculate size, key not found in context")
        if isinstance(self.parsebuildfrom, int):
            index = self.parsebuildfrom
            self.subcons[index]  #IndexError check
        if isinstance(self.parsebuildfrom, str):
            index = [i for i,sc in enumerate(self.subcons) if sc.name == self.parsebuildfrom][0]
        return self.subcons[index]._sizeof(context, path)


def OneOf(subcon, valids):
    r"""
    Validates that the object is one of the listed values, both during parsing and building.

    :param subcon: a construct to validate
    :param valids: a collection implementing `in`

    Example::

        >>> OneOf(Byte, [1,2,3]).parse(b"\x01")
        1
        >>> OneOf(Byte, [1,2,3]).parse(b"\x08")
        construct.core.ValidationError: ('invalid object', 8)

        >>> OneOf(Bytes(1), b"1234567890").parse(b"4")
        b'4'
        >>> OneOf(Bytes(1), b"1234567890").parse(b"?")
        construct.core.ValidationError: ('invalid object', b'?')

        >>> OneOf(Bytes(2), b"1234567890").parse(b"78")
        b'78'
        >>> OneOf(Bytes(2), b"1234567890").parse(b"19")
        construct.core.ValidationError: ('invalid object', b'19')
    """
    return ExprValidator(subcon, lambda obj,ctx: obj in valids)


def NoneOf(subcon, invalids):
    r"""
    Validates that the object is none of the listed values, both during parsing and building.

    :param subcon: a construct to validate
    :param invalids: a collection implementing `in`

    .. seealso:: Look at :func:`~construct.core.OneOf` for examples, works the same.

    """
    return ExprValidator(subcon, lambda obj,ctx: obj not in invalids)


def Filter(predicate, subcon):
    r"""
    Filters a list leaving only the elements that passed through the validator.

    :param subcon: a construct to validate, usually a Range or Array or Sequence
    :param predicate: a function taking (obj, context) and returning a bool

    Example::

        >>> Filter(obj_ != 0, Byte[:]).parse(b"\x00\x02\x00")
        [2]
        >>> Filter(obj_ != 0, Byte[:]).build([0,1,0,2,0])
        b'\x01\x02'
    """
    return ExprSymmetricAdapter(subcon, lambda obj,ctx: list(filter(lambda x: predicate(x,ctx), obj)) )


class Check(Construct):
    r"""
    Checks for a condition and raises ValidationError if the check fails.

    Example::

        Check(lambda ctx: len(ctx.payload.data) == ctx.payload_len)

        Check(len_(this.payload.data) == this.payload_len)
    """
    def __init__(self, func):
        super(Check, self).__init__()
        self.func = func
        self.flagbuildnone = True
    def _parse(self, stream, context, path):
        if not self.func(context):
            raise ValidationError("check failed during parsing")
    def _build(self, obj, stream, context, path):
        if not self.func(context):
            raise ValidationError("check failed during building")
    def _sizeof(self, context, path):
        return 0


#===============================================================================
# strings
#===============================================================================
globalstringencoding = None


def setglobalstringencoding(encoding):
    r"""
    Sets the encoding globally for all String PascalString CString GreedyString instances.

    :param encoding: a string like "utf8" etc or None, which means working with bytes
    """
    global globalstringencoding
    globalstringencoding = encoding


class StringEncoded(Adapter):
    """Used internally."""
    __slots__ = ["encoding"]
    def __init__(self, subcon, encoding):
        super(StringEncoded, self).__init__(subcon)
        self.encoding = encoding
    def _decode(self, obj, context):
        encoding = self.encoding or globalstringencoding
        if encoding:
            if isinstance(encoding, str):
                obj = obj.decode(encoding)
            else:
                obj = encoding.decode(obj)
        return obj
    def _encode(self, obj, context):
        encoding = self.encoding or globalstringencoding
        if not isinstance(obj, bytes):
            if not encoding:
                raise StringError("no encoding provided when processing a unicode obj")
            if isinstance(encoding, str):
                obj = obj.encode(encoding)
            else:
                obj = encoding.encode(obj)
        return obj


class StringPaddedTrimmed(Adapter):
    """Used internally."""
    __slots__ = ["length", "padchar", "paddir", "trimdir"]
    def __init__(self, length, subcon, padchar=b"\x00", paddir="right", trimdir="right"):
        if not isinstance(padchar, bytes):
            raise StringError("padchar must be b-string character")
        super(StringPaddedTrimmed, self).__init__(subcon)
        self.length = length
        self.padchar = padchar
        self.paddir = paddir
        self.trimdir = trimdir
    def _decode(self, obj, context):
        length = self.length(context) if callable(self.length) else self.length
        if self.paddir == "right":
            obj = obj.rstrip(self.padchar)
        elif self.paddir == "left":
            obj = obj.lstrip(self.padchar)
        elif self.paddir == "center":
            obj = obj.strip(self.padchar)
        else:
            raise StringError("paddir must be one of: right left center")
        return obj
    def _encode(self, obj, context):
        length = self.length(context) if callable(self.length) else self.length
        if self.paddir == "right":
            obj = obj.ljust(length, self.padchar[0:1])
        elif self.paddir == "left":
            obj = obj.rjust(length, self.padchar[0:1])
        elif self.paddir == "center":
            obj = obj.center(length, self.padchar[0:1])
        else:
            raise StringError("paddir must be one of: right left center")
        if len(obj) > length:
            if self.trimdir == "right":
                obj = obj[:length]
            elif self.trimdir == "left":
                obj = obj[-length:]
            else:
                raise StringError("expected a string of length %s given %s (%r)" % (length,len(obj),obj))
        return obj


def String(length, encoding=None, padchar=b"\x00", paddir="right", trimdir="right"):
    r"""
    A configurable, fixed-length or variable-length string field.

    When parsing, the byte string is stripped of pad character (as specified) from the direction (as specified) then decoded (as specified). Length is a constant integer or a function of the context.
    When building, the string is encoded (as specified) then padded (as specified) from the direction (as specified) or trimmed as bytes (as specified).

    The padding character and direction must be specified for padding to work. The trim direction must be specified for trimming to work.

    :param length: length in bytes (not unicode characters), as int or context function
    :param encoding: encoding (e.g. "utf8") or None for bytes
    :param padchar: b-string character to pad out strings (by default b"\x00")
    :param paddir: direction to pad out strings (one of: right left both)
    :param trimdir: direction to trim strings (one of: right left)

    Example::

        >>> String(10).build(b"hello")
        b'hello\x00\x00\x00\x00\x00'
        >>> String(10).parse(_)
        b'hello'
        >>> String(10).sizeof()
        10

        >>> String(10, encoding="utf8").build("Афон")
        b'\xd0\x90\xd1\x84\xd0\xbe\xd0\xbd\x00\x00'
        >>> String(10, encoding="utf8").parse(_)
        'Афон'

        >>> String(10, padchar=b"XYZ", paddir="center").build(b"abc")
        b'XXXabcXXXX'
        >>> String(10, padchar=b"XYZ", paddir="center").parse(b"XYZabcXYZY")
        b'abc'

        >>> String(10, trimdir="right").build(b"12345678901234567890")
        b'1234567890'
    """
    return StringEncoded(
        StringPaddedTrimmed(
            length, Bytes(length), padchar, paddir, trimdir),
        encoding)


def PascalString(lengthfield, encoding=None):
    r"""
    A length-prefixed string.

    ``PascalString`` is named after the string types of Pascal, which are length-prefixed. Lisp strings also follow this convention.

    The length field will not appear in the same dict, when parsing. Only the string will be returned. When building, actual length is prepended before the encoded string. The length field can be variable length (such as VarInt). Stored length is in bytes, not characters.

    :param lengthfield: a field used to parse and build the length
    :param encoding: encoding (e.g. "utf8") or None for bytes

    Example::

        >>> PascalString(VarInt, encoding="utf8").build("Афон")
        b'\x08\xd0\x90\xd1\x84\xd0\xbe\xd0\xbd'
        >>> PascalString(VarInt, encoding="utf8").parse(_)
        'Афон'
    """
    return StringEncoded(Prefixed(lengthfield, GreedyBytes), encoding)


def CString(terminators=b"\x00", encoding=None):
    r"""
    A string ending in a terminator b-string character.

    ``CString`` is similar to the strings of C.

    By default, the terminator is the NULL byte (b'\x00'). Terminators field can be a longer b-string, and any of the characters breaks parsing. First terminator byte is used when building.

    :param terminators: sequence of valid terminators, first is used when building, all are used when parsing
    :param encoding: encoding (e.g. "utf8") or None for bytes

    Example::

        >>> CString(encoding="utf8").build("Афон")
        b'\xd0\x90\xd1\x84\xd0\xbe\xd0\xbd\x00'
        >>> CString(encoding="utf8").parse(_)
        'Афон'
    """
    return StringEncoded(
        ExprAdapter(
            RepeatUntil(lambda obj,ctx: int2byte(obj) in terminators, Byte),
            encoder = lambda obj,ctx: iterateints(obj+terminators),
            decoder = lambda obj,ctx: b''.join(int2byte(c) for c in obj[:-1])),
        encoding)


def GreedyString(encoding=None):
    r"""
    A string that reads the rest of the stream until EOF, and writes a given string as is. If no encoding is given, this is essentially GreedyBytes.

    :param encoding: encoding (e.g. "utf8") or None for bytes

    .. seealso:: Analog to :class:`~construct.core.GreedyBytes` and the same when no enoding is used.

    Example::

        >>> GreedyString(encoding="utf8").build("Афон")
        b'\xd0\x90\xd1\x84\xd0\xbe\xd0\xbd'
        >>> GreedyString(encoding="utf8").parse(_)
        'Афон'
    """
    return StringEncoded(GreedyBytes, encoding)


#===============================================================================
# end of file
#===============================================================================
