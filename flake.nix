{
  description = "Specter DIY development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.05";
    flake-utils.url = "github:numtide/flake-utils";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-utils,  ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = [ 
            pkgs.buildPackages.gcc-arm-embedded-9
            # embit needs >=3.10; micropython/tools/pydfu.py:71 uses inspect.getargspec, removed in 3.11.
            pkgs.buildPackages.python310
            pkgs.openocd
            pkgs.stlink
            pkgs.SDL2
          ];
          hardeningDisable = ["all"];
        };
      });
}
