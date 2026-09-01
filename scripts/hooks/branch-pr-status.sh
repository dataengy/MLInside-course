#!/usr/bin/env bash
# SessionStart hook: work that never became a PR. Fail-open, no network.
# Warns when local branches carry commits not merged into the base branch, or when
# the base itself has unpushed commits (work that exists only on this workstation).
# Hold-pattern branches (backup/wip/rollback snapshots) are reported as HOLD — they
# must never be merged. Lane: /prs-create-merge-all-owned (~/.ai), agent pr-merge-conductor.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

base=$(git symbolic-ref --short HEAD 2>/dev/null) || exit 0
case "$base" in main|master) ;; *) base=main ;; esac
git show-ref --verify --quiet "refs/heads/$base" || exit 0

mergeable=""; held=""
while read -r b; do
  [ -n "$b" ] || continue
  case "$b" in
    backup-*|*-backup|wip/*|wip-*|*rollback*|*-before-*|pre-*) held="$held $b" ;;
    *) mergeable="$mergeable $b" ;;
  esac
done < <(git branch --no-merged "$base" --format='%(refname:short)' 2>/dev/null)

[ -n "$mergeable" ] && echo "[branch-pr] ⚠ не сведено в $base:$mergeable — PR-свип: /prs-create-merge-all-owned"
[ -n "$held" ] && echo "[branch-pr] ⓘ снимки (мержить НЕЛЬЗЯ):$held"

# Merged-but-lingering: a branch fully contained in the base is done and should be deleted.
# Nothing else surfaced these — five of them (3 remote, 2 local) piled up unnoticed until a
# manual sweep. A branch that a session still holds (the shared checkout's HEAD, or a
# worktree) is NOT safe to delete: deleting it yanks the ground from under that session.
stale=""; busy=""
held_refs=$(git worktree list --porcelain 2>/dev/null \
  | awk '/^branch /{sub("refs/heads/","",$2); print $2}' | tr '\n' ' ')
cur=$(git symbolic-ref --short HEAD 2>/dev/null)
while read -r b; do
  [ -n "$b" ] || continue
  [ "$b" = "$base" ] && continue
  case " $held_refs $cur " in
    *" $b "*) busy="$busy $b" ;;
    *)        stale="$stale $b" ;;
  esac
done < <(git branch --merged "$base" --format='%(refname:short)' 2>/dev/null)

[ -n "$stale" ] && echo "[branch-pr] ⓘ влито, можно удалить:$stale — git branch -d <ветка>"
[ -n "$busy" ] && echo "[branch-pr] ⓘ влито, но занято сессией (не удалять):$busy"

ahead=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo 0)
[ "$ahead" -gt 0 ] 2>/dev/null && echo "[branch-pr] ⚠ $ahead коммит(ов) не запушено на $base — существуют только здесь"

exit 0
