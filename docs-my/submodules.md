# Submodules

## Map

- The table below is a snapshot
- Committed gitlinks are the source of truth for pins
- Nested gitlinks live in their immediate parent submodule
- All forks live under `hardware-wallets-and-cryptography/`
- Paths are relative to the repository root
- Remote names below are the canonical repository names, not Git remote aliases
- Verification uses each submodule's `origin`
- Pins, remote branches, tags, and drift were checked on `2026-11-25`

| Submodule                                   | Remote                                   | Fork | Pin          | `origin` target (`branch =`) | Drift past pin | Pin reachable from          | Firmware |
| ------------------------------------------- | ---------------------------------------- | :--: | ------------ | ---------------------------- | -------------- | --------------------------- | :------: |
| `libs/common/embit`                         | `embit`                                  |  ✅  | `6ed1571236` | `dev`                        | 0              | `dev` only                  |    ✅    |
| `libs/common/embit/secp256k1/secp256k1-zkp` | `BlockstreamResearch--secp256k1-zkp`     |  ✅  | `d9560e0af7` | `shared--pin`                | 0              | `master`, `shared--pin`     |    ❌    |
| `micropython`                               | `micropython`                            |  ✅  | `6bdf1b6916` | `f469-disco--pin`            | 0              | `master`, `f469-disco--pin` |    ✅    |
| `usermods/secp256k1`                        | `diybitcoinhardware--secp256k1-embedded` |  ✅  | `3a661645c4` | `f469-disco--pin`            | 0              | `f469-disco--pin`           |    ✅    |
| `usermods/secp256k1/secp256k1`              | `BlockstreamResearch--secp256k1-zkp`     |  ✅  | `d9560e0af7` | `shared--pin`                | 0              | `master`, `shared--pin`     |    ✅    |
| `usermods/udisplay_f469/lvgl`               | `lvgl`                                   |  ✅  | `dd100e5e07` | `f469-disco--pin`            | 0              | `master`, `f469-disco--pin` |    ✅    |

> **Six** submodules use **five** fork remotes. `secp256k1-zkp` appears **twice**:
>
> - under `usermods/secp256k1`
> - under `libs/common/embit/secp256k1`
>
> Both checkouts use the same fork and pin, so their committed sources match.
>
> **Keep the two in step when bumping.**

## What reaches the device

With the Makefile defaults, `make disco` builds the following components into
the firmware. Overriding the board, module directory, or manifests can change
this selection.

| Submodule                                    | Built into      | Mechanism                                                                  |
| -------------------------------------------- | --------------- | -------------------------------------------------------------------------- |
| `micropython`                                | the build       | `make -C micropython/ports/stm32`                                          |
| `usermods/secp256k1` + its `secp256k1/` tree | signing usermod | `USER_C_MODULES=../../../usermods` (relative to `micropython/ports/stm32`) |
| `libs/common/embit`                          | frozen Python   | `manifests/disco.py` → `empty.py` + `common.py` → `embit.py`               |
| `usermods/udisplay_f469/lvgl`                | display usermod | its `micropython.mk` includes `lvgl/lvgl.mk`                               |
| `libs/common/embit/secp256k1/secp256k1-zkp`  | **not built**   | excluded from freezing and not referenced by the firmware C build          |

> `embit.py` walks `embit/src` and skips `embit/util`, which contains
> CPython-only backends. Firmware uses the C usermod.

> `common.py` skips `embit` to avoid freezing it twice.

> `empty.py` freezes `usermods/udisplay_f469/display_f469`.

> `make empty` builds the same C usermods but uses only the `empty.py` manifest:
> the display Python module is frozen, but neither `embit` nor `libs/common` is.

**Why the nested embit tree is not built.** `libs/common/embit/secp256k1/secp256k1-zkp` is a C source
tree for `embit`'s own CPython ctypes build. `common.py` skips the entire
`embit` checkout, and `embit.py` walks only its `src` directory. No firmware
usermod references this nested C tree. Its parent,
`libs/common/embit/secp256k1/`, shares its name with the `secp256k1`
module that `embit` imports. Under CPython, with the embit repository root on
`sys.path` and no regular package taking precedence, `import secp256k1` can
resolve that directory as an implicit namespace package.
`libs/common/embit/src/embit/util/secp256k1.py` guards
against this by using `from micropython import const` to distinguish
MicroPython from CPython.

## Running the scripts

[scripts/submodules.sh](../scripts/submodules.sh) contains the operational
commands below. It requires Git and a POSIX shell; no Python packages or
firmware toolchain are needed. Run from this repository's root:

```sh
sh scripts/submodules.sh --help
```

The script operates on the repository containing the current working
directory, not the directory where the script itself is stored.

- `verify` fetches configured origins, reports branch drift, and checks pins,
  worktrees, and ignored frozen inputs. It does not change checkouts or pins.
- `ignored-inputs` checks frozen input directories without fetching.
- `sync-urls` changes local Git URL configuration and shows initialized origins.
- `restore` changes the superproject and submodule checkouts.
- `update` stages a reviewed top-level pin change.
- `prepare-nested` stages a nested pin change in its parent repository.
- `stage-nested` stages the two published parent pins and this document here.

**No command commits or pushes.** Review diffs, run tests, and explicitly commit
and publish changes yourself. Stop on any nonzero exit status. A failed
mutating command can leave earlier steps applied; inspect Git status and diffs
before continuing. There is no automatic rollback.
Git checkout operations can add or remove tracked files as part of changing
revisions; there is no automatic cleanup of untracked or ignored files.

### Running the automated validation

The host-side [tests](../tests/host/test_submodules.py) require Python 3.8+ and
Git. They do not require initialized project submodules, a clean checkout,
SDL, or an ARM compiler:

```sh
python3 -m unittest discover -s tests/host -p 'test_submodules.py' -v
```

The tests create disposable local repositories, disable external Git hooks
and user/system configuration, permit only local-file Git transport, and
clean up their temporary directories. They exercise successful updates and
failure cases: missing/deleted branches, stale local branches, ignored
Python/bytecode inputs, dirty checkouts, unpublished parents, and mismatched
nested pins. They also check shell syntax and that concrete commit IDs remain
inside tables. They do not contact GitHub, change this checkout's pins, or
compile firmware. Live remote state still requires `verify`.

These are separate from the MicroPython application tests run by `make test`.

## Verify pin and drift for each submodule

Run from the repository root, after initializing submodules and reviewing
their URLs as described below. The check requires a clean index and worktree,
including untracked files. It refuses uninitialized or mismatched checkouts
instead of letting `foreach` silently skip them. After reviewing URLs,
initialize missing submodules with
`git submodule update --init --recursive --checkout`.

All current entries explicitly name a branch in their immediate parent's
`.gitmodules`. The script requires that configuration, uses `origin`, and
rejects differing branch overrides. Fetching updates remote-tracking refs,
not checked-out pins.

```sh
sh scripts/submodules.sh verify
```

- `target-only` is the table's **Drift past pin**: commits reachable from the
  fetched target but not from the pin.
- `pin-only` counts commits reachable from the pin but not from that target.
- **Both counts must be zero to establish equality.** A zero `target-only`
  count alone can also mean the branch is behind the pin.
- Nonzero counts do not move the checkout or invalidate a pinned build.
  Investigate them before updating pins or claiming the table is current.
- A missing target branch, failed fetch, or invalid configuration must be
  resolved; do not substitute a different branch to make verification pass.

**Ignored frozen inputs need an explicit check.** Clean Git status does not
include ignored files. The manifests select files without consulting Git:
`common.py` and `embit.py` walk their selected directories for `.py` files,
and the display manifest also accepts `.mpy` files. `verify` includes this
check; to run it separately without fetching:

```sh
sh scripts/submodules.sh ignored-inputs
```

The command reports success only if no ignored frozen inputs are found.
Otherwise it lists the paths and exits unsuccessfully. Investigate Python
sources inside ignored cache or build directories; do not bulk-delete
unrelated environments or artifacts.

## Reproducibility

**What the pins guarantee.** Every entry above is pinned by commit hash
(a gitlink), not by branch. This command clones the trees pinned by `dev`
at clone time:

```sh
git clone --branch dev --recursive https://github.com/hardware-wallets-and-cryptography/f469-disco.git
```

That command follows the current `dev`, not a permanent snapshot. To preserve
a release, retain and publish a reference to the **superproject revision**,
preferably a protected release tag. The table alone does not identify the
complete superproject source tree. No stable release tag is implied here.

To restore a release whose tag has been fetched, start from a clean checkout.
Replace the example tag with your retained release tag:

```sh
sh scripts/submodules.sh restore 'retained-release-tag'
```

For releases that predate these scripts, keep a copy of `submodules.sh` outside
the checkout and invoke it by its external path, with this repository as the
working directory.

Then run `verify`. Branch targets can have advanced since the release;
pinned checkouts should still match the release's gitlinks. Pins preserve
source selection, not the compiler,
dependencies outside these gitlinks, or a bit-for-bit reproducible binary.

**Do not use `--remote` for reproducible builds.** It follows mutable branch
targets rather than the recorded pins. The two nested targets currently
match their pins, but a future push can change that. Local
`submodule.<name>.branch` configuration overrides `.gitmodules`; `--remote`
can also use a different remote if the submodule's branch is configured for one.

### Moving a top-level pin

Start from a verified clean checkout. Replace the example submodule and
`reviewed-ref` before running. The ref is an explicitly reviewed commit,
fetched tag, or remote-tracking ref; do not blindly take the latest branch head.

```sh
sh scripts/submodules.sh update libs/common/embit 'reviewed-ref'
```

Run the affected tests/builds before committing the superproject change:
`make test` exercises the Unix build, and `make disco` builds the default
device firmware. Confirm that the selected commit and all nested pins are
available from their declared remotes before publishing the new gitlink.
Refresh the table and stage `docs-my/submodules.md` with the pin change.
Commit the reviewed staged change with `git commit -m "Update submodule pin"`.

### Moving a nested pin

A nested pin is recorded in its immediate parent's repository. Updating one
requires a parent-submodule commit and a superproject commit. Keeping both
copies in step requires **two parent commits and one superproject commit**.

Start from a verified clean checkout and synchronized URLs. These examples
use `reviewed-ref` as a placeholder: replace it with the same reviewed
revision in both checkouts. Choose an unused local work-branch name.

The first command updates the signing parent. It derives the base from the
committed gitlink,
requires the fetched target to equal that base, and creates a new local
branch there. It never trusts a pre-existing local branch.

```sh
sh scripts/submodules.sh prepare-nested usermods/secp256k1 'reviewed-ref' bump-nested-secp256k1
```

After the command succeeds, inspect its staged diff and explicitly commit in
that parent:

```sh
git -C usermods/secp256k1 commit -m "Update nested secp256k1 pin"
```

Prepare the embit parent, selecting the **same reviewed commit**:

```sh
sh scripts/submodules.sh prepare-nested libs/common/embit 'reviewed-ref' bump-nested-secp256k1
```

Review and commit its staged diff:

```sh
git -C libs/common/embit commit -m "Update nested secp256k1 pin"
```

The script knows each parent's nested path and reads the branch target from
`.gitmodules`. The superproject is intentionally dirty between these updates;
do not reset the first or rerun the clean-checkout `verify` in between.

After preparing both parent commits, run the affected tests/builds. Then
publish both commits to their configured target branches. Where direct pushes
are permitted, use `git -C <parent> push origin HEAD:refs/heads/<target-branch>`.
With protected branches, publish review branches and merge through the required
review process, then check out and test the resulting parent commits. If a
target advances or a push is rejected, stop and reconcile; do not force-push.

Refresh the table from the prepared parent commits and fetched branch state.
Before recording the superproject commit, require both parent commits to be
published and their **committed nested gitlinks** to agree. Include the table
update in that same commit:

```sh
sh scripts/submodules.sh stage-nested
```

After the command succeeds, inspect the staged diff and explicitly commit here:

```sh
git commit -m "Update both secp256k1 parent pins"
```

Rerun `verify` after committing, when the superproject is clean again.

**How to check the pins.**

```sh
git submodule status --recursive
```

Every line must start with a **space**. A leading `+` means the checkout differs
from the recorded gitlink, `-` means uninitialized, and `U` means conflicts. This
compares against the **index**, so a staged-but-uncommitted pin also shows a
space; use `git diff --cached --submodule=short` to see pins that differ from
`HEAD`. A space does not establish a clean worktree or exclude ignored build
inputs; use `verify` above.

**Local remote URLs.** The URLs in `.git/config` (here and in each submodule)
should match the corresponding `.gitmodules`. Fetching `origin` uses each
submodule's own `remote.origin.url`, so check that too. The old unprefixed
secp256k1 repository names currently redirect to the canonical names in the
table; do not depend on those redirects remaining available.

Review committed URLs before syncing, especially when checking out a different
release. An initialized checkout keeps its configured URL until changed or
synced. Run from the repository root:

```sh
sh scripts/submodules.sh sync-urls
```

Syncing changes the fetch URLs, not the pins.

**What can break reproducibility.** A fresh recursive clone requires the
superproject revision and every pinned submodule commit to remain obtainable.
Deletion, access changes, outages, or unreachable objects can prevent that.
Existing local clones may retain objects that a fresh clone cannot obtain.

Each pin in this snapshot is reachable from a branch listed in the table.
Losing one containing branch is not enough to make it unreachable if another
branch, tag, or retained reference still contains it. Force-pushes or reference
deletions can remove the last such reference.

None of the five fork remotes advertised tags when checked. Publishing and
protecting tags for release pins provides additional retention references,
but tags can also be moved or deleted. Protect release references in the
superproject and dependency repositories, and retain backups where needed.
