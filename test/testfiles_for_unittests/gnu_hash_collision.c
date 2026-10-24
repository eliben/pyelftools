/* Both symbol names have GNU hash 0x00597728.
 * Build with:
 * gcc -shared -fPIC -Wl,--hash-style=gnu gnu_hash_collision.c -o gnu_hash_collision.so.elf
 */
int ab(void) { return 1; }
int bA(void) { return 2; }
