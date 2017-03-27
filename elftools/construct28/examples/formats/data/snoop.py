"""
what : snoop v2 capture file.
 how : http://tools.ietf.org/html/rfc1761
 who : jesse@housejunkie.ca
"""

from construct import *
import time


class EpochTimeStampAdapter(Adapter):
    """ Convert epoch timestamp <-> localtime """
    def _decode(self, obj, context):
        return time.ctime(obj)
    def _encode(self, obj, context):
        return int(time.mktime(time.strptime(obj)))

packet_record = "packet_record" / Struct(
        "original_length" / Int32ub,
        "included_length" / Int32ub,
        "record_length" / Int32ub,
        "cumulative_drops" / Int32ub,
        "timestamp_seconds" / EpochTimeStampAdapter(Int32ub),
        "timestamp_microseconds" / Int32ub,
        "data" / HexDump(Bytes(this.included_length)),
        # 24 being the static length of the packet_record header
        Padding(this.record_length - this.included_length - 24),
    )

datalink_type = "datalink" / Enum(Int32ub,
        IEEE802dot3 = 0,
        IEEE802dot4 = 1,
        IEEE802dot5 = 2,
        IEEE802dot6 = 3,
        ETHERNET = 4,
        HDLC = 5,
        CHARSYNC = 6,
        IBMCHANNEL = 7,
        FDDI = 8,
        OTHER = 9,
        UNASSIGNED = 10,
    )

snoop_file = Struct(
        "signature" / Const(b"snoop\x00\x00\x00"),
        "version" / Int32ub, # snoop v1 is deprecated
        datalink_type,
        GreedyRange(packet_record),
    )

