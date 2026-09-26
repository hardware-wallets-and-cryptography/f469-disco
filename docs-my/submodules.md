# Submodules

## Map

Single source of truth for pins.  
Forks live under `hardware-wallets-and-cryptography/`.  
Drift snapshot as of `2026-09-26`.  

| Submodule | Remote | Fork | Pin | Describe | `--remote` target | Drift past pin | Pin reachable from | Firmware |
|---|---|:-:|---|---|---|---|---|:-:|
| `micropython` | `micropython` | ✅ | `6bdf1b6` | `v1.10-1185-g6bdf1b691` | `master` (default) | 0 | fork `master` | ✅ |
| `usermods/secp256k1` | `secp256k1-embedded` | ✅ | `0502cf4` | — | `secp-zkp--int` (`branch =`) | 0 | `secp-zkp--int` only | ✅ |
| `usermods/secp256k1/secp256k1` | `secp256k1-zkp` | ✅ | `d9560e0` | — | `master` (default) | **1949** (→ `037cc6d`) | `master`, `dev`, `int` | ✅ |
| `usermods/udisplay_f469/lvgl` | `lvgl/lvgl` | ❌ | `dd100e5` | `v6.0.2-31-gdd100e5e0` | `master` (default) | **10204** (→ v9.x) | `master`, 33 `release/*`, 56 tags | ✅ |
| `libs/common/embit` | `embit` | ✅ | `d418ef3` | `v0.8.2-4-gd418ef3` | `int` (`branch =`) | 0 | `int` only | ✅ |
| `libs/common/embit/secp256k1/secp256k1-zkp` | `secp256k1-zkp` | ✅ | `d9560e0` | — | `master` (default) | **1949** (→ `037cc6d`) | `master`, `dev`, `int` | ❌ |

> **5 forked**  
> **1 external**

> Remote `secp256k1-zkp` appears twice:
> - under `usermods/secp256k1`  
> - under `libs/common/embit/secp256k1`  
> Both from the same fork and at the same commit `d9560e0`, so there is no version skew
> between the two checkouts.  
> **Keep the two in step when bumping.**

### What reaches the device

**Firmware** (`make disco`; paths relative to repo root):

- `micropython` — the build (`make -C micropython/ports/stm32`)
- `usermods/secp256k1` + its `secp256k1/` tree — compiled into the
  signing usermod (`USER_C_MODULES=usermods`)
- `usermods/udisplay_f469/lvgl` — compiled into the display usermod
  (its `micropython.mk` includes `lvgl/lvgl.mk`)
- `libs/common/embit` — frozen as Python. Chain:
  `manifests/disco.py` → `empty.py` + `common.py` → `embit.py`. `embit.py`
  walks `embit/src` and skips `embit/util` (CPython-only backends — firmware
  uses the C usermod); `common.py` skips `embit`, so no double-freeze.
  `empty.py` freezes `usermods/udisplay_f469/display_f469`.

`make empty` builds the same C usermods but freezes only `empty.py` — no
`embit`, no `libs/common`.

**Not built**: `libs/common/embit/secp256k1/secp256k1-zkp`. It is a C source tree
for `embit`'s own CPython ctypes build, outside every freeze root. It sits next
to code that does `import secp256k1`, which under CPython would make it an
implicit namespace package; `libs/common/embit/src/embit/util/secp256k1.py`
guards against that explicitly (it keys on `from micropython import const`).

## Verify pin and drift for each submodule

Reads each pin and `--remote` target from git, so it needs no edit after a pin
bump. Use it to refresh the Map's drift column:

```sh
git submodule foreach --recursive -q '
  b=$(git config -f "$toplevel/.gitmodules" "submodule.$name.branch") || \
    { git remote set-head origin -a >/dev/null; b=HEAD; }
  git fetch -q origin
  printf "%-45s pin=%.7s head=%s drift=%s dirty=%s\n" "$displaypath" "$sha1" \
    "$(git rev-parse --short=7 HEAD)" \
    "$(git rev-list --count "$sha1..origin/$b")" \
    "$(git status --short | wc -l | tr -d " ")"
'
```

- `head` must equal `pin`; otherwise the checkout has moved.
- `dirty` must be `0`.
- `drift` is commits past the pin on the `--remote` target. `0` means the pin
  sits at the target's head today, not that it is protected from future pushes.

## Reproducibility

**What is guaranteed.** Every entry above is pinned by commit hash in this
repo's tree (a gitlink), not by branch. A fresh

```sh
git clone --recursive https://github.com/hardware-wallets-and-cryptography/f469-disco.git
```

resolves the exact same trees, regardless of who owns each remote. The `Makefile`
guard rules for `micropython/mpy-cross/Makefile` and
`libs/common/embit/src/embit/__init__.py` run

```make
git submodule update --init --recursive
```

with **no `--remote`**, so a fresh checkout is initialised at the recorded
hashes. These are file targets: they run only when those files are missing.
`make` does not reset a submodule that is initialised but has moved — it builds
whatever is checked out. Run the verify script before building.

**What `--remote` does.** Nothing during a normal clone or build. Only
`git submodule update --remote` reads branches: it moves a submodule to the head
of its `branch =`, or of the remote's default branch (`origin/HEAD`) when no
`branch =` is set, and stages a new gitlink. Omitting `branch =` therefore does
not opt a submodule out — it just targets the default branch. With
`--recursive`, nested submodules move too. That is the drift footgun: it
silently replaces a verified tree with an untested one (see the Map's drift
column).

A single `--remote --recursive` would swap the display stack (lvgl `v9.x`
over the pinned `v6.0.2`) and both `secp256k1-zkp` trees — including the one
compiled into the signing usermod. Even lvgl's `release/v6` is 490 commits past
`dd100e5` (`1f707f9`, 2025-08-14, vs 2019-10-29; as of 2026-09-26).

Avoid `--remote`. To move a top-level pin, do it explicitly:

```sh
git submodule sync --recursive
git -C <path> fetch origin <branch>
git -C <path> checkout <full-sha>
git -C <path> submodule sync --recursive
git -C <path> submodule update --init --recursive
git add <path>
```

A nested pin (either `secp256k1-zkp` checkout) is recorded in the parent
submodule's repo, not here. Bumping it takes two commits in two repos. Check
first that the parent's drift is `0`; otherwise checking out its branch also
pulls in the untested commits past its pin.

```sh
# 1. in the parent fork: move the nested pin, commit, push to its branch
git -C <parent> checkout <parent-branch>          # e.g. usermods/secp256k1 → secp-zkp--int
git -C <parent>/<nested> fetch origin
git -C <parent>/<nested> checkout <full-sha>
git -C <parent> add <nested>
git -C <parent> commit -m "bump <nested> to <sha>"
git -C <parent> push origin <parent-branch>

# 2. here: move the parent pin to that new commit
git add <parent>
```

Both `secp256k1-zkp` checkouts are pinned to the same commit. To keep them in
step, run step 1 in both `usermods/secp256k1` (branch `secp-zkp--int`) and
`libs/common/embit` (branch `int`), then stage both parents here in one commit.

**Verifying a checkout matches the pins**

```sh
git submodule status --recursive
```

Every line must start with a **space**. A leading `+` means the checkout differs
from the recorded gitlink, `-` means uninitialized, `U` means conflicts. This
compares against the **index**, so a staged-but-uncommitted pin also shows a
space; use `git diff --cached --submodule=short` to see pins that differ from
`HEAD`. For changes inside submodules, nested ones included, check the
verify script's `dirty` field.

Untracked content inside a submodule is not harmless here: `manifests/common.py`
and `manifests/embit.py` walk whole directory trees and freeze every `.py` they
find, so stray files can end up compiled into firmware or break the build.

**Local remote URLs.** The URLs in `.git/config` (here and in each submodule)
should match the matching `.gitmodules`. Re-check after any `.gitmodules` edit,
here or in a submodule — an already-initialised checkout keeps the old URL until
synced:

```sh
git config --get-regexp '^submodule\..*\.url'
git submodule foreach --recursive 'git config --get-regexp "^submodule\..*\.url" || :'
git submodule sync --recursive
```

This never affects a pin, only where a re-fetch goes.

**What can still break reproducibility.** The pins are only as durable as the
remotes and branches hosting them. An orphaned pin makes a fresh `--recursive`
clone fail; its objects then survive only in existing local clones. None of the
pins is orphaned today (see the Map's "Pin reachable from" column).

- **Forks:** a pin reachable from only one branch (`libs/common/embit`,
  `usermods/secp256k1`) is orphaned if that branch is force-pushed past it.
  Tagging those pins in their forks would protect them.
- **`lvgl/lvgl`** (the one external remote, C source that reaches firmware): the
  pin is contained in upstream tags, so only repository deletion (or tag
  removal plus force-push of every containing branch) can orphan it.
