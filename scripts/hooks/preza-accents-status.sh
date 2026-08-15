#!/usr/bin/env bash
# SessionStart hook: state of the GSheet→accents review lane. Fail-open, no network.
# Warns when settings/gsheet.yml is missing or when a plan entry that HAS a deck
# (content:) still carries an empty accents rubric — i.e. /preza-review's accent
# axis is a no-op for that lecture. Spec: docs/schedule-gsheet-lane.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

PLAN="content/presentations.yml"
[ -f "$PLAN" ] || exit 0

if [ ! -f settings/gsheet.yml ]; then
  echo "[preza-accents] ⚠ settings/gsheet.yml отсутствует — синк листа не настроен (just presentations-plan)"
fi

python3 - "$PLAN" 2>/dev/null <<'EOF' || true
import sys, yaml
plan = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
decks = [e for e in plan.get("presentations", []) if e.get("content")]
if not any(e.get("accents") for e in decks):
    print("[preza-accents] ⚠ ни у одной деки нет accents — синк листа ещё не запускался "
          "(just presentations-plan); акцентная ось preza-review молчит")
else:
    # after the first sync, nag only about sheet-matched entries (owner set by the sync)
    empty = [e.get("topic", "?") for e in decks if e.get("owner") and not e.get("accents")]
    if empty:
        print(f"[preza-accents] ⚠ accents: [] у sheet-matched дек(и): " + "; ".join(empty)
              + " — перезапустите just presentations-plan")
EOF
exit 0
