"""``python -m course`` — план блоков записи и статус правил продакшена курса."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import click

from course import blocks as bl
from course import status as st
from course.settings import MissingSetting, load_plan, load_rules


@click.group()
def main() -> None:
    """Правила продакшена курса как код (docs/course-rules.md)."""


@main.command()
@click.argument("content", nargs=-1)
@click.option(
    "--strict", is_flag=True, help="блок длиннее лимита — ошибка (exit 1), а не предупреждение"
)
@click.option(
    "--md", "fmt", flag_value="md", default="text", help="markdown-таблица для вставки в docs"
)
def blocks(content: tuple[str, ...], strict: bool, fmt: str) -> None:
    """План блоков записи для дек с recording.blocks (все или указанные CONTENT-файлы)."""
    rules = load_rules()
    want = {str(Path(c)) for c in content}
    plans = [p for p in bl.plans_from(load_plan()) if not want or p.content in want]
    if not plans:
        scope = ", ".join(sorted(want)) if want else "ни у одной деки"
        raise click.ClickException(
            f"в content/presentations.yml нет recording.blocks для: {scope} — см. docs/course-rules.md"
        )
    rc = 0
    for plan in plans:
        click.echo(bl.render(plan, rules, fmt))
        click.echo()
        if plan.errors or (strict and bl.overlong(plan, rules)):
            rc = 1
    sys.exit(rc)


@main.command()
@click.option("--hook", is_flag=True, help="режим SessionStart-хука: префикс, всегда exit 0")
@click.option(
    "--today",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="дата «сегодня» для дедлайнов (по умолчанию — системная)",
)
def status(hook: bool, today: datetime | None) -> None:
    """Дедлайн записи, деки без плана блоков, длинные блоки, открытые вопросы менеджеру."""
    try:
        rules = load_rules()
    except MissingSetting as exc:
        click.echo(f"{st.PREFIX} ⚠ {exc}")
        sys.exit(0 if hook else 1)
    day = today.date() if today else date.today()
    for line in st.report(rules, load_plan(), day, hook=hook):
        click.echo(line)
