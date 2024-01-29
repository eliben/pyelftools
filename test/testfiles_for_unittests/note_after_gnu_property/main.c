#include <link.h>

// NOTE: This is a minimal test fixture that creates an ELF file with a note
// segment that has a single NOTE segment with a NT_GNU_PROPERTY_TYPE_0,
// followed by a custom note. It's used in a regression test for a buffer
// overrun bug in the parsing of the NT_GNU_PROPERTY_TYPE_0.

struct elf_note {
  ElfW(Nhdr) nhdr;  // header: 12 bytes
  char name[4];     // name buffer: 2 bytes + 2 bytes padding
  uint8_t data[8];  // data buffer: 8 bytes
};

__attribute__((section(".note.custom"), aligned(8)))
__attribute__((used))
const struct elf_note note = {
    .nhdr = {
        .n_namesz = 4,
        .n_descsz = 8,
        .n_type = 0,
    },
    .name = {'H', 'i', '\0'},
    .data = {},
};

int main() {
  return 0;
}
