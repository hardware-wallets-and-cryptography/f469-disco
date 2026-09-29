# Submodules

## Map

- The table below is a snapshot; the gitlinks in this repo's tree are the
  source of truth for pins
- Forks live under `hardware-wallets-and-cryptography/`
- Paths are relative to this repo's root
- Drift snapshot is documented as of `2026-09-29`

| Submodule | Remote | Fork | Pin | Describe (`git describe --tags --abbrev=10`) | `--remote` target | Drift past pin | Pin reachable from | Firmware |
|---|---|:-:|---|---|---|---|---|:-:|
| `libs/common/embit` | `embit` | ✅ | `b2e606bb71` | `v0.8.2-4-gb2e606bb71` | `int` (`branch =`) | 0 | `int` only | ✅ |
| `libs/common/embit/secp256k1/secp256k1-zkp` | `secp256k1-zkp` | ✅ | `d9560e0af7` | — | `master` (default) | **1949** (→ `037cc6d`) | `master`, `dev`, `int` | ❌ |
| `micropython` | `micropython` | ✅ | `6bdf1b6916` | `v1.10-1185-g6bdf1b6916` | `master` (default) | 0 | `master` | ✅ |
| `usermods/secp256k1` | `secp256k1-embedded` | ✅ | `1c41d24e56` | — | `secp-zkp--int` (`branch =`) | 0 | `secp-zkp--int` only | ✅ |
| `usermods/secp256k1/secp256k1` | `secp256k1-zkp` | ✅ | `d9560e0af7` | — | `master` (default) | **1949** (→ `037cc6d`) | `master`, `dev`, `int` | ✅ |
| `usermods/udisplay_f469/lvgl` | `lvgl` | ✅ | `dd100e5e07` | `v6.0.2-31-gdd100e5e07` | `f469-disco--pin` (`branch =`) | 0 | `f469-disco--pin`, `master` | ✅ |

> Describe values come from upstream tags left in a local clone. The forks have
> no tags, so in a fresh clone `git describe --tags` fails with "No names found".

> **5 remotes are forked** *(Why not 6? See info below.)*

> Remote `secp256k1-zkp` appears twice:
> - under `usermods/secp256k1`  
> - under `libs/common/embit/secp256k1`
>
> Both from the same fork and at the same commit `d9560e0`, so there is no version skew
> between the two checkouts.
>
> **Keep the two in step when bumping.**

## What reaches the device

**Firmware**
- `make disco`

| Submodule | Built into | Mechanism |
|---|---|---|
| `micropython` | the build | `make -C micropython/ports/stm32` |
| `usermods/secp256k1` + its `secp256k1/` tree | signing usermod | `USER_C_MODULES=../../../usermods` (relative to `micropython/ports/stm32`) |
| `libs/common/embit` | frozen Python | `manifests/disco.py` → `empty.py` + `common.py` → `embit.py` |
| `usermods/udisplay_f469/lvgl` | display usermod | its `micropython.mk` includes `lvgl/lvgl.mk` |
| `libs/common/embit/secp256k1/secp256k1-zkp` | **not built** | outside every freeze root (see note below) |

> `embit.py` walks `embit/src` and skips `embit/util` (CPython-only backends —
firmware uses the C usermod)

> `common.py` skips `embit`, so no double-freeze

> `empty.py` freezes `usermods/udisplay_f469/display_f469`

`make empty` builds the same C usermods but freezes only `empty.py` — no
`embit`, no `libs/common`.

**Not built note**: `libs/common/embit/secp256k1/secp256k1-zkp` is a C source
tree for `embit`'s own CPython ctypes build, outside every freeze root. Its
parent, `libs/common/embit/secp256k1/`, shares its name with the `secp256k1`
module that `embit` imports. Under CPython, with the embit repo root on
`sys.path`, `import secp256k1` would resolve that directory as an implicit
namespace package; `libs/common/embit/src/embit/util/secp256k1.py` guards
against that explicitly (it keys on `from micropython import const`).

## Verify pin and drift for each submodule

Reads each pin and `--remote` target from git, so it needs no edit after a pin
bump. Use it to refresh the Map's drift column:

```sh
git submodule foreach --recursive -q '
  b=$(git config -f "$toplevel/.gitmodules" "submodule.$name.branch") || \
    { git remote set-head origin -a >/dev/null; b=HEAD; }
  git fetch -q origin
  printf "%-45s pin=%.10s head=%s drift=%s dirty=%s\n" "$displaypath" "$sha1" \
    "$(git rev-parse --short=10 HEAD)" \
    "$(git rev-list --count "$sha1..origin/$b")" \
    "$(git status --short | wc -l | tr -d " ")"
'
```

- `head` must equal `pin` (otherwise the checkout has moved)
- `dirty` must be `0`
- `drift` is commits past the pin on the `--remote` target. `0` means the pin
  sits at the target's head today, not that it is protected from future pushes.

## Reproducibility

**What is guaranteed.** Every entry above is pinned by commit hash in this
repo's tree (a gitlink), not by branch. A fresh

```sh
git clone --recursive https://github.com/hardware-wallets-and-cryptography/f469-disco.git
```

resolves the exact same trees, regardless of who owns each remote. This holds
once `dev` is pushed and merged to `master`; until then the fork's `master`
still carries the old upstream URLs. The `Makefile`
guard rules for `micropython/mpy-cross/Makefile` and
`libs/common/embit/src/embit/__init__.py` run

```make
git submodule update --init --recursive
```

with **no `--remote`**, so a fresh checkout is initialized at the recorded
hashes. These are file targets: they run only when those files are missing.
A partly initialized tree (e.g. `micropython` and `embit` present but
`usermods/secp256k1` missing) is not caught. A missing `usermods/secp256k1` is
silently left out of the firmware (`py/py.mk` only picks up usermods that have
a `micropython.mk`); a missing lvgl fails the build. `make` does not reset a
submodule that is initialized but has moved — it builds whatever is checked
out. Run the verify script before building.

**What `--remote` does.** Nothing during a normal clone or build. Only
`git submodule update --remote` reads branches: it moves a submodule to the head
of its `branch =`, or of the remote's default branch (`origin/HEAD`) when no
`branch =` is set, and checks out the new commit without staging it
(`git submodule status` shows `+`; `git add` records it). Omitting `branch =`
therefore does not opt a submodule out — it just targets the default branch.
With `--recursive`, nested submodules move too. That is the drift footgun: it
silently replaces a verified tree with an untested one (see the Map's drift
column).

A single `--remote --recursive` would move both `secp256k1-zkp` trees 1949
commits past `d9560e0` (to `037cc6d`), including the one compiled into the
signing usermod.

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
should match the corresponding `.gitmodules`. A re-fetch uses each submodule's
own `remote.origin.url`, so check that too. Re-check after any `.gitmodules`
edit, here or in a submodule — an already-initialized checkout keeps the old URL
until synced:

```sh
git config --get-regexp '^submodule\..*\.url'
git submodule foreach --recursive 'git config --get-regexp "^submodule\..*\.url" || :'
git submodule foreach --recursive -q 'echo "$displaypath $(git remote get-url origin)"'
git submodule sync --recursive
```

This never affects a pin, only where a re-fetch goes.

**What can still break reproducibility.** The pins are only as durable as the
remotes and branches hosting them. An orphaned pin makes a fresh `--recursive`
clone fail; its objects then survive only in existing local clones. None of the
pins is orphaned today (see the Map's "Pin reachable from" column).

- **Forks:** a pin reachable from only one branch (`libs/common/embit`,
  `micropython`, `usermods/secp256k1`) is orphaned if that branch is
  force-pushed past it. Tagging those pins in their forks would protect them.
- **Forks with several branches** (`lvgl`: `f469-disco--pin`, `master`;
  `secp256k1-zkp`: `master`, `dev`, `int`): orphaned only if every containing
  branch is force-pushed. No fork has tags.
