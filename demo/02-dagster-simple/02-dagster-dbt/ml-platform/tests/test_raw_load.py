"""Ассеты загрузки: строки и — что важнее — ТИПЫ.

Регрессия, на которой демо один раз уже упало: CSV типов не несёт, и без явного разбора
order_date ложится в склад строкой. Ошибка всплывает не на загрузке, а тремя моделями
ниже, в feature_mart:
    Binder Error: Cannot compare values of type VARCHAR and type DATE
"""

from __future__ import annotations

import duckdb


def test_stroki_zagruzheny(raw_loaded):
    assert raw_loaded == {"raw_customers": 100, "raw_orders": 99, "raw_payments": 113}


def test_order_date_eto_data_a_ne_stroka(warehouse, raw_loaded):
    with duckdb.connect(str(warehouse), read_only=True) as con:
        types = dict(
            con.execute(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = 'raw' and table_name = 'raw_orders'"
            ).fetchall()
        )
    assert types["order_date"] == "DATE", (
        "order_date уехал строкой — feature_mart упадёт на сравнении с date '...'"
    )


def test_tablicy_lezhat_v_sheme_raw(warehouse, raw_loaded):
    """Схема raw — то, что объявлено в _sources.yml (schema: raw). Ключ ассета к ней не привязан."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        tables = {
            row[0]
            for row in con.execute(
                "select table_name from information_schema.tables where table_schema = 'raw'"
            ).fetchall()
        }
    assert tables == {"raw_customers", "raw_orders", "raw_payments"}
