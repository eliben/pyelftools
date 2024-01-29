PHDRS
{
  elf_headers PT_LOAD FILEHDR PHDRS FLAGS(PF_R) ;
  text PT_LOAD FLAGS(PF_R | PF_X) ;
  data PT_LOAD FLAGS(PF_R | PF_W) ;
  bss PT_LOAD FLAGS(PF_R | PF_W) ;
  note PT_NOTE FLAGS(PF_R) ;
}

SECTIONS
{
  .text : {
    *(.text .text.* .gnu.linkonce.t.*)
  } :text

  .rela.dyn : {
    *(.rela.dyn)
  } :text

  .bss . (NOLOAD): {
    *(.bss)
    *(COMMON)
  } :bss

  .note : ALIGN(8) {
    KEEP(*(.note.gnu*))
    KEEP(*(.note.custom))
  } :text :note

  /DISCARD/ : {
    *(.note.ABI-tag)
  }
}

