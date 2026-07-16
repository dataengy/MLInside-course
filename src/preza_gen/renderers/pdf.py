"""preza_gen.renderers.pdf — HTML→PDF renderer.

STUB: LibreOffice (soffice) is unavailable on this machine, so pptx→pdf via LO is out. The chosen
path is HTML→PDF; the engine is a backlog decision (WeasyPrint pip vs headless Chromium/Playwright)
tracked in .ai/tasks/. If WeasyPrint is installed, it is used; otherwise a clear hint is logged.
"""

from __future__ import annotations

from pathlib import Path

from ..settings import Config, Content
from ..utils import log


def render(cfg: Config, content: Content, html_path: Path | None = None) -> Path | None:
    """Render the HTML deck → PDF via WeasyPrint if available; else log a backlog hint."""
    if html_path is None:
        html_path = cfg.out_dir / f"{cfg.out_name}.html"
    if not Path(html_path).is_file():
        log.warning("PDF: no HTML input — run the html renderer first (build with --html/--all).")
        return None
    try:
        from weasyprint import HTML  # ty: ignore[unresolved-import]  # optional dep: '.[pdf]'
    except Exception:
        log.warning(
            "PDF renderer not wired: install an engine — `uv pip install weasyprint` (HTML→PDF), "
            "or use headless Chromium/Playwright. See .ai/tasks/ backlog. "
            f"For now open {html_path} and print-to-PDF."
        )
        return None
    out = cfg.out_dir / f"{cfg.out_name}.pdf"
    HTML(filename=str(html_path)).write_pdf(str(out))
    log.success(f"pdf → {out}")
    return out
