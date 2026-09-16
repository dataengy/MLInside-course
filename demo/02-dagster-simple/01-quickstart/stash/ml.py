# src/ml_platform/defs/ml.py — Quick Start целиком: слайды 10–16 в одном файле.
# На шаге 2 демо файл КЛАДЁТСЯ в defs/ готовым (`just add-assets`), вживую не набирается.
#
# Отличия от кода на слайдах — две, обе помечены «≠ слайд»:
#   · training_dataset выбрасывает колонку split: иначе строка "train" попадает в X,
#     и LogisticRegression падает на «could not convert string to float»;
#   · trained_model создаёт папку models/ перед joblib.dump.
from datetime import timedelta
from pathlib import Path

import dagster as dg
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

# ── шаг 7 · свежесть: «данные не приехали», а не «упало» ──────────────────────
# 12 ч без обновления → WARN, 24 ч → FAIL
fresh = dg.FreshnessPolicy.time_window(
    fail_window=timedelta(hours=24),
    warn_window=timedelta(hours=12),
)


# ── шаг 1 · первый ассет ──────────────────────────────────────────────────────
@dg.asset(
    group_name="features",  # папка в UI
    compute_kind="pandas",  # бейдж: чем считаем
    description="Витрина признаков",
    freshness_policy=fresh,  # шаг 7
)
def feature_table() -> pd.DataFrame:
    # тело — обычный Python, без API Dagster
    # (features.parquet собран из сырья jaffle shop: scripts/make_features.py)
    return pd.read_parquet("features.parquet")


# ── шаг 2 · зависимость — это аргумент функции ────────────────────────────────
@dg.asset(group_name="features")
def training_dataset(
    feature_table: pd.DataFrame,  # ассет выше
) -> pd.DataFrame:  # аргумент = ребро графа
    # значение приехало готовым объектом
    df = feature_table.dropna()
    # ≠ слайд: split больше не нужен — иначе строка попадёт в признаки модели
    return df[df.split == "train"].drop(columns="split")


# ── шаг 3 · модель — такой же ассет, плюс метаданные ──────────────────────────
@dg.asset(group_name="ml", compute_kind="sklearn")
def trained_model(
    training_dataset: pd.DataFrame,
) -> dg.MaterializeResult:
    X = training_dataset.drop(columns="target")
    y = training_dataset["target"]
    clf = LogisticRegression().fit(X, y)
    proba = clf.predict_proba(X)[:, 1]
    roc = roc_auc_score(y, proba)
    # где лежит модель — решаем сами
    Path("models").mkdir(exist_ok=True)  # ≠ слайд: папки может не быть
    joblib.dump(clf, "models/clf.joblib")
    # «ассет готов» + метаданные; числа ложатся на график по времени в UI
    return dg.MaterializeResult(
        metadata={
            "roc_auc": round(float(roc), 4),
            "rows": len(training_dataset),
            "features": len(X.columns),
        }
    )


# ── шаг 6 · asset check — проверка рядом с ассетом ────────────────────────────
@dg.asset_check(
    asset=training_dataset,  # к какому ассету
    blocking=True,  # упала → downstream стоит
)
def net_propuskov(
    training_dataset: pd.DataFrame,
) -> dg.AssetCheckResult:
    target = training_dataset["target"]
    bad = int(target.isna().sum())
    return dg.AssetCheckResult(
        passed=bad == 0,  # статус на карточке
        # ERROR блокирует, WARN лишь сообщает
        severity=dg.AssetCheckSeverity.ERROR,
        metadata={"propuski": bad},  # на график
    )
