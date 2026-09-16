"""feature_mart — СТЫК dbt и ML (слайд 18): сверху её строит dbt, снизу читает обучение.

Проверяется то же, что у витрины демо 1, но на SQL: одна строка на клиента, домены
target и split, отсутствие утечки будущего. Плюс главный кросс-тест обеих демо —
dbt-версия витрины и pandas-версия должны давать ОДНО И ТО ЖЕ.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from .conftest import DEMO, load_by_path

CUTOFF = "2018-03-01"
FEATURES = ["n_orders", "total_amount", "avg_order_value", "days_since_last_order",
            "coupon_share", "n_returns"]


@pytest.fixture(scope="module")
def mart(built) -> pd.DataFrame:
    with duckdb.connect(str(built), read_only=True) as con:
        return con.execute("select * from main.feature_mart").df().set_index("customer_id")


def test_odna_stroka_na_klienta(mart):
    assert mart.index.is_unique
    assert len(mart) == 100, "в сырье jaffle shop 100 клиентов"


def test_domeny_target_i_split(mart):
    assert set(mart["target"].unique()) <= {0, 1}
    assert set(mart["split"].unique()) == {"train", "test"}
    assert all((int(cid) % 5 == 0) == (split == "test") for cid, split in mart["split"].items())


def test_net_utechki_buduschego(built):
    """Признаки — только по заказам ДО среза; проверяем напрямую по складу.

    Если в history просочится `>=` вместо `<`, n_orders вырастет — и модель начнёт
    «предсказывать» то, что уже видела.
    """
    with duckdb.connect(str(built), read_only=True) as con:
        before, total = con.execute(
            f"""
            select
              (select count(*) from main.orders where order_date < date '{CUTOFF}'),
              (select sum(n_orders) from main.feature_mart)
            """
        ).fetchone()
    assert total == before, "сумма n_orders должна равняться числу заказов ДО среза"


def test_klienty_bez_istorii_pustye(mart):
    no_history = mart[mart["n_orders"] == 0]
    assert len(no_history) > 0
    assert no_history["avg_order_value"].isna().all()


def test_vitrina_dbt_sovpadaet_s_vitrinoj_pandas(mart):
    """КРОСС-ТЕСТ ДВУХ ДЕМО. feature_mart.sql (демо 2) и make_features.py (демо 1)
    считают одну и ту же витрину двумя способами — на SQL и на pandas.

    Именно поэтому обе демо показывают одинаковые метаданные модели
    (rows 35, roc_auc 0.6049, features 6). Разъедутся — разъедется и рассказ:
    в демо 2 придётся объяснять, почему числа другие.
    """
    demo1 = load_by_path(
        "demo1_make_features_cross", DEMO.parent / "01-quickstart" / "scripts" / "make_features.py"
    )
    pandas_mart = demo1.build(CUTOFF)

    assert set(pandas_mart.index) == set(mart.index)
    left = mart.sort_index()
    right = pandas_mart.sort_index()

    assert (left["split"] == right["split"]).all()
    assert (left["target"].astype("int64") == right["target"]).all()
    for col in FEATURES:
        pd.testing.assert_series_equal(
            left[col].astype("float64"),
            right[col].astype("float64"),
            check_names=False,
            rtol=1e-9,
        )
