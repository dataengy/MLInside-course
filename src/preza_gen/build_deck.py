"""preza_gen.build_deck — CLI: build a deck as pptx/html/pdf from settings + content yamls.

Thin Click wrapper over pipeline.build_deck() (the importable core the future flow also calls).
    uv run python -m preza_gen.build_deck --all
    uv run python -m preza_gen.build_deck --content src/preza_gen/content/mle.yml --pptx --open
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import click

from . import pipeline
from .utils import log

_DEFAULT_SETTINGS = Path(__file__).with_name("build_deck_v3-settings.yml")
_DEFAULT_CONTENT = Path(__file__).with_name("preza-dbt-v3-content.yml")
# CLI convenience only; Phase C's publish.py reads this path from settings instead.
_PUBLISH_SH = os.path.expanduser("~/.ai/scripts/publish/publish-deck.sh")


@click.command()
@click.option(
    "--settings",
    "settings_yml",
    default=str(_DEFAULT_SETTINGS),
    show_default=True,
    help="settings yaml — HOW to render (template/theme/layouts/generation)",
)
@click.option(
    "--content",
    "content_yml",
    default=str(_DEFAULT_CONTENT),
    show_default=True,
    help="content yaml — WHAT deck (naming, source deck, slides)",
)
@click.option("--pptx", "do_pptx", is_flag=True, help="render .pptx")
@click.option("--html", "do_html", is_flag=True, help="render .html")
@click.option("--pdf", "do_pdf", is_flag=True, help="render .pdf (needs an engine)")
@click.option("--all", "do_all", is_flag=True, help="pptx + html + pdf")
@click.option(
    "--open",
    "do_open",
    is_flag=True,
    help="open the built .pptx in PowerPoint (publish-deck.sh --no-send)",
)
def main(
    settings_yml: str,
    content_yml: str,
    do_pptx: bool,
    do_html: bool,
    do_pdf: bool,
    do_all: bool,
    do_open: bool,
) -> None:
    if do_all:
        do_pptx = do_html = do_pdf = True
    elif not (do_pptx or do_html or do_pdf):
        do_pptx = do_html = True  # sensible default: pptx + html (pdf is opt-in / stubbed)

    res = pipeline.build_deck(settings_yml, content_yml, pptx=do_pptx, html=do_html, pdf=do_pdf)

    if do_open and res.out_path:
        if os.path.isfile(_PUBLISH_SH):
            subprocess.run(
                ["bash", _PUBLISH_SH, "--file", str(res.out_path), "--no-send"], check=False
            )
        else:
            log.warning(f"--open: publish helper not found: {_PUBLISH_SH}")


if __name__ == "__main__":
    main()
