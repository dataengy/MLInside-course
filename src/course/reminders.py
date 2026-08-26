"""Напоминания курса → задачи трекера: чистая логика плана (без сети).

Данные ленты — ``settings/reminders.yml`` (что напоминать, срок, приоритет, лейблы, текст);
мутирующий вход — ``scripts/todoist/upsert_reminders.py`` (``just course-reminders[-apply]``).
Здесь только то, что можно проверить тестами: разбор настроек и вычисление diff-а
«хотим → что уже есть в трекере».

Идемпотентность держится на **ключе напоминания** — строке ``key: <key>`` в описании задачи
(.ai/AI-glossary.ru.md#ключ-напоминания). Матчинг по ключу, а не по тексту: задачу можно
переименовать или передвинуть руками, повторный прогон всё равно найдёт её и синхронизирует
поля вместо создания дубля. Поле ``adopt: <task_id>`` принимает задачу, созданную до ленты.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from course.settings import REPO_ROOT, read_yaml, require

REMINDERS_YML = REPO_ROOT / "settings" / "reminders.yml"
KEY_LINE = "key: "
_KEY_RE = re.compile(rf"^\s*{KEY_LINE}(\S+)\s*$", re.M)
#: Поля, которые лента синхронизирует; остальное в задаче принадлежит человеку.
SYNCED = ("content", "due", "priority", "labels", "description")


@dataclass(frozen=True)
class Reminder:
    key: str
    project_id: str
    content: str
    due: str
    priority: int
    labels: tuple[str, ...]
    description: str
    adopt: str | None = None

    @property
    def full_description(self) -> str:
        body = self.description.rstrip("\n")
        return f"{body}\n\n{KEY_LINE}{self.key}" if body else f"{KEY_LINE}{self.key}"


@dataclass
class Change:
    kind: str  # create | update | ok
    key: str
    task_id: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)


def key_of(task: dict) -> str | None:
    """Ключ напоминания из описания задачи.

    >>> key_of({"description": "текст\\n\\nkey: mlinside-record-dbt"})
    'mlinside-record-dbt'
    >>> key_of({"description": "без ключа"}) is None
    True
    """
    m = _KEY_RE.search(task.get("description") or "")
    return m.group(1) if m else None


def load(path: Path = REMINDERS_YML) -> list[Reminder]:
    """``settings/reminders.yml`` → список напоминаний (fail-loud по каждому полю).

    ``{issues}`` в описании разворачивается в базовый URL issues репозитория.
    """
    cfg = read_yaml(path)
    projects = require(cfg, "projects")
    issues = require(cfg, "issue_url")
    out = []
    for i, r in enumerate(require(cfg, "reminders"), start=1):
        missing = [k for k in ("key", "project", "content", "due", "priority") if k not in r]
        if missing:
            raise KeyError(f"{path} → reminders[{i}]: нет ключей {', '.join(missing)}")
        if r["project"] not in projects:
            raise KeyError(f"{path} → reminders[{i}]: проект {r['project']!r} не задан в projects")
        out.append(
            Reminder(
                key=str(r["key"]),
                project_id=str(projects[r["project"]]),
                content=str(r["content"]),
                due=str(r["due"]),
                priority=int(r["priority"]),
                labels=tuple(r.get("labels") or []),
                description=str(r.get("description") or "").format(issues=issues),
                adopt=str(r["adopt"]) if r.get("adopt") else None,
            )
        )
    keys = [r.key for r in out]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"{path}: ключи повторяются: {', '.join(sorted(dupes))}")
    return out


def plan(want: list[Reminder], existing: list[dict]) -> list[Change]:
    """Diff «хотим → есть». Матч по ключу в описании, затем по ``adopt``-id.

    Лейблы только добавляются (руками навешенное не снимаем); остальные поля выравниваются.

    >>> r = Reminder("k", "p", "Задача", "2026-08-30", 4, ("a",), "тело")
    >>> plan([r], [])[0].kind
    'create'
    >>> have = [{"id": "1", "content": "Задача", "due": {"date": "2026-08-30"},
    ...          "priority": 4, "labels": ["a"], "description": "тело\\n\\nkey: k"}]
    >>> plan([r], have)[0].kind
    'ok'
    """
    by_key = {k: t for t in existing if (k := key_of(t))}
    by_id = {str(t.get("id")): t for t in existing}
    out = []
    for r in want:
        task = by_key.get(r.key) or (by_id.get(r.adopt) if r.adopt else None)
        if task is None:
            out.append(
                Change(
                    "create",
                    r.key,
                    fields={
                        "content": r.content,
                        "project_id": r.project_id,
                        "due_date": r.due,
                        "priority": r.priority,
                        "labels": list(r.labels),
                        "description": r.full_description,
                    },
                )
            )
            continue
        patch: dict[str, Any] = {}
        if task.get("content") != r.content:
            patch["content"] = r.content
        if ((task.get("due") or {}).get("date") or "")[:10] != r.due:
            patch["due_date"] = r.due
        if int(task.get("priority") or 1) != r.priority:
            patch["priority"] = r.priority
        if set(r.labels) - set(task.get("labels") or []):
            patch["labels"] = sorted(set(task.get("labels") or []) | set(r.labels))
        if (task.get("description") or "") != r.full_description:
            patch["description"] = r.full_description
        out.append(Change("update" if patch else "ok", r.key, str(task.get("id")), patch))
    return out


def render(changes: list[Change], apply: bool = False) -> str:
    """Человекочитаемый план/отчёт."""
    mark = {"create": "+ CREATE", "update": "~ UPDATE", "ok": "= OK    "}
    head = "APPLY" if apply else "DRY-RUN (без записи; --apply чтобы применить)"
    lines = [
        f"{head}: {sum(c.kind == 'create' for c in changes)} создать, "
        f"{sum(c.kind == 'update' for c in changes)} обновить, "
        f"{sum(c.kind == 'ok' for c in changes)} без изменений"
    ]
    for c in changes:
        detail = (
            ", ".join(sorted(c.fields))
            if c.kind == "update"
            else (c.fields.get("content", "")[:60] if c.kind == "create" else "")
        )
        lines.append(f"  {mark[c.kind]} {c.key}" + (f" · {detail}" if detail else ""))
    return "\n".join(lines)
