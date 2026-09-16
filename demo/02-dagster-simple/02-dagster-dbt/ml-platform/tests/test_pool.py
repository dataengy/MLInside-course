"""ПУЛ duckdb — то, без чего демо падает на ровном месте.

DuckDB пускает в файл только одного писателя, а исполнитель Dagster по умолчанию
многопроцессный. Забыли pool="duckdb" у ассета — и запуск падает не всегда, а когда
повезёт с таймингом: три загрузки стартуют одновременно и ловят

    IO Error: Could not set lock on file ... Conflicting lock is held ... (PID ...)

Тест держит договорённость: всё, что открывает файл склада, объявляет пул.
"""

from __future__ import annotations

import yaml

from .conftest import DEMO, ROOT, load_by_path

POOL = "duckdb"


def _pool(assets_def) -> str | None:
    return assets_def.node_def.pool


def test_assety_zagruzki_v_pule():
    raw = load_by_path("demo2_raw_pool", ROOT / "src" / "ml_platform" / "defs" / "raw.py")
    assert raw.POOL == POOL
    for name in ("raw_customers", "raw_orders", "raw_payments"):
        assert _pool(getattr(raw, name)) == POOL, name


def test_dbt_i_ml_v_tom_zhe_pule():
    """dbt пишет в тот же файл своим процессом; training_dataset его читает."""
    level0 = (DEMO / "stash" / "level0.py").read_text()
    analytics = (DEMO / "stash" / "analytics_dbt.py").read_text()
    ml = (DEMO / "stash" / "ml.py").read_text()
    for name, src in (("level0.py", level0), ("analytics_dbt.py", analytics), ("ml.py", ml)):
        assert f'pool="{POOL}"' in src, f"{name}: ассет без пула — вернётся блокировка DuckDB"


def test_granulyarnost_pula_op_a_ne_run():
    """`granularity: run` ограничивает ЗАПУСКИ, а не шаги внутри запуска.

    Ловушка: `run` читается как «по одному за раз», но внутри одного запуска шаги
    продолжают идти параллельно, и блокировка возвращается. Нужен `op`.
    Конфиг пишет `just reset`, поэтому проверяем сам Justfile — он под гитом.
    """
    justfile = (DEMO / "Justfile").read_text()
    assert "granularity: op" in justfile
    assert "granularity: run" not in justfile
    assert "default_limit: 1" in justfile


def test_zhivoj_dagster_yaml_soglasen_s_justfile():
    """Если .dagster_home уже создан — он должен быть создан правильным."""
    live = DEMO / ".dagster_home" / "dagster.yaml"
    if not live.exists():
        return
    cfg = yaml.safe_load(live.read_text())
    pools = cfg["concurrency"]["pools"]
    assert pools["granularity"] == "op"
    assert pools["default_limit"] == 1
