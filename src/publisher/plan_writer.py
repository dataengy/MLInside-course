"""publisher.plan_writer — the git-tracked ``published:`` block in content/presentations.yml.

The per-machine JSON cursor is gitignored, so this block is the cross-machine record of what
was published (the runner seeds a fresh clone's cursor from it). Only the matching entry's
``published:`` key is touched; everything else round-trips through the same yaml dump the
schedule lane uses (``mapper.upsert`` preserves unknown keys, so the block also survives
``just presentations-plan``). Write is atomic — this file now has two writers.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from schedule.cli import PLAN_HEADER


def update_published_block(plan_path: Path, out_name: str, block: dict) -> None:
    """Set ``published: block`` on the entry whose ``out_name`` matches. Raises if absent."""
    doc = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    entries = doc.get("presentations") or []
    entry = next((e for e in entries if e.get("out_name") == out_name), None)
    if entry is None:
        raise ValueError(f"no plan entry with out_name={out_name!r} in {plan_path}")
    entry["published"] = block

    body = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100)
    tmp = plan_path.with_suffix(plan_path.suffix + ".tmp")
    tmp.write_text(f"{PLAN_HEADER}{body}", encoding="utf-8")
    os.replace(tmp, plan_path)
