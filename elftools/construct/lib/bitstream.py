import io

from .binary import encode_bin, decode_bin

class BitStream(io.RawIOBase):

    __slots__ = ["substream"]

    def __init__(self, substream):
        self.substream = substream

    def __enter__(self):
        return self


class BitStreamReader(BitStream):

    __slots__ = ["buffer", "total_size"]

    def __init__(self, substream):
        super().__init__(substream)
        self.total_size = 0
        self.buffer = b""

    def close(self):
        if self.total_size % 8 != 0:
            raise ValueError("total size of read data must be a multiple of 8",
                self.total_size)

    def tell(self):
        return self.substream.tell()

    def seek(self, pos, whence = 0):
        self.buffer = b""
        self.total_size = 0
        self.substream.seek(pos, whence)
        return 0

    def read(self, count):
        if count < 0:
            raise ValueError("count cannot be negative")

        l = len(self.buffer)
        if count == 0:
            data = b""
        elif count <= l:
            data = self.buffer[:count]
            self.buffer = self.buffer[count:]
        else:
            data = self.buffer
            count -= l
            bytes = count // 8
            if count & 7:
                bytes += 1
            buf = encode_bin(self.substream.read(bytes))
            data += buf[:count]
            self.buffer = buf[count:]
        self.total_size += len(data)
        return data


class BitStreamWriter(BitStream):

    __slots__ = ["buffer", "pos"]

    def __init__(self, substream):
        super().__init__(substream)
        self.buffer = []
        self.pos = 0

    def close(self):
        self.flush()

    def flush(self):
        bytes = decode_bin(b"".join(self.buffer))
        self.substream.write(bytes)
        self.buffer = []
        self.pos = 0

    def tell(self):
        return self.substream.tell() + self.pos // 8

    def seek(self, pos, whence = 0):
        self.flush()
        return self.substream.seek(pos, whence)

    def write(self, data):
        if not data:
            return 0
        if type(data) is not bytes:
            raise TypeError("data must be a bytes, not %r" % (type(data),))
        self.buffer.append(data)
        return len(data)
