#include <link.h>

// NOTE: This is a minimal test fixture that creates an ELF file with a note
// segment that has an 8-byte alignment requirement, causing additional padding
// to be added after the note data.

struct elf_note {
  ElfW(Nhdr) nhdr;  // header: 12 bytes
  char name[4];     // name buffer: 2 bytes + 2 bytes padding
  uint8_t data[4];  // data buffer: 1 bytes + 3 bytes padding
  // Due to the 8-byte alignment of the .note segment,
  // an additional 4 bytes of padding is added here:
  uint8_t pad[4];   // pad segment to 8 bytes
};

__attribute__((section(".note.custom"), aligned(8)))
__attribute__((used))
const struct elf_note note = {
    .nhdr = {
        .n_namesz = 4,
        .n_descsz = 1,
        .n_type = 0,
    },
    .name = {'H', 'i', '\0'},
    .data = {'\x55'},
};

int main() {
  return 0;
}
