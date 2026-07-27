"""Sheet rows → presentation records, and the upsert that protects hand-curated fields."""

from __future__ import annotations

import re
from typing import Any

from loguru import logger as log

#: Order of keys in ``content/presentations.yml`` entries.
FIELD_ORDER = ["n", "date", "topic", "owner", "status", "accents", "content", "out_name", "slides"]

#: Fields that come from the sheet — everything else in an existing entry is hand-curated
#: and preserved by :func:`upsert`.
SHEET_FIELDS = {"n", "date", "topic", "owner", "status", "accents", "notes"}

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize(text: Any) -> str:
    """Casefold, drop punctuation, collapse whitespace, ё→е — for header/topic matching.

    >>> normalize("  Тема №1 / лекции ")
    'тема 1 лекции'
    >>> normalize("Ключевые Моменты")
    'ключевые моменты'
    >>> normalize(None)
    ''
    """
    if text is None:
        return ""
    s = str(text).replace("ё", "е").replace("Ё", "Е").casefold()
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def resolve_columns(header: list[Any], columns: dict[str, list[str]]) -> dict[str, int]:
    """Map each field to a column index using the candidate header names.

    Exact normalized match wins, then a literal match (for punctuation-only headers such as
    "№" or "#", which normalize to nothing), then a substring match. Fields whose header is
    absent are simply left out.

    >>> hdr = ["№", "Дата", "Тема лекции", "Акценты"]
    >>> cols = {"n": ["№"], "date": ["дата"], "topic": ["тема"], "owner": ["лектор"]}
    >>> resolve_columns(hdr, cols)
    {'n': 0, 'date': 1, 'topic': 2}
    """
    norm = [normalize(h) for h in header]
    literal = ["" if h is None else str(h).strip().casefold() for h in header]
    found: dict[str, int] = {}
    for field, candidates in (columns or {}).items():
        cands = [normalize(c) for c in candidates or []]
        cands_literal = [str(c).strip().casefold() for c in candidates or []]
        idx = next((i for i, h in enumerate(norm) if h and h in cands), None)
        if idx is None:
            idx = next((i for i, h in enumerate(literal) if h and h in cands_literal), None)
        if idx is None:
            idx = next(
                (i for i, h in enumerate(norm) if h and any(c and c in h for c in cands)),
                None,
            )
        if idx is not None:
            found[field] = idx
    return found


def find_header_row(rows: list[list[Any]], columns: dict[str, list[str]], limit: int = 10) -> int:
    """Index of the row that resolves the most fields — used when ``header_row`` is unset.

    >>> rows = [["Расписание"], ["№", "Тема"], ["1", "dbt"]]
    >>> find_header_row(rows, {"n": ["№"], "topic": ["тема"]})
    1
    """
    best, best_score = 0, -1
    for i, row in enumerate(rows[:limit]):
        score = len(resolve_columns(row, columns))
        if score > best_score:
            best, best_score = i, score
    return best


def split_accents(value: Any, seps: list[str]) -> list[str]:
    """Split one cell into individual accents.

    >>> split_accents("модели; тесты\\n- docs", ["\\n", ";"])
    ['модели', 'тесты', 'docs']
    >>> split_accents("", ["\\n"])
    []
    """
    if not value:
        return []
    text = str(value)
    for sep in seps or []:
        text = text.replace(sep, "\n")
    out = []
    for part in text.split("\n"):
        part = part.strip().lstrip("-–—•*").strip()
        if part:
            out.append(part)
    return out


def _cell(row: list[Any], idx: int | None) -> Any:
    if idx is None or idx >= len(row):
        return ""
    v = row[idx]
    return v.strip() if isinstance(v, str) else v


def rows_to_presentations(rows: list[list[Any]], mapping: dict) -> list[dict]:
    """Turn a tab's raw rows into presentation records.

    Rows with no topic are skipped (spacers, totals, notes). ``n`` is coerced to int when the
    cell is a bare number.
    """
    columns = mapping.get("columns") or {}
    header_row = mapping.get("header_row")
    hidx = (header_row - 1) if isinstance(header_row, int) and header_row > 0 else None
    if hidx is None or hidx >= len(rows):
        hidx = find_header_row(rows, columns)

    cols = resolve_columns(rows[hidx] if hidx < len(rows) else [], columns)
    if "topic" not in cols:
        log.warning(
            f"No 'topic' column resolved from header row {hidx + 1}: "
            f"{rows[hidx] if hidx < len(rows) else []!r} — fix mapping.columns in settings/gsheet.yml"
        )
        return []
    log.info(f"header row {hidx + 1}; columns resolved: {cols}")

    seps = mapping.get("accents_split") or ["\n"]
    out: list[dict] = []
    for row in rows[hidx + 1 :]:
        topic = _cell(row, cols.get("topic"))
        if not topic:
            continue
        rec: dict[str, Any] = {}
        raw_n = _cell(row, cols.get("n"))
        if raw_n not in ("", None):
            m = re.search(r"\d+", str(raw_n))
            rec["n"] = int(m.group()) if m else raw_n
        for field in ("date", "owner", "status"):
            val = _cell(row, cols.get(field))
            if val not in ("", None):
                rec[field] = val
        rec["topic"] = topic
        accents = split_accents(_cell(row, cols.get("accents")), seps)
        if accents:
            rec["accents"] = accents
        notes = _cell(row, cols.get("notes"))
        if notes:
            rec["notes"] = notes
        out.append(rec)
    return out


def entry_key(rec: dict) -> str:
    """Identity of a presentation: its number, else its normalized topic.

    >>> entry_key({"n": 9, "topic": "dbt"})
    'n:9'
    >>> entry_key({"topic": "Введение в dbt"})
    'topic:введение в dbt'
    """
    if rec.get("n") not in (None, ""):
        return f"n:{rec['n']}"
    return f"topic:{normalize(rec.get('topic'))}"


def _ordered(rec: dict) -> dict:
    known = {k: rec[k] for k in FIELD_ORDER if k in rec}
    extra = {k: v for k, v in rec.items() if k not in known}
    return {**known, **extra}


def upsert(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], dict[str, list[str]]]:
    """Merge freshly-read records into the curated list.

    Sheet-sourced fields (:data:`SHEET_FIELDS`) are overwritten; every other key already in an
    entry — ``content``, ``out_name``, ``slides``, anything hand-added — is preserved. Entries
    that vanished from the sheet are kept and reported, never deleted.

    An entry seeded by hand without ``n`` is matched to a numbered sheet row by normalized
    topic, so hand-seeding the plan before the first sync does not create duplicates.

    Returns ``(merged, changes)`` where ``changes`` has ``added``/``updated``/``stale`` keys.

    >>> old = [{"n": 9, "topic": "dbt", "content": "content/preza-dbt-v3-content.yml"}]
    >>> new = [{"n": 9, "topic": "Введение в dbt", "accents": ["модели"]}]
    >>> merged, changes = upsert(old, new)
    >>> merged[0]["topic"], merged[0]["content"]
    ('Введение в dbt', 'content/preza-dbt-v3-content.yml')
    >>> changes["updated"]
    ['n:9']

    Hand-seeded (unnumbered) entry adopts the sheet's number instead of duplicating:

    >>> seeded = [{"topic": "Введение в dbt", "content": "content/preza-dbt-v3-content.yml"}]
    >>> merged, changes = upsert(seeded, [{"n": 9, "topic": "Введение в dbt"}])
    >>> len(merged), merged[0]["n"], merged[0]["content"]
    (1, 9, 'content/preza-dbt-v3-content.yml')
    """
    by_key = {entry_key(e): dict(e) for e in existing}
    # Secondary index: unnumbered entries, addressable by topic alone.
    by_topic = {k: k for k in by_key if k.startswith("topic:")}
    changes: dict[str, list[str]] = {"added": [], "updated": [], "stale": []}
    seen = set()

    merged: list[dict] = []
    for rec in incoming:
        key = entry_key(rec)
        match = key if key in by_key else by_topic.get(f"topic:{normalize(rec.get('topic'))}")
        if match:
            seen.add(match)
            base = by_key[match]
            updated = {**base, **{k: v for k, v in rec.items() if k in SHEET_FIELDS}}
            if updated != base:
                changes["updated"].append(key)
            merged.append(_ordered(updated))
        else:
            seen.add(key)
            changes["added"].append(key)
            merged.append(_ordered({**rec, "content": None, "out_name": None}))

    for key, entry in by_key.items():
        if key not in seen:
            changes["stale"].append(key)
            merged.append(_ordered(entry))

    return merged, changes
