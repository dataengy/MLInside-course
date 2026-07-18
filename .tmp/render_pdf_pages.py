#!/usr/bin/env python3
"""Render selected 1-based PDF pages to PNG using Poppler (true LibreOffice visual QA)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="PDF produced by `just build-all`")
    parser.add_argument("slides", nargs="+", type=int, help="1-based page numbers")
    parser.add_argument("--dpi", type=int, default=160, help="PNG resolution (default: 160)")
    parser.add_argument("--out-dir", type=Path, default=Path(".tmp/render-pdf"))
    args = parser.parse_args()

    if not args.pdf.is_file():
        parser.error(f"PDF does not exist: {args.pdf}")
    if shutil.which("pdftoppm") is None:
        parser.error("pdftoppm is required (install Poppler first)")
    if any(page < 1 for page in args.slides):
        parser.error("slide numbers are 1-based positive integers")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for page in args.slides:
        output = args.out_dir / f"slide{page:02d}"
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(page),
                "-l",
                str(page),
                "-r",
                str(args.dpi),
                "-png",
                "-singlefile",
                str(args.pdf),
                str(output),
            ],
            check=True,
        )
        print(output.with_suffix(".png"))


if __name__ == "__main__":
    main()
