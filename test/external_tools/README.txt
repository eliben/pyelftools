Some utilities that use libelf to create synthetic ELF files

readelf is built as follows:

* From binutils Git: https://sourceware.org/git/binutils-gdb.git
* git fetch --all --tags
* git co binutils-<VERSION>-branch
* Run configure, then make
* Built on a 64-bit Ubuntu machine
