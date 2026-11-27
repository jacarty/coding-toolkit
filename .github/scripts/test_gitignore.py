"""Every secret Claude is denied reading is also gitignored, so it can't be
committed by mistake or reach a review diff (review-diff.sh shows untracked
files that aren't ignored).

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sample_paths() -> list[str]:
    """A path for each repo-level Read deny rule: `**/` becomes a folder, `*` becomes `x`."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    paths = []
    for rule in settings["permissions"]["deny"]:
        if not rule.startswith("Read(") or rule.startswith(("Read(~", "Read(!")):
            continue
        pattern = rule[5:-1]
        path = pattern.lstrip("/").replace("**/", "sub/")
        if path.endswith("/**"):
            path = path[:-3] + "/x"
        path = path.replace("*", "x")
        paths.append(path)
        if not pattern.startswith("/"):  # unanchored, like `.env`: any folder
            paths.append("sub/" + path)
    return paths


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
        paths = sample_paths()
        self.assertGreater(len(paths), 20)
        missing = sorted(set(paths) - self.check_ignore(paths))
        self.assertEqual(missing, [], "add these to .gitignore, or drop the deny rule")

    def test_env_templates_are_not_ignored(self) -> None:
        templates = [f"{folder}.env.{kind}" for folder in ("", "sub/") for kind in ("example", "sample", "template")]
        self.assertEqual(self.check_ignore(templates), set())


if __name__ == "__main__":
    unittest.main()
