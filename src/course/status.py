"""Статус правил продакшена — то, что печатает SessionStart-хук ``course-production-status.sh``.

Четыре сигнала, все из локальных файлов (без сети): дни до дедлайна записи, деки лектора
без плана блоков записи, блоки длиннее лимита монтажа, открытые вопросы менеджеру
(чекбоксы ``- [ ]`` в разделе «Открытые вопросы» docs/course-qa.md).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from course import blocks as bl
from course.settings import REPO_ROOT, require

PREFIX = "[course-production]"
#: Заголовок раздела docs/course-qa.md, под которым считаются открытые вопросы.
OPEN_SECTION = "## Открытые вопросы"
_OPEN_ITEM = re.compile(r"^\s*- \[ \]\s+")


def _as_date(value: object) -> date:
    """YAML отдаёт date для ``2026-08-31`` и str для ``"2026-08-31"`` — принимаем оба.

    >>> _as_date("2026-08-31"), _as_date(date(2026, 8, 31))
    (datetime.date(2026, 8, 31), datetime.date(2026, 8, 31))
    """
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def deadline_lines(rules: dict, today: date) -> list[str]:
    by = _as_date(require(rules, "deadlines.record_all_by"))
    announce = require(rules, "deadlines.announce_module")
    left = (by - today).days
    if left < 0:
        return [
            f"⚠ дедлайн записи всех лекций ({by}) просрочен на {-left} дн. — "
            "согласовать новый срок с менеджером (docs/course-qa.md)"
        ]
    return [f"⏳ запись всех лекций — до {by}: осталось {left} дн. (анонс модуля — {announce})"]


def decks_without_plan(entries: list[dict], rules: dict) -> list[str]:
    """Деки лектора (owner ~ ``recording.plan_required_owner_match``) без ``recording.blocks``."""
    pat = re.compile(str(require(rules, "recording.plan_required_owner_match")))
    return [
        str(e.get("out_name") or e.get("topic") or "?")
        for e in entries
        if e.get("content")
        and pat.search(str(e.get("owner") or ""))
        and not (e.get("recording") or {}).get("blocks")
    ]


def open_questions(qa_md: Path) -> list[str]:
    """Тексты незакрытых чекбоксов из раздела «Открытые вопросы» (до следующего ``## ``)."""
    if not qa_md.is_file():
        return []
    items, inside = [], False
    for line in qa_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip() == OPEN_SECTION
            continue
        if inside and _OPEN_ITEM.match(line):
            items.append(_OPEN_ITEM.sub("", line).strip())
    return items


def report(
    rules: dict, entries: list[dict], today: date, root: Path = REPO_ROOT, hook: bool = False
) -> list[str]:
    lines = deadline_lines(rules, today)
    missing = decks_without_plan(entries, rules)
    if missing:
        lines.append(
            "⚠ нет плана блоков записи (recording.blocks): "
            + "; ".join(missing)
            + " — docs/course-rules.md"
        )
    for plan in bl.plans_from(entries, root):
        for err in plan.errors:
            lines.append(f"✗ {plan.out_name}: {err} — just preza-blocks {plan.content}")
        if plan.ok:
            lines += [f"⚠ {plan.out_name}: {w}" for w in bl.overlong(plan, rules)]
    qa = root / str(require(rules, "docs.qa"))
    open_items = open_questions(qa)
    if open_items:
        lines.append(f"❓ открытых вопросов менеджеру: {len(open_items)} — {qa.relative_to(root)}")
    return [f"{PREFIX} {line}" for line in lines] if hook else lines
