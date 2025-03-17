from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self  # 3.11+


# Map an integer in the inclusive range 0-255 to its string byte representation
_printable = dict((i, ".") for i in range(256))
_printable.update((i, chr(i)) for i in range(32, 128))


def hexdump(data: bytes, linesize: int) -> list[str]:
    """
    data is a bytes object. The returned result is a string.
    """
    prettylines = []
    if len(data) < 65536:
        fmt = "%%04X   %%-%ds   %%s"
    else:
        fmt = "%%08X   %%-%ds   %%s"
    fmt = fmt % (3 * linesize - 1,)
    for i in range(0, len(data), linesize):
        line = data[i : i + linesize]
        hextext = " ".join('%02x' % b for b in line)
        rawtext = "".join(_printable[b] for b in line)
        prettylines.append(fmt % (i, str(hextext), str(rawtext)))
    return prettylines


class HexString(bytes):
    """
    Represents bytes that will be hex-dumped to a string when its string
    representation is requested.
    """
    def __init__(self, data: bytes, linesize: int = 16) -> None:
        self.linesize = linesize

    def __new__(cls, data: bytes, *args: object, **kwargs: object) -> Self:
        return bytes.__new__(cls, data)

    def __str__(self) -> str:
        if not self:
            return "''"
        sep = "\n"
        return sep + sep.join(
            hexdump(self, self.linesize))
