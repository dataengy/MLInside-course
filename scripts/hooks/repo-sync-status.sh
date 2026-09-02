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
    # Разошлись обе стороны — это НЕ две независимые строки выше, а третье состояние:
    # ни ff, ни `pull` не пройдут, а `reset --hard` уничтожит $ahead коммитов, которых нет
    # НИГДЕ, кроме этой машины. В общем чекауте они обычно чужие: коммитила другая сессия.
    # 2026-09-02 так разошёлся main с коммитом «пять ручных дек 4.7.x сведены в одну».
    if [ "$ahead" != "0" ] && [ "$behind" != "0" ] && [ "$ahead" != "?" ]; then
        say "⛔ $branch РАЗОШЁЛСЯ с $upstream (+$ahead/-$behind): ff не пройдёт, reset --hard сотрёт $ahead коммит(ов), которых нет на remote — порядок в скилле shared-checkout-sync"
        # …и вдвойне опасно, когда поверх лежит чья-то незавершённая работа: rebase откажет,
        # merge полезет в правящиеся файлы. Сначала пусть автор закоммитит.
        tracked_dirty="$(git status --porcelain=v1 2>/dev/null | grep -cv '^??' || true)"
        [ "${tracked_dirty:-0}" != "0" ] && \
            say "⛔ …и ${tracked_dirty} незакоммиченных путей поверх расхождения — синхронизацию не начинать, пока автор не закоммитит"
    fi
else
    say "⚠ $branch has no upstream"
fi

dirty="$(git status --porcelain=v1 2>/dev/null | wc -l | tr -d ' ')"
[ "$dirty" != "0" ] && say "⚠ working tree dirty: $dirty path(s)"

# Submodules: '+' = checked-out commit differs from the recorded gitlink
drift="$(git submodule status 2>/dev/null | grep -c '^+' || true)"
[ "${drift:-0}" != "0" ] && say "⚠ $drift submodule(s) drifted from recorded gitlinks"

# Submodules ahead of their upstream: a superproject gitlink that points at an unpushed
# commit breaks `git clone --recurse-submodules` on another machine. Push them first.
unpushed="$(git submodule foreach --quiet 'a=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0); [ "${a:-0}" != "0" ] && echo "$sm_path(+$a)"' 2>/dev/null | paste -sd" " -)"
[ -n "$unpushed" ] && say "⚠ submodule(s) ahead of upstream — push them first: $unpushed"

# Secrets lanes (offline checks only)
if [ -f settings/.env.secrets ]; then
    if [ -f settings/.env.secrets.secret ] && [ settings/.env.secrets -nt settings/.env.secrets.secret ]; then
        say "⚠ settings/.env.secrets is newer than its .secret blob — run: just secrets-hide"
    fi
else
    say "⚠ settings/.env.secrets missing — run: just secrets-bootstrap (docs/secrets-sync.md)"
fi

exit 0
