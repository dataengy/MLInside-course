"""Общая оснастка тестов демо 2.

Два правила, из-за которых оснастка вообще нужна:

1. ТЕСТЫ НЕ ТРОГАЮТ СКЛАД ДЕМО. `ml_platform.project.DUCKDB_PATH` указывает на
   02-dagster-dbt/jaffle_shop.duckdb — состояние, которое готовит `just reset` и
   показывают на записи. Тесты работают в своём временном файле: путь подменяется
   и ассетам (monkeypatch), и dbt (переменная окружения DUCKDB_PATH).

2. ТЕСТЫ ПРОВЕРЯЮТ КАНОН ИЗ stash/, а не рабочие копии в defs/: рабочие появляются
   по ходу демо (`just level-1`, `just level-2-ml`) и правятся вживую.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]  # ml-platform/
DEMO = ROOT.parent  # 02-dagster-dbt/
DBT_DIR = DEMO / "analytics_dbt"
STASH = DEMO / "stash"
DBT_BIN = ROOT / ".venv" / "bin" / "dbt"


def load_by_path(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_dbt(*args: str, duckdb_path: Path, check: bool = True) -> subprocess.CompletedProcess:
    """dbt своим процессом — так же, как его запускает DbtCliResource."""
    env = {**os.environ, "DUCKDB_PATH": str(duckdb_path)}
    return subprocess.run(
        [str(DBT_BIN), *args, "--profiles-dir", ".", "--project-dir", str(DBT_DIR)],
        cwd=DBT_DIR, env=env, check=check, capture_output=True, text=True,
    )


@pytest.fixture(scope="session")
def warehouse(tmp_path_factory) -> Path:
    """Отдельный файл DuckDB на весь прогон тестов: склад демо остаётся нетронутым."""
    return tmp_path_factory.mktemp("warehouse") / "test.duckdb"


@pytest.fixture(scope="session")
def raw_loaded(warehouse):
    """Сырьё в raw.* — тем же кодом, которым его грузят ассеты демо."""
    raw = load_by_path("demo2_raw", ROOT / "src" / "ml_platform" / "defs" / "raw.py")
    raw.DUCKDB_PATH = warehouse  # см. правило 1 в докстринге модуля
    counts = {name: raw.load_csv(name) for name in raw.TABLES}
    return counts


@pytest.fixture(scope="session")
def built(warehouse, raw_loaded):
    """Собранный dbt-проект поверх загруженного сырья: `dbt build` целиком."""
    proc = run_dbt("build", duckdb_path=warehouse)
    assert "ERROR=0" in proc.stdout, proc.stdout[-3000:]
    return warehouse


@pytest.fixture(scope="session")
def manifest(warehouse) -> dict:
    """manifest.json — единственное, что Dagster знает о проекте (слайд 21)."""
    import json

    run_dbt("parse", "--quiet", duckdb_path=warehouse)
    return json.loads((DBT_DIR / "target" / "manifest.json").read_text())
