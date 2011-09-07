"""
Construct 2.00 -- parsing made even more fun (and faster)

Homepage:
http://construct.wikispaces.com

Typical usage:
>>> from construct import *

Example:
>>> from construct import *
>>>
>>> s = Struct("foo",
...     UBInt8("a"),
...     UBInt16("b"),
... )
>>>
>>> s.parse("\x01\x02\x03")
Container(a = 1, b = 515)
>>> print s.parse("\x01\x02\x03")
Container:
    a = 1
    b = 515
>>> s.build(Container(a = 1, b = 0x0203))
"\x01\x02\x03"
"""
from core import *
from adapters import *
from macros import *
from debug import Probe, Debugger


#===============================================================================
# meta data
#===============================================================================
__author__ = "tomer filiba (tomerfiliba [at] gmail.com)"
__version__ = "2.00"

#===============================================================================
# shorthands
#===============================================================================
Bits = BitField
Byte = UBInt8
Bytes = Field
Const = ConstAdapter
Tunnel = TunnelAdapter
Embed = Embedded

#===============================================================================
# backward compatibility with RC1
#===============================================================================
MetaField = Field
MetaBytes = Field
GreedyRepeater = GreedyRange
OptionalGreedyRepeater = OptionalGreedyRange
Repeater = Array
StrictRepeater = Array
MetaRepeater = Array
OneOfValidator = OneOf
NoneOfValidator = NoneOf

#===============================================================================
# don't want to leek these out...
#===============================================================================
del encode_bin, decode_bin, int_to_bin, bin_to_int, swap_bytes
del Packer, StringIO
del HexString, LazyContainer, AttrDict














