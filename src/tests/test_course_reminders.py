"""course.reminders — разбор settings/reminders.yml и план upsert-а (без сети)."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from course import reminders as rem
from course import settings as cs

SPEC: dict[str, Any] = {
    "projects": {"mlinside": "P1", "sys": "P2"},
    "issue_url": "https://example/issues/",
    "reminders": [
        {
            "key": "a",
            "project": "mlinside",
            "content": "Задача A",
            "due": "2026-08-30",
            "priority": 4,
            "labels": ["x"],
            "description": "тело {issues}10",
        },
        {"key": "b", "project": "sys", "content": "Задача B", "due": "2026-09-02", "priority": 1},
    ],
}


def write(tmp_path: Path, spec: dict) -> Path:
    p = tmp_path / "reminders.yml"
    p.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    return p


def task(**kw):
    base = {
        "id": "1",
        "content": "Задача A",
        "due": {"date": "2026-08-30"},
        "priority": 4,
        "labels": ["x"],
        "description": "тело https://example/issues/10\n\nkey: a",
    }
    base.update(kw)
    return base


# ── разбор настроек ──────────────────────────────────────────────────────────


def test_load_resolves_projects_and_issue_url(tmp_path: Path):
    a, b = rem.load(write(tmp_path, SPEC))
    assert (a.key, a.project_id, a.priority, a.labels) == ("a", "P1", 4, ("x",))
    assert a.description == "тело https://example/issues/10"
    assert a.full_description.endswith("\n\nkey: a")
    assert (b.project_id, b.labels, b.description) == ("P2", (), "")


def test_load_is_loud_about_bad_spec(tmp_path: Path):
    bad = {
        **SPEC,
        "reminders": [
            {"key": "a", "project": "nope", "content": "c", "due": "2026-08-30", "priority": 1}
        ],
    }
    with pytest.raises(KeyError, match="не задан в projects"):
        rem.load(write(tmp_path, bad))
    missing = {**SPEC, "reminders": [{"key": "a", "project": "mlinside"}]}
    with pytest.raises(KeyError, match="нет ключей"):
        rem.load(write(tmp_path, missing))
    dupes = {**SPEC, "reminders": SPEC["reminders"] + [dict(SPEC["reminders"][0])]}
    with pytest.raises(ValueError, match="ключи повторяются"):
        rem.load(write(tmp_path, dupes))
    with pytest.raises(cs.MissingSetting):
        rem.load(write(tmp_path, {"projects": {}, "issue_url": "u"}))


# ── план ─────────────────────────────────────────────────────────────────────


def test_plan_creates_when_absent(tmp_path: Path):
    want = rem.load(write(tmp_path, SPEC))
    changes = rem.plan(want, [])
    assert [c.kind for c in changes] == ["create", "create"]
    assert changes[0].fields["project_id"] == "P1"
    assert changes[0].fields["description"].endswith("key: a")


def test_plan_is_idempotent_when_in_sync(tmp_path: Path):
    want = rem.load(write(tmp_path, SPEC))
    changes = rem.plan(want[:1], [task()])
    assert [c.kind for c in changes] == ["ok"] and changes[0].fields == {}


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        ({"content": "старое имя"}, "content"),
        ({"due": {"date": "2026-08-29"}}, "due_date"),
        ({"priority": 1}, "priority"),
        ({"labels": []}, "labels"),
        ({"description": "key: a"}, "description"),
    ],
)
def test_plan_syncs_each_drifted_field(tmp_path: Path, patch: dict, expected: str):
    want = rem.load(write(tmp_path, SPEC))[:1]
    (change,) = rem.plan(want, [task(**patch)])
    assert change.kind == "update" and expected in change.fields
    assert change.task_id == "1"


def test_plan_only_adds_labels(tmp_path: Path):
    want = rem.load(write(tmp_path, SPEC))[:1]
    (change,) = rem.plan(want, [task(labels=["x", "вручную"])])
    assert change.kind == "ok"  # свои лейблы не снимаем
    (change,) = rem.plan(want, [task(labels=["вручную"])])
    assert change.fields["labels"] == ["x", "вручную"]


def test_plan_matches_by_key_not_by_text(tmp_path: Path):
    want = rem.load(write(tmp_path, SPEC))[:1]
    renamed = task(content="переименована человеком")
    (change,) = rem.plan(want, [renamed])
    assert change.kind == "update" and change.task_id == "1"  # найдена по ключу


def test_plan_adopts_pre_existing_task_by_id(tmp_path: Path):
    spec = {**SPEC, "reminders": [{**SPEC["reminders"][0], "adopt": "77"}]}
    want = rem.load(write(tmp_path, spec))
    legacy = task(id="77", description="создана до ленты")
    (change,) = rem.plan(want, [legacy])
    assert change.kind == "update" and change.task_id == "77"
    assert change.fields["description"].endswith("key: a")


def test_key_of_and_render(tmp_path: Path):
    assert rem.key_of(task()) == "a"
    assert rem.key_of({"description": "нет ключа"}) is None
    assert rem.key_of({}) is None
    want = rem.load(write(tmp_path, SPEC))
    text = rem.render(rem.plan(want, []), apply=False)
    assert "DRY-RUN" in text and "2 создать" in text and "+ CREATE a" in text


# ── живые настройки репозитория ──────────────────────────────────────────────


def test_repo_reminders_yml_parses_and_covers_open_issues():
    want = rem.load()
    keys = {r.key for r in want}
    assert {"mlinside-test-clip", "mlinside-record-dbt", "mlinside-record-dagster"} <= keys
    for r in want:
        assert r.due >= "2026-08-26", (r.key, r.due)
        assert 1 <= r.priority <= 4
        assert r.full_description.strip().endswith(f"key: {r.key}")
