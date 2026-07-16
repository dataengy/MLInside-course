"""preza_gen.settings — typed Config + Content dataclasses loaded from settings + content yamls.

All scalars come from the yaml (fail-loud on missing keys — no inline defaults, per
script_standards.yml). `settings.load()` returns (Config, Content). Sub-dataclasses
(Theme/ImageBox/Layouts/Generation) make the config `ty`-checkable instead of raw dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .utils import expand_path, load_yaml

_KINDS = ("title", "agenda", "section", "content", "table", "closing")


@dataclass
class SlideSpec:
    """One slide. `kind` ∈ {title, agenda, section, content, table, closing}.

    `notes` support inline emphasis markup (see Config.notes_emphasis) and blank-line paragraphs.
    `materials` is an optional list of {label, url} rendered as a small links footer.
    """

    kind: str
    title: str = ""
    subtitle: str = ""
    bullets: list = field(default_factory=list)  # str | [str, level]
    table: dict | None = None  # {headers, rows, col_ratios}
    image: str | None = None  # media filename under Config.media_dir
    code: str = ""  # code snippet → dark monospace panel
    code_caption: str = ""  # small caption above the code panel
    notes: str = ""
    materials: list = field(default_factory=list)  # [{label, url}]


@dataclass
class Theme:
    """Deck palette + font (hex without '#')."""

    accent: str
    white: str
    dark: str
    alt: str
    font: str


@dataclass
class ImageBox:
    """Content-slide image box, in inches."""

    left: float
    top: float
    width: float
    height: float


@dataclass
class Layouts:
    """kind → template layout name. Supports `layouts[kind]` and `kind in layouts`."""

    title: str
    agenda: str
    section: str
    content: str
    table: str
    closing: str

    def __getitem__(self, kind: str) -> str:
        return getattr(self, kind)

    def __contains__(self, kind: object) -> bool:
        return kind in _KINDS


@dataclass
class Generation:
    """HOW-to-render options (rendering policy, deck-agnostic)."""

    parallel: bool


@dataclass
class Config:
    template: Path  # MLInside .pptx template built upon
    source_deck: Path  # deck whose media (ppt/media/*) is reused
    media_dir: Path | None  # extracted-media cache (None → extract to a temp dir)
    out_dir: Path  # data/generated
    out_name: str  # base stem at load; pipeline resolves the versioned name in place
    downloads_dir: Path | None  # ~/Downloads — pipeline derives downloads_link from it
    downloads_link: Path | None  # resolved by pipeline: downloads_dir / f"{out_name}.pptx"
    theme: Theme
    layouts: Layouts
    image_box: ImageBox
    body_font: dict  # {bullets_only|with_image: {level: pt}} — bullet sizing
    code_style: dict  # {font, size, fg, bg} for code panels
    code_box: ImageBox  # code panel box when bullets share the slide (right side)
    code_box_full: ImageBox  # code panel box when the slide is code-only (full width)
    notes_emphasis: dict  # markup convention (doc) — see utils.parse_runs markers
    generation: Generation
    naming: str  # fixed | increment | timestamp (see utils.resolve_out_name)
    version_major: int | None  # increment mode → _v{major}.{n}


@dataclass
class Content:
    slides: list[SlideSpec]


def load(settings_path: str | Path, content_path: str | Path) -> tuple[Config, Content]:
    """Load a deck from a settings yaml (HOW to render) + a content yaml (WHAT deck).

    settings yaml → `settings:` (template, theme, layouts, image_box, generation, out_dir…)
    content  yaml → `deck:` (out_name, naming, version_major, downloads_dir, source_deck)
                    + `content:` (slides)
    Fail-loud on missing keys — no inline defaults. Sub-dataclasses reject unknown keys.
    """
    s: dict[str, Any] = load_yaml(settings_path)["settings"]
    c: dict[str, Any] = load_yaml(content_path)
    d: dict[str, Any] = c["deck"]
    cfg = Config(
        template=expand_path(s["template"]),
        source_deck=expand_path(d["source_deck"]),
        media_dir=(expand_path(s["media_dir"]) if s.get("media_dir") else None),
        out_dir=expand_path(s["out_dir"]),
        out_name=d["out_name"],
        downloads_dir=(expand_path(d["downloads_dir"]) if d.get("downloads_dir") else None),
        downloads_link=None,
        theme=Theme(**s["theme"]),
        layouts=Layouts(**s["layouts"]),
        image_box=ImageBox(**s["image_box"]),
        body_font=s["body_font"],
        code_style=s["code_style"],
        code_box=ImageBox(**s["code_box"]),
        code_box_full=ImageBox(**s["code_box_full"]),
        notes_emphasis=s["notes_emphasis"],
        generation=Generation(**s["generation"]),
        naming=d["naming"],
        version_major=d.get("version_major"),
    )
    slides = [SlideSpec(**sl) for sl in c["content"]]
    return cfg, Content(slides=slides)
