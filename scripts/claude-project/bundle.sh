#!/usr/bin/env bash
# Собрать комплект файлов для Knowledge Claude-проекта «MLInside | 2026/09».
# Состав и причины — docs/claude-project/knowledge.md. Запуск: just claude-project-bundle
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out="${1:-$repo/.tmp/claude-project-bundle}"
cd "$repo"

rm -rf "$out"
mkdir -p "$out/reviews"

copy() {  # copy <src> <dst-name>
  if [[ -f "$1" ]]; then cp "$1" "$out/$2"; echo "  + $2"
  else echo "  ! пропущен (нет файла): $1" >&2; fi
}

echo "Сборка knowledge-бандла → $out"

copy content/presentations.yml     presentations.yml
copy docs/course-rules.md          course-rules.md
copy docs/course-qa.md             course-qa.md
copy README.md                     README-repo.md
copy .ai/AI-glossary.ru.md         glossary-ru.md
copy docs/claude-project/README.md claude-project-guide.md

# settings/config.yml → только курсовые разделы (без ingest/materials/deployment)
awk '
  /^[a-zA-Z_]+:/ { keep = ($1 == "project:" || $1 == "participants:" || $1 == "course_production:" \
                        || $1 == "planning:" || $1 == "deck_generation:" || $1 == "stack:") }
  keep
' settings/config.yml > "$out/config-course.yml"
echo "  + config-course.yml (срез settings/config.yml)"

# отчёты ревью дек — только верхний уровень docs/reviews/
found_reviews=0
for f in docs/reviews/*.md; do
  [[ -e "$f" ]] || continue
  cp "$f" "$out/reviews/$(basename "$f")"
  found_reviews=$((found_reviews + 1))
done
echo "  + reviews/ ($found_reviews шт.)"

# домашки (сабмодуль может быть не инициализирован)
found_hw=0
for f in homework/mlinside-hw-olist/docs/HW*.md; do
  [[ -e "$f" ]] || continue
  cp "$f" "$out/homework-$(basename "$f")"
  found_hw=$((found_hw + 1))
done
if [[ $found_hw -eq 0 ]]; then
  echo "  ! домашки не найдены — git submodule update --init homework/mlinside-hw-olist" >&2
else
  echo "  + homework-* ($found_hw шт.)"
fi

# Гейт: в облако не должно уехать ничего секретного. Ищем ЗНАЧЕНИЯ, а не упоминания:
# имя файла `.env.secrets` в прозе — норма (README, гайд), присвоенное значение — нет.
leak="$(grep -rilE 'BEGIN [A-Z ]*PRIVATE KEY|"private_key"[[:space:]]*:|bot[0-9]{6,}:[A-Za-z0-9_-]{30,}|^[A-Z][A-Z0-9_]{3,}=[^[:space:]#]{12,}' "$out" || true)"
if [[ -n "$leak" ]]; then
  echo "ОТКАЗ: в бандле похоже на секрет:" >&2
  echo "$leak" >&2
  exit 1
fi

manifest="$out/MANIFEST.md"
{
  echo "# Knowledge bundle — MLInside | 2026/09"
  echo
  echo "- собран: $(date -u '+%Y-%m-%dT%H:%M:%SZ') (UTC)"
  echo "- ветка/HEAD: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?') / $(git rev-parse --short HEAD 2>/dev/null || echo '?')"
  echo "- рабочее дерево: $(git status --porcelain 2>/dev/null | wc -l | tr -d ' ') изменённых путей"
  echo
  echo "Если дата сборки заметно старше сегодняшней — знание проекта устарело:"
  echo 'пересобрать `just claude-project-bundle` и перезалить файлы в Project → Files.'
  echo
  echo "## Файлы"
  echo
  echo "| файл | размер |"
  echo "|---|---|"
} > "$manifest"

(cd "$out" && find . -type f ! -name MANIFEST.md | sort | while read -r f; do
   printf '| `%s` | %s |\n' "${f#./}" "$(du -h "$f" | cut -f1 | tr -d ' ')"
 done) >> "$manifest"

echo "Готово: $(find "$out" -type f | wc -l | tr -d ' ') файл(ов). Открыть: open $out"
