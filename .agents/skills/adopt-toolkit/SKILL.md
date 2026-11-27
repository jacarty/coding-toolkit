---
name: adopt-toolkit
description: "Bring the coding-toolkit (agent rules, process, skills, reviewer agents, permission defaults, git hooks, PR template, repo protection) into an existing repo that wasn't created from the template, without overwriting what's already there. Use when asked to adopt, add or install the toolkit in an existing project. Needs a checkout of the toolkit and the target repo."
---

# Adopt the toolkit

Repos created from the template get the toolkit through `init-from-template.sh`. This is for a repo that already exists: copy in what it doesn't have, merge what it does, and change nothing without the user seeing it first.

**Toolkit** is a checkout of the coding-toolkit at a known commit (`git -C <toolkit> rev-parse HEAD`); **target** is the repo adopting it. Work on a new branch in the target (`chore/adopt-toolkit`, or another name if `git ls-remote --heads` or `gh pr list` shows it's taken), never on its default branch. Never edit the toolkit checkout, and copy only files it tracks (`git -C <toolkit> ls-files`), never local ones such as `.claude/settings.local.json` or `.env` files.

## 1. Take stock of the target

Read, don't change. Note for each what's already there:
- **Agent instructions:** `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/rules` or similar.
- **Agent config:** `.claude/` (settings, agents, skills, hooks), `.agents/skills/`, `.codex/config.toml`, and a `.claudeignore` (Claude Code doesn't read it: its secret entries become deny rules). In `settings.json`, flag broad allow entries that undercut the deny rules or auto mode, such as `Bash(cp:*)`, `Bash(mv:*)`, `Bash(gh:*)` or `Bash(git push:*)`.
- **An older copy of this toolkit:** files that match an earlier version (the same skill and agent names, `.githooks/`, `.claudeignore`, a `@YOUR-GITHUB-USERNAME` placeholder). See **Upgrading an older copy** in step 3.
- **Git hooks:** `git config core.hooksPath`, `.pre-commit-config.yaml`, husky (`.husky/`), lefthook (`lefthook.yml`), or files in `.git/hooks/`.
- **Conventions:** recent commit messages and branch names (`git log --oneline -20`, `git branch -r`). Do they follow Conventional Commits and `<type>/<slug>`?
- **CI:** the workflows, and the name of the check that must pass on PRs (the job name, or its `name:`).
- **GitHub:** `.github/pull_request_template.md`, `CODEOWNERS`, rulesets (`gh api repos/OWNER/REPO/rulesets`) and classic protection (`gh api repos/OWNER/REPO/branches/BRANCH/protection`), and the merge settings (`gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed`).
- **Ignore rules:** `.gitignore`.
- **Linting:** which formatters and linters the target configures (ruff, eslint, prettier, gofmt…). The lint hook only runs tools the project has set up.
- **The target's own automation:** anything that runs `git commit` or `git push` itself (scripts, agents, release tooling). The adopted hooks will check those commits too.

Don't open secret files to take stock: their names are enough.

## 2. Choose the pieces

Show the user this list, marked with what the target already has, and let them pick. Recommend Agent rules, Process, Skills, Reviewer agents and Secret guardrails for any repo, and the Lint hook when the target configures a linter.

| Piece | Toolkit files |
|---|---|
| Agent rules | `AGENTS.md`, `CLAUDE.md` (imports it) |
| Process | `docs/process.md`, `docs/tech-debt.md`, `docs/decisions/0000-template.md`; `docs/prd/` and `docs/build-guides/` if the target plans in phases (the phase gates read them) |
| Skills | `.agents/skills/*` and their links in `.claude/skills/`, plus `.claude/skills/codex` and `.claude/skills/antigravity` |
| Reviewer agents and review helper | `.claude/agents/*` (the gate skills run in them) and `.github/scripts/review-diff.sh` (every gate uses it) |
| Secret guardrails | `.claude/settings.json` (see below), `.claude/settings.example.jsonc`, `.codex/config.toml`, the secret patterns in `.gitignore` |
| Lint hook | `.claude/hooks/lint-edited-file.sh` and its `hooks` entry in `.claude/settings.json` |
| Git hooks | `.pre-commit-config.yaml`, `.githooks/`, `.gitattributes` (keeps the hooks and scripts on LF line endings, or they break on Windows) |
| PR and issue templates | `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/`, `.github/CODEOWNERS` |
| Repo protection | `.github/rulesets/main-protection.json`, `.github/scripts/apply-repo-defaults.sh`, `.github/SECURITY.md`, `.github/dependabot.yml` |
| Editor defaults | `.editorconfig` |
| Worktree commands | `.claude/commands/` |

**Skills:** the gates need `code-review-gate`, `devops-review-gate`, `test-generation`, `phase-acceptance-check`, `codebase-assessment` and `doc-generator`; `commit-and-pr`, `debugging`, `dependency-check` and `project-retrospective` back the process. `code-optimiser` and `refactorer` are general workflows. Offer the planning and strategy skills as a group the user can drop: `requirements-elicitation`, `research-brief`, `implementation-spec`, `tree-of-thought`, `graph-of-thought`, `trade-off-analysis`, `design-thinking-ideation`, `value-chain-analysis`, `vrio-analysis`. If the target doesn't plan in phases, leave out `phase-acceptance-check` too. Leave out `adopt-toolkit` itself: both `.agents/skills/adopt-toolkit` and its link in `.claude/skills/`. The target's own skills: offer to move them into `.agents/skills/` and link them from `.claude/skills/` with a relative link (`ln -s ../../.agents/skills/<name> .claude/skills/<name>`), so Codex and Antigravity see them too. Check first that no name clashes with a toolkit skill.

**`.claude/settings.json`:** the toolkit's file holds an `allow` list designed for auto mode, the `deny` rules and the lint hook. A target with no settings file gets the whole file; say so, since the allow list comes with it. Without the Lint hook piece, leave out the `hooks` entry, or every edit runs a hook script that isn't there.

**Never adopt** what only makes sense in the template: `README.md`, `LICENSE`, `docs/toolkit.md`, `init-from-template.sh`, `check_toolkit.py`, `toolkit-checks.yml`, the `test_*.py` files and `deny_rules.py`, which only they use. They test the toolkit itself, so in the target they'd fail on its layout or check things it didn't adopt.

## 3. Copy and merge

- **The target doesn't have the file:** copy it. For `CODEOWNERS`, check the root and `docs/` too: GitHub uses only one, so merge into an existing one instead. Keep the `.claude/skills/` links as links (`cp -P`), and fill in placeholders (`[Project Name]`, `@YOUR-GITHUB-USERNAME`) from the target.
- **Upgrading an older copy:** when a target file is an older version of a toolkit file nobody customises (skills, agents, `.githooks/`, scripts, templates), offer to replace it, and show the diff. Files the target customises (`AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `.pre-commit-config.yaml`, `.gitignore`, `docs/process.md`) still merge, as below. The old pieces map to the new ones:

  | Old | New |
  |---|---|
  | agents `code-reviewer`, `devops-reviewer`, `test-generator`, `codebase-review`, `phase-acceptance` | the toolkit's agents of those names, run by the gate skills `code-review-gate`, `devops-review-gate`, `test-generation`, `codebase-assessment`, `phase-acceptance-check` |
  | agents `doc-generator`, `refactorer`, `code-optimiser` | skills of the same names |
  | agent `linter` | the Lint hook piece |
  | skill `architecture-decision-record` | `doc-generator`'s ADR section and `docs/decisions/0000-template.md` |
  | `.claudeignore` | deny rules in `.claude/settings.json`, each with a matching `.gitignore` entry (the `.gitignore` bullet below) and a deny glob in both profiles of `.codex/config.toml` (`toolkit` and `toolkit-review`). Its non-secret entries, such as `*.log`, have no equivalent: drop them or say so |
  | a hand-written secrets check in `.githooks/pre-commit` | gitleaks through `.pre-commit-config.yaml` |

  Removing the old files needs the user's OK, like any deletion.
- **The target has the file:** never overwrite it. Merge, then show the user the diff before moving on:
  - **`AGENTS.md` / `CLAUDE.md`:** start from the toolkit's `AGENTS.md`. Put the target's own instructions under Rules as project rules (or Key Patterns, for how the code works), word for word. Fill in Architecture, Repository Structure, Testing and Deployment from the target's code, and remove fields and lines that don't apply (the PRD and build-guide links if Process didn't bring them). Git Workflow says `main` is protected only once repo protection is applied. Then `CLAUDE.md` is just `@AGENTS.md`.
  - **`.claude/settings.json`:** add the toolkit's `deny` rules and the lint hook to the target's; keep its `allow` list and other settings. Strict JSON.
  - **`.pre-commit-config.yaml`:** keep the target's hooks and top-level keys, add the toolkit's top-level keys it doesn't set, and add the toolkit's `repos` entries. If both pin the same repo, keep one entry, at a version `dependency-check` accepts. If both use the same hook with different `args`, keep the target's and ask.
  - **`.gitignore`:** append what's needed so every repo-level `Read` deny rule in `.claude/settings.json` is ignored (make a sample path per rule, as the toolkit's `test_gitignore.py` does, and check each with `git check-ignore --no-index`), and the `.env` templates aren't. Then check nothing of the target's is now hidden: `git ls-files -ci --exclude-standard` (tracked files) and `git ls-files --others --ignored --exclude-standard` (new files) must show nothing that belongs in the repo. If a pattern catches a real source or manifest folder (`src/secrets/`, a `credentials/` package), narrow it, and narrow the matching deny rule in `.claude/settings.json` to the same paths.
  - **`docs/process.md`:** if the target has its own process, ask whether to replace it, merge sections, or skip. If the target doesn't plan in phases, remove the phase-acceptance gate and the phase-boundary section.
- **Adapt what was copied to the target.** Toolkit files mention things the target doesn't have:
  - `docs/process.md` and `.github/rulesets/main-protection.json` name the `toolkit-checks` check. Change it to the target's own required check, exactly as a PR shows it (a matrix job reads like `test (3.12)`). The ruleset's `integration_id` (15368) is GitHub Actions: if the check comes from another CI, set that app's ID or remove the field. If the target has no CI check, delete the whole `required_status_checks` rule, not just its entry. Do it in this branch, so the ruleset is right when it's merged.
  - Drop mentions of `docs/toolkit.md`, `check_toolkit.py` and the toolkit's tests. Grep what you copied for `toolkit-checks`, `docs/toolkit.md`, `test_`, `docs/prd`, `build-guide` and `[Project Name]` to find them.
  - Leave copied skills and agents as they are, even where they mention toolkit files: they're shared with the toolkit, and a later update replaces them. List those mentions in the PR.
  - Files whose effect reaches the whole target: `CODEOWNERS` (`* @owner` makes that owner review every file: ask who), `.gitattributes` (`* text=auto`: check `git add --renormalize . && git status` shows no line-ending churn), and `SECURITY.md` (its private reporting link works only on public repos: on a private one, give a contact instead).
- **Another hook manager** (husky, lefthook, or a `core.hooksPath` other than `.githooks`): skip the git hooks piece and say why. `setup-hooks.sh` stops when `core.hooksPath` points elsewhere; a local `.githooks` setting is from an older copy of this toolkit, and it clears that one. Otherwise it moves an existing `commit-msg` or `pre-push` hook aside to a `.bak` file, and `pre-commit install` renames an existing `pre-commit` hook to `pre-commit.legacy` and still runs it. The user can add the checks to their own manager.
- **Conventions the target doesn't follow yet:** say so before adding the hooks that enforce them. The hooks check new commits and pushes only; existing history isn't touched.

Then check versions with the `dependency-check` skill: pin what you copied. The target's own hooks and actions come under the adopted `AGENTS.md` rule too (exact SHA pins, the 7-day cool-down), but changing them changes its dependencies: list the proposed bumps and get the user's OK first. A hook that's also a project dependency (ruff in `uv.lock`) is bumped together with its lockfile. If `.github/dependabot.yml` was adopted, propose adding the target's own package ecosystems to it, with the cool-down set, on the same OK.

## 4. Check it works

In the target, on the branch:
- `.githooks/setup-hooks.sh` (if git hooks were adopted), then `git add` the changes and `pre-commit run --all-files` (it skips untracked files), which runs the target's own hooks too;
- the commit and push hooks, without committing or pushing. Each must print `1` (rejected) after the hook's message. `<remote>` is the target's remote name, `<default branch>` its default branch; the local sha must be non-zero, or pre-push treats the line as a branch deletion and passes it:
  ```sh
  msg=$(mktemp); printf 'Bad message\n' > "$msg"; .githooks/commit-msg "$msg"; echo $?; rm -f "$msg"
  z=$(printf '%040d' 0); sha=$(printf '1%.0s' $(seq 40))
  printf 'refs/heads/x %s refs/heads/<default branch> %s\n' "$sha" "$z" | .githooks/pre-push <remote> "$(git remote get-url <remote>)"; echo $?
  printf 'refs/heads/x %s refs/heads/Bad_Name %s\n' "$sha" "$z" | .githooks/pre-push <remote> "$(git remote get-url <remote>)"; echo $?
  ```
- the `.claude/skills/` links resolve (`find .claude/skills -xtype l` prints nothing), and each gate skill's `agent:` exists in `.claude/agents/`. If you can't start Claude Code, ask the user to check in a new session that the skills are listed;
- the lint hook runs on an edited file without error. If the target configures no formatter or linter, say that the hook will do nothing until one is set up;
- the target's own lint, tests and build still pass. For its own automation (step 1), check the commit messages and branch names it produces against the hooks, by reading it or in a throwaway clone: don't run it here, where it would make real commits.

## 5. Hand over

Use the `commit-and-pr` skill. The copied files were reviewed in the toolkit; the gates review what's new here: the merged and adapted files (`AGENTS.md`, settings, pre-commit config, `.gitignore`, the ruleset), so run `devops-review-gate` and `antigravity` on the change. The PR body lists the pieces adopted and skipped, every merged or adapted file, and the toolkit commit, so a later update can see what came from where.

Repo protection is a separate step, after the PR merges. Run `.github/scripts/apply-repo-defaults.sh --repo OWNER/NAME` from the target's checkout, not the toolkit's (it reads the rulesets next to it, so only the target's has the adapted check), in preview first, and apply only with the user's OK, once the required check has reported on the default branch (otherwise PRs wait for a check that never runs). Before applying, tell the user what changes:
- **merge settings:** merge commits and squash only (rebase merging is turned off), and branches deleted on merge;
- **the `main-protection` ruleset** is created, or replaced if one with that name exists. Existing classic branch protection stays and both apply. Rulesets on private repos need GitHub Pro, Team or Enterprise;
- secret scanning, push protection, Dependabot alerts and security updates, and private vulnerability reporting (public repos) are turned on where the plan allows.

## Don't

- **Don't overwrite** a file the target already has, or delete anything of the target's.
- **Don't apply repo protection or change GitHub settings** without the user's OK.
- **Don't copy secrets or untracked files** from the toolkit checkout.
