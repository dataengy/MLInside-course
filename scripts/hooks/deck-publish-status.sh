#!/usr/bin/env bash
# SessionStart hook: unpublished deck versions. Fail-open, no network.
# Compares the newest built version per plan deck (data/generated/{out_name}_v*.pptx)
# against the publish record — the local cursor if present, else the git-tracked
# published: block. Warns when something built is newer than what was published.
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

behind = []
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
    pub_ver = rec.get("version") or (e.get("published") or {}).get("version") or ""
    done = bool(rec.get("published_at") or (e.get("published") or {}).get("at"))
    if pub_ver != f"{newest[0]}.{newest[1]}" or not done:
        behind.append(f"{out_name} v{newest[0]}.{newest[1]} (издано: {pub_ver or '—'})")

if behind:
    print("[deck-publish] ⚠ не опубликованы свежие версии: " + "; ".join(behind)
          + " — just publish-new")
EOF
exit 0
