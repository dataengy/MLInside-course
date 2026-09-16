"""Собрать ml-platform/features.parquet — витрину признаков для демо 1 — из сырья jaffle shop.

Логика та же, что у dbt-модели feature_mart из демо 2
(02-dagster-dbt/analytics_dbt/models/marts/feature_mart.sql), только на pandas:
в Quick Start dbt ещё нет, ассет feature_table просто читает parquet.

    python scripts/make_features.py                      # срез 2018-03-01 — состояние «до демо»
    python scripts/make_features.py --cutoff 2018-03-15  # «пришли новые данные» (шаг 4 демо)

Одна строка = один клиент, индекс — customer_id (в признаки модели он не попадает).
Признаки — по заказам ДО даты среза, target — был ли заказ ПОСЛЕ неё.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "ml-platform" / "features.parquet"
DEFAULT_CUTOFF = "2018-03-01"


def build(cutoff: str) -> pd.DataFrame:
    customers = pd.read_csv(DATA / "raw_customers.csv").rename(columns={"id": "customer_id"})
    orders = pd.read_csv(DATA / "raw_orders.csv", parse_dates=["order_date"]).rename(
        columns={"id": "order_id", "user_id": "customer_id"}
    )
    payments = pd.read_csv(DATA / "raw_payments.csv")
    payments["amount"] = payments["amount"] / 100  # в сырье центы

    # оплаты по способам на заказ — как в модели orders у jaffle shop
    per_order = payments.pivot_table(
        index="order_id", columns="payment_method", values="amount", aggfunc="sum", fill_value=0
    )
    orders = orders.join(per_order, on="order_id")
    orders["amount"] = orders[list(per_order.columns)].sum(axis=1)

    cut = pd.Timestamp(cutoff)
    history = (
        orders[orders.order_date < cut]
        .groupby("customer_id")
        .agg(
            n_orders=("order_id", "count"),
            total_amount=("amount", "sum"),
            avg_order_value=("amount", "mean"),
            last_order=("order_date", "max"),
            coupon_share=("coupon", lambda s: float((s > 0).mean())),
            n_returns=("status", lambda s: int(s.isin(["returned", "return_pending"]).sum())),
        )
    )
    history["days_since_last_order"] = (cut - history.pop("last_order")).dt.days
    future = set(orders.loc[orders.order_date >= cut, "customer_id"])

    df = customers[["customer_id"]].set_index("customer_id").join(history)
    df["n_orders"] = df["n_orders"].fillna(0).astype("int64")
    df["total_amount"] = df["total_amount"].fillna(0.0)
    df["n_returns"] = df["n_returns"].fillna(0).astype("int64")
    df["target"] = df.index.isin(future).astype("int64")
    df["split"] = ["test" if cid % 5 == 0 else "train" for cid in df.index]
    return df[
        [
            "n_orders",
            "total_amount",
            "avg_order_value",
            "days_since_last_order",
            "coupon_share",
            "n_returns",
            "target",
            "split",
        ]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF, help="дата среза, YYYY-MM-DD")
    args = parser.parse_args()
    df = build(args.cutoff)
    df.to_parquet(OUT)
    known = int(df["avg_order_value"].notna().sum())
    print(
        f"{OUT.relative_to(ROOT)}: срез {args.cutoff}, клиентов {len(df)}, "
        f"с историей {known}, target=1 у {int(df['target'].sum())}"
    )


if __name__ == "__main__":
    main()
