"""plan_writer: only the target entry's published: changes; hand keys + header survive."""

import pytest
import yaml

from publisher import plan_writer
from schedule.cli import PLAN_HEADER

PLAN = {
    "source": {"gsheet": "https://sheet", "tab": "S"},
    "presentations": [
        {
            "topic": "Трансформация данных и витрины (dbt)",
            "out_name": "MLInside_Введение-в-dbt",
            "content": "content/preza-dbt-v3-content.yml",
            "generated": False,
            "homework": {"repo": "https://github.com/hnkovr/mlinside-hw-olist"},
        },
        {"topic": "Dagster", "out_name": "MLInside_Dagster", "content": "content/d.yml"},
    ],
}


@pytest.fixture()
def plan_path(tmp_path):
    p = tmp_path / "presentations.yml"
    p.write_text(PLAN_HEADER + yaml.safe_dump(PLAN, allow_unicode=True, sort_keys=False), "utf-8")
    return p


def test_update_touches_only_target_entry(plan_path):
    block = {"version": "3.14", "slides": 52, "url": "https://v", "at": "t", "legs": {"tg": "ok"}}
    plan_writer.update_published_block(plan_path, "MLInside_Введение-в-dbt", block)

    text = plan_path.read_text("utf-8")
    assert text.startswith(PLAN_HEADER)
    doc = yaml.safe_load(text)
    dbt, dagster = doc["presentations"]
    assert dbt["published"] == block
    assert dbt["homework"]["repo"].endswith("mlinside-hw-olist")  # hand key survives
    assert dbt["generated"] is False
    assert "published" not in dagster
    assert doc["source"]["tab"] == "S"
    assert not plan_path.with_suffix(plan_path.suffix + ".tmp").exists()


def test_second_write_replaces_block(plan_path):
    plan_writer.update_published_block(plan_path, "MLInside_Dagster", {"version": "1.2"})
    plan_writer.update_published_block(plan_path, "MLInside_Dagster", {"version": "1.3"})
    doc = yaml.safe_load(plan_path.read_text("utf-8"))
    assert doc["presentations"][1]["published"] == {"version": "1.3"}


def test_unknown_out_name_raises(plan_path):
    with pytest.raises(ValueError, match="no plan entry"):
        plan_writer.update_published_block(plan_path, "MLInside_Nope", {})
