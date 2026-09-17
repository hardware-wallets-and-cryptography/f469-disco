# TODO

## Submodule fork migration (`02a6b94`, 2026-09-16)

Done: all `.gitmodules` URLs repointed to `hardware-wallets-and-cryptography` forks (lvgl to upstream `lvgl/lvgl`), pins unchanged, `git submodule sync --recursive` run on the local clone.

### Not needed, but worth knowing

- Nested pins `libs/common/embit/secp256k1/secp256k1-zkp` and `usermods/secp256k1/secp256k1` still point at third-party `ElementsProject/secp256k1-zkp` — outside the fork migration.
- `branch = release/v6` closes the old lvgl v6 → v9 trap on `git submodule update --remote`, but `--remote` would still move lvgl to the `release/v6` tip (`1f707f9`, ~490 commits past the pin `dd100e5e`). Use `--init --recursive`.
- Docs and `jupyter_kernel/setup.py:18` still link to `diybitcoinhardware` — cosmetic, not build inputs.

### Follow-ups

- [ ] Decide whether to fork `ElementsProject/secp256k1-zkp` into the org, or accept the third-party dependency for the two nested pins.
- [ ] Replace the stale `diybitcoinhardware` links: `jupyter_kernel/setup.py:18` (`url=`), `README.md:14` (releases link), and the `diybitcoinhardware.com` / `raw.githubusercontent.com/diybitcoinhardware` simulator links across `docs/`.
- [ ] Confirm the simulator is hosted under the new org before rewriting the `docs/` simulator URLs — otherwise the links break rather than move.
- [ ] Tell anyone with an existing clone to run `git submodule sync --recursive`; their `.git/config` still holds the old URLs.
- [ ] Verify CI on `dev` went green after the URL change (fresh `submodules: recursive` clone).
