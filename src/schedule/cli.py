"""``python -m schedule`` — read the course schedule sheet and maintain the presentations plan."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import click
import yaml
from loguru import logger as log

from schedule import mapper, reader
from schedule import settings as cfg
from schedule.gsheet import REPO_ROOT, get_service

RAW_HEADER = """\
# ──────────────────────────────────────────────────────────────────────────────
# GENERATED — do not edit by hand. Verbatim dump of the course schedule sheet.
# Regenerate: just gsheet-dump   ·   curated view: content/presentations.yml
# ──────────────────────────────────────────────────────────────────────────────
"""

PLAN_HEADER = """\
# ──────────────────────────────────────────────────────────────────────────────
# Presentations plan — lecture (from the schedule sheet) → deck (content/*-content.yml).
#
# Sheet-sourced fields (n, date, topic, owner, status, accents, notes) are OVERWRITTEN by
# `just presentations-plan`; content/out_name/slides and anything you add by hand survive.
# Raw dump: settings/schedule.yml
#
# `accents:` is the rubric `/preza-review` scores each deck against.
# Supersedes settings/config.yml → deck_generation.decks once the reviewer is proven.
# ──────────────────────────────────────────────────────────────────────────────
"""


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _pick_tab(raw: dict, want: str | None) -> dict:
    tabs = raw.get("tabs") or []
    if not tabs:
        raise click.ClickException("The dump has no tabs — re-run `just gsheet-dump`.")
    if want:
        for t in tabs:
            if t["title"] == want:
                return t
        raise click.ClickException(
            f"Tab {want!r} not in the dump. Available: {[t['title'] for t in tabs]}"
        )
    return tabs[0]


def _deck_facts(content_rel: str | None) -> dict:
    """Slide count + out_name read straight from a deck's content YAML."""
    if not content_rel:
        return {}
    path = REPO_ROOT / content_rel
    if not path.exists():
        log.warning(f"content file missing: {content_rel}")
        return {}
    data = _load_yaml(path)
    facts: dict = {}
    slides = data.get("content")
    if isinstance(slides, list):
        facts["slides"] = len(slides)
    out_name = (data.get("deck") or {}).get("out_name")
    if out_name:
        facts["out_name"] = out_name
    return facts


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Course schedule sheet → settings/schedule.yml → content/presentations.yml."""


@main.command()
def tabs() -> None:
    """List the schedule sheet's tab names (auth smoke test)."""
    s = cfg.load()
    sid = s["spreadsheet"]["id"]
    service = get_service()
    for name in reader.list_tabs(service, sid):
        click.echo(name)


@main.command()
@click.option("--tab", "tab_names", multiple=True, help="Read only these tabs (default: all).")
def dump(tab_names: tuple[str, ...]) -> None:
    """Fetch the sheet verbatim → settings/schedule.yml."""
    s = cfg.load()
    sid = s["spreadsheet"]["id"]
    wanted = list(tab_names) or (s["read"].get("tabs") or [])

    service = get_service()
    raw = reader.fetch_raw(
        service,
        sid,
        tabs=wanted,
        max_rows=int(s["read"]["max_rows"]),
        max_cols=int(s["read"]["max_cols"]),
    )
    raw["fetched_at"] = date.today().isoformat()

    out = cfg.out_path(s, "raw")
    cfg.dump_yaml(out, raw, RAW_HEADER)
    click.echo(
        f"✔ {out.relative_to(REPO_ROOT)} — {len(raw['tabs'])} tab(s), "
        f"{sum(len(t['rows']) for t in raw['tabs'])} rows"
    )


@main.command()
@click.option("--tab", "tab_name", default=None, help="Tab holding the lecture plan.")
@click.option("--dry", is_flag=True, help="Print the merge result without writing.")
def plan(tab_name: str | None, dry: bool) -> None:
    """Upsert content/presentations.yml from settings/schedule.yml."""
    s = cfg.load()
    raw_path = cfg.out_path(s, "raw")
    if not raw_path.exists():
        raise click.ClickException(
            f"No dump at {raw_path.relative_to(REPO_ROOT)} — run `just gsheet-dump` first."
        )
    raw = _load_yaml(raw_path)

    tab = _pick_tab(raw, tab_name or s["mapping"].get("tab"))
    incoming = mapper.rows_to_presentations(tab["rows"], s["mapping"])
    if not incoming:
        raise click.ClickException(
            f"No presentations parsed from tab {tab['title']!r} — adjust mapping.columns in "
            "settings/gsheet.yml (see the dump for the real header names)."
        )

    plan_path = cfg.out_path(s, "plan")
    # Round-trip: записи плана несут комментарии, которых нет в данных. upsert правит
    # записи НА МЕСТЕ, поэтому загруженные CommentedMap доносят их до записи.
    plan_doc = cfg.load_roundtrip(plan_path) or {}
    existing = plan_doc.get("presentations") or []
    merged, changes = mapper.upsert(existing, incoming)

    # Refresh the deck-derived fields for entries already mapped to a content file.
    for entry in merged:
        facts = _deck_facts(entry.get("content"))
        for k, v in facts.items():
            if k == "out_name" and entry.get("out_name"):
                continue
            entry[k] = v

    # Обновляем ЗАГРУЖЕННЫЙ документ по ключам, а не собираем новый: комментарии в ruamel
    # живут на самих объектах, и подмена мапы выбросила бы их вместе со старой.
    source = plan_doc.get("source")
    if not hasattr(source, "keys"):
        source = {}
        plan_doc["source"] = source
    source["gsheet"] = raw.get("spreadsheet", {}).get("url", s["spreadsheet"]["url"])
    source["tab"] = tab["title"]
    source["fetched_at"] = raw.get("fetched_at")
    source["raw"] = s["outputs"]["raw"]
    plan_doc["presentations"] = merged
    doc = plan_doc

    summary = (
        f"{len(merged)} presentation(s) · +{len(changes['added'])} added "
        f"· ~{len(changes['updated'])} updated · {len(changes['stale'])} not in sheet"
    )
    if changes["stale"]:
        log.warning(f"kept but absent from the sheet: {', '.join(changes['stale'])}")

    if dry:
        click.echo(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100))
        click.echo(f"[dry] {summary}", err=True)
        return

    cfg.dump_roundtrip(plan_path, doc, PLAN_HEADER)
    click.echo(f"✔ {plan_path.relative_to(REPO_ROOT)} — {summary}")


@main.command()
def show() -> None:
    """Print the current plan as a table."""
    s = cfg.load()
    doc = _load_yaml(cfg.out_path(s, "plan"))
    items = doc.get("presentations") or []
    if not items:
        raise click.ClickException("No plan yet — run `just presentations-plan`.")
    for e in items:
        deck = e.get("content") or "—"
        slides = e.get("slides")
        click.echo(
            f"{str(e.get('n', '?')):>3}  {str(e.get('topic', ''))[:48]:<48} "
            f"{str(e.get('status', '')):<10} {len(e.get('accents') or []):>2} accents  "
            f"{deck}{f' ({slides} slides)' if slides else ''}"
        )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
