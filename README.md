# coding-toolkit

A GitHub template for starting projects with AI coding agents. Built around **Claude Code**, with **Codex** and **Antigravity** (Gemini) as cross-model reviewers, and a development process that runs the right reviews before every PR.

It's my own working setup and it keeps evolving. Fork it, or take the pieces you want.

## What you get

- **One set of agent rules.** `AGENTS.md` holds the project's instructions; `CLAUDE.md` just imports it, so Claude Code, Codex and Antigravity all follow the same rules.
- **Reviews before every PR.** Subagents review code and CI/infrastructure and write missing tests; a skill keeps the docs current. Then two more model families: Gemini (via Antigravity) reviews locally before the PR opens, and Codex reviews the PR on GitHub, following the review guidelines in `AGENTS.md`. One model's blind spots don't decide what ships. Every gate sees the same diff: committed, staged, unstaged and untracked changes.
- **Safe defaults for Claude Code.** A short allow list, designed for auto mode. Deny rules keep Claude's file tools away from `.env` files, keys, cloud credentials and Terraform state (a guardrail, not a sandbox; see [the limits](docs/toolkit.md#claude-code-permissions-claudesettingsjson)).
- **Guardrails in git.** gitleaks and file-size checks on every commit, through the pre-commit framework. The repo's own tested hooks check Conventional Commits messages and branch names, and block pushing straight to `main`.
- **Protection on GitHub.** One script applies a `main` ruleset (PRs only, CI must pass), secret scanning, push protection and Dependabot. Templates don't copy these settings, so every new repo needs them applied.
- **A lint hook that costs no tokens.** After each edit Claude makes, the project's own formatters and linters run, in monorepos too. Only what they can't fix goes back to Claude.
- **Planning and thinking skills.** Requirements, research and build guides, plus tree-of-thought, trade-off analysis and strategy frameworks.
- **A supply-chain rule.** Use current major versions only, nothing released in the last 7 days, and exact pins.

## Quick start

You'll need `git`, `python3`, [pre-commit](https://pre-commit.com) (`brew install pre-commit` or `uv tool install pre-commit`) and the GitHub CLI, signed in (`gh auth login`), with admin on the new repo.

1. Click **Use this template**, then clone your new repo.
2. Run the first-run setup. It fills in the placeholders and installs the git hooks.
   ```bash
   .github/scripts/init-from-template.sh           # preview
   .github/scripts/init-from-template.sh --apply
   ```
3. Commit the result on a branch and open a PR.
4. Once that PR is merged and `main` has reported `toolkit-checks`, protect `main` and apply the repo defaults:
   ```bash
   .github/scripts/apply-repo-defaults.sh          # preview
   .github/scripts/apply-repo-defaults.sh --apply
   ```
5. Turn on auto mode: merge these keys into your user settings, `~/.claude/settings.json`, rather than replacing the file (why: [permissions](docs/toolkit.md#claude-code-permissions-claudesettingsjson)):
   ```json
   { "permissions": { "defaultMode": "auto" }, "autoMode": { "classifyAllShell": true } }
   ```
6. Fill in `AGENTS.md` and start Claude Code.

Optional but recommended:

- install the [Codex GitHub app](https://chatgpt.com/codex) on the repo, so Codex reviews every PR;
- install the Antigravity (`agy`) and [`codex`](https://github.com/openai/codex) CLIs, for the local cross-model reviews.

## What's inside

| Path | What it is |
|---|---|
| `AGENTS.md` | Project rules for every agent: architecture, conventions, the version policy |
| `docs/process.md` | Which reviews run when: before a PR, at phase boundaries, and the fast path for trivial changes |
| `.claude/agents/` | Five subagents: code review, CI and infra review, test writing, codebase review, phase acceptance |
| `.claude/skills/` | Cross-model review, doc and refactor workflows, planning and thinking frameworks |
| `.claude/hooks/` | The lint hook |
| `.claude/settings.json` | Permissions and deny rules (`settings.example.jsonc` explains them and lists opt-ins) |
| `.githooks/`, `.pre-commit-config.yaml` | Git hooks: gitleaks, file sizes, commit messages, branch names |
| `.github/` | CI (`toolkit-checks`), the `main` ruleset, setup and review scripts, issue and PR templates |
| `docs/` | PRD, build guide, ADR and tech-debt templates |

The full reference, covering setup in detail, every file and setting, and the design decisions behind them, is in **[docs/toolkit.md](docs/toolkit.md)**.

Skills also work in Claude Desktop and claude.ai: upload a skill's `SKILL.md` to a Project's knowledge ([steps](docs/toolkit.md#claude-desktop-or-claudeai-skills-only)).

## Licence

MIT
