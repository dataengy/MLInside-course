#!/usr/bin/env bash
# SessionStart hook: reviewer forks waiting to be merged. Fail-open, no network.
# Two states, never conflated:
#   ⚠ форк-кандидат — a deck-named .pptx with a copy marker in the fork search dir;
#   ⓘ нерешённое предложение — a *.proposal.yml still carrying `decision: null`.
# Spec: docs/preza-merge-lane.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

[ -f settings/merge.yml ] || exit 0
[ -f content/presentations.yml ] || exit 0

python3 - 2>/dev/null <<'EOF' || true
import re
import shlex
from pathlib import Path

import yaml

merge = yaml.safe_load(Path("settings/merge.yml").read_text(encoding="utf-8"))["merge"]
plan = yaml.safe_load(Path("content/presentations.yml").read_text(encoding="utf-8")) or {}
decks = [e for e in plan.get("presentations", []) if e.get("out_name") and e.get("content")]

search = Path(merge["fork_search_dir"]).expanduser()
markers = merge["fork_markers"]
generated = Path("data/generated")
ver_re = re.compile(r"_v(\d+\.\d+)")

candidates = []
if search.is_dir():
    for deck in decks:
        name = deck["out_name"]
        built = list(generated.glob(f"{name}_v*.pptx"))
        ours = max(built, key=lambda p: p.stat().st_mtime, default=None)
        newest_mtime = ours.stat().st_mtime if ours else 0
        for path in search.glob(f"{name}_v*.pptx"):
            if not any(m in path.name for m in markers):
                continue
            if path.stat().st_mtime > newest_mtime - 86400:
                candidates.append((deck["content"], name, path, ours))

# `just preza-merge-propose` takes 5 POSITIONAL args: deck base ours theirs rev.
# Print something the human can actually paste — every path quoted, none truncated.
for content, name, theirs, ours in candidates[:5]:
    print(f"[preza-merge] ⚠ форк-кандидат: {theirs.name}")
    m = ver_re.search(theirs.name)
    base = generated / f"{name}_v{m.group(1)}.pptx" if m else None
    base_arg = shlex.quote(str(base)) if base and base.is_file() else "<base-не-найден>"
    ours_arg = shlex.quote(str(ours)) if ours else "<ours-не-найден>"
    print(
        f"[preza-merge]   just preza-merge-propose {shlex.quote(content)} {base_arg} "
        f"{ours_arg} {shlex.quote(str(theirs))} <git-rev-контента-базы>"
    )

report_dir = Path(merge["report_dir"])
pending = []
if report_dir.is_dir():
    for prop in report_dir.glob("*.proposal.yml"):
        doc = yaml.safe_load(prop.read_text(encoding="utf-8")) or {}
        rules = (doc.get("proposal") or {}).get("rules") or []
        undecided = [r["rule"] for r in rules if r.get("decision") is None]
        if undecided:
            pending.append((prop, undecided))

for prop, undecided in pending[:5]:
    print(f"[preza-merge] ⓘ нерешённые правила {','.join(undecided)} → {prop}")
EOF
