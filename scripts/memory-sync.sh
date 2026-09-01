#!/usr/bin/env bash
# memory-sync.sh — версионируемая копия памяти Claude Code для этого проекта.
#
# ЗАЧЕМ. Память живёт в ~/.claude/projects/<slug>/memory/ — вне репозитория и вне git.
# На второй станции (macCoreI9) её просто нет: агент там начинает без правил, которые
# здесь уже выучены. Поэтому копия лежит в .ai/memory/ и ездит вместе с репозиторием.
#
#   scripts/memory-sync.sh check    # чем отличаются живая память и копия в репо (по умолчанию)
#   scripts/memory-sync.sh push     # живая память → .ai/memory/  (перед коммитом)
#   scripts/memory-sync.sh pull     # .ai/memory/ → живая память (на новой станции)
#
# push/pull НЕ удаляют файлы на приёмнике: удаление памяти — осознанное действие, оно
# делается руками в нужном каталоге, а не как побочный эффект синхронизации.
set -euo pipefail

CMD="${1:-check}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIRROR="$REPO/.ai/memory"

# Каталог живой памяти именуется по пути ОСНОВНОГО клона, где каждый не-буквенно-цифровой
# символ заменён на дефис. Хардкодить его нельзя: на macCoreI9 репозиторий лежит по другому
# пути (/Users/nk.myg/github/...) и slug там другой — ровно на той станции, ради которой
# синхронизация и заводится. Из worktree берём общий git-dir, иначе slug укажет на worktree.
MAIN_REPO="$(cd "$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)"
SLUG="$(printf '%s' "$MAIN_REPO" | sed 's/[^a-zA-Z0-9]/-/g')"
LIVE="${CLAUDE_MEMORY_DIR:-$HOME/.claude/projects/$SLUG/memory}"

if [ ! -d "$LIVE" ]; then
  echo "живой памяти нет: $LIVE" >&2
  [ "$CMD" = "pull" ] || exit 1
  mkdir -p "$LIVE"
fi
mkdir -p "$MIRROR"

# README.md в зеркале описывает сам механизм и записью памяти не является: в живой каталог
# он попасть не должен (иначе агент прочитает его как факт о проекте), и в сравнении он
# всегда давал бы ложное расхождение.
copy_records() {  # copy_records <src> <dst>
  local n=0 f
  for f in "$1"/*.md; do
    [ -e "$f" ] || continue
    [ "$(basename "$f")" = "README.md" ] && continue
    cp -p "$f" "$2"/
    n=$((n + 1))
  done
  printf '%s' "$n"
}

case "$CMD" in
  check)
    printf 'живая:  %s\nв репо: %s\n\n' "$LIVE" "$MIRROR"
    if diff -rq -x README.md "$LIVE" "$MIRROR" >/dev/null 2>&1; then
      echo "совпадают"
    else
      diff -rq -x README.md "$LIVE" "$MIRROR" || true
      echo
      echo "свести: scripts/memory-sync.sh push (память → репо) или pull (репо → память)"
      exit 1
    fi
    ;;
  push)
    echo "скопировано в .ai/memory: $(copy_records "$LIVE" "$MIRROR") файл(ов)"
    echo "закоммитить: git add .ai/memory && git commit"
    ;;
  pull)
    echo "восстановлено в $LIVE: $(copy_records "$MIRROR" "$LIVE") файл(ов)"
    ;;
  *)
    echo "неизвестная команда: $CMD (check|push|pull)" >&2
    exit 2
    ;;
esac
