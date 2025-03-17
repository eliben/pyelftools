from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Any, Callable, Literal

from .core import Adapter, AdaptationError, Pass
from .lib import int_to_bin, bin_to_int, swap_bytes
from .lib import FlagsContainer, HexString

if TYPE_CHECKING:
    from collections.abc import Hashable, Mapping, Sized

    from .core import Construct, _Pass
    from .lib import Container, ListContainer


__all__ = [
    "BitIntegerError", "MappingError", "ConstError", "ValidationError", "PaddingError",
    "BitIntegerAdapter", "MappingAdapter", "FlagsAdapter", "StringAdapter", "PaddedStringAdapter",
    "LengthValueAdapter", "CStringAdapter", "TunnelAdapter", "ExprAdapter", "HexDumpAdapter", "ConstAdapter",
    "SlicingAdapter", "IndexingAdapter", "PaddingAdapter",
    "Validator", "OneOf", "NoneOf",
]


#===============================================================================
# exceptions
#===============================================================================
class BitIntegerError(AdaptationError):
    __slots__: list[str] = []
class MappingError(AdaptationError):
    __slots__: list[str] = []
class ConstError(AdaptationError):
    __slots__: list[str] = []
class ValidationError(AdaptationError):
    __slots__: list[str] = []
class PaddingError(AdaptationError):
    __slots__: list[str] = []

#===============================================================================
# adapters
#===============================================================================
class BitIntegerAdapter(Adapter):
    """
    Adapter for bit-integers (converts bitstrings to integers, and vice versa).
    See BitField.

    Parameters:
    * subcon - the subcon to adapt
    * width - the size of the subcon, in bits
    * swapped - whether to swap byte order (little endian/big endian).
      default is False (big endian)
    * signed - whether the value is signed (two's complement). the default
      is False (unsigned)
    * bytesize - number of bits per byte, used for byte-swapping (if swapped).
      default is 8.
    """
    __slots__: list[str] = ["width", "swapped", "signed", "bytesize"]
    def __init__(self, subcon: Construct, width: int, swapped: bool = False, signed: bool = False,
            bytesize: int = 8) -> None:
        Adapter.__init__(self, subcon)
        self.width = width
        self.swapped = swapped
        self.signed = signed
        self.bytesize = bytesize
    def _encode(self, obj: int, context: Container) -> bytes:
        if obj < 0 and not self.signed:
            raise BitIntegerError("object is negative, but field is not signed",
                obj)
        obj2 = int_to_bin(obj, width = self.width)
        if self.swapped:
            obj2 = swap_bytes(obj2, bytesize = self.bytesize)
        return obj2
    def _decode(self, obj: bytes, context: Container) -> int:
        if self.swapped:
            obj = swap_bytes(obj, bytesize = self.bytesize)
        return bin_to_int(obj, signed = self.signed)

class MappingAdapter(Adapter):
    """
    Adapter that maps objects to other objects.
    See SymmetricMapping and Enum.

    Parameters:
    * subcon - the subcon to map
    * decoding - the decoding (parsing) mapping (a dict)
    * encoding - the encoding (building) mapping (a dict)
    * decdefault - the default return value when the object is not found
      in the decoding mapping. if no object is given, an exception is raised.
      if `Pass` is used, the unmapped object will be passed as-is
    * encdefault - the default return value when the object is not found
      in the encoding mapping. if no object is given, an exception is raised.
      if `Pass` is used, the unmapped object will be passed as-is
    """
    __slots__: list[str] = ["encoding", "decoding", "encdefault", "decdefault"]
    def __init__(self, subcon: Construct, decoding: Mapping[Any, Any], encoding: Mapping[Any, Any],
            decdefault: Hashable | _Pass = NotImplemented,
            encdefault: Hashable | _Pass = NotImplemented,
    ) -> None:
        Adapter.__init__(self, subcon)
        self.decoding = decoding
        self.encoding = encoding
        self.decdefault = decdefault
        self.encdefault = encdefault
    def _encode(self, obj: Hashable, context: Container) -> Hashable:
        try:
            return self.encoding[obj]
        except (KeyError, TypeError):
            if self.encdefault is NotImplemented:
                raise MappingError("no encoding mapping for %r [%s]" % (
                    obj, self.subcon.name))
            if self.encdefault is Pass:
                return obj
            return self.encdefault
    def _decode(self, obj: Hashable, context: Container) -> Hashable:
        try:
            return self.decoding[obj]
        except (KeyError, TypeError):
            if self.decdefault is NotImplemented:
                raise MappingError("no decoding mapping for %r [%s]" % (
                    obj, self.subcon.name))
            if self.decdefault is Pass:
                return obj
            return self.decdefault

class FlagsAdapter(Adapter):
    """
    Adapter for flag fields. Each flag is extracted from the number, resulting
    in a FlagsContainer object. Not intended for direct usage.
    See FlagsEnum.

    Parameters
    * subcon - the subcon to extract
    * flags - a dictionary mapping flag-names to their value
    """
    __slots__: list[str] = ["flags"]
    def __init__(self, subcon: Construct, flags: dict[str, int]) -> None:
        Adapter.__init__(self, subcon)
        self.flags = flags
    def _encode(self, obj: FlagsContainer, context: Container) -> int:
        flags = 0
        for name, value in self.flags.items():
            if getattr(obj, name, False):
                flags |= value
        return flags
    def _decode(self, obj: int, context: Container) -> FlagsContainer:
        obj2 = FlagsContainer()
        for name, value in self.flags.items():
            setattr(obj2, name, bool(obj & value))
        return obj2

class StringAdapter(Adapter):
    """
    Adapter for strings. Converts a sequence of characters into a python
    string, and optionally handles character encoding.
    See String.

    Parameters:
    * subcon - the subcon to convert
    * encoding - the character encoding name (e.g., "utf8"), or None to
      return raw bytes (usually 8-bit ASCII).
    """
    __slots__: list[str] = ["encoding"]
    def __init__(self, subcon: Construct, encoding: str | None = None) -> None:
        Adapter.__init__(self, subcon)
        self.encoding = encoding
    def _encode(self, obj: bytes | str, context: Container) -> bytes:
        if self.encoding:
            assert isinstance(obj, str)
            obj = obj.encode(self.encoding)
        assert isinstance(obj, bytes)
        return obj
    def _decode(self, obj: bytes, context: Container) -> bytes | str:
        if self.encoding:
            return obj.decode(self.encoding)
        return obj

class PaddedStringAdapter(Adapter):
    r"""
    Adapter for padded strings.
    See String.

    Parameters:
    * subcon - the subcon to adapt
    * padchar - the padding character. default is b"\x00".
    * paddir - the direction where padding is placed ("right", "left", or
      "center"). the default is "right".
    * trimdir - the direction where trimming will take place ("right" or
      "left"). the default is "right". trimming is only meaningful for
      building, when the given string is too long.
    """
    __slots__: list[str] = ["padchar", "paddir", "trimdir"]
    def __init__(self, subcon: Construct, padchar: bytes = b"\x00", paddir: Literal["right", "left", "center"] = "right",
            trimdir: Literal["right", "left"] = "right"):
        if paddir not in ("right", "left", "center"):
            raise ValueError("paddir must be 'right', 'left' or 'center'",
                paddir)
        if trimdir not in ("right", "left"):
            raise ValueError("trimdir must be 'right' or 'left'", trimdir)
        Adapter.__init__(self, subcon)
        self.padchar = padchar
        self.paddir = paddir
        self.trimdir = trimdir
    def _decode(self, obj: bytes, context: Container) -> bytes:
        if self.paddir == "right":
            obj = obj.rstrip(self.padchar)
        elif self.paddir == "left":
            obj = obj.lstrip(self.padchar)
        else:
            obj = obj.strip(self.padchar)
        return obj
    def _encode(self, obj: bytes, context: Container) -> bytes:
        size = self._sizeof(context)
        if self.paddir == "right":
            obj = obj.ljust(size, self.padchar)
        elif self.paddir == "left":
            obj = obj.rjust(size, self.padchar)
        else:
            obj = obj.center(size, self.padchar)
        if len(obj) > size:
            if self.trimdir == "right":
                obj = obj[:size]
            else:
                obj = obj[-size:]
        return obj

class LengthValueAdapter(Adapter):
    """
    Adapter for length-value pairs. It extracts only the value from the
    pair, and calculates the length based on the value.
    See PrefixedArray and PascalString.

    Parameters:
    * subcon - the subcon returning a length-value pair
    """
    __slots__: list[str] = []
    def _encode(self, obj: Sized, context: Container) -> tuple[int, Sized]:
        return (len(obj), obj)
    def _decode(self, obj: tuple[int, Sized] | ListContainer, context: Container) -> Sized:
        return obj[1]

class CStringAdapter(StringAdapter):
    r"""
    Adapter for C-style strings (strings terminated by a terminator char).

    Parameters:
    * subcon - the subcon to convert
    * terminators - a sequence of terminator chars. default is b"\x00".
    * encoding - the character encoding to use (e.g., "utf8"), or None to
      return raw-bytes. the terminator characters are not affected by the
      encoding.
    """
    __slots__: list[str] = ["terminators"]
    def __init__(self, subcon: Construct, terminators: bytes = b"\x00", encoding: str | None = None) -> None:
        StringAdapter.__init__(self, subcon, encoding = encoding)
        self.terminators = terminators
    def _encode(self, obj: bytes | str, context: Container) -> bytes:
        return StringAdapter._encode(self, obj, context) + self.terminators[0:1]
    def _decode(self, obj: list[bytes], context: Container) -> bytes | str:  # type: ignore[override]
        return StringAdapter._decode(self, b''.join(obj[:-1]), context)

class TunnelAdapter(Adapter):
    """
    Adapter for tunneling (as in protocol tunneling). A tunnel is construct
    nested upon another (layering). For parsing, the lower layer first parses
    the data (note: it must return a string!), then the upper layer is called
    to parse that data (bottom-up). For building it works in a top-down manner;
    first the upper layer builds the data, then the lower layer takes it and
    writes it to the stream.

    Parameters:
    * subcon - the lower layer subcon
    * inner_subcon - the upper layer (tunneled/nested) subcon

    Example:
    # a pascal string containing compressed data (zlib encoding), so first
    # the string is read, decompressed, and finally re-parsed as an array
    # of UBInt16
    TunnelAdapter(
        PascalString("data", encoding = "zlib"),
        GreedyRange(UBInt16("elements"))
    )
    """
    __slots__: list[str] = ["inner_subcon"]
    def __init__(self, subcon: Construct, inner_subcon: Construct) -> None:
        Adapter.__init__(self, subcon)
        self.inner_subcon = inner_subcon
    def _decode(self, obj: bytes, context: Container) -> Any:
        return self.inner_subcon._parse(BytesIO(obj), context)
    def _encode(self, obj: Any, context: Container) -> bytes:
        stream = BytesIO()
        self.inner_subcon._build(obj, stream, context)
        return stream.getvalue()

class ExprAdapter(Adapter):
    """
    A generic adapter that accepts 'encoder' and 'decoder' as parameters. You
    can use ExprAdapter instead of writing a full-blown class when only a
    simple expression is needed.

    Parameters:
    * subcon - the subcon to adapt
    * encoder - a function that takes (obj, context) and returns an encoded
      version of obj
    * decoder - a function that takes (obj, context) and returns a decoded
      version of obj

    Example:
    ExprAdapter(UBInt8("foo"),
        encoder = lambda obj, ctx: obj / 4,
        decoder = lambda obj, ctx: obj * 4,
    )
    """
    __slots__: list[str] = ["__encode", "__decode"]
    def __init__(self, subcon: Construct, encoder: Callable[[Any, Container], bytes], decoder: Callable[[bytes, Container], Any]) -> None:
        Adapter.__init__(self, subcon)
        self.__encode = encoder
        self.__decode = decoder
    def _encode(self, obj: Any, context: Container) -> Any:
        return self.__encode(obj, context)
    def _decode(self, obj: Any, context: Container) -> Any:
        return self.__decode(obj, context)

class HexDumpAdapter(Adapter):
    """
    Adapter for hex-dumping strings. It returns a HexString, which is a string
    """
    __slots__: list[str] = ["linesize"]
    def __init__(self, subcon: Construct, linesize: int = 16) -> None:
        Adapter.__init__(self, subcon)
        self.linesize = linesize
    def _encode(self, obj: Any, context: Container) -> Any:
        return obj
    def _decode(self, obj: bytes, context: Container) -> HexString:
        return HexString(obj, linesize = self.linesize)

class ConstAdapter(Adapter):
    """
    Adapter for enforcing a constant value ("magic numbers"). When decoding,
    the return value is checked; when building, the value is substituted in.

    Parameters:
    * subcon - the subcon to validate
    * value - the expected value

    Example:
    Const(Field("signature", 2), "MZ")
    """
    __slots__ = ["value"]
    def __init__(self, subcon: Construct, value: object) -> None:
        Adapter.__init__(self, subcon)
        self.value = value
    def _encode(self, obj: object, context: Container) -> object:
        if obj is None or obj == self.value:
            return self.value
        else:
            raise ConstError("expected %r, found %r" % (self.value, obj))
    def _decode(self, obj: object, context: Container) -> object:
        if obj != self.value:
            raise ConstError("expected %r, found %r" % (self.value, obj))
        return obj

class SlicingAdapter(Adapter):
    """
    Adapter for slicing a list (getting a slice from that list)

    Parameters:
    * subcon - the subcon to slice
    * start - start index
    * stop - stop index (or None for up-to-end)
    * step - step (or None for every element)
    """
    __slots__: list[str] = ["start", "stop", "step"]
    def __init__(self, subcon: Construct, start: int, stop: int | None = None) -> None:
        Adapter.__init__(self, subcon)
        self.start = start
        self.stop = stop
    def _encode(self, obj: list[Any], context: Container) -> list[Any]:
        if self.start is None:
            return obj
        return [None] * self.start + obj
    def _decode(self, obj: list[Any], context: Container) -> list[Any]:
        return obj[self.start:self.stop]

class IndexingAdapter(Adapter):
    """
    Adapter for indexing a list (getting a single item from that list)

    Parameters:
    * subcon - the subcon to index
    * index - the index of the list to get
    """
    __slots__: list[str] = ["index"]
    def __init__(self, subcon: Construct, index: int) -> None:
        Adapter.__init__(self, subcon)
        if type(index) is not int:
            raise TypeError("index must be an integer", type(index))
        self.index = index
    def _encode(self, obj: Any, context: Container) -> list[Any]:
        return [None] * self.index + [obj]
    def _decode(self, obj: list[Any], context: Container) -> Any:
        return obj[self.index]

class PaddingAdapter(Adapter):
    r"""
    Adapter for padding.

    Parameters:
    * subcon - the subcon to pad
    * pattern - the padding pattern (character as byte). default is b"\x00"
    * strict - whether or not to verify, during parsing, that the given
      padding matches the padding pattern. default is False (unstrict)
    """
    __slots__: list[str] = ["pattern", "strict"]
    def __init__(self, subcon: Construct, pattern: bytes = b"\x00", strict: bool = False) -> None:
        Adapter.__init__(self, subcon)
        self.pattern = pattern
        self.strict = strict
    def _encode(self, obj: None, context: Container) -> bytes:
        return self._sizeof(context) * self.pattern
    def _decode(self, obj: bytes, context: Container) -> bytes:
        if self.strict:
            expected = self._sizeof(context) * self.pattern
            if obj != expected:
                raise PaddingError("expected %r, found %r" % (expected, obj))
        return obj


#===============================================================================
# validators
#===============================================================================
class Validator(Adapter):
    """
    Abstract class: validates a condition on the encoded/decoded object.
    Override _validate(obj, context) in deriving classes.

    Parameters:
    * subcon - the subcon to validate
    """
    __slots__: list[str] = []
    def _decode(self, obj: object, context: Container) -> object:
        if not self._validate(obj, context):
            raise ValidationError("invalid object", obj)
        return obj
    def _encode(self, obj: object, context: Container) -> object:
        return self._decode(obj, context)
    def _validate(self, obj: object, context: Container) -> bool:
        raise NotImplementedError()

class OneOf(Validator):
    """
    Validates that the object is one of the listed values.

    :param ``Construct`` subcon: object to validate
    :param iterable valids: a set of valid values

    >>> from ..construct import UBInt8
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).parse(b"\\x05")
    5
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).parse(b"\\x08")  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValidationError: ('invalid object', 8)
    >>>
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).build(5)
    b'\\x05'
    >>> OneOf(UBInt8("foo"), [4,5,6,7]).build(9)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValidationError: ('invalid object', 9)
    """
    __slots__: list[str] = ["valids"]
    def __init__(self, subcon: Construct, valids: list[object]) -> None:
        Validator.__init__(self, subcon)
        self.valids = valids
    def _validate(self, obj: object, context: Container) -> bool:
        return obj in self.valids

class NoneOf(Validator):
    """
    Validates that the object is none of the listed values.

    :param ``Construct`` subcon: object to validate
    :param iterable invalids: a set of invalid values

    >>> from ..construct import UBInt8
    >>> NoneOf(UBInt8("foo"), [4,5,6,7]).parse(b"\\x08")
    8
    >>> NoneOf(UBInt8("foo"), [4,5,6,7]).parse(b"\\x06")  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValidationError: ('invalid object', 6)
    """
    __slots__: list[str] = ["invalids"]
    def __init__(self, subcon: Construct, invalids: list[object]) -> None:
        Validator.__init__(self, subcon)
        self.invalids = invalids
    def _validate(self, obj: object, context: Container) -> bool:
        return obj not in self.invalids
