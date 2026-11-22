Your task is to finish the work in the worktree for branch `$ARGUMENTS`: get it into the default branch through a pull request, then clean up. Never merge it into the default branch locally: AGENTS.md requires every change to go through a PR, and the `main-protection` ruleset enforces it.

The worktree is in `.trees/`, in a folder named after the branch with `/` replaced by `-` (`feat/oauth-login` is in `.trees/feat-oauth-login`). If you can't find it, run `git worktree list` and ask the user which one they mean.

**Default branch:** run `git fetch origin` and `git remote set-head origin --auto`, then `git symbolic-ref --short refs/remotes/origin/HEAD`. That prints `origin/<name>`; below, "the default branch" means `<name>` (for example `main`), and its remote copy is `origin/<name>`.

Follow these steps:

1. **Is there already a PR?** Run `gh pr view $ARGUMENTS --json state,url`.
   - If it says `MERGED`, skip to step 7.
   - If a PR is already `OPEN`, go through steps 2 to 5, then push and tell the user the PR's URL instead of creating a new one.

2. **Check the branch.** In the worktree, confirm that the checked-out branch is `$ARGUMENTS` and that it isn't the default branch. If it is the default branch, stop and explain why.

3. **Check for unfinished work.** Run `git status` in the worktree. If there are uncommitted changes, show them and ask the user whether to commit them (following AGENTS.md and docs/process.md) or stop.

4. **Bring it up to date.** Merge the default branch into the worktree's branch: `git merge origin/<name>`. If there are conflicts:
   - list them (`git diff --name-only --diff-filter=U`);
   - resolve only the ones whose intent is clear from both sides;
   - stop and ask about any where the right answer is uncertain.

   Don't rebase or force-push a branch that's already pushed.

5. **Validate.** In the worktree:
   - run the project's lint and tests;
   - run the pre-PR gates from docs/process.md on the whole change (`.github/scripts/review-diff.sh`);
   - fix failures, and fold the gates' findings in;
   - commit those fixes, following docs/process.md;
   - confirm `git status` is clean before going on.

6. **Open the PR.** Push the branch (`git push -u origin $ARGUMENTS`). Unless a PR is already open, create one against the default branch with `gh pr create`, with a description that follows `.github/pull_request_template.md`. Give the user the PR's URL, and stop here until it's merged.

7. **Clean up after the merge.** Only when `gh pr view $ARGUMENTS --json state` says `MERGED`:
   - go back to the main checkout (the repo root, outside `.trees/`);
   - check the worktree has no uncommitted changes, then remove it with `git worktree remove <folder>`;
   - delete the local branch with `git branch -D $ARGUMENTS`. Use `-D` because a squash-merged branch isn't an ancestor of the default branch, so `-d` refuses; GitHub has confirmed it's merged;
   - run `git worktree prune` and `git fetch --prune origin`.
