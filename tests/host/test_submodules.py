import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/submodules.sh"


class SubmoduleScriptsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="f469-submodule-tests-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        hooks = self.base / "hooks"
        hooks.mkdir()
        environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.env = dict(
            environment,
            LC_ALL="C",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_SYSTEM=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_TERMINAL_PROMPT="0",
            GIT_ALLOW_PROTOCOL="file",
            GIT_AUTHOR_NAME="Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="core.hooksPath",
            GIT_CONFIG_VALUE_0=str(hooks),
        )
        self.library = self.init("library")
        (self.library / "source.c").write_text("int version = 1;\n")
        self.old_library = self.commit(self.library)
        self.git(self.library, "branch", "shared--pin")
        self.git(self.library, "checkout", "-qb", "reviewed")
        (self.library / "source.c").write_text("int version = 2;\n")
        self.new_library = self.commit(self.library)
        self.git(self.library, "checkout", "-q", "main")

        self.signing_source = self.init("signing")
        self.embit_source = self.init("embit")
        parents = [
            (self.signing_source, "secp256k1", "f469-disco--pin"),
            (self.embit_source, "secp256k1/secp256k1-zkp", "dev"),
        ]
        for source, nested, branch in parents:
            self.git(
                source, "submodule", "add", "-q", "-b", "shared--pin",
                str(self.library), nested,
            )
            (source / ".gitignore").write_text("__pycache__/\n")
            if source == self.embit_source:
                (source / "src/embit").mkdir(parents=True)
                (source / "src/embit/__init__.py").write_text("")
            self.commit(source)
            (source / "README").write_text("Parent metadata\n")
            self.commit(source)
            self.git(source, "branch", branch)

        self.root = self.init("superproject")
        for source, path, branch in [
            (self.signing_source, "usermods/secp256k1", "f469-disco--pin"),
            (self.embit_source, "libs/common/embit", "dev"),
        ]:
            self.git(
                self.root, "submodule", "add", "-q", "-b", branch,
                str(source), path,
            )
        (self.root / ".gitignore").write_text("__pycache__/\n")
        (self.root / "docs-my").mkdir()
        (self.root / "docs-my/submodules.md").write_text("Fixture documentation\n")
        self.display = self.root / "usermods/udisplay_f469/display_f469"
        self.display.mkdir(parents=True)
        (self.display / "__init__.py").write_text("")
        self.original = self.commit(self.root)
        self.git(self.root, "tag", "retained-release")
        self.git(
            self.root, "submodule", "update", "--init", "--recursive", "--checkout"
        )
        self.signing = self.root / "usermods/secp256k1"
        self.embit = self.root / "libs/common/embit"

    def run_command(self, repo, args, success=True):
        result = subprocess.run(
            args, cwd=repo, env=self.env, capture_output=True, text=True
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def git(self, repo, *args):
        return self.run_command(repo, ["git", *args]).stdout.strip()

    def cli(self, *args, error=None, repo=None):
        result = self.run_command(
            self.root if repo is None else repo,
            ["sh", str(SCRIPT), *args],
            success=error is None,
        )
        if error is not None:
            self.assertIn(error, result.stderr)
        return result.stdout

    def init(self, name):
        repo = self.base / name
        self.git(self.base, "init", "-q", "-b", "main", str(repo))
        return repo

    def commit(self, repo):
        self.git(repo, "add", ".")
        self.git(
            repo, "commit", "-qm",
            "Fixture update\n\nCo-authored-by: Copilot "
            "<223556219+Copilot@users.noreply.github.com>",
        )
        return self.git(repo, "rev-parse", "HEAD")

    def publish(self, parent, branch):
        self.git(parent, "push", "-q", "origin", "HEAD:refs/heads/" + branch)

    def bump_both(self):
        for parent, path, branch in [
            (self.signing, "usermods/secp256k1", "f469-disco--pin"),
            (self.embit, "libs/common/embit", "dev"),
        ]:
            self.cli("prepare-nested", path, "origin/reviewed", "fresh-bump")
            self.commit(parent)
            self.publish(parent, branch)
        self.cli("stage-nested")
        self.commit(self.root)

    def test_verification_rejects_incomplete_or_dirty_checkouts(self):
        self.assertEqual(
            self.cli("verify").count("pin-only=0 target-only=0"), 4
        )
        uninitialized = self.base / "uninitialized"
        self.git(self.base, "clone", "-q", str(self.root), str(uninitialized))
        self.cli("verify", repo=uninitialized, error="Initialize submodules")
        stray = self.root / "untracked.py"
        stray.write_text("")
        self.cli("verify", error="untracked files first")
        stray.unlink()
        self.git(
            self.root, "config", "submodule.libs/common/embit.branch", "main"
        )
        self.cli("verify", error="branch override differs")
        self.git(
            self.root, "config", "--unset", "submodule.libs/common/embit.branch"
        )
        self.git(
            self.root, "config", "-f", ".gitmodules", "--unset",
            "submodule.libs/common/embit.branch",
        )
        self.commit(self.root)
        self.cli("verify", error="missing or unreadable branch")
        self.git(
            self.root, "config", "-f", ".gitmodules",
            "submodule.libs/common/embit.branch", ".",
        )
        self.commit(self.root)
        self.cli("verify", error="explicit named branch")
        self.git(
            self.root, "config", "-f", ".gitmodules",
            "submodule.libs/common/embit.branch", "dev",
        )
        self.commit(self.root)
        (self.signing / "unrelated.txt").write_text("Checkout differs from pin\n")
        self.commit(self.signing)
        self.cli("verify", error="restore their recorded pins")

    def test_ignored_input_check_matches_frozen_roots(self):
        self.cli("ignored-inputs")
        sources = [
            self.root / "libs/common/__pycache__/stray.py",
            self.embit / "src/embit/__pycache__/stray.py",
            self.display / "__pycache__/stray.mpy",
        ]
        excluded = self.embit / "src/embit/util/__pycache__/excluded.py"
        for path in [*sources, excluded]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")
        self.assertEqual(self.git(self.root, "status", "--porcelain"), "")
        self.cli("ignored-inputs", error="Ignored frozen inputs found")
        self.cli("verify", error="Ignored frozen inputs found")
        for path in sources:
            self.assertTrue(path.exists())
            path.unlink()
        self.cli("ignored-inputs")
        self.cli("verify")
        self.assertTrue(excluded.exists())

    def test_drift_is_bidirectional_and_deleted_targets_are_pruned(self):
        self.git(self.library, "branch", "-f", "shared--pin", self.new_library)
        self.assertIn("pin-only=0 target-only=1", self.cli("verify"))
        self.git(self.library, "branch", "-f", "shared--pin", self.old_library)
        parent_pin = self.git(self.signing_source, "rev-parse", "HEAD")
        self.git(
            self.signing_source, "branch", "-f", "f469-disco--pin", "HEAD^"
        )
        self.assertIn("pin-only=1 target-only=0", self.cli("verify"))
        self.git(
            self.signing_source, "branch", "-f", "f469-disco--pin", parent_pin
        )
        self.git(
            self.embit, "config", "remote.origin.fetch",
            "+refs/heads/main:refs/remotes/origin/main",
        )
        self.git(self.embit_source, "branch", "-D", "dev")
        self.cli("verify", error="Needed a single revision")

    def test_nested_preparation_rejects_changed_targets_and_existing_branches(self):
        uninitialized = self.base / "uninitialized-nested"
        self.git(self.base, "clone", "-q", str(self.root), str(uninitialized))
        self.git(uninitialized, "submodule", "update", "--init", "--checkout")
        self.cli(
            "prepare-nested", "usermods/secp256k1", "origin/reviewed",
            "fresh-bump", repo=uninitialized, error="Initialize submodules",
        )
        parent_pin = self.git(self.signing, "rev-parse", "HEAD")
        (self.signing_source / "unrelated.txt").write_text("Separate update\n")
        self.commit(self.signing_source)
        self.git(self.signing_source, "branch", "-f", "f469-disco--pin", "HEAD")
        self.cli(
            "prepare-nested", "usermods/secp256k1", "origin/reviewed",
            "fresh-bump", error="Parent target differs",
        )
        self.git(
            self.signing_source, "branch", "-f", "f469-disco--pin", parent_pin
        )
        self.git(self.signing, "branch", "existing")
        self.cli(
            "prepare-nested", "usermods/secp256k1", "origin/reviewed",
            "existing", error="already exists",
        )
        self.cli(
            "prepare-nested", "usermods/secp256k1", "missing-ref",
            "fresh-bump", error="Needed a single revision",
        )
        self.assertEqual(self.git(self.signing, "rev-parse", "HEAD"), parent_pin)
        self.assertEqual(self.git(self.root, "status", "--porcelain"), "")

    def test_nested_workflow_requires_reviewed_published_matching_parents(self):
        parent_pin = self.git(self.signing, "rev-parse", "HEAD")
        self.git(self.signing, "checkout", "-q", "f469-disco--pin")
        (self.signing / "unrelated.txt").write_text("Do not include\n")
        unrelated = self.commit(self.signing)
        self.git(self.signing, "checkout", "-q", "--detach", parent_pin)
        self.cli(
            "prepare-nested", "usermods/secp256k1", "origin/reviewed", "fresh-bump"
        )
        self.assertEqual(self.git(self.signing, "rev-parse", "HEAD"), parent_pin)
        self.cli("stage-nested", error="resolve staged")
        new_signing = self.commit(self.signing)
        self.run_command(
            self.signing,
            ["git", "merge-base", "--is-ancestor", unrelated, new_signing],
            success=False,
        )
        self.cli("stage-nested", error="publish or reconcile")
        self.publish(self.signing, "f469-disco--pin")
        self.cli("stage-nested", error="Committed nested secp256k1 pins differ")
        self.cli(
            "prepare-nested", "libs/common/embit", "origin/reviewed", "fresh-bump"
        )
        self.commit(self.embit)
        self.publish(self.embit, "dev")
        (self.root / "docs-my/submodules.md").write_text("Updated table\n")
        self.cli("stage-nested")
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), self.original)
        staged = self.git(self.root, "diff", "--cached", "--name-only").splitlines()
        self.assertEqual(
            staged, ["docs-my/submodules.md", "libs/common/embit", "usermods/secp256k1"]
        )
        self.cli("verify", error="resolve staged")
        self.commit(self.root)
        self.assertEqual(
            self.git(self.signing, "rev-parse", "HEAD:secp256k1"), self.new_library
        )
        self.assertEqual(
            self.git(self.embit, "rev-parse", "HEAD:secp256k1/secp256k1-zkp"),
            self.new_library,
        )
        self.cli("verify")

    def test_restore_sync_and_top_level_update(self):
        self.bump_both()
        self.git(
            self.signing, "remote", "set-url", "origin",
            str(self.base / "wrong-origin"),
        )
        self.cli("sync-urls")
        self.assertEqual(
            self.git(self.signing, "remote", "get-url", "origin"),
            str(self.signing_source),
        )
        self.cli("restore", "retained-release")
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), self.original)
        self.assertEqual(
            self.git(self.signing / "secp256k1", "rev-parse", "HEAD"),
            self.old_library,
        )
        self.cli("verify")
        self.cli(
            "update", "usermods/secp256k1", "missing-ref",
            error="Needed a single revision",
        )
        self.assertEqual(self.git(self.root, "diff", "--cached", "--name-only"), "")
        self.cli("update", ".", "main", error="not an initialized top-level")
        self.cli(
            "update", "libs/common/embit/src", "main",
            error="not the root of a top-level submodule",
        )
        self.cli("update", "usermods/secp256k1", "origin/f469-disco--pin")
        self.assertEqual(self.git(self.root, "rev-parse", "HEAD"), self.original)
        self.assertEqual(
            self.git(self.signing / "secp256k1", "rev-parse", "HEAD"),
            self.new_library,
        )
        self.assertEqual(
            self.git(self.root, "diff", "--cached", "--name-only"),
            "usermods/secp256k1",
        )


class SubmoduleGuideTest(unittest.TestCase):
    def test_shell_syntax_help_and_documented_examples(self):
        subprocess.run(["sh", "-n", str(SCRIPT)], check=True)
        with tempfile.TemporaryDirectory(prefix="f469-submodule-help-") as directory:
            subprocess.run(
                ["sh", str(SCRIPT), "--help"], cwd=directory,
                capture_output=True, text=True, check=True,
            )
        document = (ROOT / "docs-my/submodules.md").read_text()
        for number, line in enumerate(document.splitlines(), 1):
            if re.search(r"\b[0-9a-f]{7,40}\b", line):
                self.assertTrue(line.startswith("| "), f"Commit outside table: {number}")
        for block in re.findall(r"```sh\n(.*?)\n```", document, re.S):
            subprocess.run(["sh", "-n"], input=block, text=True, check=True)


if __name__ == "__main__":
    unittest.main()
