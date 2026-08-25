"""preza_merge.verify — did the profile actually reproduce the reviewer's deck, and did the
merge keep our content intact?

Two independent questions, deliberately not merged into one score:
  * STRUCTURAL — rebuild the base content with the new profile and compare against the fork.
    A rule approximates hand-placed boxes, so residuals within `merge.tolerances` are
    expected; anything larger is printed per slide and fails.
  * INVARIANT — compare the merged build against OUR newest build. A formatting profile may
    not change what the deck says: slide count, titles, bullet text, notes, hyperlink and
    materials-footer counts must match exactly.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .diff import compare
from .model import Deck
from .rules import MergeConfig

_MATERIALS_MARK = "📚"


@dataclass
class VerifyResult:
    ok: bool
    lines: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)

    def merge(self, other: VerifyResult) -> VerifyResult:
        return VerifyResult(
            ok=self.ok and other.ok,
            lines=self.lines + other.lines,
            mismatches=self.mismatches + other.mismatches,
        )


def structural(rebuilt: Deck, theirs: Deck, cfg: MergeConfig) -> VerifyResult:
    """Rebuilt-with-profile vs the fork: residual geometry must fit the tolerances."""
    rep = compare(rebuilt, theirs)
    res = VerifyResult(ok=True)
    res.lines.append(
        f"слайдов: {rep.slide_count[0]} ↔ {rep.slide_count[1]}; "
        f"расхождений по классам: {dict(rep.counts)}"
    )
    for sd in rep.slides:
        for change in sd.geometry:
            tol = cfg.tolerances.get(change.attr)
            if tol is None:
                continue
            if abs(change.delta) > tol:
                res.ok = False
                res.mismatches.append(
                    f"слайд {sd.n} «{sd.title[:40]}»: {change.shape}.{change.attr} "
                    f"{change.before}″ → {change.after}″ (Δ{change.delta:+.2f}″ > {tol}″)"
                )
    if rep.counts.get("font"):
        res.ok = False
        res.mismatches.append(
            f"размеры шрифта разошлись на {rep.counts['font']} слайдах — правило R1 не отработало"
        )
    return res


def _links(deck: Deck) -> int:
    return sum(len(sh.hyperlinks) for s in deck.slides for sh in s.shapes)


def _materials(deck: Deck) -> int:
    return sum(
        1
        for s in deck.slides
        for sh in s.shapes
        if any(_MATERIALS_MARK in t for t in sh.text())
    )


def _notes(deck: Deck) -> int:
    return sum(1 for s in deck.slides if s.notes.strip())


def invariants(ours: Deck, merged: Deck) -> VerifyResult:
    """A formatting profile must not change what the deck says."""
    res = VerifyResult(ok=True)
    if len(ours.slides) != len(merged.slides):
        res.ok = False
        res.mismatches.append(f"слайдов: {len(ours.slides)} → {len(merged.slides)}")
    for a, b in zip(ours.slides, merged.slides):
        if a.title.upper() != b.title.upper():  # R7 may upcase the title slide
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: заголовок {a.title!r} → {b.title!r}")
        ta = [t for sh in a.shapes for t in sh.text()]
        tb = [t for sh in b.shapes for t in sh.text()]
        if ta != tb:
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: изменился текст буллетов/панелей")
        if a.notes.strip() != b.notes.strip():
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: изменились заметки спикера")
    for label, fn in (("ссылок", _links), ("футеров материалов", _materials), ("заметок", _notes)):
        x, y = fn(ours), fn(merged)
        res.lines.append(f"{label}: {x} ↔ {y}")
        if x != y:
            res.ok = False
            res.mismatches.append(f"{label}: {x} → {y}")
    return res


def contact_sheet(pptx: Path, out_dir: Path) -> Path | None:
    """Render a deck to per-slide PNGs via LibreOffice. Returns the dir, or None if absent."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)],
        check=False,
        capture_output=True,
    )
    pdf = out_dir / f"{pptx.stem}.pdf"
    if not pdf.is_file():
        return None
    subprocess.run(
        ["pdftoppm", "-png", "-r", "70", str(pdf), str(out_dir / pptx.stem)],
        check=False,
        capture_output=True,
    )
    return out_dir
