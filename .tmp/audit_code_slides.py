#!/usr/bin/env python3
"""Report code-slide density and the resulting side/full layout from a deck content YAML."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("content", type=Path, help="deck content YAML")
    args = parser.parse_args()

    deck = yaml.safe_load(args.content.read_text(encoding="utf-8"))
    print("slide  layout  lines  bullets  title")
    for index, spec in enumerate(deck["content"], start=1):
        code = spec.get("code", "").rstrip()
        if not code:
            continue
        bullets = spec.get("bullets", [])
        layout = "side" if bullets else "full"
        print(f"{index:>5}  {layout:<6}  {len(code.splitlines()):>5}  {len(bullets):>7}  {spec['title']}")


if __name__ == "__main__":
    main()
