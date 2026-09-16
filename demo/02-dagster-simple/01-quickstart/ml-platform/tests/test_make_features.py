"""scripts/make_features.py — витрина признаков демо 1.

Главное, что здесь проверяется, — ОТСУТСТВИЕ УТЕЧКИ БУДУЩЕГО: признаки считаются только
по заказам до даты среза, цель — по заказам после. Задача игрушечная, но если утечка
заведётся, демо начнёт показывать roc_auc под единицу, и объяснить это будет нечем.
"""

from __future__ import annotations

FEATURES = ["n_orders", "total_amount", "avg_order_value", "days_since_last_order",
            "coupon_share", "n_returns"]


def test_kolonki_i_indeks(features):
    assert list(features.columns) == [*FEATURES, "target", "split"]
    # customer_id — индекс, а не признак: иначе номер клиента попадёт в модель
    assert features.index.name == "customer_id"
    assert features.index.is_unique


def test_target_i_split_iz_dvuh_znachenij(features):
    assert set(features["target"].unique()) <= {0, 1}
    assert set(features["split"].unique()) <= {"train", "test"}
    # каждый пятый в тест — деление без случайности, повторяемое между прогонами
    assert all((cid % 5 == 0) == (split == "test")
               for cid, split in features["split"].items())


def test_net_utechki_buduschego(make_features, in_project):
    """Признаки клиента не должны зависеть от того, что было ПОСЛЕ среза.

    Сдвигаем срез назад: у клиента с историей число заказов до среза может только
    уменьшиться или остаться прежним — но не вырасти.
    """
    late = make_features.build("2018-03-01")
    early = make_features.build("2018-02-01")
    both = late.index.intersection(early.index)
    assert len(both) > 0
    assert (early.loc[both, "n_orders"] <= late.loc[both, "n_orders"]).all()


def test_srez_menyaet_vyborku(make_features, in_project):
    """Шаг 4 демо («пришли новые данные») обязан менять обучающую выборку.

    Числа в README демо (rows 35 → 40) держатся на этом: если срез перестанет влиять,
    шаг 4 покажет ноль изменений и рассказывать будет нечего.
    """
    base = make_features.build("2018-03-01")
    later = make_features.build("2018-03-15")
    rows = {cut: int((df["split"] == "train").sum() - df[df.split == "train"].isna().any(axis=1).sum())
            for cut, df in (("base", base), ("later", later))}
    assert rows["later"] > rows["base"], rows


def test_klienty_bez_istorii_pustye(features):
    """У клиента без заказов до среза признаки NULL — их выбрасывает dropna() в ассете."""
    no_history = features[features["n_orders"] == 0]
    assert len(no_history) > 0, "в сырье должны быть клиенты без заказов до среза"
    assert no_history["avg_order_value"].isna().all()
    assert no_history["days_since_last_order"].isna().all()


def test_summy_sovpadayut_s_syrem(features, make_features):
    """total_amount — это сумма, а не средний чек: ловит подмену агрегата."""
    with_history = features[features["n_orders"] > 0]
    assert (with_history["total_amount"] >= with_history["avg_order_value"]).all()
    approx = with_history["avg_order_value"] * with_history["n_orders"]
    assert ((approx - with_history["total_amount"]).abs() < 1e-6).all()
