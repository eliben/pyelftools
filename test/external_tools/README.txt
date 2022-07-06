Some utilities that use libelf to create synthetic ELF files

readelf is built as follows:

* From binutils Git: https://sourceware.org/git/binutils-gdb.git
* git fetch --all --tags
* git co binutils-<VERSION>-branch
* Run configure, then make
* Built on a 64-bit Ubuntu machine

llvm-dwarfdump is built as follows:

* Used Debian v10 on x86_64
* install gcc, git, cmake
* git clone https://github.com/llvm/llvm-project.git llvm
* cd llvm
* cmake -S llvm -B build -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
* cmake --build build -- llvm-dwarfdump
