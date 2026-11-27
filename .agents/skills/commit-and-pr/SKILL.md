---
name: commit-and-pr
description: "Commit the current change and write its PR, following docs/process.md: check the branch name, pick only the intended files, confirm local checks and the pre-PR gates, then write a Conventional Commits message and a PR body from the repo's template. Use when the work is ready to commit, or when asked for a commit message, a PR description or the staging commands."
---

# Commit and PR

The last step before a PR: check the change is ready, then write the commit and the PR text. `AGENTS.md` and `docs/process.md` set the rules; this skill applies them in order. The hooks named below are the repo's own (`.githooks/`); if a project changed them, they're the reference.

## Steps

1. **Branch.** Run `git branch --show-current`.
   - On the default branch: stop. Suggest a `<type>/<slug>` branch and `git switch -c` to it; nothing commits to `main`.
   - The `pre-push` hook checks the name: a type (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`), then a slug of lowercase letters, digits and hyphens, at most 50 characters, starting and ending with a letter or digit.
   - The type should fit the change: `feat` for new behaviour, `fix` for a bug. If it doesn't, suggest `git branch -m <new>` (before the first push).
2. **Pick the files.** Run `git status` and `.github/scripts/review-diff.sh --stat`, and decide what belongs in the commit, by name. Don't stage yet unless the user asked you to commit.
   - Check the names first. If one is a secret file (`.env`, a key, Terraform state or `.tfvars`, credentials), stop and tell the user: don't open it, stage it or run the full diff, which would print it.
   - Include new untracked files and links the change adds.
   - Leave out, and mention: lockfile churn the change didn't cause, editor and OS files, local settings (`.claude/settings.local.json`), build output.
   - Then read the picked files' diff (`.github/scripts/review-diff.sh -- <files>`) for anything that mustn't be committed: credentials, environment values, account IDs, project numbers, service-account emails, internal hostnames, raw logs. Write as if the repo will be public. If you find any, stop and tell the user, without quoting the value.
   - If files are already staged, check `git diff --cached --name-only` is exactly the intended list.
3. **Local checks.** Run the project's full lint, tests and build (the commands are in `AGENTS.md` under Testing, or the project's own config). All must pass. A failure is fixed first, not committed and explained.
4. **Gates.** Work out from `docs/process.md` which pre-PR gates this change needs: the lines changed and files touched, against the fast path and each gate's trigger. **Run it** is needed when the change alters behaviour.
   - Confirm each one ran, and its findings were handled as `docs/process.md` says ("When an agent or gate flags something"): blocking findings and phase-acceptance gaps fixed; non-blocking ones fixed, or added to `docs/tech-debt.md` and listed under "Known gaps" in the PR body.
   - If a gate hasn't run, say which and ask before going on. `doc-generator` and **run it** belong in this session, so run them. Don't run a gate that needs a fresh context (`code-review-gate`, `devops-review-gate`, `test-generation`, `phase-acceptance-check`) in this session (in Claude Code, the gate skill starts its own agent; in Codex or Antigravity, a new session). The `antigravity` gate runs only from Claude Code; if it couldn't run, the PR body says so.
   - If anything other than wording changed after a gate ran, check the re-review that `docs/process.md` ("Changes after the gates") asks for has run on the final diff: antigravity, plus any gate whose trigger the later change, or the whole change, now meets. Not every gate. If it hasn't, say which and ask before going on.
   - Don't write a PR that claims a gate it didn't get.
5. **Commit message.** Conventional Commits, which the `commit-msg` hook checks:
   - subject: `type(scope): description`, where the scope is optional (lowercase letters, digits, `.`, `_` and `-`) and `!` before the colon marks a breaking change;
   - the description is imperative, starts with a lowercase letter, a digit or an acronym (`fix: handle empty input`, not `fix: Handle…`), and doesn't end with a full stop; keep the subject to 72 characters;
   - body: why the change was made and anything a reviewer would otherwise ask, wrapped at 72;
   - no attribution or co-author lines unless the user asks for them.
6. **PR body.** Fill the repo's template (`.github/pull_request_template.md`) section by section, keeping its headings (drop Known gaps when there are none). Say which gates saw the final diff.
   - **Testing** states what was actually run and what it showed, and any gap, with the reason.
   - **Known gaps** lists what's deferred in the change itself: a gate finding left for later, behaviour that couldn't be run or tested. Each one gets a row in `docs/tech-debt.md` in the same PR, so it isn't lost once the PR merges (in the template's own repo, an issue instead: `docs/toolkit.md`). A gate that couldn't run, such as a logged-out `agy`, is noted in the PR body only.
   - Tick a checklist box only when it's true. Leave the rest unticked and say why.
   - Reference the tracked issue (`docs/process.md`, Issue tracking). If the tracker is private and the repo isn't, keep the body self-explanatory without the link.
   - The same rule as the commit: no identifiers, hostnames, emails or raw logs.
7. **Hand over.** By default, give the user:
   - the `git add` commands for the exact files, then `git diff --cached --name-only` to check the list, then `git commit` with the message;
   - the PR title and body, ready to paste.

   Commit, push and run `gh pr create` yourself only when the user asks. If you commit, check what's staged right before it, since that's what gets committed, not the working tree: `git diff --cached --name-only` is exactly the picked files, and `git diff --cached` has nothing that mustn't be committed (step 2). In Codex's sandbox, and in Antigravity's unless the user approves running outside it, pushing and `gh` don't work (no network, and `gh`'s config is denied), so hand those to the user. Never merge.

## Don't

- **Don't skip hooks** (`--no-verify`) or edit hook or permission settings to get a commit through. Fix what the hook found.
- **Don't amend or force-push commits that are already pushed** unless the user asks.
- **Don't commit to the default branch,** docs-only changes included.
- **Don't describe the change from memory.** Write from the diff (`review-diff.sh`), so the PR says what the branch does, not what was planned.
