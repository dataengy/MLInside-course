"""Состояние графа в терминале — то же, что UI Dagster показывает на карточках ассетов.

Для каждого ассета: когда материализован, свежий он или устарел (stale) и почему,
ключевые метаданные последней материализации; для проверок — статус последнего запуска.
Нужен, чтобы проверить демо без браузера (`just status`, `just smoke`) и чтобы на записи
было куда посмотреть, если UI не отрисовался.

Запуск — из папки ml-platform, окружением проекта:  uv run python ../scripts/status.py
Флаг --expect-stale K1,K2 — выйти с кодом 1, если перечисленные ассеты НЕ устарели,
а остальные устарели (так смоук проверяет ключевой момент демо).

Файл общий для всех трёх демо — хардлинк, реестр в ../../files.yml.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import warnings
from datetime import datetime

import dagster as dg

# Внутренний API Dagster: тот же вычислитель статуса, которым пользуется UI.
# Проверено на dagster 1.13.22; при обновлении Dagster сверить сигнатуры.
from dagster._core.definitions.data_version import CachingStaleStatusResolver, StaleStatus
from dagster._core.loader import LoadingContextForTest

warnings.filterwarnings("ignore", category=dg.PreviewWarning)
warnings.filterwarnings("ignore", category=dg.BetaWarning)

SHOW_METADATA = ("rows", "roc_auc", "features", "run_id", "model_uri", "dagster/row_count")


def _fmt_ts(ts: float | None) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="ml_platform.definitions")
    parser.add_argument(
        "--expect-stale", default=None, help="ключи через запятую; пустая строка — ничего не stale"
    )
    args = parser.parse_args()

    # definitions.py каркаса create-dagster отдаёт LazyDefinitions — вызываем загрузчик
    loaded = importlib.import_module(args.module).defs
    defs = loaded if isinstance(loaded, dg.Definitions) else loaded()
    graph = defs.resolve_asset_graph()
    instance = dg.DagsterInstance.get()
    resolver = CachingStaleStatusResolver(instance, graph, LoadingContextForTest(instance))

    stale_now: set[str] = set()
    keys = [k for k in graph.toposorted_asset_keys if graph.get(k).is_materializable]
    print(f"{'ассет':28} {'материализован':>14}  статус")
    for key in keys:
        event = instance.get_latest_materialization_event(key)
        ts = event.timestamp if event else None
        status = resolver.get_status(key)
        name = key.to_user_string()
        if status == StaleStatus.STALE:
            stale_now.add(name)
            causes = "; ".join(
                f"{c.key.asset_key.to_user_string()}: {c.reason}"
                for c in resolver.get_stale_root_causes(key)
            )
            label = f"STALE — {causes}"
        elif status == StaleStatus.MISSING:
            label = "никогда не материализован"
        else:
            label = "свежий"
        print(f"{name:28} {_fmt_ts(ts):>14}  {label}")
        if event and event.asset_materialization:
            md = event.asset_materialization.metadata
            shown = {k: md[k].value for k in SHOW_METADATA if k in md}
            if shown:
                print(f"{'':28} {'':>14}  {shown}")

    check_keys = list(graph.asset_check_keys)
    if check_keys:
        latest = instance.event_log_storage.get_latest_asset_check_execution_by_key(check_keys)
        print("\nпроверки")
        for ck in sorted(check_keys, key=lambda c: c.to_user_string()):
            rec = latest.get(ck)
            state = rec.status.value if rec else "не запускалась"
            print(f"  {ck.to_user_string():60} {state}")

    if args.expect_stale is not None:
        expected = {k.strip() for k in args.expect_stale.split(",") if k.strip()}
        if stale_now != expected:
            print(f"\nОЖИДАЛОСЬ stale: {sorted(expected)}, по факту: {sorted(stale_now)}")
            return 1
        print(f"\nstale ровно как ожидалось: {sorted(expected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
