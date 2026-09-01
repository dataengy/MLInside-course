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


# ── комментарии ──────────────────────────────────────────────────────────────
#
# Регрессия 2026-09-01: один прогон publisher снёс из content/presentations.yml
# 19 строк комментариев. Файл остался валидным, диff выглядел переформатированием,
# а вместе с комментариями пропали пояснения, которых нет в данных. Причина —
# yaml.safe_load + safe_dump: pyyaml комментарии не хранит в принципе.

PLAN_WITH_COMMENTS = """\
source:
  gsheet: https://sheet
  tab: S
presentations:
- topic: Трансформация данных и витрины (dbt)
  out_name: MLInside_Введение-в-dbt
  # содержание живёт отдельно от плана
  content: content/preza-dbt-v3-content.yml
  recording:
    # блоки режет монтаж — не длиннее 25 минут
    blocks:
    - title: Первый блок
      from: 001-a
      to: 010-b
"""


@pytest.fixture()
def commented_plan(tmp_path):
    p = tmp_path / "presentations.yml"
    p.write_text(PLAN_HEADER + PLAN_WITH_COMMENTS, "utf-8")
    return p


def _comment_lines(text: str) -> list[str]:
    body = text[len(PLAN_HEADER) :]
    return [ln.strip() for ln in body.splitlines() if ln.strip().startswith("#")]


def test_comments_survive_update(commented_plan):
    before = _comment_lines(commented_plan.read_text("utf-8"))
    assert len(before) == 2, "фикстура должна нести комментарии, иначе тест ничего не проверяет"

    plan_writer.update_published_block(
        commented_plan, "MLInside_Введение-в-dbt", {"version": "4.9", "slides": 131}
    )

    text = commented_plan.read_text("utf-8")
    assert _comment_lines(text) == before, "комментарии не пережили запись"
    assert text.count(PLAN_HEADER.splitlines()[1]) == 1, "шапка удвоилась"
    doc = yaml.safe_load(text)
    assert doc["presentations"][0]["published"] == {"version": "4.9", "slides": 131}
    assert doc["presentations"][0]["recording"]["blocks"][0]["title"] == "Первый блок"


def test_repeated_writes_are_byte_stable(commented_plan):
    """Второй прогон подряд обязан дать тот же файл — иначе каждый запуск шумит диффом."""
    block = {"version": "4.9", "slides": 131}
    plan_writer.update_published_block(commented_plan, "MLInside_Введение-в-dbt", block)
    first = commented_plan.read_text("utf-8")
    plan_writer.update_published_block(commented_plan, "MLInside_Введение-в-dbt", block)
    assert commented_plan.read_text("utf-8") == first
