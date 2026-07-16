"""preza_gen.utils — logger + shared helpers (yaml, paths, image-fit, hardlink+provenance).

Logger mirrors the house `get_logger(...short_format=True)` (short, emojied, colored loguru;
falls back to stdlib logging when loguru is absent). Pure helpers carry doctests.
"""

from __future__ import annotations

import contextlib
import os
import re as _re
import shutil
import sys
from pathlib import Path
from typing import Any

try:  # loguru is optional — fall back to stdlib logging
    from loguru import logger as _loguru

    _HAS_LOGURU = True
except Exception:  # pragma: no cover
    _HAS_LOGURU = False

_LEVEL_ICONS = {
    "TRACE": "🔍",
    "DEBUG": "🔍",
    "INFO": "ℹ️",
    "SUCCESS": "✅",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
}


def get_logger(name: str = "preza_gen", level: str = "INFO", *, short_format: bool = True):
    """Return a short/emojied/colored logger; loguru if available, else stdlib."""
    if _HAS_LOGURU:
        _loguru.remove()
        for lvl, icon in _LEVEL_ICONS.items():
            with contextlib.suppress(ValueError, TypeError):  # pragma: no cover
                _loguru.level(lvl, icon=icon)
        if short_format:
            fmt = (
                "<dim>{time:HH:mm:ss}</dim> <cyan>{extra[ctx]}</cyan> "
                "<level>{level.icon} {message}</level>"
            )
        else:
            fmt = (
                "<dim>{time:YY/MM/DD HH:mm:ss}</dim> <cyan>{extra[ctx]}</cyan> "
                "<level>{level: <8}</level> {message}"
            )
        _loguru.add(sys.stderr, format=fmt, level=level, colorize=True)
        return _loguru.bind(ctx=name)
    import logging

    logging.basicConfig(level=level, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    return logging.getLogger(name)


log = get_logger()


def expand_path(p: Any) -> Path:
    """Expand ``$VARS`` and ``~`` in a path string to an absolute-ish Path.

    >>> str(expand_path("~/x")).startswith(str(Path.home()))
    True
    """
    return Path(os.path.expandvars(str(p))).expanduser()


def load_yaml(path: Any) -> dict:
    """Load a YAML file, failing loud if it is missing (no silent defaults)."""
    import yaml

    p = expand_path(path)
    if not p.is_file():
        raise FileNotFoundError(f"required yaml missing: {p}")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def fit_image_box(px_w: int, px_h: int, box_w: int, box_h: int) -> tuple[int, int]:
    """Scale (px_w,px_h) to fit inside a box (EMU), preserving aspect ratio.

    >>> fit_image_box(1000, 500, 400, 400)   # wide → constrained by width
    (400, 200)
    >>> fit_image_box(500, 1000, 400, 400)   # tall → constrained by height
    (200, 400)
    """
    if px_w / px_h > box_w / box_h:
        return box_w, int(box_w * px_h / px_w)
    return int(box_h * px_w / px_h), box_h


# Notes emphasis markup (priority: strongest → weakest). Stored/documented in
# build_deck_v3.yml → settings.notes_emphasis. Non-nested.
#   !!x!!  → bold + underline (самое важное)
#   **x**  → bold           (термины / важное)
#   __x__  → underline      (следующее по важности)
#   ~~x~~  → italic         (второстепенное)
_EMPHASIS = _re.compile(r"!!(.+?)!!|\*\*(.+?)\*\*|__(.+?)__|~~(.+?)~~", _re.S)


def parse_runs(text: str) -> list[tuple[str, bool, bool, bool]]:
    """Split marked-up text into (segment, bold, underline, italic) runs.

    >>> parse_runs("a **b** c")
    [('a ', False, False, False), ('b', True, False, False), (' c', False, False, False)]
    >>> parse_runs("!!x!!")[0]
    ('x', True, True, False)
    """
    out: list[tuple[str, bool, bool, bool]] = []
    last = 0
    for m in _EMPHASIS.finditer(text):
        if m.start() > last:
            out.append((text[last : m.start()], False, False, False))
        if m.group(1) is not None:
            out.append((m.group(1), True, True, False))
        elif m.group(2) is not None:
            out.append((m.group(2), True, False, False))
        elif m.group(3) is not None:
            out.append((m.group(3), False, True, False))
        else:
            out.append((m.group(4), False, False, True))
        last = m.end()
    if last < len(text):
        out.append((text[last:], False, False, False))
    return out


# Output naming (auto-versioning). A build resolves a versioned stem from a base name:
#   increment → {base}_v{major}.{n}  (n = max existing minor for that major + 1)
#   timestamp → {base}_{ts}
#   fixed     → {base}   (back-compat: put the full versioned name in the base)
_VER_RE = _re.compile(r"_v(\d+)\.(\d+)(?:\D|$)")


def next_minor(names: list[str], base: str, major: int) -> int:
    """Return the next minor for '{base}_v{major}.<n>' seen among ``names`` (1 if none).

    >>> next_minor(["X_v3.1.pptx", "X_v3.2.html", "X_v2.9.pptx"], "X", 3)
    3
    >>> next_minor(["X_v3.pptx"], "X", 3)   # no minor → ignored
    1
    >>> next_minor([], "X", 3)
    1
    """
    minors = [
        int(m.group(2))
        for n in names
        if n.startswith(f"{base}_v{major}.")
        for m in [_VER_RE.search(n)]
        if m and int(m.group(1)) == major
    ]
    return (max(minors) + 1) if minors else 1


def resolve_out_name(
    base: str, mode: str, existing: list[str], *, major: int | None = None, ts: str | None = None
) -> str:
    """Resolve a versioned output stem. ``mode`` ∈ {fixed, increment, timestamp}; fail-loud.

    >>> resolve_out_name("Deck", "fixed", [])
    'Deck'
    >>> resolve_out_name("Deck", "increment", ["Deck_v3.1.pptx"], major=3)
    'Deck_v3.2'
    >>> resolve_out_name("Deck", "timestamp", [], ts="20260716-2230")
    'Deck_20260716-2230'
    """
    if mode == "fixed":
        return base
    if mode == "increment":
        if major is None:
            raise ValueError("increment naming needs version_major")
        return f"{base}_v{major}.{next_minor(existing, base, major)}"
    if mode == "timestamp":
        if not ts:
            raise ValueError("timestamp naming needs a ts value")
        return f"{base}_{ts}"
    raise ValueError(f"unknown naming mode: {mode!r}")


def hardlink_or_copy(src: Any, dst: Any) -> str:
    """Hardlink src→dst (same volume, materialized); fall back to copy. Returns the method used."""
    src_p, dst_p = expand_path(src), expand_path(dst)
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    if dst_p.exists() or dst_p.is_symlink():
        dst_p.unlink()
    try:
        os.link(src_p, dst_p)
        return "hardlink"
    except OSError:
        shutil.copy2(src_p, dst_p)
        return "copy"
