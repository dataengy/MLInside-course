#!/usr/bin/env bash
# worktree_land.sh — предполётная проверка и посадка ветки worktree в main.
#
# ЗАЧЕМ. «Смержи и удали ветку и worktree» — три необратимых действия подряд, и каждое
# способно уничтожить чужую работу. В этом репозитории в одном worktree одновременно живут
# несколько сессий: untracked-файл, который никто не закоммитил, исчезает вместе с каталогом
# без следа в git, а ветка может нести коммиты не только того, кто просит её слить.
#
# Поэтому скрипт по умолчанию НИЧЕГО не делает: он проверяет и печатает вердикт.
# Удаление выполняется только явным `--force-remove` и только когда проверки чисты.
#
#   scripts/worktree_land.sh check   [<worktree>]   # только проверить (по умолчанию)
#   scripts/worktree_land.sh land    [<worktree>]   # проверить и влить в main (без удаления)
#   scripts/worktree_land.sh remove  [<worktree>] --force-remove   # проверить, влить, удалить
#
# Проверок семь; любая красная останавливает всё.
set -uo pipefail

CMD="${1:-check}"
WT="${2:-$(git rev-parse --show-toplevel)}"
FORCE=0
for a in "$@"; do [ "$a" = "--force-remove" ] && FORCE=1; done

MAIN_REPO="$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir)/.."
MAIN_REPO="$(cd "$MAIN_REPO" && pwd)"
BRANCH="$(git -C "$WT" rev-parse --abbrev-ref HEAD)"
FAIL=0
say()  { printf '  %s\n' "$*"; }
bad()  { printf '  ✗ %s\n' "$*"; FAIL=1; }
ok()   { printf '  ✓ %s\n' "$*"; }

printf '\nworktree: %s\nветка:    %s\n\n' "$WT" "$BRANCH"

# 1. Собственный каталог удалить нельзя — git откажется, а сессия останется без cwd.
if [ "$CMD" = "remove" ] && [ "$(pwd -P)" = "$(cd "$WT" && pwd -P)" ]; then
  bad "команда запущена ИЗ удаляемого worktree — перейдите в $MAIN_REPO"
else
  ok "команда запущена не из удаляемого каталога"
fi

# 2. Незакоммиченные правки отслеживаемых файлов.
DIRTY="$(git -C "$WT" status --porcelain --untracked-files=no)"
if [ -n "$DIRTY" ]; then
  bad "незакоммиченные правки ($(printf '%s\n' "$DIRTY" | wc -l | tr -d ' ') файлов):"
  printf '%s\n' "$DIRTY" | sed 's/^/      /'
else
  ok "отслеживаемые файлы чисты"
fi

# 3. Untracked-файлы. Опаснее пункта 2: они исчезнут БЕЗ СЛЕДА, их нет ни в одном коммите.
# Собранные деки и промежуточные картинки не в счёт — они воспроизводятся сборкой.
# core.quotePath=false обязателен: иначе git экранирует кириллические имена в "\320\222…",
# и фильтр артефактов по префиксу пути молча перестаёт совпадать — а именно кириллические
# имена у собранных дек здесь и есть.
UNTRACKED="$(git -C "$WT" -c core.quotePath=false status --porcelain | sed -n 's/^?? //p' \
  | grep -vE '^(data/(drafts|generated)/|\.tmp/(render|render-pdf|build|qa)/)' || true)"
if [ -n "$UNTRACKED" ]; then
  bad "untracked-файлы — пропадут безвозвратно:"
  printf '%s\n' "$UNTRACKED" | sed 's/^/      /'
else
  ok "untracked-файлов вне артефактов нет"
fi

# 4. Всё ли выложено на remote: локальный коммит умрёт вместе с каталогом.
if git -C "$WT" rev-parse --verify --quiet "origin/$BRANCH" >/dev/null; then
  AHEAD="$(git -C "$WT" rev-list --count "origin/$BRANCH..HEAD")"
  [ "$AHEAD" = "0" ] && ok "ветка выложена в origin" || bad "не выложено коммитов: $AHEAD"
else
  bad "ветки origin/$BRANCH нет — сначала git push origin HEAD"
fi

# 5. Замок. `git worktree lock` — это заявка «каталог занят», снимать её за автора нельзя.
if git -C "$MAIN_REPO" worktree list --porcelain | grep -A3 -F "worktree $(cd "$WT" && pwd -P)" \
   | grep -q '^locked'; then
  bad "worktree заблокирован (git worktree lock) — снимать замок за автора нельзя"
else
  ok "worktree не заблокирован"
fi

# 6. Чьи коммиты в ветке. Не блокирует, но человек обязан это увидеть: слияние утащит
# в main чужую работу, которую её автор мог считать незаконченной.
# Счёт ведётся по СВЕЖЕМУ origin/main: ветку мог влить кто-то другой, пока вы работали, и
# без fetch скрипт предложил бы слить то, что уже слито.
git -C "$WT" fetch -q origin 2>/dev/null || true
if git -C "$WT" rev-parse --verify --quiet origin/main >/dev/null; then
  N="$(git -C "$WT" rev-list --count origin/main..HEAD)"
  if [ "$N" = "0" ]; then
    ok "ветка уже в origin/main — сливать нечего"
  else
    say "коммитов сверх origin/main: $N (сольются ВСЕ, включая чужие)"
    git -C "$WT" log --format='      %h %s' origin/main..HEAD | head -12
    [ "$N" -gt 12 ] && say "      … и ещё $((N - 12))"
  fi
fi

# 7. Живые сессии проверяются НЕ отсюда: bash их не видит. Инструмент ListAgents —
# единственный источник правды о том, кто сейчас работает в этом каталоге.
say ""
say "ПРОВЕРЬТЕ ВРУЧНУЮ: ListAgents — нет ли живых сессий с cwd в этом worktree."
say "Удаление каталога у работающей сессии оставляет её без рабочей копии."

printf '\n'
if [ "$FAIL" = "1" ]; then
  printf 'ВЕРДИКТ: сливать и удалять НЕЛЬЗЯ — см. ✗ выше.\n\n'
  exit 1
fi
printf 'ВЕРДИКТ: проверки чисты.\n\n'
[ "$CMD" = "check" ] && exit 0

# ── посадка ──────────────────────────────────────────────────────────────────────────────
set -e
git -C "$WT" fetch origin
git -C "$WT" rebase origin/main
git -C "$WT" push origin HEAD:main
echo "влито в main: $BRANCH"

[ "$CMD" = "land" ] && exit 0
if [ "$FORCE" != "1" ]; then
  echo "удаление пропущено: нужен явный --force-remove"
  exit 0
fi
git -C "$MAIN_REPO" worktree remove "$WT"
git -C "$MAIN_REPO" branch -d "$BRANCH"
git -C "$MAIN_REPO" push origin --delete "$BRANCH"
echo "удалены: worktree $WT и ветка $BRANCH"
