# stash/level0.py → defs/level0.py — УРОВЕНЬ 0: dbt как чёрный ящик (слайд 20).
#
# Один ассет = ВЕСЬ dbt-проект. Расписание, ретраи, логи — есть уже здесь;
# графа моделей, тестов как проверок и частичного пересчёта — нет.
# На шаге «уровень 1» этот файл УДАЛЯЕТСЯ: его заменяет @dbt_assets.
import dagster as dg
from dagster_dbt import DbtCliResource


@dg.asset(
    compute_kind="dbt",
    pool="duckdb",  # тот же файл DuckDB, что у загрузки
    group_name="dbt",
    deps=["raw_customers", "raw_orders", "raw_payments"],  # загрузка выше
    description="Весь dbt-проект одним ассетом: внутри dbt build",
)
def dbt_project_build(dbt: DbtCliResource) -> None:
    # build, а не run: модели и тесты одним проходом.
    # .wait() — дождаться конца; события внутри нас на этом уровне не интересуют,
    # поэтому в UI будет один узел и один лог, без разбивки по моделям.
    dbt.cli(["build"]).wait()
