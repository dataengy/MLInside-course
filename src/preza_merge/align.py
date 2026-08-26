"""preza_merge.align — line up base / ours / theirs slides by title sequence.

Titles are the only stable identity across a fork: the reviewer's file has no slide ids and
its shape names are rewritten by the exporting tool. Ambiguity (a title appearing more than
once) is REPORTED, never guessed — a wrong alignment silently merges the wrong slide.
"""

from __future__ import annotations

import difflib
from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Row:
    """One logical slide across the three sides. Indices are 1-based, None = absent."""

    title: str
    base: int | None
    ours: int | None
    theirs: int | None
    status: str  # unchanged | ours-only | theirs-only | both | dropped


@dataclass
class Alignment:
    rows: list[Row] = field(default_factory=list)
    unaligned: list[str] = field(default_factory=list)

    def by_status(self, status: str) -> list[Row]:
        return [r for r in self.rows if r.status == status]


def _pairs(base_titles: list[str], other_titles: list[str]) -> dict[int, int]:
    """base index → other index (both 0-based) for slides the matcher considers equal."""
    matcher = difflib.SequenceMatcher(a=base_titles, b=other_titles, autojunk=False)
    out: dict[int, int] = {}
    for op, i1, i2, j1, _j2 in matcher.get_opcodes():
        if op != "equal":
            continue
        for offset in range(i2 - i1):
            out[i1 + offset] = j1 + offset
    return out


def _status(in_ours: bool, in_theirs: bool, in_base: bool) -> str:
    if in_base and in_ours and in_theirs:
        return "unchanged"
    if in_base and not in_ours and in_theirs:
        return "dropped"
    if not in_base and in_ours and not in_theirs:
        return "ours-only"
    if not in_base and not in_ours and in_theirs:
        return "theirs-only"
    return "both"


def align3(base, ours, theirs) -> Alignment:
    """Align three decks by title sequence; ambiguous titles land in ``unaligned``."""
    bt, ot, tt = base.titles(), ours.titles(), theirs.titles()
    res = Alignment()

    dupes = {t for side in (bt, ot, tt) for t, n in Counter(side).items() if n > 1 and t}
    res.unaligned = sorted(dupes)

    b2o, b2t = _pairs(bt, ot), _pairs(bt, tt)
    matched_o, matched_t = set(b2o.values()), set(b2t.values())

    for i, title in enumerate(bt):
        o, t = b2o.get(i), b2t.get(i)
        res.rows.append(
            Row(
                title=title,
                base=i + 1,
                ours=(o + 1) if o is not None else None,
                theirs=(t + 1) if t is not None else None,
                status=_status(o is not None, t is not None, True),
            )
        )
    for j, title in enumerate(ot):
        if j not in matched_o:
            res.rows.append(Row(title, None, j + 1, None, "ours-only"))
    for k, title in enumerate(tt):
        if k not in matched_t:
            res.rows.append(Row(title, None, None, k + 1, "theirs-only"))

    res.rows.sort(key=lambda r: (r.ours or 10_000, r.base or 10_000, r.theirs or 10_000))
    return res
