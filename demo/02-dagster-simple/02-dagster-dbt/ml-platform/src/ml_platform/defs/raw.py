# src/ml_platform/defs/raw.py — АССЕТЫ ЗАГРУЗКИ: верх графа, до dbt (слайд 25).
#
# Это состояние «до демо»: в графе есть только загрузка, dbt-проекта в нём ещё нет.
# У dbt-источника нет кода — это ссылка на таблицу, которую сделал кто-то другой;
# «кто-то другой» — вот эти три ассета.
#
# Ключ ассета (`raw_customers`) — то самое общее имя, по которому на шаге «сшивка»
# граф склеится с dbt-источником: тот же ключ пропишется в _sources.yml как
# meta.dagster.asset_key. Имя таблицы в складе (`raw.raw_customers`) и ключ ассета —
# РАЗНЫЕ вещи; совпадать обязаны ключи.
import dagster as dg
import duckdb
import pandas as pd

from ml_platform.project import DATA, DUCKDB_PATH

TABLES = ("raw_customers", "raw_orders", "raw_payments")

# DUCKDB ПУСКАЕТ ТОЛЬКО ОДНОГО ПИСАТЕЛЯ В ФАЙЛ. Исполнитель Dagster по умолчанию
# многопроцессный, и три загрузки — независимые ассеты, то есть пойдут ПАРАЛЛЕЛЬНО:
#   IO Error: Could not set lock on file ... Conflicting lock is held ... (PID ...)
# Лечится не ретраями, а объявлением пула: pool="duckdb" у всех, кто трогает этот файл,
# плюс лимит 1 в .dagster_home/dagster.yaml (его пишет `just reset`).
#
# ГРАНУЛЯРНОСТЬ ПУЛА — ЛОВУШКА. Нужна `granularity: op`:
#     concurrency:
#       pools:
#         granularity: op      # ← НЕ run
#         default_limit: 1
# `granularity: run` читается как «по одному за раз» и звучит правильнее, но ограничивает
# число ОДНОВРЕМЕННЫХ ЗАПУСКОВ на пул: внутри одного запуска шаги по-прежнему идут
# параллельно, и блокировка DuckDB возвращается. Проверено на dagster 1.13.22.
# В складе на нормальном движке (Postgres, Snowflake) пул не нужен — это цена DuckDB.
POOL = "duckdb"

# ТИПЫ СЫРЬЯ — ОТВЕТСТВЕННОСТЬ ЗАГРУЗЧИКА. В оригинальном jaffle shop raw_orders был seed,
# и тип даты выводил dbt. Здесь таблицу пишем мы, а CSV типов не несёт: без явного разбора
# order_date ляжет в склад строкой (VARCHAR), stg_orders и orders её так и протащат,
# а feature_mart упадёт на `where order_date < date '2018-03-01'`:
#   Binder Error: Cannot compare values of type VARCHAR and type DATE.
# Наглядно про контракт схемы: ассет загрузки отвечает не только за строки, но и за типы.
DATE_COLUMNS = {"raw_orders": ["order_date"]}


def load_csv(name: str) -> int:
    """CSV → raw.<name> в DuckDB; возвращает число строк. Обычный Python, без API Dagster."""
    df = pd.read_csv(DATA / f"{name}.csv")
    for col in DATE_COLUMNS.get(name, []):
        # .dt.date, а не datetime: в складе нужен DATE, как его дал бы seed
        df[col] = pd.to_datetime(df[col]).dt.date
    # соединение закрываем сразу: DuckDB не пускает второго писателя в тот же файл,
    # а следом за загрузкой в том же прогоне пойдёт dbt — уже своим процессом
    with duckdb.connect(str(DUCKDB_PATH)) as con:
        con.execute("create schema if not exists raw")
        con.register("df_in", df)
        con.execute(f"create or replace table raw.{name} as select * from df_in")
    return len(df)


# dagster/row_count — служебный ключ метаданных: UI рисует его отдельной строкой.
# ≠ слайд: `key=` и `name=` вместе Dagster не принимает, поэтому ключ задаёт ТОЛЬКО
# `key=` (имя ассета Dagster выведет из ключа сам).
@dg.asset(key=dg.AssetKey(["raw_customers"]), group_name="raw", compute_kind="duckdb", pool=POOL)
def raw_customers() -> dg.MaterializeResult:
    return dg.MaterializeResult(metadata={"dagster/row_count": load_csv("raw_customers")})


@dg.asset(key=dg.AssetKey(["raw_orders"]), group_name="raw", compute_kind="duckdb", pool=POOL)
def raw_orders() -> dg.MaterializeResult:
    return dg.MaterializeResult(metadata={"dagster/row_count": load_csv("raw_orders")})


@dg.asset(key=dg.AssetKey(["raw_payments"]), group_name="raw", compute_kind="duckdb", pool=POOL)
def raw_payments() -> dg.MaterializeResult:
    return dg.MaterializeResult(metadata={"dagster/row_count": load_csv("raw_payments")})
