"""course.blocks / course.status — план блоков записи и статус правил продакшена.

Без сети: правила и планы — фикстуры; плюс пины на живой план репозитория (dbt, Dagster).
"""

from datetime import date
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from course import blocks as bl
from course import cli
from course import settings as cs
from course import status as st

RULES = {
    "deadlines": {"record_all_by": date(2026, 8, 31), "announce_module": "2026-09"},
    "lecture": {"duration_min": [50, 90], "block_max_min": 25, "min_per_slide": 1.3},
    "recording": {"plan_required_owner_match": "Николай"},
    "docs": {"qa": "docs/course-qa.md"},
}
IDS = [f"s{i:02d}" for i in range(1, 11)]  # 10 слайдов


def entry(blocks, **extra):
    return {
        "out_name": "Deck",
        "content": "content/deck.yml",
        "owner": "Николай Крупий",
        "recording": {"blocks": blocks},
        **extra,
    }


def blk(title, a, b):
    return {"title": title, "from": a, "to": b}


# ── blocks: структура ────────────────────────────────────────────────────────


def test_contiguous_plan_is_ok():
    plan = bl.build(entry([blk("A", "s01", "s04"), blk("B", "s05", "s10")]), IDS)
    assert plan.ok
    assert [(b.start, b.end, b.count) for b in plan.blocks] == [(1, 4, 4), (5, 10, 6)]
    assert plan.total_slides == 10


def test_gap_is_an_error():
    plan = bl.build(entry([blk("A", "s01", "s04"), blk("B", "s06", "s10")]), IDS)
    assert not plan.ok
    assert any("пропуск" in e and "№5" in e for e in plan.errors)


def test_overlap_is_an_error():
    plan = bl.build(entry([blk("A", "s01", "s05"), blk("B", "s04", "s10")]), IDS)
    assert any("наложение" in e for e in plan.errors)


def test_unknown_id_and_reversed_range():
    plan = bl.build(entry([blk("A", "s01", "zz"), blk("B", "s05", "s02")]), IDS)
    assert any("нет слайда с id zz" in e for e in plan.errors)
    assert any("позже to" in e for e in plan.errors)


def test_tail_not_covered():
    plan = bl.build(entry([blk("A", "s01", "s08")]), IDS)
    assert plan.errors == [
        "последний блок «A» кончается на слайде 8, а в деке 10 — хвост не покрыт"
    ]


def test_empty_plan_and_broken_deck():
    assert "recording.blocks пуст" in bl.build(entry([]), IDS).errors[0]
    assert "не уникальны" in bl.build(entry([blk("A", "s01", "s01")]), ["s01", "s01"]).errors[0]
    assert "нет id" in bl.build(entry([blk("A", "s01", "s01")]), ["s01", ""]).errors[0]


# ── blocks: длительность и рендер ────────────────────────────────────────────


def test_overlong_is_a_warning_not_an_error():
    plan = bl.build(entry([blk("Long", "s01", "s10")]), IDS)  # 10 × 1.3 = 13 < 25
    assert plan.ok and bl.overlong(plan, RULES) == []
    tight = {**RULES, "lecture": {**RULES["lecture"], "block_max_min": 10}}
    warns = bl.overlong(plan, tight)
    assert warns == ["блок 1 «Long»: 10 сл. ≈ 13 мин > 10"]
    assert plan.ok  # предупреждение не делает план невалидным


def test_render_text_and_md():
    plan = bl.build(entry([blk("A", "s01", "s04"), blk("B", "s05", "s10")]), IDS)
    text = bl.render(plan, RULES)
    assert "Deck — 10 слайдов ≈ 13 мин" in text
    assert "1–4" in text and "5–10" in text
    md = bl.render(plan, RULES, "md")
    assert "| 1 | A | 1–4 | 4 | 5.2 |" in md
    assert "| 2 | B | 5–10 | 6 | 7.8 |" in md


def test_require_is_loud_about_missing_keys():
    with pytest.raises(cs.MissingSetting, match="lecture.block_max_min"):
        bl.overlong(bl.build(entry([blk("A", "s01", "s10")]), IDS), {"lecture": {}})


# ── status ──────────────────────────────────────────────────────────────────


def test_deadline_countdown_and_overdue():
    (line,) = st.deadline_lines(RULES, date(2026, 8, 26))
    assert "осталось 5 дн." in line and "2026-09" in line
    (line,) = st.deadline_lines(RULES, date(2026, 9, 3))
    assert "просрочен на 3 дн." in line


def test_decks_without_plan_only_for_matching_owner():
    entries = [
        entry([blk("A", "s01", "s10")]),
        {"out_name": "NoPlan", "content": "c.yml", "owner": "Николай Крупий/Влад"},
        {"out_name": "Vlad", "content": "v.yml", "owner": "Влад Бояджи"},
        {"out_name": "NoDeck", "owner": "Николай Крупий"},
    ]
    assert st.decks_without_plan(entries, RULES) == ["NoPlan"]


def test_open_questions_counts_only_the_open_section(tmp_path: Path):
    qa = tmp_path / "qa.md"
    qa.write_text(
        "# Q&A\n\n## Отвеченные\n\n- [ ] not counted\n\n## Открытые вопросы\n\n"
        "- [ ] **Баллы ДЗ** — нужны ли?\n- [x] закрыт\n- [ ] тест-запись\n\n## История\n\n- [ ] no\n",
        encoding="utf-8",
    )
    assert st.open_questions(qa) == ["**Баллы ДЗ** — нужны ли?", "тест-запись"]
    assert st.open_questions(tmp_path / "missing.md") == []


def test_report_hook_prefix(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "course-qa.md").write_text(
        "## Открытые вопросы\n- [ ] q\n", encoding="utf-8"
    )
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "deck.yml").write_text(
        yaml.safe_dump({"content": [{"id": i} for i in IDS]}), encoding="utf-8"
    )
    entries = [
        entry([blk("A", "s01", "s10")]),
        {"out_name": "NoPlan", "content": "content/deck.yml", "owner": "Николай"},
    ]
    lines = st.report(RULES, entries, date(2026, 8, 26), root=tmp_path, hook=True)
    assert all(line.startswith(st.PREFIX) for line in lines)
    assert any("осталось 5 дн." in line for line in lines)
    assert any("recording.blocks): NoPlan" in line for line in lines)
    assert any("открытых вопросов менеджеру: 1" in line for line in lines)


# ── живой репозиторий ────────────────────────────────────────────────────────


def test_repo_rules_carry_every_key_the_tools_read():
    rules = cs.load_rules()
    for key in (
        "deadlines.record_all_by",
        "deadlines.announce_module",
        "lecture.duration_min",
        "lecture.block_max_min",
        "lecture.min_per_slide",
        "recording.plan_required_owner_match",
        "docs.qa",
        "docs.rules",
    ):
        cs.require(rules, key)
    assert (cs.REPO_ROOT / cs.require(rules, "docs.qa")).is_file()
    assert (cs.REPO_ROOT / cs.require(rules, "docs.rules")).is_file()


def test_repo_recording_plans_are_consistent():
    plans = bl.plans_from(cs.load_plan())
    names = {p.out_name for p in plans}
    assert {
        "MLInside_Введение-в-dbt",
        "MLInside_Современная-оркестрация-ML-пайплайнов-Dagster",
    } <= names
    for plan in plans:
        assert plan.ok, (plan.out_name, plan.errors)
        assert plan.blocks[0].start == 1 and plan.blocks[-1].end == plan.total_slides


def test_cli_blocks_and_status_run_green():
    runner = CliRunner()
    res = runner.invoke(cli.main, ["blocks"])
    assert res.exit_code == 0, res.output
    assert "MLInside_Введение-в-dbt" in res.output
    res = runner.invoke(cli.main, ["status", "--hook", "--today", "2026-08-26"])
    assert res.exit_code == 0, res.output
    assert res.output.startswith(st.PREFIX)
    res = runner.invoke(cli.main, ["blocks", "content/no-such-deck.yml"])
    assert res.exit_code != 0 and "нет recording.blocks" in res.output
