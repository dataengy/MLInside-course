#!/usr/bin/env bash
# Кто сейчас занимает worktree — и можно ли его сносить.
#
# ЗАЧЕМ. `worktree_land.sh` в проверке 7 честно пишет «bash сессий не видит, смотрите
# ListAgents». Это верно про СЕССИИ, но не про ЗАНЯТОСТЬ: процесс, сидящий в каталоге,
# виден по cwd, а открытый файл — по дескриптору. 2026-09-02 именно так нашлись PowerPoint,
# державший правленую деку внутри дерева, и пять процессов с cwd в нём. ListAgents этот
# скрипт НЕ заменяет: сессия может быть жива и вне каталога — он отвечает на другой вопрос,
# «отнимет ли снос у кого-то файлы прямо сейчас».
#
# ИСПОЛЬЗОВАНИЕ
#   scripts/worktree_occupants.sh [путь]              # отчёт; exit 0 = свободно, 1 = занято
#   scripts/worktree_occupants.sh [путь] --wait [N]   # ждать, пока освободится: N чистых
#                                                     # проверок подряд с интервалом 60с (по умолчанию 10)
#   scripts/worktree_occupants.sh [путь] --quiet      # только код возврата
#
# Что считается занятостью:
#   1. открытый файл внутри дерева (кроме служебного .claude/.cc-writes своей же сессии);
#   2. процесс с cwd внутри дерева;
#   3. живой держатель `git worktree lock` (мёртвый pid → замок протух, это НЕ занятость);
#   4. незакоммиченные правки по отслеживаемым файлам (untracked сами по себе не считаются:
#      сносу они не мешают, но их надо вынести в корзину — см. скилл recyclebin).
set -u

WT="${1:-.}"; shift 2>/dev/null || true
WAIT=0; ROUNDS=10; QUIET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --wait)  WAIT=1; case "${2:-}" in ''|--*) ;; *) ROUNDS="$2"; shift ;; esac; shift ;;
    --quiet) QUIET=1; shift ;;
    *) echo "worktree_occupants: неизвестный флаг: $1" >&2; exit 2 ;;
  esac
done

[ -d "$WT" ] || { echo "worktree_occupants: нет такого каталога: $WT" >&2; exit 2; }
ABS=$(cd "$WT" && pwd -P) || exit 2
NAME=$(basename "$ABS")
say() { [ "$QUIET" = 1 ] || printf '%s\n' "$*"; }

# Замок Claude Code пишет в .git/worktrees/<имя>/locked строку с pid. Мёртвый pid = протух.
lock_holder() {
  local common lockfile pid
  common=$(git -C "$ABS" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 0
  lockfile="$common/worktrees/$NAME/locked"
  [ -f "$lockfile" ] || return 0
  pid=$(sed -n 's/.*pid \([0-9]\{1,\}\).*/\1/p' "$lockfile" | head -1)
  [ -n "$pid" ] || { printf 'без pid: %s' "$(tr -d '\n' < "$lockfile")"; return 0; }
  # Живость: под песочницей И `kill -0`, И `ps` падают с «operation not permitted» даже на
  # живом pid — то есть наивная проверка объявила бы протухшим ЛЮБОЙ замок, а это ровно та
  # сторона ошибки, которая стоит чужого рабочего каталога. Поэтому: сначала пробуем `ps`,
  # затем `kill -0`, а если оба недоступны — считаем ЖИВЫМ и говорим, что не смогли
  # проверить. Пусть человек посмотрит ListAgents, чем скрипт угадает «мёртв».
  if ps -p "$pid" -o pid= >/dev/null 2>&1 \
     || kill -0 "$pid" 2>/dev/null \
     || [ -n "$(lsof -p "$pid" -Fp 2>/dev/null)" ]; then
    printf 'ЖИВОЙ pid %s: %s' "$pid" "$(tr -d '\n' < "$lockfile")"
  elif ps -p 1 -o pid= >/dev/null 2>&1 || [ -n "$(lsof -p 1 -Fp 2>/dev/null)" ]; then
    # Пробуем НЕ свой процесс (pid 1 есть всегда): если чужой виден, значит проверки
    # работают, и ненайденный pid действительно мёртв. Пробовать на самом себе нельзя —
    # `kill -0 $$` песочница разрешает, и любой чужой замок выглядел бы протухшим.
    printf 'протух (pid %s мёртв): %s' "$pid" "$(tr -d '\n' < "$lockfile")"
  else
    printf 'НЕ ПРОВЕРЕН (ps/kill/lsof по чужому pid запрещены), считаем ЖИВЫМ — pid %s: %s' \
      "$pid" "$(tr -d '\n' < "$lockfile")"
  fi
}

check() {  # печатает отчёт, возвращает 0 если свободно
  local busy=0 files cwds lock dirty
  # Собственный измерительный конвейер сам сидит в этом каталоге и без фильтра
  # засчитывается как занятость — вопрос «занято ли дерево» превращается в «запущен ли я».
  # Группу процессов взять нечем (`ps` под песочницей запрещён), поэтому отсекаем по имени:
  # настоящий занимающий — это claude, редактор, PowerPoint, node, python, а не транзитный
  # awk из этого же конвейера. Список намеренно узкий: лучше лишний раз сказать «занято».
  drop_self() { grep -Ev '^(bash|sh|zsh|fish|awk|grep|sed|sort|head|tail|tr|cut|lsof|ps|xargs|wc|uniq|cat|find|dirname|basename) ' ; }
  # 1. открытые файлы (не cwd). Свой служебный .cc-writes не в счёт — его держит сессия,
  # которая как раз и спрашивает; он исчезнет при выходе из дерева.
  files=$(lsof 2>/dev/null | grep -F "$ABS" | awk '$4!="cwd"{print $1" "$2" "$NF}' | grep -v '/\.claude/\.cc-writes' | drop_self || true)
  if [ -n "$files" ]; then
    busy=1; say "✗ открытые файлы внутри дерева:"
    printf '%s\n' "$files" | awk '{printf "    %s pid %s → %s\n", $1, $2, $3}' | head -8
  fi
  # 2. процессы, сидящие в каталоге
  cwds=$(lsof 2>/dev/null | grep -F "$ABS" | awk '$4=="cwd"{print $1" "$2}' | sort -u | drop_self | awk '{print "    "$1" pid "$2}' || true)
  if [ -n "$cwds" ]; then
    busy=1; say "✗ процессы с cwd внутри дерева:"
    printf '%s\n' "$cwds" | head -8
  fi
  # 3. замок
  lock=$(lock_holder)
  case "$lock" in
    ЖИВОЙ*) busy=1; say "✗ git worktree lock — $lock" ;;
    '')     ;;
    *)      say "ⓘ git worktree lock — $lock (занятостью не считается)" ;;
  esac
  # 4. незакоммиченное по отслеживаемым
  dirty=$(git -C "$ABS" status --porcelain 2>/dev/null | grep -cv '^??' || true)
  if [ "${dirty:-0}" != "0" ]; then
    busy=1; say "✗ незакоммиченных путей: $dirty — снос уничтожит правки"
  fi
  [ "$busy" = "0" ] && say "✓ свободно: открытых файлов нет, никто не сидит, замка нет, незакоммиченного нет"
  return "$busy"
}

if [ "$WAIT" = "0" ]; then
  say "worktree: $ABS"
  check; exit $?
fi

# --wait: занятость мигает (сессия отходит и возвращается), поэтому требуем ПОДРЯД.
say "жду, пока $NAME освободится: нужно $ROUNDS чистых проверок подряд, интервал 60с"
n=0
while [ "$n" -lt "$ROUNDS" ]; do
  if check >/dev/null 2>&1; then n=$((n+1)); else n=0; fi
  [ "$n" -lt "$ROUNDS" ] && sleep 60
done
say "✓ $NAME свободен $ROUNDS проверок подряд — можно сносить (порядок в скилле worktree-land)"
exit 0
