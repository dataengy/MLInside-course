#!/usr/bin/env bash
# SessionStart hook: изоляция сессии на общем рабочем дереве. Fail-open, print-only, без сети.
# Печатает, где сессия (нативный worktree или ОБЩИЙ checkout), на какой ветке общий checkout,
# сколько worktree зарегистрировано (= есть ли параллельные сессии) и кто держит agent-lock —
# и рекомендацию: правки в worktree (EnterWorktree), иначе agent-lock + settle-check +
# коммиты только `only <мои пути>`; никаких `git reset`/`checkout` в общем дереве.
# Почему: 2026-08-26 параллельная сессия переключила общий checkout на feat/preza-merge между
# командами — коммит уехал в чужую ветку (#14). Локи от чужого checkout не защищают.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
ROOT=$(dirname "$COMMON")
BRANCH=$(git branch --show-current 2>/dev/null); BRANCH=${BRANCH:-detached}
DEFAULT=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
DEFAULT=${DEFAULT:-main}
N=$(git worktree list --porcelain 2>/dev/null | grep -c '^worktree ')

if [ "$GIT_DIR" != "$COMMON" ] && [ -z "$(git rev-parse --show-superproject-working-tree 2>/dev/null)" ]; then
  echo "[shared-tree] ✓ сессия в worktree ($(pwd)), ветка $BRANCH — коммиты сюда; в $DEFAULT: git fetch && git rebase origin/$DEFAULT && git push origin HEAD:$DEFAULT"
else
  msg="[shared-tree] ⚠ сессия в ОБЩЕМ checkout ($ROOT), ветка $BRANCH"
  [ "$BRANCH" != "$DEFAULT" ] && msg="$msg — не $DEFAULT: ветку мог переключить кто-то другой"
  [ "${N:-1}" -gt 1 ] && msg="$msg; worktree-ов: $N — есть параллельные сессии"
  echo "$msg. Для правок — EnterWorktree (нативный worktree в .claude/worktrees/); иначе agent-lock acquire + settle-check + коммиты только 'only <мои пути>'"
fi

LOCK="$HOME/.ai/skills/_scripts/session/agent-session-lock.sh"
if [ -f "$LOCK" ]; then
  out=$(bash "$LOCK" check --repo "$ROOT" 2>/dev/null | tail -1)
  case "$out" in HELD*|STALE*) echo "[shared-tree] 🔒 agent-lock на $ROOT: $out";; esac
fi
exit 0
