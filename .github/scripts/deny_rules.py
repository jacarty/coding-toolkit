"""Sample paths for the Read deny rules in .claude/settings.json, shared by
the tests that check other lists cover them (test_gitignore.py,
test_deny_parity.py). Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Rules that match at any depth are sampled at the root, one folder down and
# two down, so a narrower pattern elsewhere (`*/*.key` for `**/*.key`) fails.
# The same goes for what a folder rule (`/**`) and a `/**/` inside a rule cover.
DEPTHS = ("", "sub/", "a/b/")
# Stands in for `*`; a filler no real glob spells out, so a glob that
# names it literally can't pass by accident.
FILL = "zq9"


def deny_rules() -> list[str]:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return [rule[5:-1] for rule in settings["permissions"]["deny"]
            if rule.startswith("Read(") and not rule.startswith("Read(!")]


def repo_samples() -> list[str]:
    """A path for each repo-level rule at each depth it applies to: `*` becomes
    FILL, and a folder rule (`/**`) gets a file directly inside it and one two
    levels in. Rules for absolute paths (`//...`) aren't repo paths and are
    skipped."""
    samples = []
    for pattern in deny_rules():
        if pattern.startswith(("~", "//")):
            continue
        anywhere = pattern.startswith("/**/") or not pattern.startswith("/")
        body = pattern.lstrip("/").removeprefix("**/")
        bodies = [body]
        if body.endswith("/**"):  # a file directly inside, and two levels in
            bodies = [body[:-3] + "/x", body[:-3] + "/x/y"]
        # A `**` mid-pattern: zero folders, and two.
        bodies = [b2 for b in bodies for b2 in sorted({b.replace("/**/", "/"), b.replace("/**/", "/a/b/")})]
        for prefix in DEPTHS if anywhere else ("",):
            for b in bodies:
                samples.append(prefix + b.replace("*", FILL))
    return samples


def home_paths() -> list[str]:
    """Each home-folder rule's path, relative to `~`, without a trailing `/**`."""
    return [p[2:].removesuffix("/**") for p in deny_rules() if p.startswith("~/")]
