"""Tests for .github/scripts/review-diff.sh: the review scope every gate uses.

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "review-diff.sh"

def _can_symlink() -> bool:
    """Windows without Developer Mode can't create symlinks."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.symlink(tmp, Path(tmp) / "link")
            return True
        except OSError:
            return False


CAN_SYMLINK = _can_symlink()



class ReviewDiffTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(base)}
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.write("base.txt", "base\n")
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "-m", "chore: seed")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, check=True, env=self.env).stdout

    def write(self, name: str, content: str) -> None:
        (self.repo / name).write_text(content, encoding="utf-8")

    def review_diff(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["sh", str(SCRIPT), *args], cwd=self.repo, capture_output=True, text=True, env=self.env)

    @unittest.skipUnless(CAN_SYMLINK, "needs symlinks")
    def test_untracked_symlinks_are_shown(self) -> None:
        (self.repo / "target").mkdir()
        (self.repo / "target" / "SKILL.md").write_text("x\n", encoding="utf-8")
        os.symlink("target", self.repo / "link")  # a symlink to a directory, as in .claude/skills
        result = self.review_diff()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("diff --git a/link b/link", result.stdout)
        self.assertIn("new file mode 120000", result.stdout)
        stat = self.review_diff("--stat")
        self.assertIn("link | symlink to target", stat.stdout)

    def test_every_kind_of_change_is_included_once(self) -> None:
        self.git("switch", "-q", "-c", "feat/x")
        self.write("committed.txt", "c\n")
        self.git("add", "committed.txt")
        self.git("commit", "-q", "--no-verify", "-m", "feat: committed")
        self.write("staged.txt", "s\n")
        self.git("add", "staged.txt")
        self.write("base.txt", "base\nunstaged edit\n")
        self.write("new file.txt", "untracked\n")
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", "secret-ish\n")
        result = self.review_diff()
        self.assertEqual(result.returncode, 0, result.stderr)
        files = [line.split(" b/", 1)[1] for line in result.stdout.splitlines() if line.startswith("diff --git")]
        self.assertEqual(sorted(files), sorted(["committed.txt", "staged.txt", "base.txt", "new file.txt", ".gitignore"]))
        self.assertIn("+unstaged edit", result.stdout)
        self.assertNotIn("secret-ish", result.stdout)  # the ignored file's content
        stat = self.review_diff("--stat").stdout
        self.assertIn("Changes since main", stat)
        self.assertIn("Untracked (new) files:\n", stat)
        self.assertIn(" new file.txt | 1 lines", stat)

    def test_default_branch_comes_from_origin_head(self) -> None:
        self.git("branch", "trunk")
        self.git("update-ref", "refs/remotes/origin/trunk", "trunk")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
        self.git("switch", "-q", "-c", "feat/y")
        self.write("y.txt", "y\n")
        self.assertIn("Changes since origin/trunk", self.review_diff("--stat").stdout)

    def test_base_override_and_missing_default(self) -> None:
        self.git("branch", "-m", "main", "work")  # no main, master or origin/HEAD any more
        result = self.review_diff()
        self.assertEqual(result.returncode, 1)
        self.assertIn("can't find the default branch", result.stderr)
        self.write("z.txt", "z\n")
        self.assertEqual(self.review_diff("--base", "work").returncode, 0)

    def files_in(self, output: str) -> list[str]:
        # Paths come from the "+++ b/..." lines; git quotes unusual names there.
        return [line[6:] for line in output.splitlines() if line.startswith("+++ b/") or line.startswith('+++ "b/')]

    def test_unusual_untracked_filenames(self) -> None:
        names = ['quote"d.txt', "tab\tname.txt", "back\\slash.txt", "new\nline.txt", "café.txt"]
        for name in names:
            (self.repo / name).write_text("x\n", encoding="utf-8")
        result = self.review_diff()
        self.assertEqual(result.returncode, 0, result.stderr)
        # One "new file" section per file: none silently dropped.
        self.assertEqual(result.stdout.count("new file mode"), len(names))
        self.assertEqual(self.review_diff("--stat").stdout.count(" lines"), len(names))

    def test_staged_then_edited_deleted_and_renamed(self) -> None:
        self.write("keep.txt", "one\n")
        self.write("gone.txt", "bye\n")
        self.write("old.txt", "same content for a rename\n" * 5)
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "-m", "chore: more")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("switch", "-q", "-c", "feat/z")
        self.write("keep.txt", "one\ntwo\n")
        self.git("add", "keep.txt")
        self.write("keep.txt", "one\ntwo\nthree\n")  # staged, then edited again
        self.git("rm", "-q", "gone.txt")
        self.git("mv", "old.txt", "new.txt")
        out = self.review_diff().stdout
        self.assertEqual(out.count("diff --git a/keep.txt"), 1)
        self.assertIn("+two", out)
        self.assertIn("+three", out)
        self.assertIn("deleted file mode", out)
        self.assertIn("rename from old.txt", out)

    def test_runs_from_a_subdirectory_and_filters_paths(self) -> None:
        (self.repo / "sub").mkdir()
        self.write("sub/a.txt", "a\n")
        self.write("b.txt", "b\n")
        result = subprocess.run(["sh", str(SCRIPT), "--", "sub/"], cwd=self.repo / "sub", capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sub/a.txt", result.stdout)
        self.assertNotIn("b.txt", result.stdout)

    def test_ignores_the_users_diff_settings(self) -> None:
        self.git("config", "diff.external", "false")
        self.git("config", "color.ui", "always")
        self.git("config", "diff.noprefix", "true")
        self.write("base.txt", "base\nchanged\n")
        out = self.review_diff().stdout
        self.assertIn("diff --git a/base.txt b/base.txt", out)
        self.assertNotIn("\x1b[", out)

    def test_dangling_origin_head_falls_back(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/renamed")  # doesn't exist
        self.write("x.txt", "x\n")
        self.assertIn("Changes since origin/main", self.review_diff("--stat").stdout)

    def test_unrelated_history(self) -> None:
        self.git("switch", "-q", "--orphan", "island")
        self.write("i.txt", "i\n")
        self.git("add", "i.txt")
        self.git("commit", "-q", "--no-verify", "-m", "chore: island")
        result = self.review_diff("--base", "main")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no common history", result.stderr)


if __name__ == "__main__":
    unittest.main()
