"""Рёбра графа и проверки — чем сшито, что висит без родителя, сколько тестов приехало.

Нужен демо 2: главный его момент — сшивка ключей (слайд 25), а она видна не по
метаданным материализации, а по ФОРМЕ ГРАФА. status.py про форму ничего не знает.

    uv run python ../scripts/graph.py                       # напечатать граф и проверки
    uv run python ../scripts/graph.py --expect-edge raw_orders,stg_orders
    uv run python ../scripts/graph.py --expect-no-edge raw_orders,stg_orders
    uv run python ../scripts/graph.py --expect-keys stg_orders,feature_mart
    uv run python ../scripts/graph.py --expect-min-checks 20
    uv run python ../scripts/graph.py --expect-table main.feature_mart

Любое непрошедшее ожидание → код возврата 1 и строка «НЕ СОШЛОСЬ» (так проверяет смоук).
Запуск — из папки ml-platform, окружением проекта. Файл только для демо 2: остальным
двум демо нечего сшивать.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import warnings

import dagster as dg

warnings.filterwarnings("ignore", category=dg.PreviewWarning)
warnings.filterwarnings("ignore", category=dg.BetaWarning)


def load_graph(module: str):
    loaded = importlib.import_module(module).defs
    defs = loaded if isinstance(loaded, dg.Definitions) else loaded()
    return defs.resolve_asset_graph()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--module", default="ml_platform.definitions")
    p.add_argument("--expect-edge", action="append", default=[], metavar="РОДИТЕЛЬ,ПОТОМОК")
    p.add_argument("--expect-no-edge", action="append", default=[], metavar="РОДИТЕЛЬ,ПОТОМОК")
    p.add_argument("--expect-keys", action="append", default=[], metavar="K1,K2")
    p.add_argument("--expect-min-checks", type=int, default=None)
    p.add_argument("--expect-table", action="append", default=[], metavar="СХЕМА.ТАБЛИЦА")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    graph = load_graph(args.module)
    parents: dict[str, set[str]] = {}
    for key in graph.get_all_asset_keys():
        parents[key.to_user_string()] = {
            k.to_user_string() for k in graph.get(key).parent_keys
        }
    checks = sorted(c.to_user_string() for c in graph.asset_check_keys)

    if not args.quiet:
        print(f"{'ассет':34} родители")
        for name in sorted(parents):
            src = "внешний" if name not in {k.to_user_string() for k in graph.executable_asset_keys} else ""
            shown = ", ".join(sorted(parents[name])) or "—"
            print(f"{name:34} {shown}{('   [' + src + ']') if src else ''}")
        print(f"\nпроверок всего: {len(checks)}")
        for c in checks:
            print(f"  {c}")

    problems: list[str] = []

    def edge(spec: str) -> tuple[str, str]:
        parent, child = (s.strip() for s in spec.split(",", 1))
        return parent, child

    for spec in args.expect_edge:
        parent, child = edge(spec)
        if child not in parents:
            problems.append(f"нет ассета {child} — ребро {parent} → {child} проверить нечем")
        elif parent not in parents[child]:
            problems.append(
                f"ждали ребро {parent} → {child}; родители {child}: {sorted(parents[child]) or '—'}"
            )

    for spec in args.expect_no_edge:
        parent, child = edge(spec)
        if child in parents and parent in parents[child]:
            problems.append(f"ребра {parent} → {child} быть НЕ должно, а он есть")

    for spec in args.expect_keys:
        for name in (s.strip() for s in spec.split(",")):
            if name and name not in parents:
                problems.append(f"нет ассета {name}")

    if args.expect_min_checks is not None and len(checks) < args.expect_min_checks:
        problems.append(f"проверок {len(checks)}, ждали не меньше {args.expect_min_checks}")

    if args.expect_table:
        import duckdb

        from ml_platform.project import DUCKDB_PATH

        if not DUCKDB_PATH.exists():
            problems.append(f"файла склада нет: {DUCKDB_PATH}")
        else:
            with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
                for table in args.expect_table:
                    try:
                        (rows,) = con.execute(f"select count(*) from {table}").fetchone()
                    except duckdb.Error as exc:
                        problems.append(f"таблицы {table} нет в складе: {type(exc).__name__}")
                        continue
                    if rows == 0:
                        problems.append(f"таблица {table} пуста")
                    elif not args.quiet:
                        print(f"склад: {table} — строк {rows}")

    if problems:
        print("\nНЕ СОШЛОСЬ:")
        for prob in problems:
            print(f"  · {prob}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
