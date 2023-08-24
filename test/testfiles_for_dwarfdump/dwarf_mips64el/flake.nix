{
  description = "A flake for building a mips64el .o file for testing pyelftools";

  inputs.nixpkgs.url = github:NixOS/nixpkgs/nixos-23.05;

  outputs = { self, nixpkgs }: {

    defaultPackage.x86_64-linux =
      with (import nixpkgs { system = "x86_64-linux"; }).pkgsCross.mips64el-linux-gnuabi64;
      stdenv.mkDerivation {
        name = "dwarf_mips64el";
        src = self;
        buildPhase = "$CC -g -c ./dwarf_mips64el.c";
        installPhase = "mkdir -p $out; cp dwarf_mips64el.o $out/";
      };

  };
}
