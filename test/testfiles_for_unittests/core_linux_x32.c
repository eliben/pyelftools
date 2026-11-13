/* Source of the process dumped in core_linux_x32.elf, an x32 core.
 *
 * Build:  gcc -mx32 -O1 -o x32crash core_linux_x32.c
 *
 * Dump the core: ./x32crash foo bar
 *
 */
int main(void)
{
    *(volatile int *)0 = 0;
    return 0;
}
