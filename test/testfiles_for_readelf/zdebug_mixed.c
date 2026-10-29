/* objcopy leaves a section uncompressed, under its .debug_ name, when
   compression would not make it smaller. Here that happens to .debug_line_str
   and .debug_loclists:

   gcc -O2 -g -shared -fPIC -nostdlib -Wl,-z,noseparate-code -o zdebug_mixed.so zdebug_mixed.c
   objcopy --compress-debug-sections=zlib-gnu zdebug_mixed.so zdebug_mixed.so.elf
*/
__attribute__((cold)) int cold_path(int x)
{
  return x * 3;
}

int hot_path(int x)
{
  return x > 100 ? cold_path(x) : x + 1;
}
