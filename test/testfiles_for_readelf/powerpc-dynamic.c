/*
 * DT_PPC_GOT shares its value (0x70000000) with DT_LOPROC. It must be
 * recognized as a PowerPC tag when reading this shared library's .dynamic.
 *
 * Build with clang and LLD:
 *   clang --target=powerpc-linux-gnu -fPIC -shared -nostdlib -fuse-ld=lld \
 *       -Wl,--hash-style=sysv powerpc-dynamic.c -o powerpc-dynamic.so.elf
 */

extern int external_function(void);

int call_external(void)
{
    return external_function();
}
