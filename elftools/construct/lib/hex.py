_printable = dict((chr(i), ".") for i in range(256))
_printable.update((chr(i), chr(i)) for i in range(32, 128))

def hexdump(data, linesize = 16):
    prettylines = []
    if len(data) < 65536:
        fmt = "%%04X   %%-%ds   %%s"
    else:
        fmt = "%%08X   %%-%ds   %%s"
    fmt = fmt % (3 * linesize - 1,)
    for i in xrange(0, len(data), linesize):
        line = data[i : i + linesize]
        hextext = " ".join(b.encode("hex") for b in line)
        rawtext = "".join(_printable[b] for b in line)
        prettylines.append(fmt % (i, hextext, rawtext))
    return prettylines

class HexString(str):
    """
    represents a string that will be hex-dumped (only via __pretty_str__).
    this class derives of str, and behaves just like a normal string in all
    other contexts.
    """
    def __init__(self, data, linesize = 16):
        str.__init__(self, data)
        self.linesize = linesize
    def __new__(cls, data, *args, **kwargs):
        return str.__new__(cls, data)
    def __pretty_str__(self, nesting = 1, indentation = "    "):
        sep = "\n" + indentation * nesting
        return sep + sep.join(hexdump(self))



