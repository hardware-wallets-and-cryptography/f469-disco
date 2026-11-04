# Build Guide

## Development Environment

### Nix Flake + direnv (Recommended)

Requires Nix >=2.7 with flakes enabled and direnv.

After you clone the repository:

```bash
cd f469-disco
```

```bash
direnv allow
```

Environment activates automatically on entering the directory.

### nix-shell

```bash
nix develop
```

## Submodules

Initialize submodules (done automatically by make):
```bash
git submodule update --init --recursive
```

## Build Commands

Build cross-compiler (required first):
```bash
make mpy-cross
```

Firmware with frozen bitcoin lib → bin/upy-f469disco.bin
```bash
make disco
```

Minimal firmware → bin/upy-f469disco-empty.bin
```bash
make empty
```

Simulator → bin/micropython_unix
```bash
make unix
```

Run tests
```bash
make test
```

Run simulator
```bash
make simulate
```

Clean build artifacts
```bash
make clean
```

Build everything
```bash
make all
```

## Output Files

All binaries output to `bin/`:
* `upy-f469disco.bin` – full firmware
* `upy-f469disco-empty.bin` – minimal firmware
* `micropython_unix` – simulator binary
