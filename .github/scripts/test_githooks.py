"""Integration tests for .githooks: commit-msg, pre-push and setup-hooks.sh.

Each test runs the real scripts in a throwaway repo. The commit-time scanners
(gitleaks, pre-commit-hooks) are maintained tools configured in
.pre-commit-config.yaml, so they aren't re-tested here; setup-hooks.sh runs
against a stub `pre-commit` so the tests need no network.

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / ".githooks"
ZERO = "0" * 40
SHA = "1" * 40


class HookRepo(unittest.TestCase):
    """A fresh git repo containing .githooks, for each test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        shutil.copytree(HOOKS, self.repo / ".githooks")
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(self.base)}
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=cwd or self.repo, capture_output=True, text=True, check=check, env=self.env)

    def write(self, name: str, content: str) -> None:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def hook(self, name: str, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
        """Run a hook script directly, as git would."""
        return subprocess.run(
            ["sh", str(self.repo / ".githooks" / name), *args],
            cwd=self.repo, input=stdin, capture_output=True, text=True, env=self.env,
        )


class PrePushTests(HookRepo):
    def push(self, *refs: tuple[str, str], remote: str = "origin") -> subprocess.CompletedProcess[str]:
        lines = "".join(f"refs/heads/x {sha} {remote_ref} {ZERO}\n" for remote_ref, sha in refs)
        return self.hook("pre-push", remote, "git@example.com:o/r.git", stdin=lines)

    def test_branch_names(self) -> None:
        # No default branch is known here, so main and master are both treated
        # as possible defaults (and blocked); see the default-branch tests.
        ok = ["feat/oauth-login", "fix/ci", "docs/x", "feat/v1-1a-api", "develop", "release"]
        bad = ["feature/x", "fix/CI", "fix/-x", "fix/x-", "hotfix/x", "release/1.0", "wip", "fix/" + "a" * 51]
        for name in ok:
            with self.subTest(name=name):
                self.assertEqual(self.push((f"refs/heads/{name}", SHA)).returncode, 0)
        for name in bad:
            with self.subTest(name=name):
                self.assertEqual(self.push((f"refs/heads/{name}", SHA)).returncode, 1)

    def test_checks_every_pushed_ref(self) -> None:
        self.assertEqual(self.push(("refs/heads/Bad_Name", SHA)).returncode, 1)
        result = self.push(("refs/heads/feat/ok", SHA), ("refs/heads/nope", SHA))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid branch name: nope", result.stderr)

    def test_default_branch_from_cache_then_fallback(self) -> None:
        result = self.push(("refs/heads/main", SHA))  # nothing known: main is assumed
        self.assertEqual(result.returncode, 1)
        self.assertIn("straight to main", result.stderr)
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        result = self.push(("refs/heads/trunk", SHA))
        self.assertIn("straight to trunk", result.stderr)
        # main isn't the default any more, so it's just a long-lived branch.
        self.assertEqual(self.push(("refs/heads/main", SHA)).returncode, 0)

    def test_default_branch_asked_from_the_remote(self) -> None:
        # The remote's default is `develop`, which would otherwise be exempt.
        remote = self.base / "remote.git"
        self.git("init", "-q", "--bare", "-b", "develop", str(remote), cwd=self.base)
        self.write("x.txt", "x\n")
        self.git("add", "x.txt")
        self.git("commit", "-q", "-m", "chore: seed")
        self.git("push", "-q", "--no-verify", str(remote), "HEAD:develop")  # the remote's HEAD needs a commit
        result = self.push(("refs/heads/develop", SHA), remote=str(remote))
        self.assertEqual(result.returncode, 1)
        self.assertIn("straight to develop", result.stderr)

    def test_deletes_and_tags_are_not_checked(self) -> None:
        self.assertEqual(self.push(("refs/heads/Whatever", ZERO)).returncode, 0)
        self.assertEqual(self.push(("refs/heads/x", "0" * 64)).returncode, 0)  # SHA-256 repos
        self.assertEqual(self.push(("refs/tags/v1.0.0", SHA)).returncode, 0)


class CommitMsgTests(HookRepo):
    def message(self, text: str) -> subprocess.CompletedProcess[str]:
        self.write("MSG", text)
        return self.hook("commit-msg", str(self.repo / "MSG"))

    def test_subjects(self) -> None:
        ok = [
            "feat: add login",
            "fix(api): 404 on a missing user",
            "feat: OAuth login",
            "fix: CI",
            "feat: x",
            "fix: 1",
            "feat(api)!: change the response format",
            "# comment line\nfix: skip leading git comments",
            "\n\nfix: skip leading blank lines",
            "Merge branch 'x'",
            "fixup! feat: add login",
            "fix: handle crlf\r\n",
        ]
        bad = [
            "add login",
            "Feat: add login",
            "feat: Add login",
            "feat: add login.",
            "feature: x",
            "feat:add login",
            "\n\nnot conventional",  # a leading blank line no longer skips the check
        ]
        for subject in ok:
            with self.subTest(subject=subject):
                self.assertEqual(self.message(subject + "\n").returncode, 0)
        for subject in bad:
            with self.subTest(subject=subject):
                self.assertEqual(self.message(subject + "\n").returncode, 1)

    def test_long_subject_warns_only(self) -> None:
        result = self.message("feat: " + "a" * 70 + "\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("76 characters", result.stderr)
        self.assertNotIn("characters", self.message("feat: " + "a" * 66 + "\n").stderr)


class SetupTests(HookRepo):
    """setup-hooks.sh, then real commits and pushes through the installed hooks."""

    def setUp(self) -> None:
        super().setUp()
        stub = self.base / "bin"
        stub.mkdir()
        # A stub pre-commit that just installs a pre-commit hook, so no network.
        (stub / "pre-commit").write_text(
            '#!/bin/sh\n[ "$1" = install ] && printf "#!/bin/sh\\n# pre-commit stub\\nexit 0\\n" > '
            '"$(git rev-parse --git-common-dir)/hooks/pre-commit" && chmod +x '
            '"$(git rev-parse --git-common-dir)/hooks/pre-commit"\nexit 0\n'
        )
        (stub / "pre-commit").chmod(0o755)
        self.env["PATH"] = f"{stub}{os.pathsep}{self.env['PATH']}"
        self.write("README.md", "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "chore: seed")
        remote = self.base / "origin.git"
        self.git("init", "-q", "--bare", "-b", "main", str(remote), cwd=self.base)
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-q", "origin", "main")

    def setup_hooks(self, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["sh", str((cwd or self.repo) / ".githooks/setup-hooks.sh")], cwd=cwd or self.repo,
                              capture_output=True, text=True, env=self.env)

    def test_install_then_commit_and_push(self) -> None:
        self.git("config", "--local", "core.hooksPath", ".githooks")  # the old setup
        result = self.setup_hooks()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("config", "--get", "core.hooksPath", check=False).stdout, "")
        self.write("a.txt", "a\n")
        self.git("add", "a.txt")
        self.assertNotEqual(self.git("commit", "-q", "-m", "bad message", check=False).returncode, 0)
        self.assertEqual(self.git("commit", "-q", "-m", "feat: add a", check=False).returncode, 0)
        self.assertNotEqual(self.git("push", "origin", "HEAD:main", check=False).returncode, 0)
        self.assertNotEqual(self.git("push", "origin", "HEAD:Bad_Name", check=False).returncode, 0)
        self.assertEqual(self.git("push", "-q", "origin", "HEAD:feat/add-a", check=False).returncode, 0)

    def test_existing_hooks_are_backed_up_and_reruns_are_clean(self) -> None:
        hooks = Path(self.git("rev-parse", "--git-common-dir").stdout.strip())
        hooks = (self.repo / hooks if not hooks.is_absolute() else hooks) / "hooks"
        (hooks / "pre-push").write_text("#!/bin/sh\necho mine\n")
        os.symlink("/bin/true", hooks / "commit-msg")
        self.assertEqual(self.setup_hooks().returncode, 0)
        self.assertEqual(len(list(hooks.glob("pre-push.bak.*"))), 1)
        self.assertEqual(len(list(hooks.glob("commit-msg.bak.*"))), 1)
        self.assertEqual(self.setup_hooks().returncode, 0)  # re-run: our launchers aren't backed up
        self.assertEqual(len(list(hooks.glob("*.bak.*"))), 2)

    def test_hooks_survive_removing_the_worktree_that_installed_them(self) -> None:
        tree = self.base / "tree"
        self.git("worktree", "add", "-q", "-b", "feat/tree", str(tree))
        self.assertEqual(self.setup_hooks(cwd=tree).returncode, 0)
        self.git("worktree", "remove", "--force", str(tree))
        self.write("b.txt", "b\n")
        self.git("add", "b.txt")
        self.assertNotEqual(self.git("commit", "-q", "-m", "still checked", check=False).returncode, 0)

    def test_global_hooks_path_is_reported_not_crashed(self) -> None:
        self.git("config", "--global", "core.hooksPath", "/elsewhere")
        result = self.setup_hooks()
        self.assertEqual(result.returncode, 1)
        self.assertIn("core.hooksPath is set to '/elsewhere'", result.stderr)


if __name__ == "__main__":
    unittest.main()
