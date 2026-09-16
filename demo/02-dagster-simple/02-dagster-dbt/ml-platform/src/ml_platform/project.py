# src/ml_platform/project.py — всё, что Dagster знает о dbt-проекте (слайд 21).
#
# Один объект DbtProject на проект: где проект, где профили, где manifest.json.
# Из него @dbt_assets берёт manifest_path, а DbtCliResource — рабочую папку.
#
# ≠ слайд: на слайде 21 `project_dir=ROOT / "analytics_dbt"`, то есть dbt-проект лежит
# ВНУТРИ ml-platform. Здесь он рядом с ним (так же, как в коде слайда 20:
# `project_dir="../analytics_dbt"`), поэтому путь идёт от DEMO, а не от ROOT.
import os
from pathlib import Path

from dagster_dbt import DbtProject

ROOT = Path(__file__).resolve().parents[2]  # .../02-dagster-dbt/ml-platform
DEMO = ROOT.parent  # .../02-dagster-dbt
DATA = DEMO / "data"  # сырьё jaffle shop (хардлинки, ../files.yml)
DUCKDB_PATH = DEMO / "jaffle_shop.duckdb"  # один файл DuckDB на демо

# profiles.yml читает путь к базе из окружения: `env_var('DUCKDB_PATH', '../jaffle_shop.duckdb')`.
# Значение по умолчанию годится только для ручного `dbt build` из папки analytics_dbt;
# dbt, запущенный из Dagster, наследует рабочую папку процесса, поэтому путь — АБСОЛЮТНЫЙ.
# setdefault, а не '=': ручной запуск с заданным DUCKDB_PATH должен остаться ручным.
os.environ.setdefault("DUCKDB_PATH", str(DUCKDB_PATH))

dbt_project = DbtProject(
    project_dir=DEMO / "analytics_dbt",
    profiles_dir=DEMO / "analytics_dbt",
)

# dev: при `dg dev` пересобрать манифест на старте, чтобы правки моделей были видны.
# ≠ слайд: в проде (и в `dg launch`, и в pytest) эта строка НИЧЕГО не делает — манифест
# обязан существовать заранее. Его собирает `just reset` (`dbt parse`); в проде —
# `dagster-dbt project prepare-and-package` на этапе сборки образа.
dbt_project.prepare_if_dev()
