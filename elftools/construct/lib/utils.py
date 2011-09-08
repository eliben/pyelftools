try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


try:
    from struct import Struct as Packer
except ImportError:
    from struct import pack, unpack, calcsize
    class Packer(object):
        __slots__ = ["format", "size"]
        def __init__(self, format):
            self.format = format
            self.size = calcsize(format)
        def pack(self, *args):
            return pack(self.format, *args)
        def unpack(self, data):
            return unpack(self.format, data)



