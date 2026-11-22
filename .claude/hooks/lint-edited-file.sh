#!/usr/bin/env bash
#
# PostToolUse hook: format and lint each file Claude edits, using the
# project's own tools. Replaces the old `linter` subagent, so routine
# cleanup costs no model tokens.
#
# - Auto-fixes what the tools can fix (formatting, import order, unused imports).
# - Anything left over goes back to Claude on stderr with exit 2, trimmed to
#   20 lines of at most 300 characters, so it can fix it.
# - A tool runs only when the project has installed it AND configured it,
#   or (for ruff) installed it in the project's own .venv.
#   Nothing is downloaded: no bare `npx`, no `uv run` (which can sync).
# - It runs the project's own tooling and config files (node_modules/.bin,
#   .venv, eslint.config.js, ...), so only use it in repos you trust.
# - It looks for tools and config from the edited file's folder up to the
#   repo root, so frontend/ + backend/ layouts and monorepos work.
#
# Wired up in .claude/settings.json. Needs bash; `jq` or `python3` to read
# the hook input. Tested on Linux; macOS should work; on Windows use WSL.
# Add languages in the case statement below.

set -u

input=$(cat)
if command -v jq >/dev/null 2>&1; then
    file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
elif command -v python3 >/dev/null 2>&1; then
    file=$(printf '%s' "$input" | python3 -I -c \
        'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("file_path") or "")' 2>/dev/null)
else
    echo "lint hook: needs jq or python3; skipping" >&2
    exit 0
fi

# Resolve a path to its physical location (follows symlinks and ..).
# Portable: no `realpath -e`, which older macOS lacks.
physical() {
    local dir base
    dir=$(CDPATH='' cd -- "$(dirname -- "$1")" 2>/dev/null && pwd -P) || return 1
    base=$(basename -- "$1")
    if [ -L "$dir/$base" ]; then
        local target
        target=$(readlink -- "$dir/$base") || return 1
        case "$target" in /*) ;; *) target="$dir/$target" ;; esac
        physical "$target"
    else
        printf '%s/%s\n' "$dir" "$base"
    fi
}

root=$(CDPATH='' cd -- "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null && pwd -P) || exit 0

# Only real files that physically live inside the project.
[ -n "$file" ] && [ -f "$file" ] || exit 0
file=$(physical "$file") || exit 0
case "$file" in "$root"/*) ;; *) exit 0 ;; esac
# Installed dependencies aren't the project's code.
case "$file" in */node_modules/*) exit 0 ;; esac

# The folders to search, nearest first: the edited file's folder, then each
# parent up to the repo root. In a repo split into frontend/ and backend/,
# or a monorepo with packages, each file finds its own package's tools and
# config, or the root's if that's where they live.
dirs=$(
    d=$(dirname -- "$file")
    while :; do
        printf '%s\n' "$d"
        [ "$d" = "$root" ] && break
        d=$(dirname -- "$d")
    done
)

problems=""
note() { problems+="$1"$'\n'; }

# True if any of the given names (globs allowed) exists in directory $1.
has_in() {
    local dir=$1 pattern f; shift
    for pattern in "$@"; do
        # $pattern is unquoted on purpose, so its glob expands.
        # shellcheck disable=SC2086
        for f in "$dir"/$pattern; do [ -e "$f" ] && return 0; done
    done
    return 1
}
# The nearest folder (from $dirs) that has any of the given names.
nearest() {
    local d
    while IFS= read -r d; do
        has_in "$d" "$@" && { printf '%s\n' "$d"; return 0; }
    done <<< "$dirs"
    return 1
}
# True if any folder from the file up to the root has one of the names.
has() { nearest "$@" >/dev/null; }

# A project Node tool from the nearest node_modules/.bin that has it.
nodebin() {
    local d
    while IFS= read -r d; do
        [ -x "$d/node_modules/.bin/$1" ] && { printf '%s\n' "$d/node_modules/.bin/$1"; return 0; }
    done <<< "$dirs"
    return 1
}
# True if any package.json from the file up to the root has the given
# top-level key (e.g. a "prettier" config block), not just a dependency of
# that name. Prettier and ESLint inherit those from a parent package.json.
pkg_has() {
    local d pkg
    while IFS= read -r d; do
        pkg="$d/package.json"
        [ -f "$pkg" ] || continue
        if command -v jq >/dev/null 2>&1; then
            jq -e --arg k "$1" 'has($k)' "$pkg" >/dev/null 2>&1 && return 0
        elif command -v python3 >/dev/null 2>&1; then
            python3 -I -c 'import json,sys; sys.exit(0 if sys.argv[1] in json.load(open(sys.argv[2])) else 1)' "$1" "$pkg" 2>/dev/null && return 0
        fi
    done <<< "$dirs"
    return 1
}

BIOME_CONFIG="biome.json biome.jsonc"
ESLINT_CONFIG="eslint.config.* .eslintrc .eslintrc.*"
# shellcheck disable=SC2086  # the config lists are word-split on purpose
has_biome()    { has $BIOME_CONFIG; }
has_prettier() { has .prettierrc '.prettierrc.*' 'prettier.config.*' || pkg_has prettier; }
# shellcheck disable=SC2086
has_eslint()   { has $ESLINT_CONFIG || pkg_has eslintConfig; }

# True if a folder from the file up to the root configures ruff.
has_ruff_config() {
    local d
    while IFS= read -r d; do
        has_in "$d" ruff.toml .ruff.toml && return 0
        [ -f "$d/pyproject.toml" ] && grep -q '^\[tool\.ruff' "$d/pyproject.toml" && return 0
    done <<< "$dirs"
    return 1
}
# ruff: the project's own copy in the nearest .venv if there is one;
# otherwise ruff on PATH, but only when the project configures ruff (so a
# project that uses black or flake8 isn't reformatted).
ruff_bin() {
    local d
    while IFS= read -r d; do
        [ -x "$d/.venv/bin/ruff" ] && { printf '%s\n' "$d/.venv/bin/ruff"; return 0; }
    done <<< "$dirs"
    if command -v ruff >/dev/null 2>&1 && has_ruff_config; then echo ruff; fi
}

# Move to the nearest folder with any of the given names (the project's
# folder), falling back to the repo root.
run_from() {
    local d
    d=$(nearest "$@") || d=$root
    CDPATH='' cd -- "$d" || exit 0
}

# The JS tools each run from the folder that matters to them:
# - Biome and ESLint look for their config from the working folder (ESLint 9's
#   flat config does), so they run from the nearest folder with their config.
# - Prettier finds its config from the file's own path, but reads .gitignore
#   and .prettierignore from the working folder, so it runs from the repo root,
#   with a package's own .prettierignore added explicitly.
# Each runs in a subshell, so the cd doesn't leak.
js_tools() {
    local b p e cfg
    # Biome replaces prettier + eslint when the project configures it.
    if has_biome && b=$(nodebin biome); then
        # shellcheck disable=SC2086
        cfg=$(nearest $BIOME_CONFIG)
        out=$(CDPATH='' cd -- "$cfg" && "$b" check --write --no-errors-on-unmatched "$file" 2>&1) || note "$out"
        return
    fi
    if has_prettier && p=$(nodebin prettier); then
        local ignore=""
        cfg=$(nearest .prettierignore) || cfg=""
        if [ -n "$cfg" ] && [ "$cfg" != "$root" ]; then
            # Naming one ignore file replaces the defaults, so list them all.
            for f in "$root/.gitignore" "$root/.prettierignore" "$cfg/.prettierignore"; do
                [ -f "$f" ] && ignore="$ignore --ignore-path=$f"
            done
        fi
        # $ignore holds whole --ignore-path=... words; paths with spaces in a
        # package's .prettierignore aren't supported here.
        # shellcheck disable=SC2086
        out=$(CDPATH='' cd -- "$root" && "$p" --write --log-level warn $ignore "$file" 2>&1) || note "$out"
    fi
    if [ "${1:-}" = lint ] && has_eslint && e=$(nodebin eslint); then
        # shellcheck disable=SC2086
        cfg=$(nearest $ESLINT_CONFIG) || cfg=$(nearest package.json) || cfg=$root
        # --no-warn-ignored stops ignored files failing, but only flat config
        # (eslint.config.*) accepts it; legacy .eslintrc rejects the flag. The
        # nearest config decides. (A plain string, not an array: an empty
        # array under set -u aborts on bash < 4.4, which is stock macOS bash.)
        local quiet=""
        has_in "$cfg" 'eslint.config.*' && quiet="--no-warn-ignored"
        # $quiet is empty or one flag, so it's left unquoted on purpose.
        # shellcheck disable=SC2086
        (CDPATH='' cd -- "$cfg" && "$e" --fix $quiet "$file" >/dev/null 2>&1)
        # shellcheck disable=SC2086
        out=$(CDPATH='' cd -- "$cfg" && "$e" $quiet "$file" 2>&1) || note "$out"
    fi
}

CDPATH='' cd -- "$root" || exit 0   # the default; Python and the JS tools pick their own folder

case "$file" in
    *.py)
        run_from pyproject.toml ruff.toml .ruff.toml
        if r=$(ruff_bin) && [ -n "$r" ]; then
            "$r" format --quiet "$file" >/dev/null 2>&1
            "$r" check --fix --quiet "$file" >/dev/null 2>&1
            out=$("$r" check --quiet "$file" 2>&1) || note "$out"
        fi
        ;;
    *.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs|*.mts|*.cts|*.vue|*.svelte)
        js_tools lint
        ;;
    *.json|*.jsonc|*.css|*.scss|*.html|*.yml|*.yaml)
        js_tools
        ;;
    *.go)
        if command -v gofmt >/dev/null 2>&1; then
            out=$(gofmt -w "$file" 2>&1) || note "$out"
        fi
        ;;
    *.rs)
        if command -v rustfmt >/dev/null 2>&1; then
            out=$(rustfmt --quiet "$file" 2>&1) || note "$out"
        fi
        ;;
    *.tf)
        if command -v terraform >/dev/null 2>&1; then
            out=$(terraform fmt "$file" 2>&1) || note "$out"
        fi
        ;;
    *.sh)
        if command -v shellcheck >/dev/null 2>&1; then
            out=$(shellcheck "$file" 2>&1) || note "$out"
        fi
        ;;
esac

if [ -n "$problems" ]; then
    {
        echo "Lint issues left in $file after auto-fix:"
        printf '%s' "$problems" | head -n 20 | cut -c1-300
        [ "$(printf '%s' "$problems" | wc -l)" -gt 20 ] && echo "(truncated)"
    } >&2
    exit 2
fi
exit 0
