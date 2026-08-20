#!/usr/bin/env bash
# SessionStart hook: unpublished deck versions. Fail-open, no network.
# Compares the newest built version per plan deck (data/generated/{out_name}_v*.pptx)
# against the publish record — the local cursor if present, else the git-tracked
# published: block. Two distinct warnings, never conflated:
#   ⚠ a newer version was built than the one published (needs a full publish);
#   ⓘ the version is current but some legs never finished (needs a retry of those legs).
# Spec: docs/deck-publish-pipeline.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

PLAN="content/presentations.yml"
[ -f "$PLAN" ] || exit 0
[ -d data/generated ] || exit 0

python3 - "$PLAN" 2>/dev/null <<'EOF' || true
import json, re, sys
from pathlib import Path

import yaml

plan = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
decks = [e for e in plan.get("presentations", []) if e.get("content") and e.get("out_name")]
ver_re = re.compile(r"_v(\d+)\.(\d+)\.pptx$")

cursor = {}
cur_path = Path("data/.state/deck-publish-state.json")
if cur_path.is_file():
    try:
        cursor = json.loads(cur_path.read_text(encoding="utf-8")) or {}
    except Exception:
        cursor = {}

LEGS = ("tg", "drive", "sheet")
SETTLED = {"ok", "skipped"}


def leg_status(rec, block, leg):
    """Cursor leg (a dict) wins over the plan block leg (a bare string)."""
    cur = rec.get(leg)
    if isinstance(cur, dict) and cur.get("status"):
        return cur["status"]
    if isinstance(cur, str) and cur:
        return cur
    return (block.get("legs") or {}).get(leg) or "pending"


behind = []
unfinished = {}
for e in decks:
    out_name = e["out_name"]
    newest = None
    for p in Path("data/generated").glob(f"{out_name}_v*.pptx"):
        m = ver_re.search(p.name)
        if not m or p.name[: -len(m.group(0))] != out_name:
            continue
        v = (int(m.group(1)), int(m.group(2)))
        newest = v if newest is None or v > newest else newest
    if newest is None:
        continue
    rec = cursor.get(out_name) or {}
    block = e.get("published") or {}
    pub_ver = rec.get("version") or block.get("version") or ""
    if pub_ver != f"{newest[0]}.{newest[1]}":
        behind.append(f"{out_name} v{newest[0]}.{newest[1]} (издано: {pub_ver or '—'})")
        continue
    if rec.get("published_at") or block.get("at"):
        continue
    pending = tuple(l for l in LEGS if leg_status(rec, block, l) not in SETTLED)
    if pending:
        unfinished.setdefault(pending, []).append(out_name)

if behind:
    print("[deck-publish] ⚠ собрано новее опубликованного: " + "; ".join(behind)
          + " — just publish-new")
for pending, names in sorted(unfinished.items()):
    only = " ".join(f"--only {l}" for l in pending)
    print(f"[deck-publish] ⓘ версии актуальны, не завершены леги {'+'.join(pending)}: "
          f"{len(names)} дек(и) — just publish-new {only}")
EOF
exit 0
