# Toolkit reference

The full reference for this template: every skill, agent, command, hook, script and setting, and why each is set up the way it is. In the template itself, the [README](../README.md) is the short overview and quick start; in a repo created from it, `init-from-template.sh` replaces the README with a stub for the new project.

Contents: [Setting up a new repo](#setting-up-a-new-repo) · [What's included](#whats-included) · [Using agents](#using-agents) · [Using skills](#using-skills) · [Customisation](#customisation)

## Setting up a new repo

**Prerequisites:** `git`, `python3`, [pre-commit](https://pre-commit.com), and the GitHub CLI (`gh`), signed in with `gh auth login`. Applying the repo defaults needs admin on the repo.

### Claude Code (full toolkit)

1. Click **Use this template** on GitHub to create a new repository
2. Clone your new repo
3. Install [pre-commit](https://pre-commit.com) if you don't have it (`uv tool install pre-commit` or `brew install pre-commit`), then run the first-run setup: `.github/scripts/init-from-template.sh` to preview, then `--apply`. It fills in the project name (AGENTS.md and the doc templates), the CODEOWNERS owner and the LICENSE holder, replaces the toolkit's README with a stub for your project, and installs the git hooks. The defaults come from `gh` and `git config`; override them with `--name`, `--owner` and `--author`. Without `gh`, `--apply` also needs `--skip-template-check`, because it can't confirm the repo isn't the template itself.
4. Review the changes with `git diff`, then commit them on a branch and open a PR
5. Once that PR is merged and `main` has reported `toolkit-checks`, protect `main` and set the repo defaults: `.github/scripts/apply-repo-defaults.sh` to preview, then `--apply` (see **Repo defaults** under [GitHub templates](#github-templates-github))
6. Fill in `AGENTS.md` with your project's architecture and conventions (look for `[...]` and `<!-- ... -->` placeholders)
7. Copy any optional permissions you need from `.claude/settings.example.jsonc` into `.claude/settings.json` (strict JSON: no comments, no trailing commas)
8. Optional: install and log in to the [`codex`](https://github.com/openai/codex) and Antigravity (`agy`) CLIs for the cross-model review skills
9. Start Claude Code — all agents, commands, and skills are available immediately

### Claude Desktop or Claude.ai (skills only)

1. Clone or download this repo
2. Open the Claude desktop app or claude.ai
3. Create or open a **Project**
4. Click the project name to open **Project Knowledge**
5. Click **Add content** → **Upload files**
6. Upload the `SKILL.md` file from any skill folder under `.agents/skills/` (or `.claude/skills/` for the cross-model ones)

The skill will trigger automatically based on what you ask within that project.

## What's included

### Skills (`.agents/skills/`, `.claude/skills/`)

Nine reusable thinking, planning, and strategy frameworks, eight development workflows, five review and test gates, and two cross-model review skills. Claude Code loads them automatically based on what you ask.

**One copy, three tools.** The shared skills live in `.agents/skills/`, where Codex and Antigravity read them, and `.claude/skills/` links to each one for Claude Code. Only the two cross-model skills (`codex`, `antigravity`) live in `.claude/skills/` itself, since they exist to call the other tools. To add a shared skill, create it in `.agents/skills/<name>/` and link it: `ln -s ../../.agents/skills/<name> .claude/skills/<name>`; `toolkit-checks` fails if the link is missing. On Windows, turn on Developer Mode (or use an admin shell) and clone with symlinks on: `git clone -c core.symlinks=true <repo>`. Otherwise the links check out as plain text files and Claude Code can't load the shared skills; `toolkit-checks` says so. To fix an existing clone, run `git config core.symlinks true`, then `git checkout -- .claude/skills`. For Claude Desktop or Claude.ai, upload individual `SKILL.md` files to Project Knowledge.

#### Thinking & Decision-Making

| Skill | Purpose | Use When |
|---|---|---|
| `tree-of-thought` | Structured branching, evaluation, and pruning | You need to compare distinct approaches and pick one |
| `graph-of-thought` | Interconnected exploration where ideas merge and combine | The best answer combines elements from multiple angles |
| `trade-off-analysis` | Quick pros/cons comparison with a clear recommendation | You have 2-3 known options and want a decisive answer |

#### Project Planning Workflow

| Skill | Purpose | Use When |
|---|---|---|
| `requirements-elicitation` | Structured interview to turn a vague brief into a spec | You have an idea but not yet a clear specification |
| `research-brief` | Investigate the technical landscape and produce findings with a recommended approach | Requirements exist and you need to compare libraries, frameworks, or patterns before committing |
| `implementation-spec` | Turn requirements and research into a phased build guide with acceptance criteria | You have a researched problem and need a concrete plan to build it |

These three chain together: elicit requirements → research the approach → spec the build.

#### Strategy & Business Analysis

| Skill | Purpose | Use When |
|---|---|---|
| `design-thinking-ideation` | Empathise → Define → Ideate → Prototype → Test workflow for generating and validating solution concepts | You want to move from customer pain points to prototyped, testable ideas |
| `value-chain-analysis` | Porter's Value Chain — map primary and support activities to find cost and differentiation drivers | You're asking "where in the business is value created or destroyed?" |
| `vrio-analysis` | VRIO framework — assess whether resources/capabilities deliver sustainable competitive advantage | You're asking "is this defensible — what's our moat?" |

#### Development Workflows

| Skill | Purpose | Use When |
|---|---|---|
| `doc-generator` | Creates and updates READMEs, AGENTS.md, docstrings, API docs, changelogs and ADRs; doubles as the pre-PR doc gate | Docs need writing, or a non-trivial PR is about to open |
| `refactorer` | Framework upgrades, dependency migrations and pattern modernisation, with incremental, test-verified changes | Refactor or migration work is scoped |
| `code-optimiser` | Finds bottlenecks, N+1 queries, unnecessary allocations and algorithmic waste; reports before editing | Performance is a concern |
| `dependency-check` | Checks a dependency before it's added or bumped: current major, released at least 7 days ago, pinned exactly | Adding or upgrading a package, action, image, runtime or hook; setting up a new repo |
| `debugging` | Reproduce, narrow down, one hypothesis at a time, fix the root cause, then a regression test that fails without the fix | A bug, failing test or CI job, or unexpected behaviour, before proposing a fix |
| `commit-and-pr` | Checks the branch name, staging, local checks and pre-PR gates, then writes the Conventional Commits message and the PR body from the template | The change is ready to commit, or you need the commit or PR text |
| `adopt-toolkit` | Brings the toolkit into an existing repo that wasn't made from the template: takes stock, lets you pick the pieces, copies what's missing and merges what exists, never overwriting | Adding the toolkit to an existing project (run it with a toolkit checkout and the target repo) |
| `project-retrospective` | A one-page retro: goal against outcome, what went well and badly (to root cause), surprises, and at most three follow-ups. You review the draft item by item; only what you confirm is saved to `docs/retrospectives/` | End of a phase or project, or when you ask; not per PR |

The first three were subagents until they were converted to skills. They work from what the session already knows (the diff, the files just read), so running them in the main conversation saves a cold start that re-reads the same context. Reviewers that need independence run as gate skills in their own agent (below).

#### Review and Test Gates (fresh context)

Each runs in its own agent (`context: fork` and `agent:` in the skill), so it starts fresh and never sees the session that wrote the code. Codex and Antigravity don't start a fresh agent for them: to keep a gate independent there, run it in a new session, not the one that wrote the code.

| Skill | Runs in agent | Purpose |
|---|---|---|
| `code-review-gate` | `code-reviewer` | Reviews the change for correctness, design, error handling, tests and basic security. Read-only |
| `devops-review-gate` | `devops-reviewer` | Reviews workflows, containers, IaC, hooks and tooling config. Read-only; reports changes, doesn't make them |
| `test-generation` | `test-generator` | Writes missing tests and reviews existing ones |
| `phase-acceptance-check` | `phase-acceptance` | Checks a build-guide phase against every PRD requirement before its closing PR |
| `codebase-assessment` | `codebase-review` | A structured assessment of the whole repo, at phase ends or for an unfamiliar codebase |

#### Cross-Model Review (Claude Code only)

| Skill | Purpose | Use When |
|---|---|---|
| `antigravity` | Read-only review from Gemini via the `agy` CLI, run in a clean git worktree | The pre-PR gate on every PR (see `docs/process.md`), or a second opinion on a plan or ADR |
| `codex` | Read-only review from OpenAI Codex via the `codex` CLI | Ad hoc: a second opinion on uncommitted work, a plan, an ADR or a high-risk change |

A different model family has different blind spots. Between them, a PR is seen by three: Claude (the subagents), Gemini (the `antigravity` gate, locally before the PR opens) and Codex. Codex reviews on GitHub through the Codex GitHub app, installed per repo, and follows the **Review guidelines** in `AGENTS.md`: blocking issues only, security first. Its P0 and P1 findings are fixed or justified before merging (`docs/process.md`, remote gates). The `codex` skill adds a local Codex review before the PR exists, when you want one. Both skills need the CLI installed and logged in on your machine; if it isn't, the review is skipped and noted, never blocking. Both send content to the vendor under your account, so they refuse to read secrets, `.env*` files, state files or raw logs. Neither is for unattended agent runs.

#### Choosing between the thinking skills

**Trade-Off Analysis** — fast, decisive, 2-3 known options. "Should I use X or Y?"

**Tree of Thought** — thorough, branching exploration. "What are all my options and which is best?"

**Graph of Thought** — deep, interconnected synthesis. "How do I combine the best parts of multiple approaches?"

When in doubt: if the options are already known and few, use Trade-Off Analysis. If you need to discover options, use Tree of Thought. If the options overlap and could be combined, use Graph of Thought.

### Agents (`.claude/agents/`)

Five agents that the gate skills above run in. Each starts with a fresh context, which keeps reviews independent of the session that wrote the code and keeps their verbose reading out of your main conversation. An agent file sets the model, tools and memory; its instructions live in its skill, so Codex and Antigravity can use them too. Claude Code can also delegate to an agent directly, or you can call one with `@agent-name`; it then reads its skill first.

| Agent | Model | Purpose |
|---|---|---|
| `code-reviewer` | Opus | Reviews code for style, complexity, anti-patterns, naming, and architectural smells. Read-only. |
| `codebase-review` | Sonnet | Scans a repo and produces a structured briefing covering tech stack, architecture, posture assessment, and recommendations. Read-only. |
| `test-generator` | Sonnet | Generates unit tests, suggests edge cases, and reviews existing tests for quality and coverage gaps. |
| `devops-reviewer` | Sonnet | Reviews GitHub Actions workflows, Dockerfiles, Kubernetes manifests, Terraform/CloudFormation templates, git hooks and tooling configuration. Read-only: it reports, and the main session applies fixes. |
| `phase-acceptance` | Opus | Validates that a build-guide phase is complete before the PR opens. Checks code against every PRD requirement and verification checkpoint. |

All agents have `memory: project` set, so they accumulate knowledge about this codebase's patterns across sessions.

### Commands (`.claude/commands/`)

| Command | Description |
|---|---|
| `/create_worktree <type/slug>` | Creates a git worktree for the branch in `.trees/<type-slug>`. It checks the name, branches from the default branch, and opens it in VS Code if available. Dependencies are installed per worktree, not shared |
| `/merge_worktree <type/slug>` | Finishes a worktree's branch through a PR, never a local merge into `main`. It brings the branch up to date with the default branch, runs the checks and opens the PR. After the merge, it removes the worktree and the branch |

### Development process (`docs/process.md`)

A codified development process that defines when each agent runs automatically during the PR lifecycle:

- **On every edit** — a lint hook formats and lints each edited file with the project's own tools, at no token cost
- **Pre-PR gates** — code-reviewer, devops-reviewer, test-generator, and the doc-generator skill run conditionally based on what changed; antigravity runs on every PR. Every PR that changes behaviour is also run before it opens: use what was built, the way it will be used, and check it works, because tests and reviewers only check the code. Findings are folded into the branch before the PR opens
- **Phase boundaries** — codebase-review and doc-generator refresh tech-debt tracking and AGENTS.md at the end of each build-guide phase, and a short retrospective goes in `docs/retrospectives/`
- **Phase acceptance** — phase-acceptance validates PRD requirements when a phase closes out
- **Trivial-change fast path** — small changes (≤ 50 lines changed, added plus removed; ≤ 2 files; no critical paths) skip all gates except antigravity (and run it, if the change alters behaviour)
- **No direct commits to main** — docs-only changes go through a `docs/<slug>` PR too

The process doc also covers branch/PR cadence, issue tracking conventions, fold timing for gate findings, and how to handle agent feedback.

**Changing the template itself.** In this template's own repo, what gets built is the starting point of new projects, so "run it" means making one. For a change to anything a new project inherits, make a new repo from your branch: push the branch's files to a new private repo as one initial commit, which is what **Use this template** does. Then follow the README quick start through `init-from-template.sh`, the new project's first PR and `apply-repo-defaults.sh`, and run the template's tests and checks inside the new project, since it inherits them. That catches files that break once the placeholders are filled in, which no check in the template's own repo can see. Delete the trial repo afterwards.

### Git hooks (`.githooks/`, `.pre-commit-config.yaml`)

Installed once per clone with `.githooks/setup-hooks.sh`; the first-run setup script does this for you. Requires the [pre-commit](https://pre-commit.com) tool: `uv tool install pre-commit`, `pipx install pre-commit` or `brew install pre-commit`.

| Hook | Runs | What it does |
|---|---|---|
| `pre-commit` | Before each commit | Runs the [pre-commit](https://pre-commit.com) framework with `.pre-commit-config.yaml`: [gitleaks](https://github.com/gitleaks/gitleaks) for secrets (output redacted), plus private keys, files over 5MB (new or grown) and merge-conflict markers. Unstaged changes are stashed while it runs, so it checks exactly what's being committed |
| `commit-msg` | After writing the commit message | Validates the Conventional Commits format (`type(scope): description`). The description can start with a lowercase letter, a digit or an acronym |
| `pre-push` | Before each push | Checks every branch being pushed, not just the checked-out one. Blocks pushing straight to the default branch, and checks `type/slug` names (short slugs like `fix/ci` are fine) |

**Scanners:** gitleaks and pre-commit-hooks are maintained tools, pinned to release commit SHAs under the 7-day rule. The Go version that builds gitleaks is pinned too, because without it pre-commit downloads the newest Go on a machine that has none. Don't update them with `pre-commit autoupdate`, which takes the newest release however new: check the versions with the `dependency-check` skill when you set up a repo, and bump them the same way.

**False positives:** for a deliberate example in code, add a `gitleaks:allow` comment on that line. For a whole file or finding, use `.gitleaksignore`.

**Linters (optional):** code linting runs through Claude's lint hook after each edit, which doesn't cover Codex, Antigravity or people. To lint at commit time too, add `local` hooks that run the linters the project already installs, so their versions come from its lockfile and need no pins here. For example:

```yaml
  - repo: local
    hooks:
      - id: ruff
        name: ruff
        entry: ruff check --force-exclude
        language: system
        types_or: [python, pyi]
      - id: eslint
        name: eslint
        entry: npx --no-install eslint
        language: system
        types_or: [javascript, jsx, ts, tsx]
      - id: shellcheck
        name: shellcheck
        entry: shellcheck
        language: system
        types_or: [sh, bash]
```

Keep only the ones the project uses; each needs its tool installed (as a dev dependency, or on the PATH; in a uv project, `entry: uv run ruff check --force-exclude`). pre-commit's own hook repos for these tools would need pinning under the 7-day rule, and they run a second copy of the tool whose version can drift from the project's.

**Scanning the whole repo:** the gitleaks hook only looks at what's staged, even with `pre-commit run --all-files`. Install gitleaks itself (`brew install gitleaks`), then run `gitleaks dir .` for the current files or `gitleaks git .` for the full history.

**Skipping:** any hook can be skipped with `--no-verify`.

**What GitHub enforces:** push protection blocks known secret formats, and the `main-protection` ruleset requires a PR and a passing `toolkit-checks` to change the default branch. Branch names, commit messages, file sizes and conflict markers are checked only locally.

**Tests:** `.github/scripts/test_githooks.py` runs in CI. It installs the hooks with `setup-hooks.sh`, using a stub `pre-commit`, then makes real commits and pushes to a bare remote. It also covers removing the worktree that installed the hooks.

### GitHub templates (`.github/`)

| File | Purpose |
|---|---|
| `CODEOWNERS` | Default code ownership. Ships with a `@YOUR-GITHUB-USERNAME` placeholder that `init-from-template.sh` fills in |
| `SECURITY.md` | Security policy with vulnerability reporting instructions |
| `pull_request_template.md` | Default PR description with What/Why/How/Testing sections and a checklist that includes the pre-PR gates |
| `ISSUE_TEMPLATE/bug_report.yml` | Structured bug report form |
| `ISSUE_TEMPLATE/feature_request.yml` | Structured feature request form |
| `workflows/toolkit-checks.yml` | CI on every PR and push to `main`, running the checks below. Keep it in projects you create from the template, and add your own build and test workflow next to it |
| `scripts/check_toolkit.py` | The checks the workflow runs, standard library only; CI runs it on Python 3.14. Run locally with `python3 -I .github/scripts/check_toolkit.py` |
| `scripts/test_*.py` | Tests for the checker, the git hooks, `.gitignore` (it must ignore every secret Claude is denied), `review-diff.sh`, the lint hook, `init-from-template.sh` and `apply-repo-defaults.sh` (against a stub `gh`), run by the workflow: `python3 -I -m unittest discover -s .github/scripts -p 'test_*.py'` |
| `dependabot.yml` | Weekly PRs to bump the SHA-pinned GitHub Actions. Add your project's own package ecosystems here |
| `rulesets/main-protection.json` | Protection for the default branch, kept as code. Changes only through PRs; merge commits or squash; no force-pushes or deletion; `toolkit-checks` must pass. Repo admins can bypass on a PR, never by pushing directly |
| `scripts/review-diff.sh` | Prints the whole change against the default branch (committed, staged, unstaged and untracked); `--stat` for a summary. Every review gate uses it, so they all review the same thing |
| `scripts/init-from-template.sh` | First-run setup for a new repo: fills in placeholders, replaces the toolkit's README with a project stub, and installs the git hooks. Previews by default and is safe to re-run. It edits only tracked files, and refuses to apply unless `gh` confirms the repo isn't the template itself (or you pass `--skip-template-check`) |
| `scripts/apply-repo-defaults.sh` | Applies the rulesets and the repo settings a template doesn't copy (below). Safe to re-run: what already matches is marked ✓ and left alone |

**Repo defaults.** "Use this template" copies files, not settings, so a new repo starts with `main` unprotected. `.github/scripts/apply-repo-defaults.sh` shows what it would change; add `--apply` to apply it. It needs `gh` with admin on the repo. It sets:

- every ruleset in `.github/rulesets/`, created or updated in place by name;
- merge commits and squash allowed (no rebase), and branches deleted on merge;
- secret scanning and push protection;
- Dependabot alerts and security updates;
- private vulnerability reporting.

`--approvals N` requires reviews for team repos; the default is 0 for solo work. Rulesets on private repos need GitHub Pro or above. Secret scanning on private repos needs GitHub Secret Protection. Anything GitHub refuses is reported, and the rest still applies.

Apply the ruleset once the default branch's CI has reported `toolkit-checks` at least once, which for a new repo means after its first push. Any open PR still on an older workflow then needs an update from `main` before it can merge.

Merge through the PR. GitHub also accepts a push that fast-forwards `main` to a PR's head once that head has passed its checks: it marks the PR merged, but `main` gets no merge commit showing where the branch came in.

`toolkit-checks` runs these checks:

- `.claude/settings.json` is strict JSON. Claude Code skips the whole file on a `//` comment or a trailing comma, silently dropping every permission and hook.
- Hook scripts exist and are executable.
- Every status check a ruleset requires is a real workflow job. A renamed job would otherwise block every merge.
- Skill and agent names match their folders, and every description fits the skill listing. Every shared skill in `.agents/skills/` is linked from `.claude/skills/` with a relative link that resolves.
- Relative links and images between docs resolve (code blocks and HTML comments are skipped).
- ShellCheck passes on every shell script (picked by its shebang) in `.claude/hooks/`, `.githooks/` and `.github/scripts/`.

Each check runs even when an earlier one fails, and errors are annotated on the line in the PR diff.

Actions are pinned to commit SHAs, and the job token is read-only.

### Claude Code permissions (`.claude/settings.json`)

Pre-approves a minimal core of tool invocations so Claude Code doesn't prompt for confirmation on routine operations, and wires up the lint hook. The file must be strict JSON: Claude Code treats a `//` comment or a trailing comma as a syntax error and skips the whole file. The `$schema` line gives you validation and autocomplete in most editors.

**Use auto mode.** In auto mode, a classifier reviews each action by what it does, not how it's spelled. It lets routine git work through and blocks force-pushes, discarded uncommitted work, `--amend` on commits from outside the session, printed tokens and download-and-run. An `allow` rule *skips* that classifier, so this template keeps the allow list short on purpose. Project settings can't turn auto mode on, so set it once in your user settings, `~/.claude/settings.json`:

```json
{
  "permissions": { "defaultMode": "auto" },
  "autoMode": { "classifyAllShell": true }
}
```

`classifyAllShell` (Claude Code v2.1.193 or later) sends even allow-listed shell commands through the classifier. Merge these keys into your existing file rather than replacing it.

**Allowed by default** (`.claude/settings.json`):

- **Read-only `gh`:** viewing PRs, runs, issues, releases and the repo. Not `gh auth status`, whose `-t` flag prints your token.
- **`WebSearch`.**

That's all. A rule ending in `*` approves every flag, and most tools have flags that write or run anything:

- `pytest --basetemp=DIR` deletes `DIR`;
- `ruff check --output-file=FILE` truncates `FILE`;
- `npm run env -- CMD` runs any command.

So tests, linters and scripts aren't pre-approved either.

Read-only shell commands (`ls`, `cat`, `grep`, `find` without `-exec`, read-only `git`) need no rule: Claude Code already runs them without asking.

**Everything else** goes to the classifier in auto mode, or prompts in manual mode. That includes:

- every git command that changes something (`add`, `commit`, `push`, `switch`, `stash`, …);
- tests, linters and project scripts (`pytest`, `ruff`, `npm test`, `npm run`);
- `gh` beyond reading;
- `npx`, `npm install` and `npm ci`, which run dependency install scripts and skip the 7-day cool-down;
- `node`.

Glob rules can't tell `git push` from `git push -uf`, or a `-n` flag from `-n` inside a commit message, so the template doesn't try: it leaves these to the classifier. **In manual mode that means a prompt for every commit, push and test run.** To cut that down, choose "Yes, and don't ask again" for the exact commands you trust, which saves them to your `.claude/settings.local.json`, or copy narrow opt-ins from `settings.example.jsonc`. Auto mode is the better fix.

**Denied by default**: reading these files and directories.

- **In the project, at any depth:** environment files (committed templates like `.env.example` stay readable), private keys, SSH keys, `.netrc` and `.git-credentials`, `secrets/` and `credentials/` directories, cloud CLI config, and Terraform state and variables.
- **In your home directory:** `~/.ssh`, `~/.gnupg`, and cloud, GitHub CLI and registry credentials (`~/.aws` including SSO and CLI-cache tokens, gcloud, `~/.config/gh`, Azure, Terraform, docker, kube, `.netrc`, `.npmrc`, `.pypirc`).

`settings.example.jsonc` explains each group and lists project-level opt-ins.

A `Read` deny rule also blocks editing and writing those paths. It covers Claude's file tools and the file commands Claude Code recognises in Bash (`cat`, `head`, redirections). It doesn't cover a script, or a command like `grep -r`, that reads files without naming them. For OS-level enforcement, enable Claude Code's sandbox. Add your project's own secret paths to `permissions.deny`, and narrow any default that blocks legitimate code (for example a `src/credentials/` directory).

Claude Code doesn't support a `.claudeignore` file, so this toolkit uses deny rules instead.

**Optional entries** live in `.claude/settings.example.jsonc`, a commented reference copy that Claude Code doesn't load. Copy the ones you want into `.claude/settings.json` without the comments:

- **Tests, lint and scripts:** `pytest`, `ruff`, `npm test`, `npm run`, and uv's `uv run pytest` and `uv run ruff`. Each comes with the flag that makes it dangerous.
- **Broad forms for manual-mode convenience:** `git commit *`, `git push *`, `gh *`, `npx *` and others, each with the risk it carries.
- **Cloud CLIs:** `Bash(aws *)` and `Bash(terraform *)`, or the narrower `aws s3 ls *` and `terraform plan *`.
- **Linear MCP block:** if you have the Linear MCP server connected (read-only `list_*`/`get_*` tools, plus the write tools).

Every opt-in also skips the auto mode classifier, so add only what you'd trust unreviewed.

Check what loaded with `/status`; `claude doctor` lists any entry Claude Code rejected.

### Codex and Antigravity permissions (`.codex/config.toml`)

The Claude deny rules above only bind Claude. Codex and Antigravity get their own, as far as each tool allows. What's below was tested with codex-cli 0.164 and agy 1.5.16, against a repo of fake secrets.

**Codex: ships with the repo.** `.codex/config.toml` sets a permission profile (a beta Codex feature) that denies the same secrets as the Claude list: `.env` files, keys and certificates, `secrets/` and `credentials/` folders, cloud credentials, Terraform state and variables, in the repo and in your home folder. The OS sandbox enforces it, so it covers Codex's own file reads and the commands it runs. It also stops environment variables with `KEY`, `SECRET` or `TOKEN` in their names reaching those commands.

- Codex loads the file only once you've trusted the repo: run `codex` in it and choose to trust it, or add `[projects."/path/to/repo"]` with `trust_level = "trusted"` to `~/.codex/config.toml`.
- A `sandbox_mode` setting anywhere replaces the profile and drops the denies, so check `~/.codex/config.toml` doesn't set one, and don't pass `--sandbox`. The `codex` review skill selects a second, read-only profile with the same denies, `toolkit-review`.
- A pattern can only deny, so `.env.example`, `.env.sample` and `.env.template` are blocked along with the real `.env` files. `**` patterns reach 20 folders deep (`glob_scan_max_depth`), which covers any real repo layout; Codex warns on every run without a cap. `.aws` is denied as a whole folder, wider than Claude's rule.
- `gh` and `docker` don't run under it, as their config is blocked. `~/.npmrc` and `~/.pypirc` aren't blocked: they hold the registry settings too, and hiding them would send npm and pip around a company gateway to the public registry.

**Antigravity: a user setting, and narrower.** Antigravity has no per-repo permissions file, so its rules go in your own `~/.gemini/antigravity-cli/settings.json` and apply to every project. Its rules are much weaker than Claude's or Codex's:

- A rule must be an **absolute path** to a file or folder. Patterns (`*.pem`, `**/.env`, `regex:`) and `~` don't work, and a relative path breaks every sandboxed command.
- Rules stop Antigravity's file tool, but shell commands only when the **terminal sandbox** is on. Without it, `cat .env` reads the file whatever the rules say.
- Antigravity's docs say its sandbox blocks `.env` files by default. In testing it didn't.

So it can't keep a repo's own secrets away from Antigravity by pattern. What it can do is protect the credentials in your home folder, which every project shares. This prints the settings to merge into `~/.gemini/antigravity-cli/settings.json` (add to an existing `permissions.deny` rather than replacing it):

```bash
python3 -I -c '
import json, os
home = os.path.expanduser("~")
paths = [".ssh", ".aws", ".gnupg", ".config/gcloud", ".config/gh", ".azure", ".kube", ".docker/config.json",
         ".terraform.d/credentials.tfrc.json", ".terraformrc", ".netrc", ".git-credentials"]
print(json.dumps({"enableTerminalSandbox": True,
                  "permissions": {"deny": [f"read_file({home}/{p})" for p in paths]}}, indent=2))'
```

Merge the output by hand; don't redirect it into `settings.json`, which would replace your other settings. It turns the sandbox on for every project, so sandboxed commands run without network access unless you allow a domain (`read_url(...)`), and see only the workspace and system folders unless you allow more paths. Folders and files that don't exist on your machine are fine to list. As with Codex, `~/.npmrc` and `~/.pypirc` are left out so npm and pip keep using your registry settings. Reviews stay safe either way: the `antigravity` skill runs Gemini read-only, in a clean worktree that has no private files. For interactive use, keep real secrets out of the repo.

### Claude Code hooks (`.claude/hooks/`)

| Hook | Trigger | What it does |
|---|---|---|
| `lint-edited-file.sh` | After every `Edit`/`Write`/`MultiEdit` (PostToolUse) | Formats and lints the edited file with the project's own tools, then sends only the leftovers back to Claude. |

How it chooses tools: it searches from the edited file's folder up to the repo root, so a repo split into `frontend/` and `backend/`, or a monorepo with packages, works. Each file uses its own package's tools and config, or the root's if that's where they live, and each tool runs from the nearest project folder.

- **Python:** ruff, from the nearest `.venv`, or from your PATH when the project configures ruff (`ruff.toml` or `[tool.ruff]`).
- **JS/TS:** biome when `biome.json` exists. Otherwise prettier and eslint, each only when configured. All of them come from the nearest `node_modules/.bin` that has them.
- **Others:** gofmt, rustfmt, terraform fmt and shellcheck, when installed.

What to know:

- Nothing is downloaded, and files outside the project (including through symlinks) are skipped.
- It runs the project's own tooling and config code, so only use it in repos you trust.
- It needs bash, plus `jq` or `python3`. Tested on Linux; on Windows, use WSL.

This replaces a Haiku `linter` subagent: deterministic tooling does the same job without spending model tokens. Add languages in the script's `case` statement.

### Configuration files

| File | Purpose |
|---|---|
| `.claude/settings.json` | Claude Code tool permissions and hooks — pre-approves common dev commands, denies reading secrets, and wires up the lint hook. Strict JSON |
| `.codex/config.toml` | Codex's permission profiles: the same secrets denied as the Claude rules, once you've trusted the repo ([details](#codex-and-antigravity-permissions-codexconfigtoml)) |
| `.claude/settings.example.jsonc` | Commented reference copy of the settings, with the optional entries. Not loaded by Claude Code |
| `.editorconfig` | Enforces consistent formatting across editors — indent style, line endings, trailing whitespace |
| `.gitattributes` | Keeps shell scripts, git hooks, Python and YAML on LF line endings in every checkout, so a Windows `core.autocrlf` can't break them (`#!/bin/sh\r`) |
| `.gitignore` | Comprehensive ignore rules covering Python, Node.js, IDE files, secrets, build outputs, and OS-generated files |
| `AGENTS.md` | Project context skeleton, read by Claude Code, Codex and Antigravity — fill in your architecture, conventions, and patterns |
| `CLAUDE.md` | One line, `@AGENTS.md`, so Claude Code loads the shared instructions. Don't add content here |
| `LICENSE` | MIT licence. Ships with `[year]` and `[your name]` placeholders that `init-from-template.sh` fills in |

## Using agents

Claude will automatically delegate to the right agent based on what you ask. You can also be explicit:

```
# Automatic delegation
Review the code I just changed
Write tests for the auth module

# Explicit invocation
@code-reviewer look at the last 3 commits
@devops-reviewer check my GitHub Actions workflow
@codebase-review give me an overview of this repo
@phase-acceptance validate phase 3
```

## Using skills

Skills trigger automatically from natural language. Examples:

```
Help me think through whether to use PostgreSQL or DynamoDB     → trade-off-analysis
Brainstorm approaches for migrating our auth system              → tree-of-thought
Combine the best parts of these three architectures              → graph-of-thought
I want to build a CLI tool for managing deployments              → requirements-elicitation
Research the best queue library for our Node.js workers          → research-brief
Write a phased build guide for the new billing module            → implementation-spec
Run a design thinking exercise on commuter pain points           → design-thinking-ideation
Map the value chain for this DTC coffee brand                    → value-chain-analysis
Is our proprietary dataset a sustainable competitive advantage?  → vrio-analysis
```

## Customisation

### Adding agents

Drop `.md` files into `.claude/agents/` with YAML frontmatter:

```markdown
---
name: my-agent
description: When Claude should use this agent
tools: Read, Grep, Glob
model: sonnet
---

Your system prompt here.
```

### Adding skills

Create a folder in `.agents/skills/` with a `SKILL.md` file, then link it from `.claude/skills/` (see **One copy, three tools** above):

```markdown
---
name: my-skill
description: >
  When this skill should trigger. Include keywords and phrases
  that would appear in a user's natural language request.
---

# Skill Title

Instructions for how Claude should handle this type of request.
```

### Removing what you don't need

Everything is modular. Delete any agent, skill, command, or hook you don't use. The remaining components work independently.

### Project docs (`docs/`)

Templates for the documents that the process, skills and agents read and write. Fill them in as the project takes shape:

```
docs/
├── prd/v1.0-prd.md                    # Product requirements; fill in with the requirements-elicitation skill
├── build-guides/v1.0-build-guide.md   # Phases with verification checklists; fill in with the implementation-spec skill
├── decisions/0000-template.md         # ADR template: copy to NNNN-short-title.md
├── process.md                         # Development process and agent cadence
├── tech-debt.md                       # Known gaps and drift
└── retrospectives/                    # Retros from the project-retrospective skill (created on first use)
```

The phase-acceptance agent checks a finished phase against the PRD and the build guide's verification checklist. AGENTS.md points at both.
