"""Tests for the schedule reader — mapping, upsert semantics, and the review rubric.

No network: the sheet payload is fixtured as the raw rows the API would return.
"""

import sys
from pathlib import Path

import pytest
import yaml

from schedule import mapper
from schedule import settings as cfg

REVIEW_SCRIPTS = Path(
    "~/.ai/skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts"
).expanduser()

# Header + rows shaped like the course schedule sheet (ragged tail included on purpose).
SHEET_ROWS = [
    ["Расписание курса MLInside 2026"],
    ["№", "Дата", "Тема", "Лектор", "Статус", "Акценты"],
    ["9", "2026-02-10", "Введение в dbt", "Nikolai Krupii", "draft",
     "модели и материализации; тесты и документация\nисточники и seeds"],
    ["10", "2026-02-17", "Оркестрация: Dagster", "Nikolai Krupii", "planned", "assets; сенсоры"],
    ["", "", "", "", "", ""],
    ["11", "2026-02-24", "Прочее"],
]

MAPPING = cfg.DEFAULT_MAPPING | {"header_row": 2}


def test_rows_to_presentations_parses_and_skips_blanks():
    recs = mapper.rows_to_presentations(SHEET_ROWS, MAPPING)
    assert [r["n"] for r in recs] == [9, 10, 11]
    assert recs[0]["topic"] == "Введение в dbt"
    assert recs[0]["owner"] == "Nikolai Krupii"
    assert recs[0]["accents"] == [
        "модели и материализации",
        "тесты и документация",
        "источники и seeds",
    ]
    # a short, ragged row still parses; absent columns are simply omitted
    assert "owner" not in recs[2] and recs[2]["topic"] == "Прочее"


def test_header_row_autodetected_when_unset():
    recs = mapper.rows_to_presentations(SHEET_ROWS, cfg.DEFAULT_MAPPING | {"header_row": None})
    assert [r["n"] for r in recs] == [9, 10, 11]


def test_missing_topic_column_yields_nothing():
    rows = [["Итого", "42"], ["", ""]]
    assert mapper.rows_to_presentations(rows, MAPPING) == []


def test_upsert_preserves_curated_fields_and_overwrites_sheet_fields():
    existing = [
        {
            "n": 9,
            "topic": "старое название",
            "status": "planned",
            "content": "content/preza-dbt-v3-content.yml",
            "out_name": "MLInside_Введение-в-dbt",
            "slides": 48,
            "notes_for_me": "не трогать",
        }
    ]
    incoming = mapper.rows_to_presentations(SHEET_ROWS, MAPPING)
    merged, changes = mapper.upsert(existing, incoming)

    dbt = next(e for e in merged if e["n"] == 9)
    assert dbt["topic"] == "Введение в dbt"      # sheet wins
    assert dbt["status"] == "draft"               # sheet wins
    assert dbt["content"] == "content/preza-dbt-v3-content.yml"   # curated survives
    assert dbt["notes_for_me"] == "не трогать"                    # unknown key survives
    assert changes["updated"] == ["n:9"]
    assert set(changes["added"]) == {"n:10", "n:11"}
    assert changes["stale"] == []


def test_upsert_matches_hand_seeded_entry_by_topic():
    seeded = [{"topic": "Оркестрация: Dagster", "content": "content/preza-dagster-content.yml"}]
    merged, changes = mapper.upsert(seeded, mapper.rows_to_presentations(SHEET_ROWS, MAPPING))
    dagster = [e for e in merged if e.get("content") == "content/preza-dagster-content.yml"]
    assert len(dagster) == 1, "hand-seeded entry must be adopted, not duplicated"
    assert dagster[0]["n"] == 10


def test_upsert_keeps_entries_that_left_the_sheet():
    existing = [{"n": 99, "topic": "Отменённая лекция", "content": "content/x.yml"}]
    merged, changes = mapper.upsert(existing, mapper.rows_to_presentations(SHEET_ROWS, MAPPING))
    assert changes["stale"] == ["n:99"]
    assert any(e.get("n") == 99 for e in merged), "stale entries are reported, never deleted"


def test_spreadsheet_id_rejects_a_non_sheets_url():
    with pytest.raises(ValueError):
        cfg.spreadsheet_id_from_url("https://example.com/not/a/sheet")


# ── reviewer ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def review():
    sys.path.insert(0, str(REVIEW_SCRIPTS))
    pytest.importorskip("click")
    if not (REVIEW_SCRIPTS / "review_content.py").exists():
        pytest.skip("preza-review skill scripts not installed")
    import review_content

    return review_content


@pytest.fixture(scope="module")
def review_cfg(review):
    return yaml.safe_load(review.REVIEW_SETTINGS.read_text(encoding="utf-8"))


def _deck(*slides):
    return {"deck": {"out_name": "TestDeck"}, "content": list(slides)}


def test_accent_hit_partial_missing(review, review_cfg):
    slides = [
        {"kind": "title", "title": "dbt", "notes": "—"},
        {"kind": "content", "title": "Модели и материализации", "bullets": ["table", "view"],
         "notes": "инкрементальные модели"},
        {"kind": "content", "title": "Тесты", "notes": "unique, not_null"},
    ]
    texts = [review.slide_text(s, review_cfg["matching"]["search_fields"]) for s in slides]

    hit = review.score_accent("модели и материализации", texts, review_cfg)
    assert hit["status"] == "hit" and 2 in hit["slides"]

    missing = review.score_accent("оркестрация внешними сенсорами Dagster", texts, review_cfg)
    assert missing["status"] == "missing" and missing["slides"] == []

    partial = review.score_accent("тесты и документация", texts, review_cfg)
    assert partial["status"] in {"partial", "missing"}


def test_missing_accent_is_an_error_finding(review, review_cfg):
    doc = _deck(
        {"kind": "title", "title": "dbt", "notes": "n"},
        {"kind": "content", "title": "Модели", "notes": "n"},
    )
    lecture = {"n": 9, "topic": "dbt", "accents": ["модели", "полностью отсутствующая тема"]}
    findings, data = review.build_findings(doc, lecture, review_cfg, None)

    missing = [f for f in findings if f["kind"] == "accent_missing"]
    assert len(missing) == 1
    assert missing[0]["severity"] == "error"
    assert "полностью отсутствующая тема" in missing[0]["accent"]
    assert data["stats"]["accents_missing"] == 1


def test_no_lecture_means_no_accent_findings(review, review_cfg):
    doc = _deck({"kind": "title", "title": "x", "notes": "n"})
    findings, data = review.build_findings(doc, None, review_cfg, None)
    assert data["stats"]["accents_total"] == 0
    assert not [f for f in findings if f["kind"].startswith("accent_")]
