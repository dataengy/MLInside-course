"""publisher.plan_writer — the git-tracked ``published:`` block in content/presentations.yml.

The per-machine JSON cursor is gitignored, so this block is the cross-machine record of what
was published (the runner seeds a fresh clone's cursor from it). Only the matching entry's
``published:`` key is touched; everything else round-trips untouched, so the block also
survives ``just presentations-plan``. Write is atomic — this file has two writers.

КОММЕНТАРИИ. Файл читают и комментируют руками, и в комментариях лежит то, чего нет в
данных: почему блоки записи нарезаны именно так, что за блок ``demos``, зачем приложение
разбито на три части. Поэтому здесь round-trip (ruamel), а не ``safe_load`` + ``safe_dump``:
последняя пара молча сносит все комментарии, оставляя валидный YAML и диff, который
выглядит как безобидное переформатирование. Так и случилось 2026-09-01 — один прогон
стёр 19 строк пояснений.

Отсюда же требование к коду ниже: ``published`` ОБНОВЛЯЕТСЯ ПО КЛЮЧАМ внутри существующей
мапы, а не подменяется новым объектом. Комментарии в ruamel живут на самих
CommentedMap/CommentedSeq, и присваивание ``entry["published"] = {...}`` выбросило бы
вместе со старым объектом и привязанные к нему комментарии.
"""

from __future__ import annotations

from pathlib import Path

from schedule.cli import PLAN_HEADER
from schedule.settings import dump_roundtrip, load_roundtrip


def update_published_block(plan_path: Path, out_name: str, block: dict) -> None:
    """Set ``published: block`` on the entry whose ``out_name`` matches. Raises if absent."""
    doc = load_roundtrip(plan_path) or {}
    entries = doc.get("presentations") or []
    entry = next((e for e in entries if e.get("out_name") == out_name), None)
    if entry is None:
        raise ValueError(f"no plan entry with out_name={out_name!r} in {plan_path}")

    current = entry.get("published")
    if hasattr(current, "keys"):
        # Правим на месте: так переживают и комментарии внутри блока, и порядок ключей.
        for key in [k for k in current if k not in block]:
            del current[key]
        for key, value in block.items():
            current[key] = value
    else:
        entry["published"] = block

    dump_roundtrip(plan_path, doc, PLAN_HEADER)
