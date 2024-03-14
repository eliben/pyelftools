gcc -g -o debuglink debuglink.c
objcopy --only-keep-debug debuglink debuglink.debug
strip --strip-all debuglink
objcopy --add-gnu-debuglink=debuglink.debug debuglink