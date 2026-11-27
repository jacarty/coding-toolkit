"""Codex and Antigravity deny every secret Claude is denied, so a rule added
to Claude's list can't be forgotten in theirs. One way only: a rule only
Codex or Antigravity has isn't flagged.

- Claude: the Read deny rules in .claude/settings.json.
- Codex: both permission profiles in .codex/config.toml.
- Antigravity: the home-folder paths in the snippet in docs/toolkit.md
  (it has no per-repo rules, so only home-folder paths are compared).

It checks the lists agree, using Python's glob matching as a stand-in for
each tool's own: not that each tool enforces them.

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import ast
import re
import tomllib
import unittest
from pathlib import PurePosixPath

from deny_rules import ROOT, home_paths, repo_samples

PROFILES = ("toolkit", "toolkit-review")
# Left out on purpose for Codex and Antigravity: they hold the registry
# settings too, so hiding them sends npm and pip to the public registry.
HOME_EXCEPTIONS = {".npmrc", ".pypirc"}


def codex_profile(name: str) -> tuple[set[str], set[str]]:
    """A Codex profile's deny globs inside the repo, and its home-folder deny paths."""
    config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
    fs = config["permissions"][name]["filesystem"]
    repo = {glob for glob, mode in fs[":workspace_roots"].items() if mode == "deny"}
    home = {path[2:] for path, mode in fs.items() if path.startswith("~/") and mode == "deny"}
    return repo, home


def antigravity_home() -> set[str]:
    """The home-folder paths in the Antigravity settings snippet in docs/toolkit.md."""
    doc = (ROOT / "docs" / "toolkit.md").read_text(encoding="utf-8")
    match = re.search(r"^paths = (\[[^\]]*\])", doc, re.MULTILINE)
    assert match, "the Antigravity snippet's `paths = [...]` list wasn't found in docs/toolkit.md"
    paths = set(ast.literal_eval(match.group(1)))
    return paths


def under(path: str, denied: set[str]) -> bool:
    """Whether a home-relative path is a denied path or inside one."""
    return any(d in ("", ".") or path == d or path.startswith(d + "/") for d in denied)


class DenyParityTests(unittest.TestCase):
    def test_codex_denies_what_claude_denies_in_the_repo(self) -> None:
        repo = repo_samples()
        self.assertGreater(len(repo), 50)
        for profile in PROFILES:
            globs, _ = codex_profile(profile)
            missing = [p for p in repo if not any(PurePosixPath(p).full_match(g) for g in globs)]
            self.assertEqual(missing, [], f"add a deny glob to [permissions.{profile}] in .codex/config.toml")

    def test_codex_and_antigravity_deny_claudes_home_paths(self) -> None:
        wanted = [p for p in home_paths() if p not in HOME_EXCEPTIONS]
        self.assertGreater(len(wanted), 10)
        for profile in PROFILES:
            _, denied = codex_profile(profile)
            missing = [p for p in wanted if not under(p, denied)]
            self.assertEqual(missing, [], f"add a home deny to [permissions.{profile}] in .codex/config.toml")
        missing = [p for p in wanted if not under(p, antigravity_home())]
        self.assertEqual(missing, [], "add these to the Antigravity snippet's paths in docs/toolkit.md")

    def test_exceptions_stay_out_and_are_still_claude_rules(self) -> None:
        self.assertTrue(HOME_EXCEPTIONS <= set(home_paths()), "an exception is no longer a Claude rule: drop it here")
        # Not denied directly, or through a folder that holds them.
        for profile in PROFILES:
            self.assertEqual([e for e in HOME_EXCEPTIONS if under(e, codex_profile(profile)[1])], [])
        self.assertEqual([e for e in HOME_EXCEPTIONS if under(e, antigravity_home())], [])

    def test_antigravity_paths_are_plain(self) -> None:
        # Antigravity takes plain paths only: no patterns, and no `~`.
        self.assertEqual([p for p in antigravity_home() if set(p) & set("*?[~")], [])

    def test_the_two_codex_profiles_deny_the_same(self) -> None:
        self.assertEqual(codex_profile("toolkit"), codex_profile("toolkit-review"))


if __name__ == "__main__":
    unittest.main()
