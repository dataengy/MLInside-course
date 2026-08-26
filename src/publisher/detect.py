"""publisher.detect — which built version of a deck is newest on disk.

The builder (preza_gen) writes ``data/generated/{out_name}_v{major}.{minor}.pptx`` and
records the result nowhere, so the versioned filename IS the version registry. The regex is
re-implemented locally: preza_gen's ``_VER_RE`` is private and matches anywhere in a name,
while this one is anchored to the ``.pptx`` suffix and paired with an exact-stem check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Anchored to the .pptx suffix and paired with an exact-stem check. Patch and build tag are
# optional: "_v3.19.pptx", "_v3.19.1.pptx", "_v3.19.1+alina-fmt.pptx" all parse.
_VER_RE = re.compile(r"_v(\d+)\.(\d+)(?:\.(\d+))?(?:\+([a-z0-9][a-z0-9._-]*))?\.pptx$")


@dataclass(frozen=True)
class BuiltDeck:
    """One built pptx artifact of one deck."""

    out_name: str
    path: Path
    major: int
    minor: int
    patch: int
    descr: str
    sig: str  # "<int mtime>:<size>"

    @property
    def version(self) -> str:
        """
        >>> BuiltDeck("X", Path("X_v3.14.pptx"), 3, 14, 0, "", "0:0").version
        '3.14'
        >>> BuiltDeck("X", Path("X_v3.19.1+alina-fmt.pptx"), 3, 19, 1, "alina-fmt", "0:0").version
        '3.19.1+alina-fmt'
        """
        core = f"{self.major}.{self.minor}" + (f".{self.patch}" if self.patch else "")
        return core + (f"+{self.descr}" if self.descr else "")


def sig(path: Path) -> str:
    """``<int mtime>:<size>`` — same shape as preza_gen.scan.sig / deck-watch.sh."""
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def find_versions(out_dir: Path, out_name: str) -> list[BuiltDeck]:
    """Every built version of one deck, version-ascending.

    The stem must match ``out_name`` exactly: ``MLInside_Dagster`` must not pick up
    ``MLInside_Dagster-old_v1.1.pptx`` (glob prefix alone would). Ordering is the numeric
    triple — the build tag labels a build, it never ranks one.
    """
    found: list[BuiltDeck] = []
    if not out_dir.is_dir():
        return found
    for p in out_dir.glob(f"{out_name}_v*.pptx"):
        m = _VER_RE.search(p.name)
        if not m or p.name[: -len(m.group(0))] != out_name:
            continue
        found.append(
            BuiltDeck(
                out_name,
                p,
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3) or 0),
                m.group(4) or "",
                sig(p),
            )
        )
    return sorted(found, key=lambda d: (d.major, d.minor, d.patch))


def newest(out_dir: Path, out_name: str) -> BuiltDeck | None:
    """Newest built version, or None when the deck was never built (→ skip silently)."""
    versions = find_versions(out_dir, out_name)
    return versions[-1] if versions else None


def slide_count(pptx: Path) -> int:
    """Slide count of the actual built artifact (not the content YAML) — what shipped."""
    from pptx import Presentation  # deferred: python-pptx is heavy to import

    return len(Presentation(str(pptx)).slides)
