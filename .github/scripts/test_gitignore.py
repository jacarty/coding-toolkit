"""Every secret Claude is denied reading is also gitignored, so it can't be
committed by mistake or reach a review diff (review-diff.sh shows untracked
files that aren't ignored).

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import subprocess
import unittest

from deny_rules import ROOT, repo_samples


class GitignoreTests(unittest.TestCase):
    def check_ignore(self, paths: list[str]) -> set[str]:
        # --no-index: match the patterns, whether or not the paths exist or are tracked.
        result = subprocess.run(
            # Only the repo's .gitignore: not the user's own excludes file.
            ["git", "-c", "core.excludesFile=", "check-ignore", "--no-index", "--stdin"],
            cwd=ROOT, input="\n".join(paths) + "\n", capture_output=True, text=True,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return set(result.stdout.split("\n")) - {""}

    def test_denied_secrets_are_ignored(self) -> None:
        paths = repo_samples()
        self.assertGreater(len(paths), 50)
        missing = sorted(set(paths) - self.check_ignore(paths))
        self.assertEqual(missing, [], "add these to .gitignore, or drop the deny rule")

    def test_env_templates_are_not_ignored(self) -> None:
        templates = [f"{folder}.env.{kind}" for folder in ("", "sub/") for kind in ("example", "sample", "template")]
        self.assertEqual(self.check_ignore(templates), set())


if __name__ == "__main__":
    unittest.main()
