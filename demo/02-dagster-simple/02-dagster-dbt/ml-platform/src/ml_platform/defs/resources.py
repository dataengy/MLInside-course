# src/ml_platform/defs/resources.py — ресурс dbt регистрируется ОДИН раз (слайд 20, низ).
#
# Один и тот же ресурс `dbt` нужен и уровню 0 (один ассет = весь `dbt build`), и уровню 1
# (@dbt_assets). Поэтому он лежит в defs/ всегда, а не появляется по ходу демо:
# меняется только то, КАК мы разворачиваем проект, а не чем его запускаем.
import dagster as dg
from dagster_dbt import DbtCliResource

from ml_platform.project import dbt_project


@dg.definitions
def resources() -> dg.Definitions:
    return dg.Definitions(
        resources={
            # DbtCliResource принимает DbtProject целиком: из него берутся
            # project_dir и profiles_dir, задавать их второй раз не нужно
            "dbt": DbtCliResource(project_dir=dbt_project),
        }
    )
