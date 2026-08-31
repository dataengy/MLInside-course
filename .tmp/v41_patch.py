#!/usr/bin/env python3
"""Apply the v4.1 edit plan to the dbt deck content YAML — block surgery, not a YAML round-trip.

Same reason as scripts/preza/edit_slides.py: `yaml.safe_dump` renormalises every block
scalar in the file, so a ten-slide edit arrives as a three-thousand-line diff and the
hand-tuned code panels lose their exact indentation. Here the file is cut into text blocks
on the ``- kind:`` marker; untouched slides stay byte-for-byte.

The plan lives in .tmp/v41/plan.yml and supports five ops:

    - {op: replace,      id: 005-x,  file: 005-roles.yml}   # swap one slide's block
    - {op: insert_after, id: 006-x,  file: 006b-elt.yml}    # new slide after an existing one
    - {op: insert_before, id: 015-x, file: 015a-layers.yml}
    - {op: move,         id: 045-x,  after: 950-section}    # relocate an existing slide
    - {op: remove,       id: 904-x}
    - {op: sub,          find: "...", replace: "..."}       # whole-file text substitution
    - {op: header,       file: header.yml}                  # replace everything above `content:`

Ops run in file order. After writing, ids are checked for uniqueness and the result is
parsed with yaml.safe_load — on failure nothing is written.

    python3 .tmp/v41_patch.py content/preza-dbt-v4-content.yml .tmp/v41/plan.yml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

MARKER = "- kind:"
PLAN_DIR = Path(".tmp/v41")


def split_blocks(text: str) -> tuple[str, list[str]]:
    """Split a content YAML into (header, [slide block, ...]).

    The header is everything up to the first ``- kind:`` line, including the ``content:``
    key itself. Every block keeps its own trailing newline, so ``header + "".join(blocks)``
    reproduces the input exactly.
    """
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(MARKER)]
    if not starts:
        raise SystemExit("no slide blocks found — is this a preza_gen content yaml?")
    header = "".join(lines[: starts[0]])
    bounds = starts + [len(lines)]
    return header, ["".join(lines[a:b]) for a, b in zip(bounds, bounds[1:])]


def block_id(block: str) -> str:
    m = re.search(r"^  id:\s*(\S+)", block, re.M)
    return m.group(1) if m else ""


def find(blocks: list[str], slide_id: str) -> int:
    for i, b in enumerate(blocks):
        if block_id(b) == slide_id:
            return i
    raise SystemExit(f"slide id not found: {slide_id}")


def load_block(name: str) -> str:
    text = (PLAN_DIR / name).read_text(encoding="utf-8")
    if not text.startswith(MARKER):
        raise SystemExit(f"{name}: a slide file must start with '{MARKER}'")
    return text if text.endswith("\n") else text + "\n"


def apply(header: str, blocks: list[str], plan: list[dict]) -> tuple[str, list[str]]:
    for step in plan:
        op = step["op"]
        if op == "header":
            header = (PLAN_DIR / step["file"]).read_text(encoding="utf-8")
        elif op == "replace":
            blocks[find(blocks, step["id"])] = load_block(step["file"])
        elif op == "insert_after":
            blocks.insert(find(blocks, step["id"]) + 1, load_block(step["file"]))
        elif op == "insert_before":
            blocks.insert(find(blocks, step["id"]), load_block(step["file"]))
        elif op == "remove":
            blocks.pop(find(blocks, step["id"]))
        elif op == "move":
            block = blocks.pop(find(blocks, step["id"]))
            blocks.insert(find(blocks, step["after"]) + 1, block)
        elif op == "sub":
            need = step.get("count")
            hits = sum(b.count(step["find"]) for b in blocks) + header.count(step["find"])
            if need is not None and hits != need:
                raise SystemExit(f"sub {step['find']!r}: {hits} hits, expected {need}")
            if not hits:
                raise SystemExit(f"sub {step['find']!r}: no hits")
            header = header.replace(step["find"], step["replace"])
            blocks = [b.replace(step["find"], step["replace"]) for b in blocks]
        else:
            raise SystemExit(f"unknown op: {op}")
    return header, blocks


def main(content_path: str, plan_path: str) -> int:
    path = Path(content_path)
    header, blocks = split_blocks(path.read_text(encoding="utf-8"))
    plan = yaml.safe_load(Path(plan_path).read_text(encoding="utf-8")) or []
    header, blocks = apply(header, blocks, plan)

    out = header + "".join(blocks)
    doc = yaml.safe_load(out)  # fail-loud before touching the file on disk
    ids = [s.get("id", "") for s in doc["content"]]
    dupes = {i for i in ids if i and ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate slide ids: {sorted(dupes)}")
    path.write_text(out, encoding="utf-8")
    print(f"{path}: {len(doc['content'])} slides, {len(plan)} plan steps applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
