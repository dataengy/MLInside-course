"""preza_merge.diff — pairwise comparison of two normalized decks.

Compares slide-by-slide over the common prefix and shape-by-shape by NAME within a slide.
Text is compared as joined, whitespace-normalized paragraphs: a PowerPoint/Google round-trip
shatters one bullet into many runs, and a run-level comparison would report every such
slide as edited when nothing was said differently.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .model import Deck, Shape

_GEOM_ATTRS = ("left", "top", "width", "height")
_GEOM_EPS = 0.01  # inches — below this a difference is float/round-trip noise


@dataclass(frozen=True)
class GeomChange:
    shape: str
    attr: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return round(self.after - self.before, 3)


@dataclass
class SlideDiff:
    n: int
    title: str
    classes: set[str] = field(default_factory=set)
    shapes_added: list[str] = field(default_factory=list)
    shapes_removed: list[str] = field(default_factory=list)
    geometry: list[GeomChange] = field(default_factory=list)
    runs_size_cleared: int = 0
    runs_size_changed: list[tuple[int, int]] = field(default_factory=list)
    paras_before: int = 0
    paras_after: int = 0
    notes_lost: bool = False
    text_changed: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.classes)


@dataclass
class DiffReport:
    slide_count: tuple[int, int]
    theme_fonts: tuple[dict, dict]
    slides: list[SlideDiff]
    counts: Counter

    @property
    def theme_changed(self) -> bool:
        return self.theme_fonts[0] != self.theme_fonts[1]


def _compare_shape(name: str, a: Shape, b: Shape, sd: SlideDiff) -> None:
    for attr in _GEOM_ATTRS:
        before, after = getattr(a, attr), getattr(b, attr)
        if abs(after - before) > _GEOM_EPS:
            sd.geometry.append(GeomChange(name, attr, before, after))
            sd.classes.add("geometry")

    if a.text() != b.text():
        sd.text_changed.append(name)
        sd.classes.add("text")

    sd.paras_before += len([p for p in a.paras if p.runs])
    sd.paras_after += len([p for p in b.paras if p.runs])

    for pa, pb in zip(a.paras, b.paras):
        for ra, rb in zip(pa.runs, pb.runs):
            if ra.size is not None and rb.size is None:
                sd.runs_size_cleared += 1
                sd.classes.add("font")
            elif ra.size is not None and rb.size is not None and ra.size != rb.size:
                sd.runs_size_changed.append((ra.size, rb.size))
                sd.classes.add("font")
        if pa.props != pb.props or pa.level != pb.level:
            sd.classes.add("paragraph")


def compare(a: Deck, b: Deck) -> DiffReport:
    """Diff two decks over their common slide prefix."""
    slides: list[SlideDiff] = []
    counts: Counter = Counter()

    for sa, sb in zip(a.slides, b.slides):
        sd = SlideDiff(n=sa.n, title=sa.title)
        na, nb = sa.by_name(), sb.by_name()
        sd.shapes_added = sorted(set(nb) - set(na))
        sd.shapes_removed = sorted(set(na) - set(nb))
        if sd.shapes_added or sd.shapes_removed:
            sd.classes.add("shapes")
        for name in sorted(set(na) & set(nb)):
            _compare_shape(name, na[name], nb[name], sd)
        if sa.notes.strip() and not sb.notes.strip():
            sd.notes_lost = True
            sd.classes.add("notes")
        if sd.paras_before != sd.paras_after:
            sd.classes.add("paragraph")
        for cls in sd.classes:
            counts[cls] += 1
        slides.append(sd)

    for cls in ("text", "geometry", "font", "paragraph", "shapes", "notes"):
        counts.setdefault(cls, 0)
    if a.theme_fonts != b.theme_fonts:
        counts["theme"] = 1
    else:
        counts.setdefault("theme", 0)

    return DiffReport(
        slide_count=(len(a.slides), len(b.slides)),
        theme_fonts=(a.theme_fonts, b.theme_fonts),
        slides=slides,
        counts=counts,
    )
