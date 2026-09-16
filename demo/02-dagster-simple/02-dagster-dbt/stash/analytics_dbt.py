# stash/analytics_dbt.py → defs/analytics_dbt.py — УРОВЕНЬ 1: манифест → ассеты (слайд 23).
#
# ОДИН декоратор → N ассетов: по одному на каждую модель из manifest.json.
# Функция под декоратором одна на всех, и она решает только одно — как запускать dbt.
#
# Что появляется в графе сразу же, без дополнительного кода:
#   · по узлу на каждую модель (6 штук: три staging, три marts);
#   · dbt-тесты как asset checks на карточках моделей — это уже УРОВЕНЬ 3 (слайд 26),
#     он приезжает даром вместе с `build`;
#   · узлы источников jaffle_raw/raw_* — пока БЕЗ родителей: ключи не сшиты.
import dagster as dg
from dagster_dbt import DbtCliResource, dbt_assets

from ml_platform.project import dbt_project


@dbt_assets(manifest=dbt_project.manifest_path, pool="duckdb")
def analytics_dbt(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    # context передаём в cli → dbt получает выборку РОВНО тех моделей, которые Dagster
    # решил материализовать: пересчёт 'key:feature_mart+' станет `dbt build --select ...`
    #
    # stream(), а не wait(): каждое событие dbt превращается в событие Dagster по мере
    # выполнения — узлы зеленеют один за другим, а не все разом в конце
    yield from dbt.cli(["build"], context=context).stream()
