"""Ассеты демо 1 — те же три шага, что показываются вживую, только без браузера.

`just smoke` проверяет ДЕМО (порядок шагов, stale, история запусков); эти тесты проверяют
КОД ассетов и заодно фиксируют расхождения со слайдами, перечисленные в README, —
чтобы очередная правка не отменила их молча.
"""

from __future__ import annotations

from datetime import timedelta

import dagster as dg
import pandas as pd


def test_graf_iz_treh_assetov_i_odnoj_proverki(ml):
    keys = {k.to_user_string() for k in (*ml.feature_table.keys, *ml.training_dataset.keys,
                                         *ml.trained_model.keys)}
    assert keys == {"feature_table", "training_dataset", "trained_model"}
    # зависимость объявлена аргументом функции, а не списком deps
    parents = {k.to_user_string() for k in ml.training_dataset.asset_deps[
        dg.AssetKey(["training_dataset"])]}
    assert parents == {"feature_table"}


def test_politika_svezhesti_12_i_24_chasa(ml):
    """README демо обещает: 12 ч → WARN, 24 ч → FAIL. Обещание должно держаться."""
    policy = ml.feature_table.specs_by_key[dg.AssetKey(["feature_table"])].freshness_policy
    assert policy.warn_window.to_timedelta() == timedelta(hours=12)
    assert policy.fail_window.to_timedelta() == timedelta(hours=24)


def test_compute_kind_ne_daet_selektor_kind(ml):
    """Расхождение со слайдом, записанное в README, — проверяем, что оно всё ещё так.

    `compute_kind="pandas"` рисует бейдж в UI, но селектор `kind:pandas` ничего не находит:
    он смотрит на kinds={...}. Если Dagster однажды это сведёт вместе, тест упадёт —
    и README надо будет поправить, а не тест.
    """
    spec = ml.feature_table.specs_by_key[dg.AssetKey(["feature_table"])]
    assert spec.kinds == set(), "kinds заполнились — обновить раздел README про compute_kind"


def test_ves_graf_materializuetsya_s_chislami_iz_readme(features, ml):
    """Числа на слайде и в README демо: rows 35, roc_auc 0.6049, features 6.

    Они произносятся вслух на записи, поэтому зафиксированы тестом: если срез,
    сырьё или dropna() поедут, демо начнёт показывать не то, что рассказывает.
    """
    result = dg.materialize([ml.feature_table, ml.training_dataset, ml.trained_model,
                             ml.net_propuskov])
    assert result.success
    assert result.get_asset_check_evaluations()[0].passed

    (mat,) = result.asset_materializations_for_node("trained_model")
    md = {k: v.value for k, v in mat.metadata.items()}
    # шесть признаков: split выброшен, target — цель, customer_id — индекс
    assert md["features"] == 6
    assert md["rows"] == 35
    assert md["roc_auc"] == 0.6049


def test_model_pishetsya_v_models(in_project, features, ml):
    """trained_model создаёт папку models/ сам — расхождение со слайдом из README."""
    assert not (in_project / "models").exists()
    result = dg.materialize([ml.feature_table, ml.training_dataset, ml.trained_model])
    assert result.success
    assert (in_project / "models" / "clf.joblib").is_file()


def test_training_dataset_vybrasyvaet_split(features, ml):
    """Без этого LogisticRegression падает на «could not convert string to float».

    Второе расхождение со слайдом из README: строка "train" не должна попасть в признаки.
    """
    result = dg.materialize([ml.feature_table, ml.training_dataset])
    assert result.success
    df = result.output_for_node("training_dataset")
    assert "split" not in df.columns
    assert "target" in df.columns
    assert not df.isna().any().any(), "dropna() должен был убрать клиентов без истории"


def test_proverka_lovit_propuski(ml):
    """net_propuskov зелёная на чистых данных и красная на пропуске в target."""
    clean = pd.DataFrame({"target": [0, 1, 1], "n_orders": [1, 2, 3]})
    ok = ml.net_propuskov(training_dataset=clean)
    assert ok.passed and ok.metadata["propuski"].value == 0

    dirty = pd.DataFrame({"target": [0, None, 1], "n_orders": [1, 2, 3]})
    bad = ml.net_propuskov(training_dataset=dirty)
    assert not bad.passed and bad.metadata["propuski"].value == 1
    # ERROR, а не WARN: упала → downstream стоит
    assert bad.severity == dg.AssetCheckSeverity.ERROR


def test_proverka_blokiruyuschaya(ml):
    """blocking=True — на слайде это подписано как «упала → downstream стоит»."""
    (spec,) = ml.net_propuskov.check_specs
    assert spec.blocking is True
