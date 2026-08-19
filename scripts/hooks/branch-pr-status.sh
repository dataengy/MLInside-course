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

ahead=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo 0)
[ "$ahead" -gt 0 ] 2>/dev/null && echo "[branch-pr] ⚠ $ahead коммит(ов) не запушено на $base — существуют только здесь"

exit 0
