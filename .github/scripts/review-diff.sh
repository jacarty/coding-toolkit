#!/bin/sh
#
# Print everything a reviewer should see: the whole change against the
# default branch, committed or not.
#
#   .github/scripts/review-diff.sh                    the full diff
#   .github/scripts/review-diff.sh --stat             a summary (files and line counts)
#   .github/scripts/review-diff.sh --base REF         compare with REF instead
#   .github/scripts/review-diff.sh [...] -- PATH...   only these paths (to split a big diff)
#
# It covers commits on the branch, staged and unstaged edits, and untracked
# files (not gitignored ones), in one diff from the merge-base with the
# default branch to the working tree. Code review gates, the review skills
# and doc-generator all use it, so they review the same thing. The output
# ignores your git diff settings (external tools, colour, prefixes).
#
# The default branch is origin/HEAD when it resolves, otherwise origin/main,
# origin/master, main or master, whichever exists. If the remote's default
# changed, refresh git's copy with: git remote set-head origin --auto

set -eu

BASE=""; STAT=0
while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            [ $# -ge 2 ] || { echo "review-diff: --base needs a ref" >&2; exit 2; }
            BASE=$2; shift 2 ;;
        --stat) STAT=1; shift ;;
        --) shift; break ;;
        -h|--help) sed -n '3,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "review-diff: unknown option: $1" >&2; exit 2 ;;
    esac
done
# Whatever is left are paths to limit the diff to.

TOP=$(git rev-parse --show-toplevel)
CDPATH='' cd -- "$TOP"

resolves() { git rev-parse --verify --quiet "$1^{commit}" >/dev/null; }

if [ -z "$BASE" ]; then
    HEAD_REF=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
    if [ -n "$HEAD_REF" ] && resolves "$HEAD_REF"; then
        BASE=$HEAD_REF
    else
        for ref in origin/main origin/master main master; do
            if resolves "$ref"; then BASE=$ref; break; fi
        done
    fi
fi
if [ -z "$BASE" ]; then
    echo "review-diff: can't find the default branch; pass --base REF" >&2
    exit 1
fi
if ! resolves "$BASE"; then
    echo "review-diff: '$BASE' isn't a commit; pass --base REF" >&2
    exit 1
fi
MERGE_BASE=$(git merge-base "$BASE" HEAD 2>/dev/null) || {
    echo "review-diff: no common history with $BASE; pass --base REF" >&2
    exit 1
}

# Plain, predictable diff output, whatever the user's git config says.
DIFF_OPTS="--no-ext-diff --no-color --no-textconv --src-prefix=a/ --dst-prefix=b/"

# Untracked files, NUL-separated so any filename works, handed to a small sh
# loop ($UNTRACKED_LOOP) in batches.
untracked() {
    git ls-files -z --others --exclude-standard -- "$@" | xargs -0 sh -c "$UNTRACKED_LOOP" review-diff
}

if [ "$STAT" = 1 ]; then
    echo "Changes since $BASE (merge-base $(git rev-parse --short "$MERGE_BASE")):"
    # shellcheck disable=SC2086  # DIFF_OPTS is a fixed list of flags
    git diff $DIFF_OPTS --stat "$MERGE_BASE" -- "$@"
    # shellcheck disable=SC2016  # expanded by the inner sh, not here
    UNTRACKED_LOOP='for f do
        if [ -L "$f" ]; then printf " %s | symlink to %s\n" "$f" "$(readlink "$f")"; continue; fi
        [ -f "$f" ] || continue
        printf " %s | %s lines\n" "$f" "$(wc -l < "$f" | tr -d " ")"
    done'
    LIST=$(untracked "$@")
    if [ -n "$LIST" ]; then
        echo "Untracked (new) files:"
        printf '%s\n' "$LIST"
    fi
    exit 0
fi

# Committed, staged and unstaged changes to tracked files, in one diff.
# shellcheck disable=SC2086
git diff $DIFF_OPTS "$MERGE_BASE" -- "$@"
# git diff --no-index exits 1 when the files differ (always, here), so only a
# higher exit code is an error. A directory (a nested repository) is skipped.
# A symlink is shown as the link itself, the way git shows a new one: git
# diff --no-index would follow a link to a directory instead.
# shellcheck disable=SC2016
UNTRACKED_LOOP='for f do
    if [ -L "$f" ]; then
        printf "diff --git a/%s b/%s\nnew file mode 120000\n--- /dev/null\n+++ b/%s\n@@ -0,0 +1 @@\n+%s\n\\\\ No newline at end of file\n" "$f" "$f" "$f" "$(readlink "$f")"
        continue
    fi
    [ -d "$f" ] && continue
    rc=0
    git diff '"$DIFF_OPTS"' --no-index -- /dev/null "$f" || rc=$?
    [ "$rc" -le 1 ] || exit "$rc"
done'
untracked "$@"
