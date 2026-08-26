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

from .diff import _GEOM_ATTRS, compare
from .model import Deck, Slide
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
    # Fail-loud: a tolerance missing for one of diff._GEOM_ATTRS must not silently disable
    # that dimension's check — it must stop verification with a name-the-key error instead.
    missing = [attr for attr in _GEOM_ATTRS if attr not in cfg.tolerances]
    if missing:
        raise KeyError(
            f"settings/merge.yml: merge.tolerances missing {missing} — every attribute in "
            f"diff._GEOM_ATTRS must have a configured tolerance, add {missing} there"
        )
    rep = compare(rebuilt, theirs)
    res = VerifyResult(ok=True)
    res.lines.append(
        f"слайдов: {rep.slide_count[0]} ↔ {rep.slide_count[1]}; "
        f"расхождений по классам: {dict(rep.counts)}"
    )
    for sd in rep.slides:
        for change in sd.geometry:
            tol = cfg.tolerances[change.attr]
            if abs(change.delta) > tol:
                res.ok = False
                res.mismatches.append(
                    f"слайд {sd.n} «{sd.title[:40]}»: {change.shape}.{change.attr} "
                    f"{change.before}″ → {change.after}″ (Δ{change.delta:+.2f}″ > {tol}″)"
                )
    # Only `runs_size_cleared` is the R1 signal: a run that STILL carries an explicit size in
    # the rebuild while the fork cleared it — meaning R1 did not fire there. `runs_size_changed`
    # (both sides sized, but to different values) is R5 territory instead — the spec is explicit
    # that R5 is NOT a rule: the reviewer shrank code-panel text by hand where she made the panel
    # shorter, and the generator's own `_fit_code_size` does the same thing independently. Those
    # slides can never clear and must not fail verification.
    cleared_slides = [sd for sd in rep.slides if sd.runs_size_cleared]
    if cleared_slides:
        res.ok = False
        total = sum(sd.runs_size_cleared for sd in cleared_slides)
        nums = [sd.n for sd in cleared_slides]
        res.mismatches.append(
            f"явный кегль не снят у {total} прогонов на {len(nums)} слайдах {nums} — "
            f"правило R1 не отработало"
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


def _texts(slide: Slide, *, upcase_title: bool) -> list[str]:
    """Every shape's text, in order. On the title slide (``upcase_title``), the title
    shape's own text is uppercased first — R7 (rules._r7) may upcase it, and that same
    text also flows through here via the title placeholder's shape, so the exception has
    to apply here too or the shape-level check would re-flag what the title check above
    already tolerates."""
    out: list[str] = []
    for sh in slide.shapes:
        texts = sh.text()
        if upcase_title and sh.name == slide.shapes_title_name:
            texts = [t.upper() for t in texts]
        out.extend(texts)
    return out


def invariants(ours: Deck, merged: Deck) -> VerifyResult:
    """A formatting profile must not change what the deck says."""
    res = VerifyResult(ok=True)
    if len(ours.slides) != len(merged.slides):
        res.ok = False
        res.mismatches.append(f"слайдов: {len(ours.slides)} → {len(merged.slides)}")
    for idx, (a, b) in enumerate(zip(ours.slides, merged.slides, strict=False)):
        # R7 (rules._r7) upcases ONLY the title slide (base.slides[0]/theirs.slides[0]) —
        # the case-insensitive exception must stay scoped to slide 1, or a genuine
        # case-only title change anywhere else would be masked instead of caught.
        is_title_slide = idx == 0
        titles_match = (
            a.title.upper() == b.title.upper() if is_title_slide else a.title == b.title
        )
        if not titles_match:
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: заголовок {a.title!r} → {b.title!r}")
        ta = _texts(a, upcase_title=is_title_slide)
        tb = _texts(b, upcase_title=is_title_slide)
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
