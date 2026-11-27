# Compatibility shim for `nix-shell` / non-flake setups.
#
# It reuses flake.nix and flake.lock, so `nix-shell` and `nix develop` give the
# exact same, pinned environment. Do not add packages here - edit flake.nix.
#
# Why this form, and not the usual `{ pkgs ? import <nixpkgs> {} }`:
#
#   - No `<nixpkgs>`. nixpkgs comes from flake.lock (nixos-22.05, rev 380be19),
#     the same revision the flake uses. A `<nixpkgs>` shim would resolve to
#     whatever channel the user happens to have, which could select a different
#     package set or lack `gcc-arm-embedded-9`.
#   - It derives the shell from flake.nix instead of duplicating the package
#     list, so the two entry points cannot drift apart.
#   - flake-compat itself is pinned from the lock - both `rev` and `narHash` -
#     so `nix flake update` updates both entry points at once.
#   - The lock node is looked up through `lock.nodes.root.inputs.flake-compat`
#     rather than a hardcoded name, so renaming the input in flake.nix will not
#     silently break this file.
#
# Both paths use the same dev-shell derivation; verify with:
#
#   nix-instantiate shell.nix
#   nix eval .#devShells.$(nix eval --raw --impure --expr builtins.currentSystem).default.drvPath
(import (
  let
    lock = builtins.fromJSON (builtins.readFile ./flake.lock);
    node = lock.nodes.${lock.nodes.root.inputs.flake-compat}.locked;
  in
  fetchTarball {
    url = "https://github.com/${node.owner}/${node.repo}/archive/${node.rev}.tar.gz";
    sha256 = node.narHash;
  }
) { src = ./.; }).shellNix
