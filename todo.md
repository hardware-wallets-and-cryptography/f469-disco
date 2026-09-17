# TODO

## Submodule fork migration (`02a6b94`, 2026-09-16)

Done: all `.gitmodules` URLs repointed to `hardware-wallets-and-cryptography` forks (lvgl to upstream `lvgl/lvgl`), pins unchanged, `git submodule sync --recursive` run on the local clone.

Re-verified 2026-09-17 at `20cfaae`: all six recorded pins unchanged, local config matches `.gitmodules`, working tree clean, `dev` pushed.

### Not needed, but worth knowing

- Nested pins `libs/common/embit/secp256k1/secp256k1-zkp` and `usermods/secp256k1/secp256k1` still point at third-party `ElementsProject/secp256k1-zkp` — outside the fork migration.
- `branch = release/v6` closes the old lvgl v6 → v9 trap on `git submodule update --remote`, but `--remote` would still move lvgl to the `release/v6` tip (`1f707f9`, ~490 commits past the pin `dd100e5e`). Use `--init --recursive`.
- Docs, `README.md:14` and `jupyter_kernel/setup.py:18` still link to `diybitcoinhardware` — cosmetic, not build inputs. The README copyedit in `56aef82` rewrote 11 lines but left the releases link pointing at the old org.

### Follow-ups

- [ ] Decide whether to fork `ElementsProject/secp256k1-zkp` into the org, or accept the third-party dependency for the two nested pins.
- [ ] Replace the stale `diybitcoinhardware` links: `jupyter_kernel/setup.py:18` (`url=`), `README.md:14` (releases link), and the `diybitcoinhardware.com` / `raw.githubusercontent.com/diybitcoinhardware` simulator links across `docs/`.
- [ ] Confirm the simulator is hosted under the new org before rewriting the `docs/` simulator URLs — otherwise the links break rather than move.
- [ ] Tell anyone with an existing clone to run `git submodule sync --recursive`; their `.git/config` still holds the old URLs. Documented in `docs-my/notes-on-issues-with-gitmodules.md:36`, but the official `docs/build.md:39-44` "Submodules" section still shows only `--init --recursive` — add `sync` there.
- [ ] Enable GitHub Actions on the fork. It has never run: the API reports 0 registered workflows and 0 runs even though `.github/workflows/{ci,release}.yml` are on `master` — Actions is off by default on forks.
- [ ] Then exercise a fresh `submodules: recursive` clone against the new URLs: `ci.yml` triggers only on `pull_request` and pushes to `master`, so pushing `dev` never fires it. Open a `dev` → `master` PR (currently 5 commits ahead) or add `dev` to the push triggers.
