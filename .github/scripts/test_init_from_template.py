"""Tests for .github/scripts/init-from-template.sh, in a throwaway repo.

`gh` is a stub that reports signed out, so the script never reaches GitHub,
and `pre-commit` is a stub so installing the hooks needs no network.

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The template's placeholders, as files of their own: in a repo created from
# the template, init has already filled in the real ones, and these tests
# run in that repo's CI too.
FIXTURES = {
    "README.md": "# coding-toolkit\n\n<!-- template-readme: init-from-template.sh replaces this file. -->\n\nThe toolkit.\n",
    "AGENTS.md": "# [Project Name] — Agent Context\n",
    "LICENSE": "MIT License\n\nCopyright (c) [year] [your name]\n",
    ".github/CODEOWNERS": (
        "# CODEOWNERS\n"
        "# Replace YOUR-GITHUB-USERNAME with your GitHub handle, or use @your-org/team-name\n"
        "# for team ownership. Lines below assign default ownership to everything in the repo.\n"
        "\n* @YOUR-GITHUB-USERNAME\n"
    ),
}


class InitFromTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo = base / "my-app"
        for rel, content in FIXTURES.items():
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(content, encoding="utf-8")
        (self.repo / ".github/scripts").mkdir()
        shutil.copy2(ROOT / ".github/scripts/init-from-template.sh", self.repo / ".github/scripts")
        shutil.copytree(ROOT / ".githooks", self.repo / ".githooks")
        bin_dir = base / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text("#!/bin/sh\nexit 1\n")  # signed out
        (bin_dir / "pre-commit").write_text(
            '#!/bin/sh\n[ "$1" = install ] && printf "#!/bin/sh\\n# pre-commit stub\\nexit 0\\n" > '
            '"$(git rev-parse --git-common-dir)/hooks/pre-commit" && chmod +x '
            '"$(git rev-parse --git-common-dir)/hooks/pre-commit"\nexit 0\n'
        )
        for tool in ("gh", "pre-commit"):
            (bin_dir / tool).chmod(0o755)
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(base),
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        for args in (["init", "-q", "-b", "main"], ["config", "user.name", "Test Author"],
                     ["config", "user.email", "test@example.com"], ["config", "commit.gpgsign", "false"],
                     ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "chore: seed"]):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, env=self.env)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def init(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", ".github/scripts/init-from-template.sh", "--owner", "octocat", *args],
                              cwd=self.repo, capture_output=True, text=True, env=self.env)

    def readme(self) -> str:
        return (self.repo / "README.md").read_text(encoding="utf-8")

    def text(self, rel: str) -> str:
        return (self.repo / rel).read_text(encoding="utf-8")

    def hook_installed(self, name: str) -> bool:
        return (self.repo / ".git" / "hooks" / name).exists()

    def test_dry_run_changes_nothing(self) -> None:
        before = {rel: self.text(rel) for rel in FIXTURES}
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("→ README.md: replaced with a stub", result.stdout)
        self.assertEqual({rel: self.text(rel) for rel in FIXTURES}, before)
        self.assertFalse(self.hook_installed("commit-msg"))

    def test_apply_replaces_the_template_readme_once(self) -> None:
        result = self.init("--apply", "--skip-template-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        readme = self.readme()
        self.assertTrue(readme.startswith("# my-app\n"))
        self.assertNotIn("template-readme", readme)
        self.assertIn("[docs/toolkit.md](docs/toolkit.md)", readme)
        self.assertIn("my-app", self.text("AGENTS.md"))
        self.assertNotIn("[Project Name]", self.text("AGENTS.md"))
        self.assertIn("@octocat", self.text(".github/CODEOWNERS"))
        self.assertIn("Test Author", self.text("LICENSE"))
        for hook in ("commit-msg", "pre-push", "pre-commit"):
            self.assertTrue(self.hook_installed(hook), hook)
        # A re-run leaves the project's README alone, even after it's edited.
        (self.repo / "README.md").write_text(readme + "\nMy notes.\n", encoding="utf-8")
        result = self.init("--apply", "--skip-template-check")
        self.assertIn("✓ README.md: already the project's own", result.stdout)
        self.assertTrue(self.readme().endswith("My notes.\n"))

    def test_a_readme_without_the_marker_is_kept(self) -> None:
        (self.repo / "README.md").write_text("# Mine\n", encoding="utf-8")
        result = self.init("--apply", "--skip-template-check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.readme(), "# Mine\n")

    def test_apply_without_gh_needs_the_skip_flag(self) -> None:
        result = self.init("--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Can't confirm this isn't the template", result.stderr)
        self.assertIn("template-readme", self.readme())


if __name__ == "__main__":
    unittest.main()
