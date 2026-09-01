#!/usr/bin/env bash
# scripts/hooks/yaml-writers-status.sh — сторож комментариев в YAML, которые правят и
# машина, и руки.
#
# ЗАЧЕМ. Потеря комментариев при машинной перезаписи не ловится ничем: файл остаётся
# валидным, тесты зелёные, дифф выглядит переформатированием. 2026-09-01 один прогон
# publisher снёс восемь строк пояснений из content/presentations.yml; заметили глазами.
# Причина устранена (оба писателя на round-trip), но сторож нужен на будущее: следующий
# писатель может прийти от кого угодно.
#
# Две проверки, обе дешёвые и без ложных срабатываний:
#   1. в охраняемых файлах комментариев не стало меньше, чем в HEAD;
#   2. модули, переведённые на round-trip, не вернулись к yaml.safe_dump.
#
# Стратегии записи и когда какая уместна — docs/glossary.md.

set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || exit 0)" || exit 0

# Файлы: структурированные данные + комментарии, писатель машинный.
GUARDED=(content/presentations.yml settings/formats.yml)
# Модули, у которых round-trip — обязательство, а не деталь реализации.
ROUNDTRIP=(src/publisher/plan_writer.py src/preza_merge/apply.py src/schedule/cli.py)

warn() { printf '[yaml-writers] ⚠ %s\n' "$*"; }

for f in "${GUARDED[@]}"; do
    [ -f "$f" ] || continue
    now=$(grep -c '^[[:space:]]*#' "$f" 2>/dev/null || echo 0)
    was=$(git show "HEAD:$f" 2>/dev/null | grep -c '^[[:space:]]*#' || echo 0)
    if [ "$now" -lt "$was" ]; then
        warn "$f: комментариев было $was, стало $now — машинная перезапись их унесла?"
        warn "  вернуть: git show HEAD:$f  (данные из новой версии не откатывать)"
    fi
done

for m in "${ROUNDTRIP[@]}"; do
    [ -f "$m" ] || continue
    # Ищем ЗАПИСЬ, а не любое упоминание: safe_dump внутри click.echo/print — это печать
    # превью (`--dry`), она комментариям в файле не угрожает. Строки-комментарии тоже мимо.
    if grep -E '^[^#]*yaml\.safe_dump\(' "$m" | grep -qvE 'click\.echo|print\('; then
        warn "$m обязан писать round-trip, а зовёт yaml.safe_dump — комментарии умрут"
        warn "  см. docs/glossary.md → «Запись YAML: три стратегии»"
    fi
done

exit 0
