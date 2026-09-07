# Notes on issues with git submodules — history and fixes

Work done on 2026-09-05. Branch `my-dev`, at commit `513f8fe`.

This repo has 4 direct submodules and 2 nested ones — 6 in total.

A short word on terms used below:

- **Pin** — the one exact commit a submodule is fixed to. The main repo
  stores it, not a branch name.
- **Drift** — the submodule's files sit on a different commit than the
  pin says.

---

## Issue 1 — Changing `.gitmodules` did nothing

### What was wrong

The submodules moved to new GitHub accounts:

- `diybitcoinhardware/*` → `hardware-wallets-and-cryptography/*`
- `littlevgl/lvgl` → `lvgl/lvgl`

The URLs in `.gitmodules` were updated to match. But nothing changed.

The reason: git only reads `.gitmodules` when a submodule is first set
up. After that it uses two copies:

1. `.git/config` in the main repo
2. the `origin` remote inside each submodule

Both copies still held the old URLs.

### The fix

```bash
git submodule sync --recursive
```

This pushes the URLs from `.gitmodules` into both copies.

### Result

All 6 remotes now match `.gitmodules`, and all 6 answer. No
`diybitcoinhardware` or `littlevgl` URL is left anywhere. The files and
the index were not touched.

For a fresh clone, or in CI, the normal command still works:

```bash
git submodule update --init --recursive
```

---

## Issue 2 — The secp256k1 pin sat on no branch

### What was wrong

`usermods/secp256k1` is pinned to `1e74fc3`. That commit came from the
`secp-zkp` branch of the **old** repo.

When the new fork was made, only `master` came across. So the fork had
`master` (`036f465`) and nothing else. The pin pointed at a commit that
no branch and no tag reached.

The two lines of history had split at `a306c94`. The pin carried 24
commits that `master` did not have — rangeproof, surjection proof,
generator, and schnorrsig bindings. `libs/common/embit` needs those for
Liquid support (`tests/tests/test_liquid.py`,
`src/embit/util/ctypes_secp256k1.py`).

### Why this was risky, even though clones still worked

A clean clone of the fork could not check the commit out:

```
fatal: unable to read tree 1e74fc3...
```

But `git fetch origin 1e74fc3` did work, because GitHub still shared the
object through the fork network. Git tries exactly that fetch as a
fallback, so `git submodule update --init` kept working.

The pin was resting on a loose object with nothing pointing at it. Had
the fork been detached from its network, or the old branch deleted,
every clone would have started failing.

### The fix

The `secp256k1-embedded` repo was forked again, this time keeping the
`secp-zkp` branch.

### Checked afterwards

- The fork now has `master` and `secp-zkp`.
- The tip of `secp-zkp` is exactly `1e74fc3` — an exact match, not just
  an ancestor.
- A clean clone plus a plain `git checkout 1e74fc3` now works with no
  fetch first. The pin no longer leans on fork-network sharing.

### Follow-up

`branch = secp-zkp` was added to `.gitmodules`. Nothing in the repo had
shown that this submodule follows `secp-zkp` and not `master`, so a
routine "update to latest" would have quietly dropped the Liquid
bindings.

---

## Issue 3 — lvgl had drifted off its pin

### What was wrong

`usermods/udisplay_f469/lvgl` is pinned to `dd100e5` (`v6.0.2-31`). Its
files had moved to `8a8fdf2` (`v9.3.0-1647`).

That is three major versions ahead. That code does not build against
`usermods/udisplay_f469`.

The signs were a `+` in front of the line in `git submodule status`, and
an unstaged ` M` on the submodule path.

### Why it happened

Someone ran `git submodule update --remote`.

That flag ignores the pin. It follows `submodule.<name>.branch` instead,
and when no branch is set it follows the remote's default branch. For
lvgl that default is `master`, which is v9 today.

Git gave no warning. The pin is an ancestor of both `release/v6` and
`master`, so the jump looked like an ordinary fast-forward.

### The fix

```bash
git submodule update --checkout usermods/udisplay_f469/lvgl
```

lvgl went back to `dd100e5`. (If the v9 bump was ever wanted on purpose,
the commit was `8a8fdf2baa66eb8c3d908cbddc593c255daf41d5`.)

### Follow-up

`branch = release/v6` was added for lvgl, so `--remote` can no longer
jump to v9.

---

## Where things stand

### `.gitmodules`

```ini
[submodule "micropython"]
	path = micropython
	url = https://github.com/hardware-wallets-and-cryptography/micropython.git

[submodule "usermods/udisplay_f469/lvgl"]
	path = usermods/udisplay_f469/lvgl
	url = https://github.com/lvgl/lvgl.git
	branch = release/v6

[submodule "usermods/secp256k1"]
	path = usermods/secp256k1
	url = https://github.com/hardware-wallets-and-cryptography/secp256k1-embedded.git
	branch = secp-zkp

[submodule "libs/common/embit"]
	path = libs/common/embit
	url = https://github.com/hardware-wallets-and-cryptography/embit.git
```

### All 6 submodules, checked sound

| Submodule | Pin | Remote | Reachable from |
|---|---|---|---|
| `libs/common/embit` | `eb6104f` | hwac/embit | `master`, tag `v0.8.2` |
| `libs/common/embit/…/secp256k1-zkp` | `d9560e0` | ElementsProject/secp256k1-zkp | `master` |
| `micropython` | `6bdf1b6` | hwac/micropython | `master` |
| `usermods/secp256k1` | `1e74fc3` | hwac/secp256k1-embedded | `secp-zkp` |
| `usermods/secp256k1/secp256k1` | `d9560e0` | ElementsProject/secp256k1-zkp | `master` |
| `usermods/udisplay_f469/lvgl` | `dd100e5` | lvgl/lvgl | `master`, `release/v6` |

(`hwac` = `hardware-wallets-and-cryptography`.)

Every pin is reachable from a real branch or tag on its remote. No
submodule is dirty, and none has drifted.

---

## Rules going forward

### 1. Use the plain update command

```bash
git submodule update --init --recursive
```

It always checks out the exact pinned commits, and ignores the `branch`
keys completely.

### 2. Do not use `--remote`

`git submodule update --remote` exists in order to move submodules
forward, so it will always move them. The `branch` keys only limit how
far it can go — they do not lock anything:

- lvgl would still move to the tip of `release/v6` (`1f707f9`), which is
  490 commits past the pin.
- `micropython` and `libs/common/embit` happen to sit on their remotes'
  default branch tips right now, so they would not move today. That is
  luck, not protection.

### 3. Never re-pin `usermods/secp256k1` to that fork's `master`

Its `master` is missing the confidential-transaction bindings that embit
needs.

### 4. Check for drift whenever you want

```bash
git submodule status --recursive
```

- `+` — the files do not match the pin
- `-` — the submodule is not set up yet
- neither — everything is in order

The same check, as a CI guard:

```bash
git submodule status --recursive | grep -q '^[+-]' && { echo "submodule drift"; exit 1; }
```

This is written down only. It is not wired into any workflow yet.
