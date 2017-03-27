"""
Portable Executable (PE) 32 bit, little endian
Used on MSWindows systems (including DOS) for EXEs and DLLs

1999 paper:
http://download.microsoft.com/download/1/6/1/161ba512-40e2-4cc9-843a-923143f3456c/pecoff.doc

2006 with updates relevant for .NET:
http://download.microsoft.com/download/9/c/5/9c5b2167-8017-4bae-9fde-d599bac8184a/pecoff_v8.doc
"""
import time

from construct import *


class UTCTimeStampAdapter(Adapter):
    def _decode(self, obj, context):
        return time.ctime(obj)
    def _encode(self, obj, context):
        return int(time.mktime(time.strptime(obj)))

def UTCTimeStamp(name):
    return UTCTimeStampAdapter(ULInt32(name))

class NamedSequence(Adapter):
    """
    creates a mapping between the elements of a sequence and their respective
    names. this is useful for sequences of a variable length, where each
    element in the sequence has a name (as is the case with the data 
    directories of the PE header)
    """
    __slots__ = ["mapping", "rev_mapping"]
    prefix = "unnamed_"
    def __init__(self, subcon, mapping):
        super(NamedSequence, self).__init__(subcon)
        self.mapping = mapping
        self.rev_mapping = dict((v, k) for k, v in mapping.items())
    def _encode(self, obj, context):
        d = obj.__dict__
        obj2 = [None] * len(d)
        for name, value in d.items():
            if name in self.rev_mapping:
                index = self.rev_mapping[name]
            elif name.startswith("__"):
                obj2.pop(-1)
                continue
            elif name.startswith(self.prefix):
                index = int(name.split(self.prefix)[1])
            else:
                raise ValueError("no mapping defined for %r" % (name,))
            obj2[index] = value
        return obj2
    def _decode(self, obj, context):
        obj2 = Container()
        for i, item in enumerate(obj):
            if i in self.mapping:
                name = self.mapping[i]
            else:
                name = "%s%d" % (self.prefix, i)
            setattr(obj2, name, item)
        return obj2


msdos_header = Struct("msdos_header",
    Const(b"MZ"),
    ULInt16("partPag"),
    ULInt16("page_count"),
    ULInt16("relocation_count"),
    ULInt16("header_size"),
    ULInt16("minmem"),
    ULInt16("maxmem"),
    ULInt16("relocation_stackseg"),
    ULInt16("exe_stackptr"),
    ULInt16("checksum"),
    ULInt16("exe_ip"),
    ULInt16("relocation_codeseg"),
    ULInt16("table_offset"),
    ULInt16("overlay"),
    Padding(8),
    ULInt16("oem_id"),
    ULInt16("oem_info"),
    Padding(20),
    ULInt32("coff_header_pointer"),
    Anchor("_assembly_start"),
    OnDemand(
        HexDumpAdapter(
            Field("code", 
                lambda ctx: ctx.coff_header_pointer - ctx._assembly_start
            )
        )
    ),
)

symbol_table = Struct("symbol_table",
    String("name", 8, padchar = b"\x00"),
    ULInt32("value"),
    Enum(ExprAdapter(SLInt16("section_number"),
            encoder = lambda obj, ctx: obj + 1,
            decoder = lambda obj, ctx: obj - 1,
        ),
        UNDEFINED = -1,
        ABSOLUTE = -2,
        DEBUG = -3,
        _default_ = Pass,
    ),
    Enum(ULInt8("complex_type"),
        NULL = 0,
        POINTER = 1,
        FUNCTION = 2,
        ARRAY = 3,
    ),
    Enum(ULInt8("base_type"),
        NULL = 0,
        VOID = 1,
        CHAR = 2,
        SHORT = 3,
        INT = 4,
        LONG = 5,
        FLOAT = 6,
        DOUBLE = 7,
        STRUCT = 8,
        UNION = 9,
        ENUM = 10,
        MOE = 11,
        BYTE = 12,
        WORD = 13,
        UINT = 14,
        DWORD = 15,
    ),
    Enum(ULInt8("storage_class"),
        END_OF_FUNCTION = 255,
        NULL = 0,
        AUTOMATIC = 1,
        EXTERNAL = 2,
        STATIC = 3,
        REGISTER = 4,
        EXTERNAL_DEF = 5,
        LABEL = 6,
        UNDEFINED_LABEL = 7,
        MEMBER_OF_STRUCT = 8,
        ARGUMENT = 9,
        STRUCT_TAG = 10,
        MEMBER_OF_UNION = 11,
        UNION_TAG = 12,
        TYPE_DEFINITION = 13,
        UNDEFINED_STATIC = 14,
        ENUM_TAG = 15,
        MEMBER_OF_ENUM = 16,
        REGISTER_PARAM = 17,
        BIT_FIELD = 18,
        BLOCK = 100,
        FUNCTION = 101,
        END_OF_STRUCT = 102,
        FILE = 103,
        SECTION = 104,
        WEAK_EXTERNAL = 105,
    ),
    ULInt8("number_of_aux_symbols"),
    Array(lambda ctx: ctx.number_of_aux_symbols,
        Bytes("aux_symbols", 18)
    )
)

coff_header = Struct("coff_header",
    Const(b"PE\x00\x00"),
    Enum(ULInt16("machine_type"),
        UNKNOWN = 0x0,
        AM33 = 0x1d3,
        AMD64 = 0x8664,
        ARM = 0x1c0,
        EBC = 0xebc,
        I386 = 0x14c,
        IA64 = 0x200,
        M32R = 0x9041,
        MIPS16 = 0x266,
        MIPSFPU = 0x366,
        MIPSFPU16 = 0x466,
        POWERPC = 0x1f0,
        POWERPCFP = 0x1f1,
        R4000 = 0x166,
        SH3 = 0x1a2,
        SH3DSP = 0x1a3,
        SH4 = 0x1a6,
        SH5= 0x1a8,
        THUMB = 0x1c2,
        WCEMIPSV2 = 0x169,
        _default_ = Pass
    ),
    ULInt16("number_of_sections"),
    UTCTimeStamp("time_stamp"),
    ULInt32("symbol_table_pointer"),
    ULInt32("number_of_symbols"),
    ULInt16("optional_header_size"),
    FlagsEnum(ULInt16("characteristics"),
        RELOCS_STRIPPED = 0x0001,
        EXECUTABLE_IMAGE = 0x0002,
        LINE_NUMS_STRIPPED = 0x0004,
        LOCAL_SYMS_STRIPPED = 0x0008,
        AGGRESSIVE_WS_TRIM = 0x0010,
        LARGE_ADDRESS_AWARE = 0x0020,
        MACHINE_16BIT = 0x0040,
        BYTES_REVERSED_LO = 0x0080,
        MACHINE_32BIT = 0x0100,
        DEBUG_STRIPPED = 0x0200,
        REMOVABLE_RUN_FROM_SWAP = 0x0400,
        SYSTEM = 0x1000,
        DLL = 0x2000,
        UNIPROCESSOR_ONLY = 0x4000,
        BIG_ENDIAN_MACHINE = 0x8000,
    ),
    
    # symbol table
    Pointer(lambda ctx: ctx.symbol_table_pointer,
        Array(lambda ctx: ctx.number_of_symbols, symbol_table)
    )
)

def PEPlusField(name):
    return IfThenElse(name, lambda ctx: ctx.pe_type == "PE32_plus",
        ULInt64(None),
        ULInt32(None),
    )

optional_header = Struct("optional_header",
    # standard fields
    Enum(ULInt16("pe_type"),
        PE32 = 0x10b,
        PE32_plus = 0x20b,
    ),
    ULInt8("major_linker_version"),
    ULInt8("minor_linker_version"),
    ULInt32("code_size"),
    ULInt32("initialized_data_size"),
    ULInt32("uninitialized_data_size"),
    ULInt32("entry_point_pointer"),
    ULInt32("base_of_code"),
    
    # only in PE32 files
    If(lambda ctx: ctx.pe_type == "PE32",
        ULInt32("base_of_data")
    ),
    
    # WinNT-specific fields
    PEPlusField("image_base"),
    ULInt32("section_aligment"),
    ULInt32("file_alignment"),
    ULInt16("major_os_version"),
    ULInt16("minor_os_version"),
    ULInt16("major_image_version"),
    ULInt16("minor_image_version"),
    ULInt16("major_subsystem_version"),
    ULInt16("minor_subsystem_version"),
    Padding(4),
    ULInt32("image_size"),
    ULInt32("headers_size"),
    ULInt32("checksum"),
    Enum(ULInt16("subsystem"),
        UNKNOWN = 0,
        NATIVE = 1,
        WINDOWS_GUI = 2,
        WINDOWS_CUI = 3,
        POSIX_CIU = 7,
        WINDOWS_CE_GUI = 9,
        EFI_APPLICATION = 10,
        EFI_BOOT_SERVICE_DRIVER = 11,
        EFI_RUNTIME_DRIVER = 12,
        EFI_ROM = 13,
        XBOX = 14,
        _default_ = Pass
    ),
    FlagsEnum(ULInt16("dll_characteristics"),
        NO_BIND = 0x0800,
        WDM_DRIVER = 0x2000,
        TERMINAL_SERVER_AWARE = 0x8000,
    ),
    PEPlusField("reserved_stack_size"),
    PEPlusField("stack_commit_size"),
    PEPlusField("reserved_heap_size"),
    PEPlusField("heap_commit_size"),
    ULInt32("loader_flags"),
    ULInt32("number_of_data_directories"),
    
    NamedSequence(
        Array(lambda ctx: ctx.number_of_data_directories,
            Struct("data_directories",
                ULInt32("address"),
                ULInt32("size"),
            )
        ),
        mapping = {
            0 : 'export_table',
            1 : 'import_table',
            2 : 'resource_table',
            3 : 'exception_table',
            4 : 'certificate_table',
            5 : 'base_relocation_table',
            6 : 'debug',
            7 : 'architecture',
            8 : 'global_ptr',
            9 : 'tls_table',
            10 : 'load_config_table',
            11 : 'bound_import',
            12 : 'import_address_table',
            13 : 'delay_import_descriptor',
            14 : 'complus_runtime_header',
        }
    ),
)

section = Struct("section",
    String("name", 8, padchar = b"\x00"),
    ULInt32("virtual_size"),
    ULInt32("virtual_address"),
    ULInt32("raw_data_size"),
    ULInt32("raw_data_pointer"),
    ULInt32("relocations_pointer"),
    ULInt32("line_numbers_pointer"),
    ULInt16("number_of_relocations"),
    ULInt16("number_of_line_numbers"),
    FlagsEnum(ULInt32("characteristics"),
        TYPE_REG = 0x00000000,
        TYPE_DSECT = 0x00000001,
        TYPE_NOLOAD = 0x00000002,
        TYPE_GROUP = 0x00000004,
        TYPE_NO_PAD = 0x00000008,
        TYPE_COPY = 0x00000010,
        CNT_CODE = 0x00000020,
        CNT_INITIALIZED_DATA = 0x00000040,
        CNT_UNINITIALIZED_DATA = 0x00000080,
        LNK_OTHER = 0x00000100,
        LNK_INFO = 0x00000200,
        TYPE_OVER = 0x00000400,
        LNK_REMOVE = 0x00000800,
        LNK_COMDAT = 0x00001000,
        MEM_FARDATA = 0x00008000,
        MEM_PURGEABLE = 0x00020000,
        MEM_16BIT = 0x00020000,
        MEM_LOCKED = 0x00040000,
        MEM_PRELOAD = 0x00080000,
        ALIGN_1BYTES = 0x00100000,
        ALIGN_2BYTES = 0x00200000,
        ALIGN_4BYTES = 0x00300000,
        ALIGN_8BYTES = 0x00400000,
        ALIGN_16BYTES = 0x00500000,
        ALIGN_32BYTES = 0x00600000,
        ALIGN_64BYTES = 0x00700000,
        ALIGN_128BYTES = 0x00800000,
        ALIGN_256BYTES = 0x00900000,
        ALIGN_512BYTES = 0x00A00000,
        ALIGN_1024BYTES = 0x00B00000,
        ALIGN_2048BYTES = 0x00C00000,
        ALIGN_4096BYTES = 0x00D00000,
        ALIGN_8192BYTES = 0x00E00000,
        LNK_NRELOC_OVFL = 0x01000000,
        MEM_DISCARDABLE = 0x02000000,
        MEM_NOT_CACHED = 0x04000000,
        MEM_NOT_PAGED = 0x08000000,
        MEM_SHARED = 0x10000000,
        MEM_EXECUTE = 0x20000000,
        MEM_READ = 0x40000000,
        MEM_WRITE = 0x80000000,        
    ),
    
    OnDemandPointer(lambda ctx: ctx.raw_data_pointer,
        HexDumpAdapter(Field("raw_data", lambda ctx: ctx.raw_data_size))
    ),
    
    OnDemandPointer(lambda ctx: ctx.line_numbers_pointer,
        Array(lambda ctx: ctx.number_of_line_numbers,
            Struct("line_numbers",
                ULInt32("type"),
                ULInt16("line_number"),
            )
        )
    ),
    
    OnDemandPointer(lambda ctx: ctx.relocations_pointer,
        Array(lambda ctx: ctx.number_of_relocations,
            Struct("relocations",
                ULInt32("virtual_address"),
                ULInt32("symbol_table_index"),
                ULInt16("type"),
            )
        )
    ),
)

pe32_file = Struct("pe32_file",
    # headers
    msdos_header,
    coff_header,
    Anchor("_start_of_optional_header"),
    optional_header,
    Anchor("_end_of_optional_header"),
    Padding(lambda ctx: min(0, 
            ctx.coff_header.optional_header_size - 
            ctx._end_of_optional_header +
            ctx._start_of_optional_header
        )
    ),
    
    # sections
    Array(lambda ctx: ctx.coff_header.number_of_sections, section)   
)


if __name__ == "__main__":
    print (pe32_file.parse_stream(open("../../../tests/NOTEPAD.EXE", "rb")))
    print (pe32_file.parse_stream(open("../../../tests/sqlite3.dll", "rb")))











