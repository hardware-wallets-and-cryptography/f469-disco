# Reproducible builds with Nix

This repo ships a [flake.nix](./flake.nix) / [flake.lock](./flake.lock) that pins
the exact `arm-none-eabi-gcc`, `python3`, `openocd`, `stlink`, and `SDL2` versions
used to build and test the firmware.

Using Nix gives you a reproducible toolchain on both macOS and Linux. It uses the
same flake as [CI](./.github/workflows/ci.yml), so a successful local build should
also pass in CI.

Install Nix (this creates a `/nix` volume and a system daemon - see the
[Determinate Systems installer docs](https://install.determinate.systems/) for details):

```sh
curl -fsSL https://install.determinate.systems/nix | sh -s -- install
```

Open a new terminal so the Nix environment is loaded, then build and test everything with:

```sh
nix develop -c make clean
nix develop -c make all
nix develop -c make test
```

Or enter an interactive shell with all the tools on `PATH` and use `make` directly:

```sh
nix develop
make clean && make all && make test
exit
```

If you have [direnv](https://direnv.net/) installed (`brew install direnv` on macOS, hook it into
your shell, then run `direnv allow` once in this repo), the Nix environment activates
automatically whenever you `cd` into the project, since [.envrc](./.envrc) already contains
`use flake`.

If you don't want to use Nix, you can install the dependencies manually instead (see [build.md](../docs/build.md)).
