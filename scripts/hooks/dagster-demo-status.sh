#!/usr/bin/env bash
# SessionStart hook: демо упрощённой деки Dagster (demo/02-dagster-simple).
# Fail-open, без сети, без python — только bash, чтобы укладываться в таймаут.
#
# Отвечает на один вопрос: можно ли прямо сейчас садиться записывать.
# Ловит три состояния, каждое из которых уже срывало прогон:
#   · демо не возвращено в состояние «до демо» (`just reset` не сделан) — граф на записи
#     начнётся не с того, а `_sources.yml` останется сшитым и уедет в коммит;
#   · распались хардлинки общего сырья — демо 1 и демо 2 покажут разные числа;
#   · окружение не собрано — `just setup` на записи это минуты.
# Spec: docs/dagster-simple-demos.md
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

BLOCK="demo/02-dagster-simple"
D1="$BLOCK/01-quickstart"
D2="$BLOCK/02-dagster-dbt"
[ -d "$BLOCK" ] || exit 0

dirty=()

# ── 1. состояние «до демо» ───────────────────────────────────────────────────────────────
# демо 1: defs/ml.py — рабочая копия, появляется на шаге 2
[ -f "$D1/ml-platform/src/ml_platform/defs/ml.py" ] && dirty+=("демо 1: defs/ml.py на месте")
# демо 2: файлы шагов и склад
for f in level0 analytics_dbt ml; do
    [ -f "$D2/ml-platform/src/ml_platform/defs/$f.py" ] && dirty+=("демо 2: defs/$f.py на месте")
done
[ -f "$D2/jaffle_shop.duckdb" ] && dirty+=("демо 2: склад jaffle_shop.duckdb не стёрт")
# демо 2: _sources.yml — ЕДИНСТВЕННЫЙ файл под гитом, который правит показ
if [ -f "$D2/analytics_dbt/models/staging/_sources.yml" ] && [ -f "$D2/stash/_sources.plain.yml" ]; then
    if ! cmp -s "$D2/analytics_dbt/models/staging/_sources.yml" "$D2/stash/_sources.plain.yml"; then
        dirty+=("демо 2: _sources.yml СШИТ — файл под гитом, уедет в коммит")
    fi
fi

if [ ${#dirty[@]} -gt 0 ]; then
    echo "[dagster-demo] ⚠ не в состоянии «до демо» — just reset в папке демо"
    for d in "${dirty[@]}"; do echo "[dagster-demo]   · $d"; done
fi

# ── 2. хардлинки общего сырья ────────────────────────────────────────────────────────────
broken=0
for name in raw_customers.csv raw_orders.csv raw_payments.csv; do
    a="$D1/data/$name"; b="$D2/data/$name"
    [ -f "$a" ] && [ -f "$b" ] || continue
    [ "$(stat -f %i "$a" 2>/dev/null)" = "$(stat -f %i "$b" 2>/dev/null)" ] || broken=$((broken + 1))
done
a="$D1/scripts/status.py"; b="$D2/scripts/status.py"
if [ -f "$a" ] && [ -f "$b" ]; then
    [ "$(stat -f %i "$a" 2>/dev/null)" = "$(stat -f %i "$b" 2>/dev/null)" ] || broken=$((broken + 1))
fi
if [ "$broken" -gt 0 ]; then
    echo "[dagster-demo] ⚠ распались хардлинки общего сырья ($broken) — just demo-files-link"
    echo "[dagster-demo]   (нормально после клона: git хардлинков не хранит)"
fi

# ── 3. окружения ─────────────────────────────────────────────────────────────────────────
for d in "$D1" "$D2"; do
    [ -x "$d/ml-platform/.venv/bin/dagster" ] || \
        echo "[dagster-demo] ⚠ нет окружения ${d#demo/02-dagster-simple/} — cd $d && just setup"
done

exit 0
