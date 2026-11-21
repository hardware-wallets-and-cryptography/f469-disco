#!/bin/sh
set -eu

usage() {
  cat <<'EOF'
Usage: sh scripts/submodules.sh <command> [arguments]

Run in the repository to operate on (normally from its root).

  verify
      Require clean, initialized pins; fetch origin branches, report drift,
      and reject ignored frozen inputs.
  ignored-inputs
      Report ignored frozen inputs and fail if any are found.
  sync-urls
      Sync reviewed .gitmodules URLs and show initialized origins.
  restore <fetched-ref>
      Restore a clean checkout and its submodules to a retained revision.
  update <top-level-submodule> <reviewed-ref>
      Verify, check out a reviewed revision, update nested pins, and stage.
  prepare-nested <parent> <reviewed-ref> <new-work-branch>
      Prepare and stage a nested pin update on a new branch at the parent pin.
      Parent must be usermods/secp256k1 or libs/common/embit.
  stage-nested
      Require clean, published parent commits with matching nested pins;
      stage both parents and docs-my/submodules.md.

No command commits, pushes, force-updates local branches, or runs cleanup.
Fetches update remote-tracking refs. Failures do not roll back prior steps.
EOF
}

die() {
  printf "%s\n" "$*" >&2
  exit 1
}

require_clean() {
  status=$(git -C "$1" status --porcelain --untracked-files=all --ignore-submodules=none)
  if [ -n "$status" ]; then
    printf "%s: resolve staged, modified, or untracked files first:\n%s\n" \
      "$1" "$status" >&2
    exit 1
  fi
}

require_submodule() {
  parent_root=$(git -C "$1" rev-parse --show-superproject-working-tree)
  [ "$parent_root" = "$root" ] || die "$1: not an initialized top-level submodule."
  prefix=$(git -C "$1" rev-parse --show-prefix)
  [ -z "$prefix" ] || die "$1: not the root of a top-level submodule."
}

require_initialized() {
  state=$(git -C "$1" submodule status --recursive)
  printf "%s\n" "$state"
  if printf "%s\n" "$state" | grep -q "^[+U-]"; then
    die "Initialize submodules and restore their recorded pins first."
  fi
}

fetch_origin() {
  git -C "$1" fetch --prune -q origin '+refs/heads/*:refs/remotes/origin/*'
}

parent_branch() {
  branch=$(git config -f .gitmodules --get "submodule.$1.branch") ||
    die "$1: missing or unreadable parent branch setting."
  git check-ref-format "refs/heads/$branch" ||
    die "$1: an explicit named branch is required."
  effective=$(git config --default "$branch" --get "submodule.$1.branch")
  [ "$effective" = "$branch" ] ||
    die "$1: branch override differs from .gitmodules."
  printf "%s\n" "$branch"
}

ignored_inputs() {
  require_submodule libs/common/embit
  common_inputs=$(git ls-files --others --ignored --exclude-standard -- \
    ':(glob)libs/common/**/*.py' \
    ':(glob)usermods/udisplay_f469/display_f469/**/*.py' \
    ':(glob)usermods/udisplay_f469/display_f469/**/*.mpy')
  embit_inputs=$(git -C libs/common/embit ls-files --others --ignored \
    --exclude-standard -- ':(glob)src/**/*.py' \
    ':(exclude,glob)src/embit/util/**')
  if [ -n "$common_inputs" ] || [ -n "$embit_inputs" ]; then
    printf "Ignored frozen inputs found (embit paths are relative to its checkout):\n%s\n%s\n" \
      "$common_inputs" "$embit_inputs" >&2
    die "Investigate these inputs before building; no files were removed."
  fi
  echo "No ignored frozen inputs."
}

verify() {
  require_initialized .
  require_clean .
  git submodule foreach --recursive -q '
    set -eu
    branch=$(git config -f "$toplevel/.gitmodules" --get "submodule.$name.branch") || {
      echo "$displaypath: missing or unreadable branch setting." >&2
      exit 1
    }
    git check-ref-format "refs/heads/$branch" || {
      echo "$displaypath: an explicit named branch is required." >&2
      exit 1
    }
    effective=$(git -C "$toplevel" config --default "$branch" --get "submodule.$name.branch")
    if [ "$effective" != "$branch" ]; then
      echo "$displaypath: branch override differs from .gitmodules." >&2
      exit 1
    fi
    git fetch --prune -q origin "+refs/heads/*:refs/remotes/origin/*"
    target=$(git rev-parse --verify "refs/remotes/origin/$branch^{commit}")
    head=$(git rev-parse HEAD)
    pin_only=$(git rev-list --count "$target..$sha1")
    target_only=$(git rev-list --count "$sha1..$target")
    status=$(git status --porcelain --untracked-files=all --ignore-submodules=none)
    if [ "$head" != "$sha1" ] || [ -n "$status" ]; then
      printf "%s: checkout changed or is dirty.\n%s\n" "$displaypath" "$status" >&2
      exit 1
    fi
    printf "%-45s branch=%s pin-only=%s target-only=%s\n" \
      "$displaypath" "$branch" "$pin_only" "$target_only"
  '
  ignored_inputs
}

if [ "$#" -eq 0 ]; then
  usage >&2
  exit 1
fi
command=$1
shift
case "$command:$#" in
  --help:0|help:0)
    usage
    exit 0
    ;;
  verify:0|ignored-inputs:0|sync-urls:0|restore:1|update:2|prepare-nested:3|stage-nested:0)
    ;;
  *)
    usage >&2
    die "Unknown command or incorrect argument count: $command"
    ;;
esac

root=$(git rev-parse --show-toplevel)
cd "$root"

case "$command" in
  verify)
    verify
    ;;
  ignored-inputs)
    ignored_inputs
    ;;
  sync-urls)
    git submodule sync --recursive
    git submodule foreach --recursive -q '
      set -e
      printf "%s: " "$displaypath"
      git remote get-url origin
    '
    ;;
  restore)
    require_clean .
    commit=$(git rev-parse --verify --end-of-options "$1^{commit}")
    git checkout --detach "$commit"
    git submodule sync --recursive
    git submodule update --init --recursive --checkout
    ;;
  update)
    require_submodule "$1"
    verify
    git submodule sync --recursive
    fetch_origin "$1"
    commit=$(git -C "$1" rev-parse --verify --end-of-options "$2^{commit}")
    git -C "$1" checkout --detach "$commit"
    git -C "$1" submodule sync --recursive
    git -C "$1" submodule update --init --recursive --checkout
    git add -- "$1"
    git --no-pager diff --cached --submodule=log
    ;;
  prepare-nested)
    parent=$1
    case "$parent" in
      usermods/secp256k1) nested=secp256k1 ;;
      libs/common/embit) nested=secp256k1/secp256k1-zkp ;;
      *) die "Unsupported nested-pin parent: $parent" ;;
    esac
    require_submodule "$parent"
    require_initialized "$parent"
    require_clean "$parent"
    ignored_inputs
    branch=$(parent_branch "$parent")
    base=$(git rev-parse "HEAD:$parent")
    head=$(git -C "$parent" rev-parse HEAD)
    [ "$head" = "$base" ] ||
      die "Parent checkout differs from its committed pin."
    fetch_origin "$parent"
    target=$(git -C "$parent" rev-parse --verify "refs/remotes/origin/$branch^{commit}")
    [ "$target" = "$base" ] ||
      die "Parent target differs from its pin; reconcile and test separately."
    fetch_origin "$parent/$nested"
    commit=$(git -C "$parent/$nested" rev-parse --verify --end-of-options "$2^{commit}")
    git -C "$parent" checkout -b "$3" "$base"
    git -C "$parent/$nested" checkout --detach "$commit"
    git -C "$parent" add -- "$nested"
    git --no-pager -C "$parent" diff --cached --submodule=log
    echo "Review and commit the staged nested pin in $parent."
    ;;
  stage-nested)
    for parent in usermods/secp256k1 libs/common/embit; do
      require_submodule "$parent"
      require_initialized "$parent"
      require_clean "$parent"
      branch=$(parent_branch "$parent")
      fetch_origin "$parent"
      head=$(git -C "$parent" rev-parse HEAD)
      target=$(git -C "$parent" rev-parse --verify "refs/remotes/origin/$branch^{commit}")
      [ "$head" = "$target" ] ||
        die "$parent: publish or reconcile the parent commit first."
    done
    signing=$(git -C usermods/secp256k1 rev-parse HEAD:secp256k1)
    embit=$(git -C libs/common/embit rev-parse HEAD:secp256k1/secp256k1-zkp)
    [ "$signing" = "$embit" ] ||
      die "Committed nested secp256k1 pins differ; do not record these pins."
    ignored_inputs
    git add -- usermods/secp256k1 libs/common/embit docs-my/submodules.md
    git --no-pager diff --cached --submodule=log
    ;;
esac
