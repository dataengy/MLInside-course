"""dbt-проект и манифест — то, из чего Dagster строит граф (слайды 21–23).

«Манифест устарел — граф в Dagster врёт» с слайда 21 проверить тестом нельзя, но можно
проверить, что в манифесте лежит именно то, что обещают слайды и README.
"""

from __future__ import annotations

import yaml

from .conftest import DBT_DIR

MODELS = {"stg_customers", "stg_orders", "stg_payments", "customers", "orders", "feature_mart"}


def test_shest_modelej_i_ni_odnogo_seed(manifest):
    """Сырьё грузит Dagster, поэтому seed'ов в проекте быть не должно (см. README проекта)."""
    models = {n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "model"}
    seeds = [n["name"] for n in manifest["nodes"].values() if n["resource_type"] == "seed"]
    assert models == MODELS
    assert seeds == [], "вернулись seed'ы — сшивать загрузку с источником станет незачем"


def test_feature_mart_stoit_na_dvuh_vitrinah(manifest):
    node = next(n for n in manifest["nodes"].values() if n["name"] == "feature_mart")
    parents = {p.split(".")[-1] for p in node["depends_on"]["nodes"]}
    assert parents == {"customers", "orders"}


def test_staging_chitaet_istochniki_a_ne_seed(manifest):
    """staging переведён с ref('raw_*') на source('jaffle_raw', ...) — ради ключа ассета."""
    for name in ("stg_customers", "stg_orders", "stg_payments"):
        node = next(n for n in manifest["nodes"].values() if n["name"] == name)
        (upstream,) = node["depends_on"]["nodes"]
        # источник, а не модель и не seed — иначе у загрузки не будет, к чему прицепиться
        assert upstream.startswith("source.jaffle_shop.jaffle_raw."), upstream
        assert node["sources"] == [["jaffle_raw", name.replace("stg_", "raw_")]]


def test_testy_edut_v_manifeste(manifest):
    """26 dbt-тестов — это и есть «уровень 3 даром»: они станут asset checks."""
    tests = [n for n in manifest["nodes"].values() if n["resource_type"] == "test"]
    assert len(tests) == 26, f"тестов {len(tests)} — обновить число в README демо"


def test_marts_i_staging_razlozheny_po_papkam(manifest):
    """Выборка `fqn:marts.*` со слайдов работает только при такой раскладке."""
    fqns = {
        n["name"]: n["fqn"] for n in manifest["nodes"].values() if n["resource_type"] == "model"
    }
    assert fqns["feature_mart"][1] == "marts"
    assert fqns["stg_orders"][1] == "staging"


def test_data_sreza_zadana_peremennoj():
    """cutoff_date — var, а не литерал в SQL: на уровне 3 то же окно передают партицией."""
    project = yaml.safe_load((DBT_DIR / "dbt_project.yml").read_text())
    assert project["vars"]["cutoff_date"] == "2018-03-01"
    # телеметрию dbt выключаем: на показе сети может не быть
    assert project["flags"]["send_anonymous_usage_stats"] is False


def test_profil_beret_put_k_skladu_iz_okruzheniya():
    """Путь к DuckDB задаёт Dagster (абсолютный); значение по умолчанию — для ручного dbt."""
    profiles = yaml.safe_load((DBT_DIR / "profiles.yml").read_text())
    path = profiles["jaffle_shop"]["outputs"]["dev"]["path"]
    assert "DUCKDB_PATH" in path
