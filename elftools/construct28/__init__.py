r"""
Construct 2 -- Parsing Made Fun

Homepage:
	https://github.com/construct/construct
    http://construct.readthedocs.org

Hands-on example:
    >>> from construct import *
    >>> s = Struct(
    ...     "a" / UBInt8,
    ...     "b" / UBInt16,
    ... )
    >>> print s.parse(b"\x01\x02\x03")
    Container:
        a = 1
        b = 515
    >>> s.build(Container(a=1, b=0x0203))
    b"\x01\x02\x03"
"""

from construct.core import *
from construct.expr import this, Path, Path2, PathFunc, len_, sum_, min_, max_, abs_, obj_, True_, False_
from construct.debug import Probe, ProbeInto, Debugger
from construct.version import version, version_string, release_date
from construct import lib


#===============================================================================
# metadata
#===============================================================================
__author__ = "Arkadiusz Bulski <arek.bulski@gmail.com>, Tomer Filiba <tomerfiliba@gmail.com>, Corbin Simpson <MostAwesomeDude@gmail.com>"
__version__ = version_string

#===============================================================================
# aliases
#===============================================================================

#===============================================================================
# exposed names
#===============================================================================
__all__ = [
    'AdaptationError', 'Alias', 'Aligned', 'AlignedStruct', 'Array', 'Bit', 'BitIntegerError', 'BitStruct', 'Bitwise', 'CString', 'Construct', 'ConstructError', 'Container', 'Debugger', 'EmbeddedBitStruct', 'Enum', 'ExprAdapter', 'FieldError', 'Flag', 'FlagsContainer', 'FlagsEnum', 'Bytes', 'FormatField', 'GreedyRange', 'HexDump', 'HexString', 'If', 'IfThenElse', 'Indexing', 'LazyBound', 'LazyContainer', 'ListContainer', 'Mapping', 'MappingError', 'Nibble', 'NoneOf', 'Octet', 'OnDemand', 'OnDemandPointer', 'OneOf', 'Optional', 'OverwriteError', 'Packer', 'Padding', 'PaddingError', 'PascalString', 'Pass', 'Peek', 'Pointer', 'PrefixedArray', 'Probe', 'Range', 'RangeError', 'Renamed', 'RepeatUntil', 'Select', 'SelectError', 'Sequence', 'SizeofError', 'Slicing', 'String', 'Struct', 'Subconstruct', 'Switch', 'SwitchError', 'SymmetricMapping', 'Terminated', 'TerminatedError', 'UnionError', 'Union', 'ValidationError', 'Validator', 'Computed', 'Byte', 'Bytes', 'Tunnel', 'Embedded', 'Const', 'ConstError', 'VarInt', 'StringError', 'Checksum', 'ByteSwapped', 'LazyStruct', 'Numpy', 'Adapter', 'SymmetricAdapter', 'Tunnel', 'Compressed', 'GreedyBytes', 'Prefixed', 'Padded', 'GreedyString', 'RawCopy', 'LazyRange', 'LazySequence', 'LazySequenceContainer', 'BitsInteger', 'BytesInteger', '__author__', '__version__','Restreamed', 'RestreamedBytesIO', 'Bytewise', 'LazyRangeContainer', 'BitsSwapped', 'RebufferedBytesIO','Rebuffered','version','version_string','lib','Seek','Tell','setglobalstringencoding','globalstringencoding','NamedTuple','ExprValidator','Filter','Hex','Error','ExplicitError','release_date','Rebuild','Check','len_','sum_','min_','max_','abs_','obj_','singleton','singletonfunction', 'this', 'Path','Path2','PathFunc','FocusedSeq','FocusedError','ExprSymmetricAdapter','True_','False_','BoundBytesIO','ProbeInto','Default',

] + ["Int%s%s%s" % (n,us,bln) for n in (8,16,32,64) for us in "us" for bln in "bln"] + ["Int24ub","Int24ul","Int24sb","Int24sl"] + ["Float%s%s" % (n,bl) for n in (32,64) for bl in "bl"] + ["Single","Double"]


