#!/bin/sh
#
# Install this repo's git hooks. Run once per clone, from anywhere in the
# repo or any of its worktrees; safe to re-run.
#
#   pre-commit  the pre-commit framework, running .pre-commit-config.yaml:
#               gitleaks, private keys, large files, merge conflict markers,
#               plus any hooks the project adds
#   commit-msg  .githooks/commit-msg: Conventional Commits
#   pre-push    .githooks/pre-push: branch names, no pushing straight to the
#               default branch (checks every pushed ref)
#
# commit-msg and pre-push are installed as small launchers that run the
# current checkout's .githooks/<hook>, so they follow branch changes and
# survive a worktree being removed. An existing hook that isn't ours is moved
# to <hook>.bak.<timestamp> first.
#
# Needs the pre-commit tool (https://pre-commit.com); gitleaks is installed
# by pre-commit itself. Any hook can be skipped with --no-verify.

set -eu

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
MARKER="Installed by .githooks/setup-hooks.sh"

if ! command -v pre-commit >/dev/null 2>&1; then
    echo "✗ pre-commit isn't installed. Install it, then re-run this script:" >&2
    echo "    uv tool install pre-commit      # or: pipx install pre-commit / brew install pre-commit" >&2
    echo "  If it's a dev dependency of this project, run this script through it: uv run .githooks/setup-hooks.sh" >&2
    exit 1
fi

# pre-commit installs into git's hooks folder, which it won't do while
# core.hooksPath points elsewhere. Clear this repo's old setting; anything
# set globally is the user's to change.
if [ "$(git config --local --get core.hooksPath || true)" = .githooks ]; then
    git config --local --unset core.hooksPath
fi
HOOKS_PATH=$(git config --get core.hooksPath || true)
if [ -n "$HOOKS_PATH" ]; then
    echo "✗ core.hooksPath is set to '$HOOKS_PATH' (git config --show-origin core.hooksPath shows where)." >&2
    echo "  Unset it, then re-run: hooks in git's hooks folder are ignored while it's set." >&2
    exit 1
fi

HOOKS_DIR=$(git rev-parse --git-common-dir)/hooks
mkdir -p "$HOOKS_DIR"
STAMP=$(date +%Y%m%d%H%M%S)

echo "🔧 Installing hooks..."

# The repo's own hooks first: they need no network.
for hook in commit-msg pre-push; do
    dest="$HOOKS_DIR/$hook"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        if ! grep -q "$MARKER" "$dest" 2>/dev/null; then
            mv "$dest" "$dest.bak.$STAMP"
            echo "  (moved your existing $hook hook to $hook.bak.$STAMP)"
        fi
        rm -f "$dest"
    fi
    cat > "$dest" <<EOF
#!/bin/sh
# $MARKER: runs this checkout's .githooks/$hook.
hook="\$(git rev-parse --show-toplevel)/.githooks/$hook"
if [ ! -f "\$hook" ]; then
    echo "warning: \$hook not found on this branch; skipping the $hook check" >&2
    exit 0
fi
exec sh "\$hook" "\$@"
EOF
    chmod +x "$dest"
done

pre-commit install --hook-type pre-commit >/dev/null
# Fetch and build gitleaks now, so the first commit isn't slow. Needs the
# network; if it fails, pre-commit retries on the first commit.
if ! pre-commit install-hooks >/dev/null 2>&1; then
    echo "  ! couldn't fetch the pre-commit hooks now (offline?); they'll install on your first commit"
fi

echo "✓ Git hooks installed"
echo "  pre-commit  the hooks in .pre-commit-config.yaml (gitleaks, private keys, large files, merge conflicts, and any you've added)"
echo "  commit-msg  Conventional Commits"
echo "  pre-push    branch names; no pushing straight to the default branch"
echo "Skip any hook with --no-verify."
