"""preza_gen.pipeline — orchestrator-agnostic build entry point.

`build_deck()` is the one function both the Click CLI (build_deck.py) and a future Prefect
flow call — importing it gives real exceptions instead of exit codes. No prefect import here;
this module stays unit-testable in the lean 5-dep env.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import settings as S
from .renderers import html as R_html
from .renderers import pdf as R_pdf
from .renderers import pptx as R_pptx
from .utils import expand_path, log, resolve_out_name


@dataclass
class BuildResult:
    """What a build produced. `out_path` is the .pptx; `method` is its hardlink/copy to Downloads."""

    out_name: str
    out_path: Path | None = None
    method: str | None = None
    html_out: Path | None = None
    pdf_out: Path | None = None


def _resolve_naming(cfg: S.Config) -> None:
    """Resolve cfg.out_name (versioned stem) + cfg.downloads_link in place. Fail-loud."""
    existing = [p.name for p in cfg.out_dir.glob("*")] if cfg.out_dir.is_dir() else []
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    cfg.out_name = resolve_out_name(
        cfg.out_name, cfg.naming, existing, major=cfg.version_major, ts=ts
    )
    if cfg.downloads_dir:
        cfg.downloads_link = expand_path(cfg.downloads_dir) / f"{cfg.out_name}.pptx"


def build_deck(
    settings_yml: str | Path,
    content_yml: str | Path,
    *,
    pptx: bool = False,
    html: bool = False,
    pdf: bool = False,
) -> BuildResult:
    """Load settings+content, resolve the versioned name, render the requested formats."""
    cfg, content = S.load(settings_yml, content_yml)
    _resolve_naming(cfg)
    log.info(
        f"building '{cfg.out_name}' — {len(content.slides)} slides "
        f"(pptx={pptx} html={html} pdf={pdf}, parallel={cfg.generation.parallel})"
    )
    res = BuildResult(out_name=cfg.out_name)

    def _do_pptx() -> None:
        res.out_path, res.method = R_pptx.render(cfg, content)

    def _do_html() -> None:
        res.html_out = R_html.render(cfg, content)

    if cfg.generation.parallel and pptx and html:
        R_pptx.ensure_media(cfg)  # pre-extract so the two renderers don't race on ppt/media/*
        with ThreadPoolExecutor(max_workers=2) as ex:
            list(ex.map(lambda fn: fn(), (_do_pptx, _do_html)))
    else:
        if pptx:
            _do_pptx()
        if html:
            _do_html()
    if pdf:
        res.pdf_out = R_pdf.render(cfg, content, res.html_out)
    return res
