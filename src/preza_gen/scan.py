"""preza_gen.scan — cursor-based change detection for source inputs (prefect-free).

Port of ~/.ai/scripts/publish/deck-watch.sh: keys each file as ``<mtime>:<size>`` and diffs
against a state file. Two deliberate differences from the bash hook:
  • the cursor is a separate JSON (data/.state/publish-cursor.json) — NOT files.yml, which is
    the *input-provenance* manifest (different lifecycle);
  • write_state_atomic RAISES on failure — the hook swallows errors (exit 0) because a hook
    must never break the session; a Prefect task must surface the failure instead.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .utils import expand_path


@dataclass
class Changed:
    """A watched input whose signature differs from the cursor."""

    path: str  # absolute path
    sig: str  # "<mtime>:<size>"


def sig(path: Path) -> str:
    """Signature of a file: ``<int mtime>:<size>`` (matches deck-watch.sh `stat -f '%m:%z'`)."""
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def expand_watch(watch: list[str], root: Path) -> list[Path]:
    """Expand watch entries (files, dirs, missing) → concrete files under ``root``.

    Directories expand to every file within (recursively); missing entries are skipped
    (a watched input may not exist yet, e.g. an empty drafts/ landing zone).
    """
    out: list[Path] = []
    for w in watch:
        p = root / w
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file())
        elif p.is_file():
            out.append(p)
    return out


def scan_changed(
    watched: list[Path], state: dict[str, str]
) -> tuple[list[Changed], dict[str, str]]:
    """Diff watched files against ``state``; return (changed, new_state). Pure of side effects."""
    new_state = dict(state)
    changed: list[Changed] = []
    for p in watched:
        key = str(p)
        s = sig(p)
        if state.get(key) != s:
            changed.append(Changed(path=key, sig=s))
        new_state[key] = s
    return changed, new_state


def read_state(path: str | Path) -> dict[str, str]:
    """Read the cursor JSON ({abs_path: sig}); empty dict if missing or unreadable."""
    p = expand_path(path)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state_atomic(path: str | Path, state: dict[str, str]) -> None:
    """Write the cursor atomically (.tmp + os.replace). RAISES on failure (unlike the hook)."""
    p = expand_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def seed(watched: list[Path], cursor_file: str | Path) -> int:
    """Record current signatures without flagging anything (deck-watch.sh --seed). Returns count."""
    state = {str(p): sig(p) for p in watched}
    write_state_atomic(cursor_file, state)
    return len(state)
