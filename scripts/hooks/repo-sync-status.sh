#!/usr/bin/env bash
# scripts/hooks/repo-sync-status.sh — SessionStart hook: one-glance sync state.
# Prints branch ahead/behind, dirty count, submodule drift, secrets-lane staleness.
# Fail-open by design: never blocks a session, always exits 0. No network calls.

set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 0

say() { printf '[repo-sync] %s\n' "$*"; }

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || exit 0
upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo '')"
if [ -n "$upstream" ]; then
    counts="$(git rev-list --left-right --count "${branch}...${upstream}" 2>/dev/null || echo '? ?')"
    ahead="${counts%%	*}"; behind="${counts##*	}"
    [ "$ahead" != "0" ] && say "⚠ $branch is ahead of $upstream by $ahead commit(s) — push pending"
    [ "$behind" != "0" ] && say "⚠ $branch is behind $upstream by $behind commit(s) — pull/rebase pending"
else
    say "⚠ $branch has no upstream"
fi

dirty="$(git status --porcelain=v1 2>/dev/null | wc -l | tr -d ' ')"
[ "$dirty" != "0" ] && say "⚠ working tree dirty: $dirty path(s)"

# Submodules: '+' = checked-out commit differs from the recorded gitlink
drift="$(git submodule status 2>/dev/null | grep -c '^+' || true)"
[ "${drift:-0}" != "0" ] && say "⚠ $drift submodule(s) drifted from recorded gitlinks"

# Secrets lanes (offline checks only)
if [ -f settings/.env.secrets ]; then
    if [ -f settings/.env.secrets.secret ] && [ settings/.env.secrets -nt settings/.env.secrets.secret ]; then
        say "⚠ settings/.env.secrets is newer than its .secret blob — run: just secrets-hide"
    fi
else
    say "⚠ settings/.env.secrets missing — run: just secrets-bootstrap (docs/secrets-sync.md)"
fi

exit 0
