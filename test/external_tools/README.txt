Some utilities that use libelf to create synthetic ELF files

readelf is built as follows:

* From binutils Git: https://sourceware.org/git/binutils-gdb.git
* git fetch --all --tags
* git checkout binutils-<VERSION>-release
* Run configure, then make
* Built on a 64-bit Ubuntu machine

To run the readelf comparisons on another architecture, build the same binutils
version with a compiler for that system. For development snapshots such as
2.47.20260726, use the corresponding binutils source snapshot rather than a
release tag. Point READELF at the resulting binutils/readelf executable:

    READELF=/path/to/build/binutils/readelf python3 test/run_readelf_tests.py --parallel

READELF overrides the default on all platforms and accepts an executable path
or a command name on PATH, without arguments. Quote paths containing spaces.
There is no need to replace the bundled binary. Other binutils versions can
produce different output and cause comparison failures.

llvm-dwarfdump is built as follows:

* Used Debian v10 on x86_64
* install gcc, git, cmake
* git clone https://github.com/llvm/llvm-project.git llvm
* cd llvm
* cmake -S llvm -B build -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release
* cmake --build build -- llvm-dwarfdump
