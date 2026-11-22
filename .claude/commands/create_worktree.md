Your task is to create a git worktree for the branch `$ARGUMENTS`, in the `.trees/` folder, so work can happen in parallel with the main checkout.

Follow these steps:

1. **Check the branch name.** It must be `<type>/<slug>`, the same rule the pre-push hook enforces:
   - `<type>` is a Conventional Commits type: feat, fix, docs, style, refactor, perf, test, build, ci, chore or revert;
   - the slug is lowercase letters, digits and hyphens, 1 to 50 characters, starting and ending with a letter or digit.

   If `$ARGUMENTS` doesn't match, stop and suggest a valid name, for example `feat/oauth-login`.

2. **Work out the folder.** It's `.trees/` plus the branch name with `/` replaced by `-` (so `feat/oauth-login` becomes `.trees/feat-oauth-login`). If that folder already exists, stop and tell the user the worktree already exists.

3. **Find the default branch.**
   - Run `git fetch origin` and `git remote set-head origin --auto`, which refreshes git's record of the remote's default.
   - Read the default with `git symbolic-ref --short refs/remotes/origin/HEAD`. That prints `origin/<name>`; call `<name>` the default branch.
   - If there's no `origin` remote, use the local `main` (or `master`).

4. **Create the worktree.**
   - If the branch exists on origin but not locally: `git worktree add <folder> <branch>`, which tracks `origin/<branch>`.
   - If it exists locally: `git worktree add <folder> <branch>`. If the local branch is behind `origin/<branch>`, tell the user.
   - Otherwise create it from the default branch: `git worktree add -b <branch> <folder> origin/<default branch>`.

5. **Dependencies.** Tell the user the worktree has none installed yet, and give the project's install command to run inside it (for example `uv sync` or `npm ci`). Don't share or symlink the main checkout's `.venv` or `node_modules`: different branches can need different dependencies.

6. **Open it.** If the `code` command is on PATH, open the worktree in a new VS Code window (`code <folder>`). Otherwise print the folder's path so the user can open it.

The git hooks are shared with the main checkout, so commits and pushes in the worktree are checked the same way. When the work is done, `/merge_worktree $ARGUMENTS` opens the PR and, once it's merged, cleans up.
