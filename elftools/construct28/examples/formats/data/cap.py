"""
tcpdump capture file
"""
from construct import *
import time, datetime


class MicrosecAdapter(Adapter):
    def _decode(self, obj, context):
        return datetime.datetime.fromtimestamp(obj[0] + obj[1] / 1000000.0)
    def _encode(self, obj, context):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return [int((obj - epoch).total_seconds()), 0]

        # offset = time.mktime(*obj.timetuple())
        # sec = int(offset)
        # usec = (offset - sec) * 1000000
        # return (sec, usec)

packet = Struct(
    "time" / MicrosecAdapter(Int32ul >> Int32ul),
    "length" / Int32ul,
    Padding(4),
    "data" / HexDump(Bytes(this.length)),
)

cap_file = Struct(
    Padding(24),
    "packets" / GreedyRange(packet),
)

print("WARNING: header is skipped not parsed, datetime can be wrong")
print("https://wiki.wireshark.org/Development/LibpcapFileFormat")

