# Submodules

## Map

| Submodule | Remote | Fork? | Pinned commit | Describe | Branch (`branch =`) |
|-----------|--------|:-----:|---------------|----------|---------------------|
| `usermods/udisplay_f469/lvgl` | `lvgl/lvgl` | ❌ | `dd100e5` | `v6.0.2-31-gdd100e5e0` | — |
| `micropython` | `hardware-wallets-and-cryptography/micropython` | ✅ | `6bdf1b6` | `v1.10-1185-g6bdf1b691` | — |
| `usermods/secp256k1` | `hardware-wallets-and-cryptography/secp256k1-embedded` | ✅ | `0502cf4435` | `remotes/origin/secp-zkp--int` | `secp-zkp--int` |
| `usermods/secp256k1` | `hardware-wallets-and-cryptography/secp256k1-embedded` | ✅ | `0502cf4435` | `remotes/origin/secp-zkp--int` | `secp-zkp--int` |
| `usermods/secp256k1/secp256k1` | `hardware-wallets-and-cryptography/secp256k1-zkp` | ✅ | `d9560e0` | `d9560e0a` | — |
| `libs/common/embit/secp256k1/secp256k1-zkp` | `hardware-wallets-and-cryptography/secp256k1-zkp` | ✅ | `d9560e0` | `d9560e0a` | — |
| `libs/common/embit` | `hardware-wallets-and-cryptography/embit` | ✅ | `d418ef3` | `v0.8.2-4-gd418ef3` | `int` |

> **5 forked / 1 external**

> Remote `secp256k1-zkp` appears twice — under `usermods/secp256k1` and under
> `embit/secp256k1` — both from the same fork and at the same commit `d9560e0`,
> so there is no version skew between the two checkouts.

### What reaches firmware

- `micropython` — is the build
- `usermods/secp256k1` + its `secp256k1/` tree — compiled into the signing
  usermod (`usermods/secp256k1/micropython.mk`)
- `lvgl` — compiled into the display usermod
  (`usermods/udisplay_f469/micropython.mk` includes `lvgl/lvgl.mk`)
- `embit` — frozen as Python. `manifests/embit.py` walks
  `libs/common/embit/src` and skips `embit/util` (CPython-only backends —
  firmware uses the C usermod); `manifests/common.py` walks `libs/common` and
  skips `embit`, so the two do not double-freeze

The `embit/secp256k1/` checkout is a C source tree for `embit`'s own CPython
ctypes build, not a Python package. It sits next to code that does
`import secp256k1`, which under CPython would make it an implicit namespace
package; `libs/common/embit/src/embit/util/secp256k1.py` guards against that
explicitly (it keys on `from micropython import const`). It is outside every
freeze root, so it never reaches firmware.

## Verify pin and drift for each submodule

For each, fetch the row's `--remote` target (its `branch =`, or the fork's
default branch when none is set), then compare `HEAD` to the pin and count
commits of drift:

| Submodule | Target | Pin | Command |
|-----------|--------|-----|---------|
| `usermods/udisplay_f469/lvgl` | `master` (default) | `dd100e5` | `git -C usermods/udisplay_f469/lvgl fetch origin master -q; git -C usermods/udisplay_f469/lvgl rev-parse --short HEAD; git -C usermods/udisplay_f469/lvgl rev-list --count dd100e5..origin/master` |
| `micropython` | `master` (default) | `6bdf1b6` | `git -C micropython fetch origin master -q; git -C micropython rev-parse --short HEAD; git -C micropython rev-list --count 6bdf1b6..origin/master` |
| `usermods/secp256k1` | `secp-zkp--int` | `0502cf4435` | `git -C usermods/secp256k1 fetch origin secp-zkp--int -q; git -C usermods/secp256k1 rev-parse --short HEAD; git -C usermods/secp256k1 rev-list --count 0502cf4435..origin/secp-zkp--int` |
| `usermods/secp256k1/secp256k1` | `master` (default) | `d9560e0` | `git -C usermods/secp256k1/secp256k1 fetch origin master -q; git -C usermods/secp256k1/secp256k1 rev-parse --short HEAD; git -C usermods/secp256k1/secp256k1 rev-list --count d9560e0..origin/master` |
| `libs/common/embit/secp256k1/secp256k1-zkp` | `master` (default) | `d9560e0` | `git -C libs/common/embit/secp256k1/secp256k1-zkp fetch origin master -q; git -C libs/common/embit/secp256k1/secp256k1-zkp rev-parse --short HEAD; git -C libs/common/embit/secp256k1/secp256k1-zkp rev-list --count d9560e0..origin/master` |
| `libs/common/embit` | `int` | `d418ef3` | `git -C libs/common/embit fetch origin int -q; git -C libs/common/embit rev-parse --short HEAD; git -C libs/common/embit rev-list --count d418ef3..origin/int` |

Each command has three parts, reading its output line by line:

```sh
git -C <path> fetch origin <branch> -q
# no output — just refreshes the local view of the remote

git -C <path> rev-parse --short HEAD
# should print the pin itself; any other value means HEAD has moved,
# including an unstaged pin change

git -C <path> rev-list --count <pin>..origin/<branch>
# drift: commits past the pin on that target;
# 0 means the pin currently sits at the head of its --remote target,
# not that it's protected from future pushes
```

## Reproducibility

**What is guaranteed.** Every entry above is pinned by commit hash in this
repo's tree (a gitlink), not by branch. A fresh

```sh
git clone --recursive https://github.com/hardware-wallets-and-cryptography/f469-disco.git
```

resolves the exact same trees, regardless of who owns each remote. The `Makefile`
reinforces this — the `mpy-cross/Makefile` and `embit/src/embit/__init__.py`
guard rules run

```make
git submodule update --init --recursive
```

with **no `--remote`**, so a build always honours the recorded hashes.

**What `--remote` does.** Nothing during a normal clone or build. Only
`git submodule update --remote` reads branches: it moves a submodule to the head
of its `branch =`, or of the remote's default branch (`origin/HEAD`) when no
`branch =` is set, and stages a new gitlink. Omitting `branch =` therefore does
not opt a submodule out — it just targets the default branch. With
`--recursive`, nested submodules move too. That is the drift footgun: it
silently replaces a verified tree with an untested one. As of 2026-09-25:

| Submodule | `--remote` target | Target head | Commits past pin |
|---|---|---|---|
| `micropython` | `master` (default) | `6bdf1b6` | 0 |
| `embit` | `int` | `d418ef3` | 0 |
| `secp256k1-embedded` | `secp-zkp--int` | `0502cf4435` | 0 |
| `lvgl` | `master` (default) | `d3c5b41` | **10203** |
| `embit/secp256k1/secp256k1-zkp` | `master` (default, fork) | `037cc6d` | **1949** |
| `usermods/secp256k1/secp256k1` | `master` (default, fork) | `037cc6d` | **1949** |

So a single `--remote --recursive` would swap the display stack (lvgl `v9.x`
over the pinned `v6.0.2`) and both `secp256k1-zkp` trees — including the one
compiled into the signing usermod. Even lvgl's `release/v6` is 490 commits past
`dd100e5` (`1f707f9`, 2025-08-14, vs 2019-10-29). The zero rows sit on their
pins by timing, not by guarantee.

Avoid `--remote`. To move a pin, do it explicitly:

```sh
git submodule sync --recursive
git -C <path> fetch origin <branch>
git -C <path> checkout <full-sha>
git -C <path> submodule sync --recursive
git -C <path> submodule update --init --recursive
git add <path>
```

**Verifying a checkout matches the pins**

```sh
git submodule status --recursive
```

Every line must start with a **space**. A leading `+` means the checkout differs
from the recorded gitlink, `-` means uninitialized, `U` means conflicts. This
compares against the **index**, so a staged-but-uncommitted pin also shows a
space; use `git diff --cached --submodule=short` to see pins that differ from
`HEAD`. Also check for drift inside submodules:

```sh
git -C micropython                 status --short   # expect empty
git -C libs/common/embit           status --short   # expect empty
git -C usermods/secp256k1          status --short   # expect empty
git -C usermods/udisplay_f469/lvgl status --short   # expect empty
```

Untracked content inside a submodule is not harmless here: `manifests/common.py`
and `manifests/embit.py` walk whole directory trees and freeze every `.py` they
find, so stray files can end up compiled into firmware or break the build.

**Local remote URLs.** All four top-level `.url` entries in `.git/config` match
`.gitmodules`, and both nested `secp256k1-zkp` entries (under `embit` and under
`usermods/secp256k1`) match their repos' `.gitmodules` (the fork). Re-check after
any `.gitmodules` edit, here or in a submodule — an already-initialised checkout
keeps the old URL until synced:

```sh
git config --get-regexp '^submodule\..*\.url'
git -C libs/common/embit  config --get-regexp '^submodule\..*\.url'
git -C usermods/secp256k1 config --get-regexp '^submodule\..*\.url'
git submodule sync --recursive
```

This never affects a pin, only where a re-fetch goes.

**What can still break reproducibility.** The pins are only as durable as the
remotes and branches hosting them. For the one external remote, `lvgl/lvgl`,
repository deletion (or tag removal plus force-push of every containing branch)
upstream would make a fresh `--recursive`
clone fail, and the pinned objects would then survive only in existing local
clones. It is C source that reaches firmware.

Forks are not immune: a pin reachable from only one branch is orphaned if that
branch is force-pushed past it.

| Pin | Reachable from |
|---|---|
| `d418ef3` (embit) | `int` only |
| `0502cf4435` (secp256k1-embedded) | `secp-zkp--int` only |
| `6bdf1b6` (micropython) | fork `master` |
| `d9560e0` (secp256k1-zkp) | fork `master` + `dev` + `int` |
| `dd100e5` (lvgl) | `master` + every `release/v6`…`v9.6` (33 branches) + 56 tags (e.g. `v6.1`) |

None of the pins is currently an orphaned commit reachable only by hash. The
`lvgl` pin is contained in upstream tags, so a single branch rewrite cannot orphan
it — only repository deletion can. Tagging the single-branch pins in their forks
would give them the same protection.
