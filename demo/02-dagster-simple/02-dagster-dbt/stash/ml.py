# stash/ml.py → defs/ml.py — УРОВЕНЬ 2, НИЗ: продолжение dbt-графа в ML (слайд 25).
#
# feature_mart — СТЫК: сверху её строит dbt, снизу её читает обучение.
# Сшивка вниз делается не через meta, а через deps=[AssetKey("feature_mart")]:
# ключ dbt-модели известен, кода dbt мы не касаемся.
from pathlib import Path

import dagster as dg
import duckdb
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from ml_platform.project import DUCKDB_PATH, ROOT

# dbt-duckdb кладёт модели в схему main (в profiles.yml схема не задана)
FEATURE_MART = "main.feature_mart"


@dg.asset(
    deps=[dg.AssetKey("feature_mart")],  # ← ключ dbt-МОДЕЛИ, ребро появляется само
    group_name="ml",
    compute_kind="pandas",
    pool="duckdb",  # читает тот же файл склада
    description="Обучающая выборка: витрину признаков читаем из склада",
)
def training_dataset() -> dg.Output[pd.DataFrame]:
    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        df = con.execute(f"select * from {FEATURE_MART}").df()
    # customer_id — ключ витрины, а не признак: в X он попасть не должен
    df = df.set_index("customer_id").dropna()
    train = df[df.split == "train"].drop(columns="split")
    return dg.Output(train, metadata={"dagster/row_count": len(train)})


@dg.asset(group_name="ml", compute_kind="sklearn")
def trained_model(training_dataset: pd.DataFrame) -> dg.MaterializeResult:
    X = training_dataset.drop(columns="target")
    y = training_dataset["target"]
    clf = LogisticRegression().fit(X, y)
    roc = roc_auc_score(y, clf.predict_proba(X)[:, 1])
    models = ROOT / "models"
    models.mkdir(exist_ok=True)
    joblib.dump(clf, models / "clf.joblib")
    return dg.MaterializeResult(
        metadata={
            "roc_auc": round(float(roc), 4),
            "rows": len(training_dataset),
            "features": len(X.columns),
        }
    )


# УРОВЕНЬ 3 со стороны Python: проверка рядом с ассетом, в дополнение к dbt-тестам,
# которые приехали сами. Смысл тот же, что у net_propuskov в демо 1.
@dg.asset_check(asset=training_dataset, blocking=True)
def net_propuskov(training_dataset: pd.DataFrame) -> dg.AssetCheckResult:
    bad = int(training_dataset["target"].isna().sum())
    return dg.AssetCheckResult(
        passed=bad == 0,
        severity=dg.AssetCheckSeverity.ERROR,
        metadata={"propuski": bad},
    )
