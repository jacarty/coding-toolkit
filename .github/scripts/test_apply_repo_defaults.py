"""Tests for .github/scripts/apply-repo-defaults.sh, against a stub `gh`.

The stub answers the few GitHub API reads the script makes from a JSON state
file, the way the real API does (including a 404's JSON body on stdout), and
logs every write. No network, no real repo.

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SCRIPT = SCRIPTS / "apply-repo-defaults.sh"
RULESET = json.loads((SCRIPTS.parent / "rulesets" / "main-protection.json").read_text(encoding="utf-8"))
NOT_FOUND = '{"message":"Not Found","documentation_url":"https://docs.github.com/rest","status":"404"}'

# A stub gh. State: {"repo": {...}, "rulesets": [...], "alerts": bool,
# "fixes": bool|null, "pvr": bool|null}; null means the endpoint 404s.
STUB = r'''
import json, os, sys
args = sys.argv[1:]
state = json.load(open(os.environ["GH_STUB_STATE"]))
if args[:2] == ["auth", "status"]:
    sys.exit(0)
if args[0] != "api":
    sys.exit(f"stub gh: unexpected {args}")
method, query, path, rest, i = "GET", None, None, args[1:], 0
while i < len(rest):
    a = rest[i]
    if a in ("-X", "-q", "-F", "--input"):
        if a == "-X": method = rest[i + 1]
        if a == "-q": query = rest[i + 1]
        i += 2
    elif a.startswith("-"):
        i += 1
    else:
        path, i = a, i + 1
if method != "GET":
    body = sys.stdin.read() if "--input" in rest else ""
    with open(os.environ["GH_STUB_LOG"], "a") as log:
        log.write(json.dumps([method, path, body]) + "\n")
    sys.exit(0)

def not_found():
    print(os.environ["NOT_FOUND"])
    sys.exit(1)

def enabled(value):
    if value is None: not_found()
    print("on" if value else "off") if query else print(json.dumps({"enabled": value}))

repo = state["repo"]["full_name"]
if path == f"repos/{repo}":
    print(json.dumps(state["repo"]))
elif path.startswith(f"repos/{repo}/rulesets?"):
    for r in state["rulesets"]:
        print(f"{r['name']}\t{r['id']}")
elif path.startswith(f"repos/{repo}/rulesets/"):
    if state.get("ruleset_read_fails"):
        sys.exit(1)  # e.g. a network error: no output at all
    found = [r for r in state["rulesets"] if str(r["id"]) == path.rsplit("/", 1)[1]]
    print(json.dumps(found[0])) if found else not_found()
elif path == f"repos/{repo}/vulnerability-alerts":
    if not state["alerts"]: not_found()  # GitHub answers 404 when they're off
elif path == f"repos/{repo}/automated-security-fixes":
    enabled(state["fixes"])
elif path == f"repos/{repo}/private-vulnerability-reporting":
    enabled(state["pvr"])
else:
    sys.exit(f"stub gh: unexpected path {path}")
'''


def live_ruleset(approvals: int = 0) -> dict:
    """The ruleset as GitHub returns it: with metadata and defaults of its own."""
    ruleset = copy.deepcopy(RULESET)
    for rule in ruleset["rules"]:
        if rule["type"] == "pull_request":
            rule["parameters"]["required_approving_review_count"] = approvals
            rule["parameters"]["required_reviewers"] = []  # a default the file doesn't set
    ruleset["rules"].reverse()  # order isn't guaranteed
    return {"id": 42, "node_id": "RRS_x", "source_type": "Repository", "source": "o/r",
            "created_at": "2026-01-01T00:00:00Z", "current_user_can_bypass": "pull_requests_only",
            "_links": {"self": {"href": "https://example.com"}}, **ruleset}


SCANNING_ON = {k: {"status": "enabled"} for k in ("secret_scanning", "secret_scanning_push_protection")}
SCANNING_OFF = {k: {"status": "disabled"} for k in ("secret_scanning", "secret_scanning_push_protection")}


def fresh_state(private: bool = True) -> dict:
    """A new repo. A private one without GitHub Secret Protection reports no
    secret scanning at all; a public one reports it as disabled."""
    return {
        "repo": {
            "full_name": "o/r", "private": private, "permissions": {"admin": True},
            "allow_squash_merge": True, "allow_merge_commit": True, "allow_rebase_merge": True,
            "delete_branch_on_merge": False, "security_and_analysis": None if private else SCANNING_OFF,
        },
        "rulesets": [], "alerts": False, "fixes": False, "pvr": None if private else False,
    }


def configured_state(private: bool = True) -> dict:
    """Everything this script sets, already set."""
    state = fresh_state(private)
    state["repo"].update(allow_rebase_merge=False, delete_branch_on_merge=True)
    if not private:
        state["repo"]["security_and_analysis"] = SCANNING_ON
        state["pvr"] = True
    state.update(rulesets=[live_ruleset()], alerts=True, fixes=True)
    return state


def pull_request(state: dict) -> dict:
    return next(r for r in state["rulesets"][0]["rules"] if r["type"] == "pull_request")["parameters"]


class ApplyRepoDefaultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        bin_dir = base / "bin"
        bin_dir.mkdir()
        (bin_dir / "stub_gh.py").write_text(STUB, encoding="utf-8")
        gh = bin_dir / "gh"
        gh.write_text(f'#!/bin/sh\nexec "{sys.executable}" -I "{bin_dir / "stub_gh.py"}" "$@"\n', encoding="utf-8")
        gh.chmod(0o755)
        self.state_file = base / "state.json"
        self.log = base / "writes.log"
        self.env = {
            **os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "GH_STUB_STATE": str(self.state_file), "GH_STUB_LOG": str(self.log), "NOT_FOUND": NOT_FOUND,
        }

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_script(self, state: dict, *args: str) -> subprocess.CompletedProcess[str]:
        self.state_file.write_text(json.dumps(state), encoding="utf-8")
        return subprocess.run(["bash", str(SCRIPT), "--repo", "o/r", *args],
                              capture_output=True, text=True, env=self.env)

    def writes(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_fresh_repo_preview_plans_everything_and_writes_nothing(self) -> None:
        for private in (True, False):
            with self.subTest(private=private):
                result = self.run_script(fresh_state(private))
                self.assertEqual(result.returncode, 0, result.stderr)
                for line in ("→ merge commits and squash", "→ main-protection: create", "→ Dependabot alerts",
                             "→ Dependabot security updates"):
                    self.assertIn(line, result.stdout)
                self.assertEqual("→ secret scanning" in result.stdout, not private)
                self.assertIn("Re-run with --apply", result.stdout)
                self.assertEqual(self.writes(), [])

    def test_error_bodies_never_reach_the_output(self) -> None:
        for private in (True, False):
            state = fresh_state(private)
            state["pvr"] = state["fixes"] = None  # both 404
            with self.subTest(private=private):
                result = self.run_script(state)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Not Found", result.stdout)
                self.assertIn("dependabot security updates=unknown", result.stdout)
                expected = "n/a" if private else "unknown"
                self.assertIn(f"private vulnerability reporting={expected}", result.stdout)

    def test_configured_repo_has_nothing_left_to_do(self) -> None:
        # What "run it" checks (docs/process.md): a re-run plans nothing and writes nothing.
        for private in (True, False):
            with self.subTest(private=private):
                self.log.unlink(missing_ok=True)
                result = self.run_script(configured_state(private))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("→", result.stdout)
                self.assertIn("✓ main-protection: ruleset 42 already matches", result.stdout)
                self.assertIn("Nothing to change.", result.stdout)
                result = self.run_script(configured_state(private), "--apply")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.writes(), [])
                self.assertEqual("not offered on this private repo" in result.stdout, private)

    def test_a_changed_ruleset_is_updated(self) -> None:
        result = self.run_script(configured_state(), "--approvals", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("→ main-protection: update ruleset 42 (approvals: 1)", result.stdout)
        result = self.run_script(configured_state(), "--approvals", "1", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([w[:2] for w in self.writes()], [["PUT", "repos/o/r/rulesets/42"]])

    def test_near_misses_are_not_a_match(self) -> None:
        changes = {
            "a rule removed": lambda s: s["rulesets"][0]["rules"].pop(),
            "rebase allowed": lambda s: pull_request(s).update(allowed_merge_methods=["merge", "squash", "rebase"]),
            "a method repeated": lambda s: pull_request(s).update(allowed_merge_methods=["merge", "merge"]),
            "a boolean flipped": lambda s: pull_request(s).update(dismiss_stale_reviews_on_push=False),
            "a count as a boolean": lambda s: pull_request(s).update(required_approving_review_count=False),
            "a reviewer added by hand": lambda s: pull_request(s).update(required_reviewers=[{"reviewer": {"id": 1}}]),
            "a bypass actor added": lambda s: s["rulesets"][0]["bypass_actors"].append(
                {"actor_id": 1, "actor_type": "Integration", "bypass_mode": "always"}),
            "an unknown setting on": lambda s: pull_request(s).update(some_new_setting=True),
        }
        for label, change in changes.items():
            state = configured_state()
            change(state)
            with self.subTest(label):
                result = self.run_script(state)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("→ main-protection: update ruleset 42", result.stdout)

    def test_an_unreadable_ruleset_is_updated_quietly(self) -> None:
        state = configured_state()
        state["ruleset_read_fails"] = True
        result = self.run_script(state)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("→ main-protection: update ruleset 42", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_apply_on_a_fresh_repo_writes_each_setting(self) -> None:
        result = self.run_script(fresh_state(private=False), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([w[:2] for w in self.writes()], [
            ["PATCH", "repos/o/r"],
            ["POST", "repos/o/r/rulesets"],
            ["PATCH", "repos/o/r"],
            ["PUT", "repos/o/r/vulnerability-alerts"],
            ["PUT", "repos/o/r/automated-security-fixes"],
            ["PUT", "repos/o/r/private-vulnerability-reporting"],
        ])
        self.assertEqual(json.loads(self.writes()[1][2])["name"], "main-protection")
        self.assertIn("secret_scanning", self.writes()[2][2])


if __name__ == "__main__":
    unittest.main()
