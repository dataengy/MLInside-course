"""СШИВКА КЛЮЧЕЙ — главный момент демо 2 (слайд 25) и самое хрупкое место проекта.

Сшивка держится на том, что одна и та же строка написана в ДВУХ файлах:
    defs/raw.py            @dg.asset(key=dg.AssetKey(["raw_orders"]))
    _sources.yml           meta.dagster.asset_key: ["raw_orders"]
Переименуют ассет — граф не упадёт и dbt не пожалуется: источник просто молча повиснет
отдельным узлом, и демо покажет ровно то, что должно было опровергнуть. Отсюда тесты.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from .conftest import DBT_DIR, ROOT, STASH, load_by_path

LIVE = DBT_DIR / "models" / "staging" / "_sources.yml"
PLAIN = STASH / "_sources.plain.yml"
STITCHED = STASH / "_sources.stitched.yml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _strip_meta(doc: dict) -> dict:
    doc = copy.deepcopy(doc)
    for source in doc["sources"]:
        for table in source["tables"]:
            table.pop("meta", None)
    return doc


def test_sshivka_menyaet_TOLKO_meta():
    """`just stitch` — это не переписывание источников, а ровно добавление meta.

    Если в сшитой версии поедет schema, имя источника или список таблиц, dbt соберёт
    другой проект, и «одно отличие — появилось ребро» станет неправдой.
    """
    assert _strip_meta(_load(STITCHED)) == _strip_meta(_load(PLAIN))


def test_do_sshivki_meta_net():
    for source in _load(PLAIN)["sources"]:
        for table in source["tables"]:
            assert "meta" not in table, f"{table['name']}: в канон просочилась meta"


def test_klyuchi_sshivki_sovpadayut_s_assetami_zagruzki():
    """Тот самый тест, ради которого написан файл: ключи в ДВУХ местах должны совпасть."""
    raw = load_by_path("demo2_raw_keys", ROOT / "src" / "ml_platform" / "defs" / "raw.py")
    from_yaml = {
        tuple(table["meta"]["dagster"]["asset_key"])
        for source in _load(STITCHED)["sources"]
        for table in source["tables"]
    }
    from_python = {(name,) for name in raw.TABLES}
    assert from_yaml == from_python, (
        "ключи разошлись: источник повиснет в графе без родителя, а демо этого не покажет"
    )


def test_zhivoj_fajl_v_odnom_iz_dvuh_sostoyanij():
    """По ходу демо _sources.yml равен канону или сшитой версии — третьего не бывает.

    Файл под гитом: `just stitch` его правит, `just reset` возвращает канон. Если он
    оказался в каком-то третьем виде — кто-то правил его руками, и `reset` это затрёт.
    """
    live = _load(LIVE)
    assert live in (_load(PLAIN), _load(STITCHED)), (
        "_sources.yml не совпал ни с stash/_sources.plain.yml, ни с stash/_sources.stitched.yml"
    )


def test_istochnik_smotrit_v_shemu_raw():
    """schema: raw — то, куда пишут ассеты загрузки. Имя таблицы ≠ ключ ассета."""
    (source,) = _load(PLAIN)["sources"]
    assert source["name"] == "jaffle_raw"
    assert source["schema"] == "raw"
    assert {t["name"] for t in source["tables"]} == {
        "raw_customers", "raw_orders", "raw_payments"
    }
