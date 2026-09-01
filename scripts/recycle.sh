#!/usr/bin/env bash
# Убрать файл или каталог БЕЗ безвозвратного удаления.
#
# ПРАВИЛО (решение владельца, 2026-09-01):
#   убирая файлы — не удалять, а переносить в ../.recyclebin рядом с репозиториями;
#   исключение — файл, чьё содержимое ПОБАЙТОВО совпадает с уже сохранённой копией:
#   такой можно удалить, но запись об удалении обязана попасть в .recyclebin/.history.csv.
#
# ЗАЧЕМ. «Восстановимо из git» верно только пока цел коммит: ветки сводят, переименовывают
# и удаляют вместе с worktree. Под git-lfs указатель в истории остаётся, а объект уезжает
# в GC вместе с последним ref. Заигнорированные каталоги (.tmp/build/, data/generated/)
# не видит ни `git status`, ни проверки worktree_land.sh — оттуда файл исчезает молча.
# 2026-09-01 так чуть не пропал час ручной правки деки в .tmp/build/.
#
# ИСПОЛЬЗОВАНИЕ
#   scripts/recycle.sh <путь> [ещё путь…]         # перенести в корзину (по умолчанию)
#   scripts/recycle.sh --dup-of <копия> <путь>    # удалить как дубль, сверив sha256
#   scripts/recycle.sh --dry-run <путь>           # показать, что будет сделано
#
# Проверки перед необратимым шагом:
#   * файл открыт другим процессом (lsof) → отказ: удаление выдернет его из-под редактора;
#   * --dup-of: sha256 обязан совпасть, иначе отказ — «дубль» без сверки это не дубль;
#   * корзина и источник на разных томах → не mv, а копирование со сверкой sha256.
set -u

# Корзина живёт РЯДОМ с репозиториями, поэтому корень берём от ОСНОВНОГО чекаута, а не от
# расположения скрипта: в worktree (.claude/worktrees/<имя>/) отсчёт «на два вверх» дал бы
# .claude/.recyclebin. `--git-common-dir` в worktree указывает на .git основного чекаута.
_common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
if [ -n "$_common" ]; then
  _repo_root=$(dirname "$_common")
else
  _repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd -P)
fi
BIN="${RECYCLEBIN:-$(dirname "$_repo_root")/.recyclebin}"
LOG="$BIN/.history.csv"
DRY=0
DUP_OF=""

die() { echo "recycle: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --dup-of)  DUP_OF="${2:-}"; [ -n "$DUP_OF" ] || die "--dup-of требует путь к сохранённой копии"; shift 2 ;;
    --) shift; break ;;
    -*) die "неизвестный флаг: $1" ;;
    *) break ;;
  esac
done
[ $# -gt 0 ] || die "нечего убирать; см. заголовок файла"

mkdir -p "$BIN"
[ -f "$LOG" ] || printf 'ts_utc,action,path_from,repo,sha256,size_bytes,kept_at,reason,actor\n' > "$LOG"

sha_of()  { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }
size_of() { stat -f %z "$1" 2>/dev/null || stat -c %s "$1" 2>/dev/null; }
dev_of()  { stat -f %d "$1" 2>/dev/null || stat -c %d "$1" 2>/dev/null; }

log_row() { # action path repo sha size kept reason
  printf '%s,%s,%s,%s,%s,%s,"%s","%s",%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "$3" "$4" "$5" "$6" "$7" "${ACTOR:-$(whoami)}" >> "$LOG"
}

for target in "$@"; do
  [ -e "$target" ] || die "нет такого пути: $target"

  # 1. кто-то держит открытым — не трогаем
  if command -v lsof >/dev/null && lsof -- "$target" >/dev/null 2>&1; then
    holder=$(lsof -t -- "$target" 2>/dev/null | head -1)
    die "$target открыт процессом $holder — сначала закройте, иначе правка уйдёт в никуда"
  fi

  repo=$(basename "$(git -C "$(dirname "$target")" rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
  repo="${repo:--}"
  sha=$(sha_of "$target")
  size=$(size_of "$target")

  if [ -n "$DUP_OF" ]; then
    # 2. дубль удаляем ТОЛЬКО после сверки содержимого
    [ -e "$DUP_OF" ] || die "копия не найдена: $DUP_OF"
    # …и только если «копия» — действительно ДРУГОЙ файл. Иначе сверка вырождается в
    # сравнение файла с самим собой, всегда проходит, и скрипт удаляет единственный
    # экземпляр, записав в журнал, что копия осталась «там же». Ловится по inode, а не
    # по строке пути: ./x, x и симлинк на x — один и тот же файл.
    if [ "$(cd "$(dirname "$target")" && pwd -P)/$(basename "$target")" = \
         "$(cd "$(dirname "$DUP_OF")" && pwd -P)/$(basename "$DUP_OF")" ] || \
       [ "$target" -ef "$DUP_OF" ]; then
      die "--dup-of указывает на сам удаляемый файл ($target) — это не сверка, а её видимость; укажите ДРУГУЮ копию"
    fi
    other=$(sha_of "$DUP_OF")
    [ "$sha" = "$other" ] || die "не дубль: $target ($sha) ≠ $DUP_OF ($other) — переносите, а не удаляйте"
    if [ "$DRY" = 1 ]; then echo "[dry] удалить как дубль: $target (копия $DUP_OF)"; continue; fi
    log_row deleted-duplicate "$target" "$repo" "$sha" "$size" "$DUP_OF" "точный дубль по sha256"
    rm -rf -- "$target"
    echo "удалён как дубль: $target → копия остаётся в $DUP_OF (запись в $LOG)"
    continue
  fi

  # 3. обычный путь — перенос в корзину
  dest="$BIN/$(date -u +%Y%m%d)-$(basename "$target")"
  n=1
  while [ -e "$dest" ]; do dest="$BIN/$(date -u +%Y%m%d)-$n-$(basename "$target")"; n=$((n+1)); done
  if [ "$DRY" = 1 ]; then echo "[dry] перенести: $target → $dest"; continue; fi

  if [ "$(dev_of "$target")" = "$(dev_of "$BIN")" ]; then
    mv -- "$target" "$dest"                       # один том: переименование, атомарно
  else
    cp -R -p -- "$target" "$dest"                 # разные тома: копия → сверка → удаление
    if [ -f "$dest" ] && [ "$(sha_of "$dest")" != "$sha" ]; then
      die "копия не сошлась по sha256, оригинал НЕ тронут: $target"
    fi
    rm -rf -- "$target"
  fi
  log_row moved "$target" "$repo" "$sha" "$size" "$dest" "убран из репозитория, не удалён"
  echo "перенесён: $target → $dest (запись в $LOG)"
done
