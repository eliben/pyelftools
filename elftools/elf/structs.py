from ..construct import (
    UBInt8, UBInt16, UBInt32, UBInt64,
    ULInt8, ULInt16, ULInt32, ULInt64,
    SBInt32, SLInt32, SBInt64, SLInt64,
    Struct, Array, Enum, Padding,
    )

from .enums import *


class ELFStructs(object):
    def __init__(self, little_endian=True, elfclass=32):
        assert elfclass == 32 or elfclass == 64
        self.little_endian = little_endian
        self.elfclass = elfclass        
        self._create_structs()
    
    def _create_structs(self):
        if self.little_endian:
            self.Elf_byte = ULInt8
            self.Elf_half = ULInt16
            self.Elf_word = ULInt32
            self.Elf_addr = ULInt32 if self.elfclass == 32 else ULInt64
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = SLInt32
            self.Elf_xword = ULInt32 if self.elfclass == 32 else ULInt64
            self.Elf_sxword = SLInt32 if self.elfclass == 32 else SLInt64
        else:
            self.Elf_byte = UBInt8
            self.Elf_half = UBInt16
            self.Elf_word = UBInt32
            self.Elf_addr = UBInt32 if self.elfclass == 32 else UBInt64
            self.Elf_offset = self.Elf_addr
            self.Elf_sword = SBInt32
            self.Elf_xword = UBInt32 if self.elfclass == 32 else UBInt64
            self.Elf_sxword = SBInt32 if self.elfclass == 32 else SBInt64
        
        self._create_ehdr()
        self._create_shdr()
        self._create_sym()
    
    def _create_ehdr(self):
        self.Elf_Ehdr = Struct('Elf_Ehdr',
            Struct('e_ident',
                Array(4, self.Elf_byte('EI_MAG')),
                Enum(self.Elf_byte('EI_CLASS'), **ENUM_EI_CLASS),
                Enum(self.Elf_byte('EI_DATA'), **ENUM_EI_DATA),
                Enum(self.Elf_byte('EI_VERSION'), **ENUM_E_VERSION),
                Padding(9)                
            ),
            Enum(self.Elf_half('e_type'), **ENUM_E_TYPE),
            Enum(self.Elf_half('e_machine'), **ENUM_E_MACHINE),
            Enum(self.Elf_word('e_version'), **ENUM_E_VERSION),
            self.Elf_addr('e_entry'),
            self.Elf_offset('e_phoff'),
            self.Elf_offset('e_shoff'),
            self.Elf_word('e_flags'),
            self.Elf_half('e_ehsize'),
            self.Elf_half('e_phentsize'),
            self.Elf_half('e_phnum'),
            self.Elf_half('e_shentsize'),
            self.Elf_half('e_shnum'),
            self.Elf_half('e_shstrndx'),
        )
    
    def _create_shdr(self):
        self.Elf_Shdr = Struct('Elf_Shdr',
            self.Elf_word('sh_name'),
            Enum(self.Elf_word('sh_type'), **ENUM_SH_TYPE),
            self.Elf_xword('sh_flags'),
            self.Elf_addr('sh_addr'),
            self.Elf_offset('sh_offset'),
            self.Elf_xword('sh_size'),
            self.Elf_word('sh_link'),
            self.Elf_word('sh_info'),
            self.Elf_xword('sh_addralign'),
            self.Elf_xword('sh_entsize'),
        )
    
    def _create_sym(self):
        if self.elfclass == 32:
            self.Elf_Sym = Struct('Elf_Sym',
                self.Elf_word('st_name'),
                self.Elf_addr('st_value'),
                self.Elf_word('st_size'),
                self.Elf_byte('st_info'),
                self.Elf_byte('st_other'),
                self.Elf_half('st_shndx'),
            )
        else:
            self.Elf_Sym = Struct('Elf_Sym',
                self.Elf_word('st_name'),
                self.Elf_byte('st_info'),
                self.Elf_byte('st_other'),
                self.Elf_half('st_shndx'),
                self.Elf_addr('st_value'),
                self.Elf_xword('st_size'),
            )



