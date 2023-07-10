#-------------------------------------------------------------------------------
# elftools: common/construct_utils.py
#
# Some complementary construct utilities
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import itertools

from construct import (
    Subconstruct, Adapter, Bytes, RepeatUntil, Container, StopFieldError,
    singleton, GreedyBytes, NullTerminated, Struct, Array
)


def exclude_last_value(predicate):
    def _exclude_last_value(obj, list, ctx):
        result = predicate(obj, list, ctx)
        if result:
            del list[-1]
        return result

    return _exclude_last_value


def _LEB128_reader():
    """ Read LEB128 variable-length data from the stream. The data is terminated
        by a byte with 0 in its highest bit.
    """
    return RepeatUntil(
        lambda obj, list, ctx: ord(obj) < 0x80,
        Bytes(1)
    )

class _SLEB128Adapter(Adapter):
    """ An adapter for SLEB128, given a sequence of bytes in a sub-construct.
    """
    def _decode(self, obj, context, path):
        value = 0
        for b in reversed(obj):
            value = (value << 7) + (ord(b) & 0x7F)
        if ord(obj[-1]) & 0x40:
            # negative -> sign extend
            value |= - (1 << (7 * len(obj)))
        return value
    
    def _emitparse(self, code):
        block = f"""
            def parse_sleb128(io, this):
                l = []
                while True:
                    b = io.read(1)[0]
                    l.append(b)
                    if b < 0x80:
                        break
                value = 0
                for b in reversed(l):
                    value = (value << 7) + (b & 0x7F)
                if l[-1] & 0x40:
                    value |= - (1 << (7 * len(l)))
                return value
        """
        code.append(block)
        return f"parse_sleb128(io, this)"
    
    def _emitbuild(self, code):
        return "None"

# ULEB128 was here, but construct has a drop-in replacement called VarInt

@singleton
def SLEB128():
    """ A construct creator for SLEB128 encoding.
    """
    return _SLEB128Adapter(_LEB128_reader())


class EmbeddableStruct(Struct):
    r"""
    A special Struct that allows embedding of fields with type Embed.
    """

    def __init__(self, *subcons, **subconskw):
        super().__init__(*subcons, **subconskw)

    def _parse(self, stream, context, path):
        obj = Container()
        obj._io = stream
        context = Container(_ = context, _params = context._params, _root = None, _parsing = context._parsing, _building = context._building, _sizing = context._sizing, _subcons = self._subcons, _io = stream, _index = context.get("_index", None), _parent = obj)
        context._root = context._.get("_root", context)
        for sc in self.subcons:
            try:
                subobj = sc._parsereport(stream, context, path)
                if sc.name:
                    obj[sc.name] = subobj
                    context[sc.name] = subobj
                elif subobj and isinstance(sc, Embed):
                    obj.update(subobj)

            except StopFieldError:
                break
        return obj


class Embed(Subconstruct):
    r"""
    Special wrapper that allows outer multiple-subcons construct to merge fields from another multiple-subcons construct.
    Parsing building and sizeof are deferred to subcon.
    :param subcon: Construct instance, its fields to embed inside a struct or sequence
    Example::
        >>> outer = EmbeddableStruct(
        ...     Embed(Struct(
        ...         "data" / Bytes(4),
        ...     )),
        ... )
        >>> outer.parse(b"1234")
        Container(data=b'1234')
    """

    def __init__(self, subcon):
        super().__init__(subcon)


@singleton
def CStringBytes():
    """
    A stripped back version of CString that returns bytes instead of a unicode string.
    """
    return NullTerminated(GreedyBytes)
