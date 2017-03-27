"""
Master Boot Record
The first sector on disk, contains the partition table, bootloader, et al.

http://www.win.tue.nl/~aeb/partitions/partition_types-1.html
"""
from construct import *


mbr_format = "mbr" / Struct(
    "bootloader_code" / HexDump(Bytes(446)),
    "partitions" / Array(4, Struct(
        "state" / Enum(Byte,
            INACTIVE = 0x00,
            ACTIVE = 0x80,
        ),
        "beginning" / BitStruct(
            "head" / Octet,
            "sect" / BitsInteger(6),
            "cyl" / BitsInteger(10),
        ),
        "type" / Enum(Byte,
            Nothing = 0x00,
            FAT12 = 0x01,
            XENIX_ROOT = 0x02,
            XENIX_USR = 0x03,
            FAT16_old = 0x04,
            Extended_DOS = 0x05,
            FAT16 = 0x06,
            FAT32 = 0x0b,
            FAT32_LBA = 0x0c,
            NTFS = 0x07,
            LINUX_SWAP = 0x82,
            LINUX_NATIVE = 0x83,
            default=Pass,
        ),
        "ending" / BitStruct(
            "head" / Octet,
            "sect" / BitsInteger(6),
            "cyl" / BitsInteger(10),
        ),
        "sector_offset" / Int32ub, # offset from MBR in sectors
        "size" / Int32ub, # in sectors
    )),
    "signature" / Const(b"\x55\xAA"),
)

