from construct.lib.py3compat import byte2int, int2byte, bytes2str, iteratebytes, iterateints


# Map an integer in the inclusive range 0-255 to its string byte representation
_printable = [bytes2str(int2byte(i)) if 32 <= i < 128 else '.' for i in range(256)]
_hexprint = [format(i, '02X') for i in range(256)]

def hexdump(data, linesize):
    r"""
    Turns bytes into a unicode string of the format:

    >>>print(hexdump(b'0' * 100, 16))
    0000   30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30   0000000000000000
    0010   30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30   0000000000000000
    0020   30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30   0000000000000000
    0030   30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30   0000000000000000
    0040   30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30   0000000000000000
    0050   30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30   0000000000000000
    0060   30 30 30 30                                       0000             
    """
    if len(data) < 16**4:
        fmt = "%%04X   %%-%ds   %%s" % (3 * linesize - 1,)
    elif len(data) < 16**8:
        fmt = "%%08X   %%-%ds   %%s" % (3 * linesize - 1,)
    else:
        raise ValueError("hexdump cannot process more than 16**8 or 4294967296 bytes")
    prettylines = []
    for i in range(0, len(data), linesize):
        line = data[i:i+linesize]
        hextext = " ".join(_hexprint[b] for b in iterateints(line))
        rawtext = "".join(_printable[b] for b in iterateints(line))
        prettylines.append(fmt % (i, str(hextext), str(rawtext)))
    prettylines.append("")
    return "\n".join(prettylines)


def hexundump(data, linesize):
    r"""
    Reverse of ``hexdump()``.
    """
    raw = []
    for line in data.split("\n"):
        line = line[line.find(" "):].lstrip()
        bytes = [int2byte(int(s,16)) for s in line[:3*linesize].split()]
        raw.extend(bytes)
    return b"".join(raw)


class HexString(bytes):
    r"""
    Represents bytes that will be hex-dumped when parsing, and un-dumped when building.

    See hexdump().
    """
    def __init__(self, data, linesize=16):
        self.linesize = linesize

    def __new__(cls, data, *args, **kwargs):
        return bytes.__new__(cls, data)

    def __str__(self):
        if not self:
            return "''"
        return "\n" + "\n".join(hexdump(self, self.linesize))

