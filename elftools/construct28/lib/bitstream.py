from io import BlockingIOError
from time import sleep
from sys import maxsize



class RestreamedBytesIO(object):
    __slots__ = ["substream", "encoder", "encoderunit", "decoder", "decoderunit", "rbuffer", "wbuffer","sincereadwritten"]

    def __init__(self, substream, encoder, encoderunit, decoder, decoderunit):
        self.substream = substream
        self.encoder = encoder
        self.encoderunit = encoderunit
        self.decoder = decoder
        self.decoderunit = decoderunit
        self.rbuffer = b""
        self.wbuffer = b""
        self.sincereadwritten = 0

    def read(self, count):
        if count < 0:
            raise ValueError("count cannot be negative")
        while len(self.rbuffer) < count:
            data = self.substream.read(self.decoderunit)
            if data is None or len(data) == 0:
                raise IOError("Restreamed cannot satisfy read request of %d bytes" % count)
            self.rbuffer += self.decoder(data)
        data, self.rbuffer = self.rbuffer[:count], self.rbuffer[count:]
        self.sincereadwritten += count
        return data

    def write(self, data):
        self.wbuffer += data
        datalen = len(data)
        while len(self.wbuffer) >= self.encoderunit:
            data, self.wbuffer = self.wbuffer[:self.encoderunit], self.wbuffer[self.encoderunit:]
            self.substream.write(self.encoder(data))
        self.sincereadwritten += datalen
        return datalen

    def close(self):
        if len(self.rbuffer):
            raise ValueError("closing stream but %d unread bytes remain, %d is decoded unit" % (len(self.rbuffer), self.decoderunit))
        if len(self.wbuffer):
            raise ValueError("closing stream but %d unwritten bytes remain, %d is encoded unit" % (len(self.wbuffer), self.encoderunit))

    def seekable(self):
        return False

    def tell(self):
        """WARNING: tell is correct only on read-only and write-only instances."""
        return self.sincereadwritten

    def tellable(self):
        return True




class RebufferedBytesIO(object):
    __slots__ = ["substream","offset","rwbuffer","moved","tailcutoff"]

    def __init__(self, substream, tailcutoff=None):
        self.substream = substream
        self.offset = 0
        self.rwbuffer = b""
        self.moved = 0
        self.tailcutoff = tailcutoff

    def read(self, count=None):
        if count is None:
            raise ValueError("count must be an int, reading until EOF not supported")
        startsat = self.offset
        endsat = startsat + count
        if startsat < self.moved:
            raise IOError("could not read because tail was cut off")
        while self.moved + len(self.rwbuffer) < endsat:
            try:
                newdata = self.substream.read(128*1024)
            except BlockingIOError:
                newdata = None
            if not newdata:
                sleep(0)
                continue
            self.rwbuffer += newdata
        data = self.rwbuffer[startsat-self.moved:endsat-self.moved]
        self.offset += count
        if self.tailcutoff is not None and self.moved < self.offset - self.tailcutoff:
            removed = self.offset - self.tailcutoff - self.moved
            self.moved += removed
            self.rwbuffer = self.rwbuffer[removed:]
        if len(data) < count:
            raise IOError("could not read enough bytes, something went wrong")
        return data

    def write(self, data):
        startsat = self.offset
        endsat = startsat + len(data)
        while self.moved + len(self.rwbuffer) < startsat:
            newdata = self.substream.read(128*1024)
            self.rwbuffer += newdata
            if not newdata:
                sleep(0)
        self.rwbuffer = self.rwbuffer[:startsat-self.moved] + data + self.rwbuffer[endsat-self.moved:]
        self.offset = endsat
        if self.tailcutoff is not None and self.moved < self.offset - self.tailcutoff:
            removed = self.offset - self.tailcutoff - self.moved
            self.moved += removed
            self.rwbuffer = self.rwbuffer[removed:]
        return len(data)

    def seek(self, at, whence=0):
        if whence == 0:
            self.offset = at
            return self.offset
        elif whence == 1:
            self.offset += at
            return self.offset
        else:
            raise ValueError("seeks only with whence 0 and 1")

    def seekable(self):
        return True

    def tell(self):
        return self.offset

    def tellable(self):
        return True

    def cachedfrom(self):
        return self.moved

    def cachedto(self):
        return self.moved + len(self.rwbuffer)



class BoundBytesIO(object):
    __slots__ = ["substream","start","size"]
    def __init__(self, substream, available):
        self.substream = substream
        self.start = self.tell()
        self.size = available

    @property
    def available(self):
        return self.size - (self.tell() - self.start)

    @property
    def offset(self):
        return self.substream.tell()

    def read(self, count=maxsize):
        avail = self.available
        if avail == 0:
            return b""
        count = min(count, avail)
        data = self.substream.read(count)
        if len(data) < count:
            raise IOError("could only read %s bytes, requested %s" % (len(data),count))
        return data

    def seekable(self):
        return True

    def seek(self, offset):
        if offset < self.start or offset > self.start + self.size:
            raise IOError("trying to seek out of bounds [%d-%d)" % (self.start, self.start + self.size))
        self.substream.seek(offset)

    def tell(self):
        return self.offset

    def tellable(self):
        return True


