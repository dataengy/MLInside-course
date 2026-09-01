#!/usr/bin/env bash
# SessionStart hook: пора ли закрывать это рабочее дерево. Fail-open, print-only, без сети
# (сравнение с локальным ref origin/main; свежесть ref-ов даёт repo-sync-status.sh).
#
# Отношение к соседям. shared-tree-guard.sh отвечает «где я и куда коммитить», этот — «пора
# ли сводить и убирать». Саму посадку делает scripts/worktree_land.sh (скилл worktree-land,
# рецепт `just worktree-land`) — хук ничего не меняет, только сообщает и советует команду.
#
# Что печатает, помимо счётчика коммитов: ЖИВ ЛИ ДЕРЖАТЕЛЬ ЗАМКА. Claude Code пишет в
# `.git/worktrees/<имя>/locked` строку вида «claude session <имя> (pid 36270 start …)»,
# и разница между живым и мёртвым pid решает всё: у мёртвого замок просто протух, у живого
# `git worktree remove` отнимет рабочий каталог у сессии посреди задачи. Проверка семь в
# worktree_land.sh делается вручную через ListAgents (bash сессий не видит) — эта строка
# даёт тот же сигнал заранее и бесплатно, но не заменяет ListAgents: в одном дереве может
# сидеть больше сессий, чем держателей замка.
#
# Молчит, когда сказать нечего: ветка пуста относительно main и дерево ещё занято работой.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P) || exit 0
COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P) || exit 0
if [ "$GIT_DIR" = "$COMMON" ]; then exit 0; fi        # общий checkout — не наша тема
ROOT=$(dirname "$COMMON")

BRANCH=$(git branch --show-current 2>/dev/null) || exit 0
if [ -z "$BRANCH" ]; then exit 0; fi
DEFAULT=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
DEFAULT=${DEFAULT:-main}
if [ "$BRANCH" = "$DEFAULT" ]; then exit 0; fi
git show-ref --verify --quiet "refs/remotes/origin/$DEFAULT" || exit 0

AHEAD=$(git rev-list --count "origin/$DEFAULT..HEAD" 2>/dev/null) || exit 0
BEHIND=$(git rev-list --count "HEAD..origin/$DEFAULT" 2>/dev/null) || exit 0
DIRTY=$(git status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')
# Untracked считаем отдельно: именно они исчезают без следа при `git worktree remove`.
# Артефакты сборки не в счёт — воспроизводятся. Тот же фильтр, что в scripts/worktree_land.sh;
# core.quotePath=false обязателен, иначе кириллические имена дек экранируются в "\320\222…"
# и фильтр по префиксу молча перестаёт совпадать.
NEW=$(git -c core.quotePath=false status --porcelain 2>/dev/null | sed -n 's/^?? //p' \
  | grep -vcE '^(data/(drafts|generated)/|\.tmp/(render|render-pdf|build|qa)/)' || true)
NEW=${NEW:-0}

WT=$(pwd -P)
HELD=""
LOCKF="$COMMON/worktrees/$(basename "$WT")/locked"
if [ -f "$LOCKF" ]; then
  PID=$(tr -d '\n' < "$LOCKF" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    HELD=" · замок держит ЖИВАЯ сессия (pid $PID) — удалять нельзя"
  elif [ -n "$PID" ]; then
    HELD=" · замок протух (pid $PID мёртв) — снимает тот, кто ставил: git worktree unlock"
  fi
fi

# Скрипт ищем и в общем checkout, и здесь: общий checkout может стоять на другой ветке,
# где посадочного скрипта ещё нет, а в дереве он уже есть.
if [ -x "$ROOT/scripts/worktree_land.sh" ] || [ -x "$WT/scripts/worktree_land.sh" ]; then
  CMD="just worktree-land check $WT"
else
  CMD="слить вручную: git push origin HEAD:$DEFAULT"
fi

if [ "$AHEAD" = "0" ]; then
  # Всё уже в main. Единственное, что осталось, — уборка, и подталкивать к ней можно
  # только когда дерево свободно и в нём нечего терять.
  if [ -n "$HELD" ] || [ "$DIRTY" != "0" ] || [ "$NEW" != "0" ]; then exit 0; fi
  echo "[worktree-land] ✓ ветка $BRANCH целиком в $DEFAULT, дерево чисто — можно убирать: (из $ROOT) $CMD"
  exit 0
fi

MSG="[worktree-land] ветка $BRANCH: не в $DEFAULT $AHEAD коммит(ов)"
if [ "$BEHIND" != "0" ]; then MSG="$MSG, отстаёт на $BEHIND — сначала git rebase origin/$DEFAULT"; fi
if [ "$DIRTY" != "0" ]; then MSG="$MSG · незакоммичено: $DIRTY"; fi
if [ "$NEW" != "0" ]; then MSG="$MSG · untracked (пропадут при сносе): $NEW"; fi
MSG="$MSG$HELD"
echo "$MSG. Свести и убрать: (из $ROOT) $CMD"
exit 0
