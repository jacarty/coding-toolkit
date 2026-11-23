#!/usr/bin/env bash
#
# Apply this template's GitHub repo defaults to a repo created from it.
# "Use this template" copies files, not settings, so a new repo starts with
# no branch protection. Run this once after creating it, then again whenever
# .github/rulesets/ changes.
#
#   .github/scripts/apply-repo-defaults.sh                 show what would change (read-only)
#   .github/scripts/apply-repo-defaults.sh --apply         apply it
#   options: --repo OWNER/NAME   default: the repo of the current checkout
#            --approvals N       required PR approvals (default 0, solo-friendly; 1+ for teams)
#
# What it sets, in this order:
#   - merge settings: merge commits and squash (no rebase), and head branches
#     deleted automatically on merge (first, because the ruleset only allows
#     methods the repo allows)
#   - every ruleset in .github/rulesets/*.json, created or updated in place by
#     name (main-protection: PRs only, merge or squash, no force-push or
#     deletion, toolkit-checks must pass, admins may bypass on PRs only)
#   - secret scanning and push protection
#   - Dependabot alerts and security updates
#   - private vulnerability reporting (the form SECURITY.md links to; public
#     repos only)
#
# Apply the ruleset only once the default branch's CI reports every check it
# requires (for a new repo, after its first push); otherwise open PRs wait
# for a check that never runs.
#
# Each setting is applied on its own, and what GitHub refuses is reported.
# Rulesets on private repos need GitHub Pro, Team or Enterprise; secret
# scanning on private repos needs GitHub Secret Protection, so there a refusal
# is a note, not a failure. It never deletes rulesets it doesn't manage.
#
# Safe to re-run: settings that already match are marked ✓ and left alone,
# and a preview with nothing to do says "Nothing to change."
#
# Needs: gh (signed in, with admin on the repo) and python3.

set -euo pipefail

usage() { sed -n '3,11p' "$0" | sed 's/^# \{0,1\}//'; }

REPO=""; APPROVALS=0; APPLY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO=${2:?--repo needs OWNER/NAME}; shift 2 ;;
        --approvals) APPROVALS=${2:?--approvals needs a number}; shift 2 ;;
        --apply) APPLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done
case "$APPROVALS" in ''|*[!0-9]*) echo "--approvals must be a whole number" >&2; exit 2 ;; esac

ROOT=$(cd "$(dirname "$0")/../.." && pwd -P)
command -v gh >/dev/null || { echo "needs the GitHub CLI (gh)" >&2; exit 1; }
command -v python3 >/dev/null || { echo "needs python3" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh isn't signed in: run 'gh auth login'" >&2; exit 1; }

[ -n "$REPO" ] || REPO=$(cd "$ROOT" && gh repo view --json nameWithOwner -q .nameWithOwner)
INFO=$(gh api "repos/$REPO") || { echo "can't read $REPO" >&2; exit 1; }

# A dotted field from the repo JSON: True/False for booleans, JSON for
# objects, lists and null, so a missing or null parent never crashes.
field() {
    printf '%s' "$INFO" | python3 -I -c '
import json, sys
value = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    value = value.get(key) if isinstance(value, dict) else None
print(json.dumps(value) if value is None or isinstance(value, (dict, list)) else value)' "$1"
}

if [ "$(field permissions.admin)" != "True" ]; then
    echo "you need admin on $REPO to change its settings" >&2; exit 1
fi
if [ "$(field private)" = True ]; then PRIVATE=1; VISIBILITY=private; else PRIVATE=0; VISIBILITY=public; fi

if [ "$APPLY" = 1 ]; then MODE="applying"; else MODE="dry run: nothing is changed; add --apply to apply"; fi
echo "Repo: $REPO ($VISIBILITY), $MODE"
echo

FAILED=0; PLANNED=0
ok()   { echo "  ✓ $*"; }
plan() { PLANNED=1; echo "  → $*"; }
note() { echo "  - $*"; }
warn() { echo "  ! $*"; }

# GitHub's error message from gh's output: the JSON body, then gh's own line.
github_message() {
    python3 -I -c '
import json, sys
text = sys.stdin.read()
start = text.find("{")
try:
    print(json.JSONDecoder().raw_decode(text[start:])[0].get("message", "").strip() or text.strip())
except Exception:
    print(text.strip().splitlines()[-1] if text.strip() else "unknown error")'
}

# write WHAT BODY [optional] -- GH_API_ARGS...
# Runs one gh api write (BODY on stdin when it isn't empty). On failure it
# reports GitHub's message and carries on, counting it as a failure. With
# `optional`, a refusal because the feature isn't in the repo's plan is only
# a note; any other error (permissions, timeouts, 5xx) is still a failure.
# It runs in the current shell, so FAILED sticks.
write() {
    local what=$1 body=$2 optional=0 out msg
    shift 2
    if [ "$1" = optional ]; then optional=1; shift; fi
    [ "$1" = -- ] && shift
    if [ -n "$body" ]; then
        out=$(printf '%s' "$body" | gh api "$@" --input - 2>&1) && { ok "$what"; return; }
    else
        out=$(gh api "$@" 2>&1) && { ok "$what"; return; }
    fi
    msg=$(printf '%s' "$out" | github_message)
    if [ "$optional" = 1 ] && printf '%s' "$msg" | grep -qiE 'not available|advanced security|secret protection|upgrade|purchase|not enabled for this'; then
        note "$what: not available here ($msg)"
    else
        warn "$what: not applied: $msg"
        FAILED=1
    fi
}

# on|off from a gh api read that answers {"enabled": bool}, or unknown. gh
# prints an error's JSON body on stdout, so capture first, then fall back.
enabled_state() {
    local state
    state=$(gh api "$1" -q 'if .enabled then "on" else "off" end' 2>/dev/null) || state=unknown
    case "$state" in on|off) echo "$state" ;; *) echo unknown ;; esac
}

# Whether the live ruleset (stdin) is the wanted one ($1). GitHub adds its
# own metadata at the top level, and parameters the file doesn't set come
# back at their empty defaults; anything else extra (a reviewer or setting
# added by hand) is a difference, so --apply puts the file's version back.
# List items may come back in any order, but each live item matches one
# wanted item, and values match by type (False isn't 0). Anything unreadable
# (an error, empty output) counts as not matching.
ruleset_matches() {
    python3 -I -c '
import json, sys

METADATA = {"id", "node_id", "source", "source_type", "created_at", "updated_at", "current_user_can_bypass", "_links"}

def covers(have, want, top=False):
    if isinstance(want, dict):
        if not isinstance(have, dict) or not all(k in have and covers(have[k], v) for k, v in want.items()):
            return False
        extra = {k: v for k, v in have.items() if k not in want and not (top and k in METADATA)}
        return all(v in ([], {}, None, "") or v is False or (type(v) is int and v == 0) for v in extra.values())
    if isinstance(want, list):
        if not isinstance(have, list) or len(have) != len(want):
            return False
        pool = list(have)
        for w in want:
            match = next((i for i, h in enumerate(pool) if covers(h, w)), None)
            if match is None:
                return False
            del pool[match]
        return True
    return type(have) is type(want) and have == want

try:
    live = json.load(sys.stdin)
except ValueError:
    sys.exit(1)
sys.exit(0 if covers(live, json.loads(sys.argv[1]), top=True) else 1)' "$1"
}

# The current state, so a re-run shows ✓ for what's already set. "off" means
# "not confirmed on" (a failed read counts too), so the worst case is an
# extra, harmless write, never a skipped one.
SCANNING_NOW=$(field security_and_analysis | python3 -I -c '
import json, sys
data = json.load(sys.stdin) or {}
on = lambda k: (data.get(k) or {}).get("status") == "enabled"
# GitHub leaves the keys out when the plan of the repo lacks the feature.
print("on" if on("secret_scanning") and on("secret_scanning_push_protection")
      else "off" if "secret_scanning" in data else "not offered")')
if gh api "repos/$REPO/vulnerability-alerts" >/dev/null 2>&1; then ALERTS_NOW=on; else ALERTS_NOW=off; fi
FIXES_NOW=$(enabled_state "repos/$REPO/automated-security-fixes")
if [ "$PRIVATE" = 1 ]; then PVR_NOW=n/a; else PVR_NOW=$(enabled_state "repos/$REPO/private-vulnerability-reporting"); fi

# ── Merge settings (before the ruleset, which only allows enabled methods) ──
echo "Merge settings:"
MERGE_WANT="squash=True merge commits=True rebase=False delete branch on merge=True"
MERGE_NOW="squash=$(field allow_squash_merge) merge commits=$(field allow_merge_commit) rebase=$(field allow_rebase_merge) delete branch on merge=$(field delete_branch_on_merge)"
MERGE_WHAT="merge commits and squash, no rebase; delete head branches on merge"
echo "  now: $MERGE_NOW"
if [ "$MERGE_NOW" = "$MERGE_WANT" ]; then
    ok "$MERGE_WHAT (already set)"
elif [ "$APPLY" = 0 ]; then
    plan "$MERGE_WHAT"
else
    write "$MERGE_WHAT" "" -- -X PATCH "repos/$REPO" \
        -F allow_squash_merge=true -F allow_merge_commit=true -F allow_rebase_merge=false \
        -F delete_branch_on_merge=true
fi
echo

# ── Rulesets ─────────────────────────────────────────────────────────────
echo "Rulesets (.github/rulesets/):"
if ! EXISTING=$(gh api --paginate "repos/$REPO/rulesets?includes_parents=false" \
        -q '.[] | select(.source_type == "Repository") | "\(.name)\t\(.id)"' 2>&1); then
    warn "can't list the repo's rulesets, so none were changed: $(printf '%s' "$EXISTING" | github_message)"
    FAILED=1
else
    shopt -s nullglob
    for file in "$ROOT"/.github/rulesets/*.json; do
        body=$(APPROVALS=$APPROVALS python3 -I - "$file" <<'PY'
import json, os, sys
ruleset = json.load(open(sys.argv[1], encoding="utf-8"))
for rule in ruleset.get("rules", []):
    if rule.get("type") == "pull_request":
        rule["parameters"]["required_approving_review_count"] = int(os.environ["APPROVALS"])
print(json.dumps(ruleset))
PY
)
        name=$(printf '%s' "$body" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["name"])')
        ids=$(printf '%s\n' "$EXISTING" | awk -F'\t' -v n="$name" '$1 == n {print $2}')
        if [ "$(printf '%s' "$ids" | grep -c .)" -gt 1 ]; then
            warn "$name: more than one ruleset has this name; fix it by hand"; FAILED=1; continue
        fi
        if [ -n "$ids" ] && gh api "repos/$REPO/rulesets/$ids" 2>/dev/null | ruleset_matches "$body"; then
            ok "$name: ruleset $ids already matches (approvals: $APPROVALS)"
        elif [ "$APPLY" = 0 ]; then
            if [ -n "$ids" ]; then action="update ruleset $ids"; else action="create"; fi
            plan "$name: $action (approvals: $APPROVALS)"
        elif [ -n "$ids" ]; then
            write "$name: update ruleset $ids" "$body" -- -X PUT "repos/$REPO/rulesets/$ids"
        else
            write "$name: create" "$body" -- -X POST "repos/$REPO/rulesets"
        fi
    done
fi
echo

# ── Security ─────────────────────────────────────────────────────────────
echo "Security:"
echo "  now: secret scanning and push protection=$SCANNING_NOW, dependabot alerts=$ALERTS_NOW, dependabot security updates=$FIXES_NOW, private vulnerability reporting=$PVR_NOW"
SCANNING='{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}'
if [ "$SCANNING_NOW" = on ]; then
    ok "secret scanning and push protection (already on)"
elif [ "$PRIVATE" = 1 ] && [ "$SCANNING_NOW" = "not offered" ]; then
    note "secret scanning and push protection: not offered on this private repo (needs GitHub Secret Protection; once it's added, re-run or turn them on in Settings)"
elif [ "$APPLY" = 0 ]; then
    if [ "$PRIVATE" = 1 ]; then plan "secret scanning and push protection (private repo: needs GitHub Secret Protection)"
    else plan "secret scanning and push protection"; fi
elif [ "$PRIVATE" = 1 ]; then
    write "secret scanning and push protection" "$SCANNING" optional -- -X PATCH "repos/$REPO"
else
    write "secret scanning and push protection" "$SCANNING" -- -X PATCH "repos/$REPO"
fi
if [ "$ALERTS_NOW" = on ]; then ok "Dependabot alerts (already on)"
elif [ "$APPLY" = 0 ]; then plan "Dependabot alerts"
else write "Dependabot alerts" "" -- -X PUT "repos/$REPO/vulnerability-alerts"; fi
if [ "$FIXES_NOW" = on ]; then ok "Dependabot security updates (already on)"
elif [ "$APPLY" = 0 ]; then plan "Dependabot security updates"
else write "Dependabot security updates" "" -- -X PUT "repos/$REPO/automated-security-fixes"; fi
if [ "$PRIVATE" = 1 ]; then
    note "private vulnerability reporting: skipped (public repos only)"
elif [ "$PVR_NOW" = on ]; then
    ok "private vulnerability reporting (already on)"
elif [ "$APPLY" = 0 ]; then
    plan "private vulnerability reporting"
else
    write "private vulnerability reporting" "" -- -X PUT "repos/$REPO/private-vulnerability-reporting"
fi
echo

if [ "$FAILED" = 1 ]; then
    echo "Done, but some settings weren't applied (marked !). Fix them in the repo's Settings, or re-run after resolving the cause."
    exit 1
fi
if [ "$APPLY" = 1 ]; then echo "Done."
elif [ "$PLANNED" = 0 ]; then echo "Nothing to change."
else echo "Re-run with --apply to make these changes."; fi
