"""preza_merge.rules — turn a diff into profile keys, with the evidence that justified them.

A rule fires only when the change is SYSTEMATIC (share of eligible slides >= min_share);
anything rarer stays a per-slide note, because writing a one-off into a profile would apply
it to slides the reviewer never touched. Changes that must NOT be carried over (export
artefacts, lost content) are emitted as `regression` findings so "not merged" never reads
as "overlooked".
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .diff import DiffReport
from .model import Deck

# Shape-name prefixes the generator produces. The reviewer's tool renames shapes it creates,
# but keeps the names of shapes it merely moves — which is exactly what this lane inspects.
_CODE_PANEL = "Rounded Rectangle"
_PICTURE = "Picture"
_TABLE = "Table"
_BODY = "Text Placeholder"
# Theme roles / hex values that read as "the dark theme text colour" rather than the accent.
_DARK_BORDERS = {"tx1", "1A1A1A", "000000"}


@dataclass(frozen=True)
class Finding:
    """One conclusion about the fork. ``kind`` ∈ {format, regression}."""

    rule: str
    kind: str
    key: str | None  # profile key for kind=format; None for regressions
    value: object
    share: float
    evidence: str
    slides: list[int] = field(default_factory=list)


@dataclass
class MergeConfig:
    min_share: float
    tolerances: dict
    report_dir: Path
    fork_markers: list[str]
    fork_search_dir: Path
    default_profile: str
    base_profile: str

    @classmethod
    def load(cls, path: str | Path) -> MergeConfig:
        """Load settings/merge.yml. Fail-loud on a missing file or key."""
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"merge settings not found: {p}")
        m = yaml.safe_load(p.read_text(encoding="utf-8"))["merge"]
        return cls(
            min_share=float(m["min_share"]),
            tolerances=m["tolerances"],
            report_dir=Path(m["report_dir"]),
            fork_markers=list(m["fork_markers"]),
            fork_search_dir=Path(m["fork_search_dir"]).expanduser(),
            default_profile=m["default_profile"],
            base_profile=m["base_profile"],
        )


def _shapes_named(deck: Deck, prefix: str):
    """(slide_number, shape) for every shape whose name starts with ``prefix``."""
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.name.startswith(prefix):
                yield slide.n, shape


def _r1(rep: DiffReport, cfg: MergeConfig) -> Finding | None:
    cleared = sum(s.runs_size_cleared for s in rep.slides)
    if not cleared:
        return None
    eligible = [s for s in rep.slides if s.paras_before]
    hit = [s.n for s in rep.slides if s.runs_size_cleared]
    share = len(hit) / len(eligible) if eligible else 0.0
    if share < cfg.min_share:
        return None
    return Finding(
        "R1",
        "format",
        "body_font",
        "inherit",
        share,
        f"сняты явные размеры у {cleared} прогонов на {len(hit)} слайдах — "
        f"кегль наследуется от мастера",
        hit,
    )


def _bottoms(deck: Deck, prefix: str) -> list[tuple[int, float]]:
    return [(n, sh.bottom) for n, sh in _shapes_named(deck, prefix) if sh.height]


def _r2(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    pairs = _bottoms(theirs, _CODE_PANEL) + _bottoms(theirs, _PICTURE)
    if len(pairs) < 2:
        return None
    values = [b for _, b in pairs]
    median = round(st.median(values), 2)
    hit = [n for n, b in pairs if abs(b - median) <= 0.35]
    share = len(hit) / len(pairs)
    if share < cfg.min_share:
        return None
    base_pairs = _bottoms(base, _CODE_PANEL) + _bottoms(base, _PICTURE)
    if base_pairs and abs(st.median([b for _, b in base_pairs]) - median) < 0.2:
        return None  # nothing moved
    return Finding(
        "R2",
        "format",
        "visual_anchor",
        {"visual_anchor": "bottom", "visual_bottom": median},
        share,
        f"нижняя кромка визуала у {len(hit)}/{len(pairs)} элементов ≈ {median}″ "
        f"(разброс {min(values):.2f}–{max(values):.2f})",
        sorted(hit),
    )


def _r3(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    tops = [(n, sh.top) for n, sh in _shapes_named(theirs, _TABLE)]
    if not tops:
        return None
    values = [t for _, t in tops]
    median = round(st.median(values), 2)
    hit = [n for n, t in tops if abs(t - median) <= 0.15]
    share = len(hit) / len(tops)
    base_tops = [t for _, t in ((n, sh.top) for n, sh in _shapes_named(base, _TABLE))]
    if share < cfg.min_share or (base_tops and abs(st.median(base_tops) - median) < 0.2):
        return None
    return Finding(
        "R3",
        "format",
        "table_top",
        median,
        share,
        f"верх таблиц {st.median(base_tops):.2f}″ → {median}″ на {len(hit)}/{len(tops)} слайдах",
        sorted(hit),
    )


def _r4(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    widened, total = [], 0
    base_by_slide = {n: sh for n, sh in _shapes_named(base, _BODY)}
    for n, shape in _shapes_named(theirs, _BODY):
        before = base_by_slide.get(n)
        if before is None or not before.width:
            continue
        total += 1
        if shape.width - before.width > 0.3:
            widened.append(n)
    if not total:
        return None
    share = len(widened) / total
    if share < cfg.min_share:
        return None
    return Finding(
        "R4",
        "format",
        "bullets_width",
        "adaptive",
        share,
        f"колонка буллетов расширена на {len(widened)}/{total} слайдах",
        sorted(widened),
    )


def _r6(base: Deck, theirs: Deck, rep: DiffReport, cfg: MergeConfig) -> Finding | None:
    eligible, hit = 0, []
    for sb, sd in zip(base.slides, rep.slides):
        empty = [
            sh.name
            for sh in sb.shapes
            if sh.placeholder and sh.paras and not sh.text() and sh.name != sb.shapes_title_name
        ]
        if not empty:
            continue
        eligible += 1
        if set(empty) & set(sd.shapes_removed):
            hit.append(sb.n)
    if not eligible:
        return None
    share = len(hit) / eligible
    if share < cfg.min_share:
        return None
    return Finding(
        "R6",
        "format",
        "drop_empty_placeholders",
        True,
        share,
        f"пустые плейсхолдеры сняты на {len(hit)}/{eligible} слайдах",
        hit,
    )


def _r7(base: Deck, theirs: Deck) -> Finding | None:
    if not base.slides or not theirs.slides:
        return None
    b, t = base.slides[0].title, theirs.slides[0].title
    if b and t and t == b.upper() and t != b:
        return Finding(
            "R7", "format", "title_slide_uppercase", True, 1.0, f"титул: {b!r} → {t!r}", [1]
        )
    return None


def _r11(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    """Code-panel outline (R11).

    Found via the manager's stated rule, not via the geometry diff — see the plan's Global
    Constraints. Only the two unambiguous outcomes are proposed (dark / none); any other
    colour is left to the human rather than guessed into a profile.
    """
    before = {n: sh.line_color for n, sh in _shapes_named(base, _CODE_PANEL)}
    after = {n: sh.line_color for n, sh in _shapes_named(theirs, _CODE_PANEL)}
    common = sorted(set(before) & set(after))
    if not common:
        return None
    changed = [n for n in common if before[n] != after[n]]
    share = len(changed) / len(common)
    if share < cfg.min_share:
        return None
    values = {after[n] for n in changed}
    if values <= _DARK_BORDERS:
        value = "dark"
    elif values == {None}:
        value = "none"
    else:
        return None
    sample = before[changed[0]]
    return Finding(
        "R11",
        "format",
        "code_border",
        value,
        share,
        f"обводка код-панелей {sample} → {sorted(str(v) for v in values)} "
        f"на {len(changed)}/{len(common)} панелях",
        changed,
    )


def _regressions(base: Deck, theirs: Deck, rep: DiffReport) -> list[Finding]:
    out: list[Finding] = []
    if rep.theme_changed:
        out.append(
            Finding(
                "R8",
                "regression",
                None,
                rep.theme_fonts[1],
                1.0,
                f"шрифты темы {rep.theme_fonts[0]} → {rep.theme_fonts[1]} — артефакт экспорта",
                [],
            )
        )
    merged = [s.n for s in rep.slides if s.paras_after < s.paras_before]
    if merged:
        out.append(
            Finding(
                "R9",
                "regression",
                None,
                merged,
                len(merged) / max(1, len(rep.slides)),
                f"склеены абзацы на слайдах {merged} — потеря структуры буллетов",
                merged,
            )
        )
    lost = [s.n for s in rep.slides if s.notes_lost]
    if lost:
        out.append(
            Finding(
                "R10",
                "regression",
                None,
                lost,
                len(lost) / max(1, len(rep.slides)),
                f"потеряны заметки спикера на слайдах {lost}",
                lost,
            )
        )
    return out


def detect(base: Deck, theirs: Deck, rep: DiffReport, cfg: MergeConfig) -> list[Finding]:
    """All findings about the fork: profile rules first, then regressions."""
    found = [
        _r1(rep, cfg),
        _r2(base, theirs, cfg),
        _r3(base, theirs, cfg),
        _r4(base, theirs, cfg),
        _r6(base, theirs, rep, cfg),
        _r7(base, theirs),
        _r11(base, theirs, cfg),
    ]
    return [f for f in found if f is not None] + _regressions(base, theirs, rep)
