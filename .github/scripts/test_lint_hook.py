"""Tests for .claude/hooks/lint-edited-file.sh, using stub tools.

Each stub records the folder it ran from and its arguments, so the tests can
check which tools run, in what order, from where and with which flags, for
files in nested projects.

Run: python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "lint-edited-file.sh"

# A stub tool: logs "<name>\t<cwd>\t<args>" (tab-separated, so paths with
# spaces are fine) and succeeds on fix steps; fails a check when STUB_FAIL is set.
STUB = """#!/bin/sh
printf '%s\\t%s\\t%s\\n' "{name}" "$(pwd -P)" "$*" >> "$STUB_LOG"
case "$*" in *--fix*|*--write*|format*) exit 0 ;; esac
if [ -n "${{STUB_FAIL:-}}" ]; then echo "{name}: problem"; exit 1; fi
exit 0
"""


class LintHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve() / "my repo"  # a space, on purpose
        self.root.mkdir()
        self.log = self.root.parent / "stub.log"
        self.log.write_text("")
        self.path_dir = self.root.parent / "bin"  # for tools on PATH
        self.path_dir.mkdir()
        self.env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.root),
            "STUB_LOG": str(self.log),
            "PATH": f"{self.path_dir}{os.pathsep}{os.environ['PATH']}",
        }
        self.env.pop("STUB_FAIL", None)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def file(self, rel: str, content: str = "") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def stub(self, folder: Path | str, name: str) -> None:
        path = (self.root / folder if isinstance(folder, str) else folder) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(STUB.format(name=name))
        path.chmod(0o755)

    def run_hook(self, edited: Path, fail: bool = False) -> subprocess.CompletedProcess[str]:
        env = {**self.env, **({"STUB_FAIL": "1"} if fail else {})}
        payload = json.dumps({"tool_input": {"file_path": str(edited)}})
        return subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True, env=env, cwd=self.root.parent)

    def calls(self) -> list[tuple[str, str, str]]:
        """(tool, folder relative to the repo root, arguments), in call order."""
        out = []
        for line in self.log.read_text().splitlines():
            name, cwd, args = line.split("\t")
            out.append((name, os.path.relpath(cwd, self.root), args.replace(str(self.root) + "/", "")))
        return out

    def tools(self) -> list[tuple[str, str]]:
        return [(name, cwd) for name, cwd, _ in self.calls()]

    # ── JS/TS ────────────────────────────────────────────────────────────

    def test_frontend_package_uses_its_own_tools(self) -> None:
        self.file("frontend/package.json", "{}")
        self.file("frontend/eslint.config.js")
        self.file("frontend/.prettierrc")
        self.stub("frontend/node_modules/.bin", "eslint")
        self.stub("frontend/node_modules/.bin", "prettier")
        result = self.run_hook(self.file("frontend/src/app.ts", "x"))
        self.assertEqual(result.returncode, 0, result.stderr)
        # Prettier from the root (for root ignore files), ESLint from its config folder.
        self.assertEqual(self.tools(), [("prettier", "."), ("eslint", "frontend"), ("eslint", "frontend")])

    def test_hoisted_monorepo(self) -> None:
        self.file("package.json", "{}")
        self.stub("node_modules/.bin", "eslint")
        self.file("packages/web/package.json", "{}")
        self.file("packages/web/eslint.config.js")
        result = self.run_hook(self.file("packages/web/src/a.js", "x"), fail=True)
        self.assertEqual(result.returncode, 2)  # leftover issues go back to Claude
        self.assertIn("eslint: problem", result.stderr)
        self.assertEqual(set(self.tools()), {("eslint", "packages/web")})

    def test_root_package_json_config_is_inherited(self) -> None:
        self.file("package.json", '{"prettier": {}}')
        self.stub("node_modules/.bin", "prettier")
        self.file("packages/web/package.json", "{}")  # no prettier key of its own
        self.run_hook(self.file("packages/web/src/a.json", "{}"))
        self.assertEqual(self.tools(), [("prettier", ".")])

    def test_nested_eslint_config_without_a_package_json(self) -> None:
        self.file("package.json", "{}")
        self.stub("node_modules/.bin", "eslint")
        self.file("frontend/eslint.config.js")
        self.run_hook(self.file("frontend/src/a.ts", "x"))
        self.assertEqual(set(self.tools()), {("eslint", "frontend")})

    def test_eslint_flag_follows_the_nearest_config(self) -> None:
        self.file("eslint.config.js")  # flat config at the root
        self.stub("node_modules/.bin", "eslint")
        self.file("legacy/.eslintrc.json", "{}")  # legacy config in a package
        self.run_hook(self.file("legacy/a.js", "x"))
        self.run_hook(self.file("modern/b.js", "x"))
        flags = {cwd: "--no-warn-ignored" in args for name, cwd, args in self.calls()}
        self.assertEqual(flags, {"legacy": False, ".": True})

    def test_root_prettierignore_still_applies_in_a_package(self) -> None:
        self.file(".gitignore", "dist/\n")
        self.file(".prettierignore", "generated/\n")
        self.file("package.json", '{"prettier": {}}')
        self.stub("node_modules/.bin", "prettier")
        self.file("web/package.json", "{}")
        self.run_hook(self.file("web/a.json", "{}"))
        (_, cwd, args), = self.calls()
        self.assertEqual(cwd, ".")  # from the root, prettier reads the root ignore files itself
        self.assertNotIn("--ignore-path", args)
        # A package's own .prettierignore is added on top of the root's.
        self.file("web/.prettierignore", "fixtures/\n")
        self.log.write_text("")
        self.run_hook(self.file("web/b.json", "{}"))
        (_, _, args), = self.calls()
        for ignore in (".gitignore", ".prettierignore", "web/.prettierignore"):
            self.assertIn(f"--ignore-path={ignore}", args)

    def test_biome_replaces_prettier_and_eslint(self) -> None:
        self.file("app/biome.json", "{}")
        self.file("app/.prettierrc")
        self.stub("node_modules/.bin", "biome")
        self.stub("node_modules/.bin", "prettier")
        self.run_hook(self.file("app/src/x.ts", "x"))
        self.assertEqual(self.tools(), [("biome", "app")])

    def test_unconfigured_tools_are_not_run(self) -> None:
        self.file("frontend/package.json", '{"devDependencies": {"eslint": "9"}}')
        self.stub("frontend/node_modules/.bin", "eslint")
        self.run_hook(self.file("frontend/a.ts", "x"))
        self.assertEqual(self.calls(), [])

    def test_sibling_projects_dont_leak(self) -> None:
        self.file("frontend/eslint.config.js")
        self.stub("frontend/node_modules/.bin", "eslint")
        self.file("backend/package.json", "{}")
        self.run_hook(self.file("backend/tool.js", "x"))
        self.assertEqual(self.calls(), [])

    # ── Python ───────────────────────────────────────────────────────────

    def test_backend_python_uses_its_venv(self) -> None:
        self.file("backend/pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        self.stub("backend/.venv/bin", "ruff")
        self.run_hook(self.file("backend/app/main.py", "x = 1\n"))
        self.assertEqual(set(self.tools()), {("ruff", "backend")})

    def test_ruff_on_path_only_when_configured(self) -> None:
        self.stub(self.path_dir, "ruff")
        self.run_hook(self.file("svc/main.py", "x = 1\n"))
        self.assertEqual(self.calls(), [])  # no ruff config anywhere
        self.file("ruff.toml", "")
        self.run_hook(self.file("svc/main.py", "x = 1\n"))
        self.assertEqual(set(self.tools()), {("ruff", ".")})

    # ── What's skipped ───────────────────────────────────────────────────

    def test_skips_outside_the_project_and_node_modules(self) -> None:
        self.file("package.json", '{"prettier": {}}')
        self.stub("node_modules/.bin", "prettier")
        outside = self.root.parent / "outside.json"
        outside.write_text("{}")
        self.assertEqual(self.run_hook(outside).returncode, 0)
        os.symlink(outside, self.root / "link.json")  # a symlink that leaves the repo
        self.assertEqual(self.run_hook(self.root / "link.json").returncode, 0)
        self.assertEqual(self.run_hook(self.file("node_modules/pkg/index.json", "{}")).returncode, 0)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
