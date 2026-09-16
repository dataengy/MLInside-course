"""ML-ассеты демо 2 — низ сквозного графа (слайд 25), продолжение dbt.

Проверяем канон из stash/ml.py: он кладётся в defs/ на шаге `just level-2-ml`.
"""

from __future__ import annotations

import dagster as dg
import pytest

from .conftest import DEMO, ROOT, load_by_path


@pytest.fixture(scope="module")
def ml(built):
    """stash/ml.py с подменённым складом и папкой моделей: демо не задеваем."""
    module = load_by_path("demo2_ml", DEMO / "stash" / "ml.py")
    module.DUCKDB_PATH = built
    return module


def test_training_dataset_prodolzhaet_dbt_graf(ml):
    """Сшивка ВНИЗ — через deps=[AssetKey("feature_mart")], а не через meta."""
    parents = {
        k.to_user_string()
        for k in ml.training_dataset.asset_deps[dg.AssetKey(["training_dataset"])]
    }
    assert parents == {"feature_mart"}


def test_chisla_sovpadayut_s_demo_1(ml, tmp_path, monkeypatch):
    """rows 35, roc_auc 0.6049, features 6 — те же, что в демо 1 (см. test_feature_mart)."""
    monkeypatch.setattr(ml, "ROOT", tmp_path)
    result = dg.materialize(
        [ml.training_dataset, ml.trained_model, ml.net_propuskov]
    )
    assert result.success
    assert result.get_asset_check_evaluations()[0].passed

    (mat,) = result.asset_materializations_for_node("trained_model")
    md = {k: v.value for k, v in mat.metadata.items()}
    assert md["features"] == 6
    assert md["rows"] == 35
    assert md["roc_auc"] == 0.6049
    assert (tmp_path / "models" / "clf.joblib").is_file()


def test_customer_id_ne_priznak(ml):
    """Ключ витрины — индекс: номер клиента в признаки модели попадать не должен."""
    result = dg.materialize([ml.training_dataset])
    assert result.success
    df = result.output_for_node("training_dataset")
    assert df.index.name == "customer_id"
    assert "customer_id" not in df.columns
    assert "split" not in df.columns
    assert not df.isna().any().any()


def test_proverka_lovit_propuski(ml):
    import pandas as pd

    ok = ml.net_propuskov(training_dataset=pd.DataFrame({"target": [0, 1]}))
    assert ok.passed and ok.metadata["propuski"].value == 0
    bad = ml.net_propuskov(training_dataset=pd.DataFrame({"target": [0, None]}))
    assert not bad.passed and bad.metadata["propuski"].value == 1
