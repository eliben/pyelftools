"""
Extension 2 (ext2) used in Linux systems
"""
from construct import *


Char = SLInt8
UChar = ULInt8
Short = SLInt16
UShort = ULInt16
Long = SLInt32
ULong = ULInt32

def BlockPointer(name):
    return Struct(name,
        ULong("block_number"),
        OnDemandPointer(lambda ctx: ctx["block_number"]),
    )

superblock = Struct("superblock",
    ULong('inodes_count'),
    ULong('blocks_count'),
    ULong('reserved_blocks_count'),
    ULong('free_blocks_count'),
    ULong('free_inodes_count'),
    ULong('first_data_block'),
    Enum(ULong('log_block_size'), 
        OneKB = 0,
        TwoKB = 1,
        FourKB = 2,
    ),
    Long('log_frag_size'),
    ULong('blocks_per_group'),
    ULong('frags_per_group'),
    ULong('inodes_per_group'),
    ULong('mtime'),
    ULong('wtime'),
    UShort('mnt_count'),
    Short('max_mnt_count'),
    Const(UShort('magic'), 0xEF53),
    UShort('state'),
    UShort('errors'),
    Padding(2),
    ULong('lastcheck'),
    ULong('checkinterval'),
    ULong('creator_os'),
    ULong('rev_level'),
    Padding(235 * 4),
)

group_descriptor = Struct("group_descriptor",
    ULong('block_bitmap'),
    ULong('inode_bitmap'),
    ULong('inode_table'),
    UShort('free_blocks_count'),
    UShort('free_inodes_count'),
    UShort('used_dirs_count'),
    Padding(14),
)

inode = Struct("inode",
    FlagsEnum(UShort('mode'),
        IXOTH = 0x0001,
        IWOTH = 0x0002,
        IROTH = 0x0004,
        IRWXO = 0x0007,
        IXGRP = 0x0008,
        IWGRP = 0x0010,
        IRGRP = 0x0020,
        IRWXG = 0x0038,
        IXUSR = 0x0040,
        IWUSR = 0x0080,
        IRUSR = 0x0100,
        IRWXU = 0x01C0,
        ISVTX = 0x0200,
        ISGID = 0x0400,
        ISUID = 0x0800,
        IFIFO = 0x1000,
        IFCHR = 0x2000,
        IFDIR = 0x4000,
        IFBLK = 0x6000,
        IFREG = 0x8000,
        IFLNK = 0xC000,
        IFSOCK = 0xA000,
        IFMT = 0xF000,
    ),
    UShort('uid'),
    ULong('size'),
    ULong('atime'),
    ULong('ctime'),
    ULong('mtime'),
    ULong('dtime'),
    UShort('gid'),
    UShort('links_count'),
    ULong('blocks'),
    FlagsEnum(ULong('flags'),
        SecureDelete = 0x0001,
        AllowUndelete = 0x0002,
        Compressed = 0x0004,
        Synchronous = 0x0008,
    ),
    Padding(4),
    Array(12, ULong('blocks')),
    ULong("indirect1_block"),
    ULong("indirect2_block"),
    ULong("indirect3_block"),
    ULong('version'),
    ULong('file_acl'),
    ULong('dir_acl'),
    ULong('faddr'),
    UChar('frag'),
    Byte('fsize'),
    Padding(10)   ,
)

# special inodes
EXT2_BAD_INO = 1
EXT2_ROOT_INO = 2
EXT2_ACL_IDX_INO = 3
EXT2_ACL_DATA_INO = 4
EXT2_BOOT_LOADER_INO = 5
EXT2_UNDEL_DIR_INO = 6
EXT2_FIRST_INO = 11 

directory_record = Struct("directory_entry",
    ULong("inode"),
    UShort("rec_length"),
    UShort("name_length"),
    Field("name", lambda ctx: ctx["name_length"]),
    Padding(lambda ctx: ctx["rec_length"] - ctx["name_length"])
)

if __name__ == "__main__":
    print (superblock.sizeof())



