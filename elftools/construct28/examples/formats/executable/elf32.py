"""
Executable and Linkable Format (ELF), 32 bit, big or little endian.
Used on *nix systems as a replacement of the older a.out format.

Big-endian support kindly submitted by Craig McQueen (mcqueen-c#edsrd1!yzk!co!jp).
"""
from construct import *


def elf32_body(ElfInt16, ElfInt32):
    elf32_program_header = Struct("program_header",
        Enum(ElfInt32("type"),
            NULL = 0,
            LOAD = 1,
            DYNAMIC = 2,
            INTERP = 3,
            NOTE = 4,
            SHLIB = 5,
            PHDR = 6,
            _default_ = Pass,
        ),
        ElfInt32("offset"),
        ElfInt32("vaddr"),
        ElfInt32("paddr"),
        ElfInt32("file_size"),
        ElfInt32("mem_size"),
        ElfInt32("flags"),
        ElfInt32("align"),
    )
    
    elf32_section_header = Struct("section_header",
        ElfInt32("name_offset"),
        Pointer(lambda ctx: ctx._.strtab_data_offset + ctx.name_offset,
            CString("name")
        ),
        Enum(ElfInt32("type"), 
            NULL = 0,
            PROGBITS = 1,
            SYMTAB = 2,
            STRTAB = 3,
            RELA = 4,
            HASH = 5,
            DYNAMIC = 6,
            NOTE = 7,
            NOBITS = 8,
            REL = 9,
            SHLIB = 10,
            DYNSYM = 11,
            _default_ = Pass,
        ),
        ElfInt32("flags"),
        ElfInt32("addr"),
        ElfInt32("offset"),
        ElfInt32("size"),
        ElfInt32("link"),
        ElfInt32("info"),
        ElfInt32("align"),
        ElfInt32("entry_size"),
        OnDemandPointer(lambda ctx: ctx.offset,
            HexDumpAdapter(Field("data", lambda ctx: ctx.size))
        ),
    )
    
    return Struct("body",
        Enum(ElfInt16("type"),
            NONE = 0,
            RELOCATABLE = 1,
            EXECUTABLE = 2,
            SHARED = 3,
            CORE = 4,
        ),
        Enum(ElfInt16("machine"),
            NONE = 0,
            M32 = 1,
            SPARC = 2,
            I386 = 3,
            Motorolla68K = 4,
            Motorolla88K = 5,
            Intel860 = 7,
            MIPS = 8,
            _default_ = Pass
        ),
        ElfInt32("version"),
        ElfInt32("entry"),
        ElfInt32("ph_offset"),
        ElfInt32("sh_offset"),
        ElfInt32("flags"),
        ElfInt16("header_size"),
        ElfInt16("ph_entry_size"),
        ElfInt16("ph_count"),
        ElfInt16("sh_entry_size"),
        ElfInt16("sh_count"),
        ElfInt16("strtab_section_index"),
        
        # calculate the string table data offset (pointer arithmetics)
        # ugh... anyway, we need it in order to read the section names, later on
        Pointer(lambda ctx: 
            ctx.sh_offset + ctx.strtab_section_index * ctx.sh_entry_size + 16,
            ElfInt32("strtab_data_offset"),
        ),
        
        # program header table
        Rename("program_table",
            Pointer(lambda ctx: ctx.ph_offset,
                Array(lambda ctx: ctx.ph_count,
                    elf32_program_header
                )
            )
        ),
        
        # section table
        Rename("sections", 
            Pointer(lambda ctx: ctx.sh_offset,
                Array(lambda ctx: ctx.sh_count,
                    elf32_section_header
                )
            )
        ),    
    )

elf32_body_little_endian = elf32_body(ULInt16, ULInt32)
elf32_body_big_endian = elf32_body(UBInt16, UBInt32)

elf32_file = Struct("elf32_file",
    Struct("identifier",
        Const(b"\x7fELF"),
        Enum(Byte("file_class"),
            NONE = 0,
            CLASS32 = 1,
            CLASS64 = 2,
        ),
        Enum(Byte("encoding"),
            NONE = 0,
            LSB = 1,
            MSB = 2,            
        ),
        Byte("version"),
        Padding(9),
    ),
    Embedded(IfThenElse("body", lambda ctx: ctx.identifier.encoding == "LSB",
        elf32_body_little_endian,
        elf32_body_big_endian,
    )),
)


if __name__ == "__main__":
    obj = elf32_file.parse_stream(open("../../../tests/_ctypes_test.so", "rb"))
    #[s.data.value for s in obj.sections]
    print(obj)



