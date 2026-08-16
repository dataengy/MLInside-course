"""publisher.state — per-workstation publish cursor.

``data/.state/deck-publish-state.json`` (gitignored) records, per ``out_name``, which built
``(version, sig)`` each leg (tg / drive / sheet) last succeeded for. The cross-machine,
git-tracked record is the ``published:`` block in ``content/presentations.yml`` (see
``plan_writer``); the runner seeds this cursor from it on a fresh clone, so losing this file
must never cause a Telegram re-send. The shape is richer than preza_gen.scan's flat
``{path: sig}`` cursor — hence a local implementation, not an import.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

LEGS = ("tg", "drive", "sheet")


@dataclass
class LegStatus:
    """Outcome of one leg for the (version, sig) recorded on the parent DeckState."""

    status: str = "pending"  # pending | ok | error | skipped
    at: str | None = None
    error: str | None = None


@dataclass
class DeckState:
    version: str = ""
    sig: str = ""
    slides: int | None = None
    drive_file_id: str | None = None
    drive_url: str | None = None
    tg: LegStatus = field(default_factory=LegStatus)
    drive: LegStatus = field(default_factory=LegStatus)
    sheet: LegStatus = field(default_factory=LegStatus)
    # Resolved 0-based sheet column indices per written field — the header-drift defense:
    # reused next run while the header text still matches (see gsheet_write.ensure_columns).
    sheet_cols: dict[str, int] = field(default_factory=dict)
    published_at: str | None = None  # set once the deck counts as fully served

    def leg(self, name: str) -> LegStatus:
        return getattr(self, name)

    def reset_for(self, version: str, sig: str) -> None:
        """A new build invalidates every leg (drive id/cols survive — they are identities)."""
        self.version, self.sig, self.slides = version, sig, None
        for name in LEGS:
            setattr(self, name, LegStatus())
        self.published_at = None


def _leg_from(raw: object) -> LegStatus:
    if not isinstance(raw, dict):
        return LegStatus()
    return LegStatus(
        status=str(raw.get("status") or "pending"),
        at=raw.get("at"),
        error=raw.get("error"),
    )


def deck_state_from(raw: object) -> DeckState:
    """Tolerant deserialization — unknown keys ignored, missing legs → pending.

    >>> deck_state_from({"version": "1.2", "tg": {"status": "ok"}}).tg.status
    'ok'
    >>> deck_state_from("garbage").version
    ''
    """
    if not isinstance(raw, dict):
        return DeckState()
    cols = raw.get("sheet_cols")
    return DeckState(
        version=str(raw.get("version") or ""),
        sig=str(raw.get("sig") or ""),
        slides=raw.get("slides"),
        drive_file_id=raw.get("drive_file_id"),
        drive_url=raw.get("drive_url"),
        tg=_leg_from(raw.get("tg")),
        drive=_leg_from(raw.get("drive")),
        sheet=_leg_from(raw.get("sheet")),
        sheet_cols={str(k): int(v) for k, v in cols.items()} if isinstance(cols, dict) else {},
        published_at=raw.get("published_at"),
    )


def read_state(path: str | Path) -> dict[str, DeckState]:
    """Cursor keyed by out_name; empty on missing/corrupt file (forgiving read)."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): deck_state_from(v) for k, v in raw.items()}


def write_state_atomic(path: str | Path, state: dict[str, DeckState]) -> None:
    """Atomic write (.tmp + os.replace). Raises on failure — a lost cursor means re-sends."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    payload = {k: asdict(v) for k, v in state.items()}
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
