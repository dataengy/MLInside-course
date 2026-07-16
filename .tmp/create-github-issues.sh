#!/usr/bin/env bash
# Create GitHub issues (repo-bound) from the .ai/tasks/*.md backlog, labeled by project.
# GitHub is the best-fit tracker for this repo (Linear MCP is not connected here).
#
# The repo lives under the `dataengy` account — run this yourself (the agent is blocked from
# switching gh identity). Run from the repo root:
#     bash .tmp/create-github-issues.sh
# Restores your previous active account at the end.
set -uo pipefail
REPO="dataengy/MLInside-course"

PREV=$(gh auth status 2>&1 | awk '/account /{a=$NF} /Active account: true/{print a; exit}')
gh auth switch --user dataengy >/dev/null 2>&1 || true
echo "active gh: $(gh api user --jq .login 2>/dev/null)"

# labels (idempotent) — two "projects" as labels + a pdf tag
gh label create preza_gen        --repo "$REPO" --color 2419FF --description "Deck generator" 2>/dev/null || true
gh label create MLInside-course  --repo "$REPO" --color 505050 --description "Course project"  2>/dev/null || true
gh label create pdf              --repo "$REPO" --color 808080 2>/dev/null || true

# task-file → project label
declare -A LABEL=(
  [0001-pdf-weasyprint]=preza_gen
  [0002-pdf-chromium]=preza_gen
  [0003-mle-content]=MLInside-course
  [0004-prefect-and-claude-move]=preza_gen
)
for f in .ai/tasks/*.md; do
  base=$(basename "$f" .md)
  title=$(head -1 "$f" | sed 's/^#* *//')
  lbl="${LABEL[$base]:-preza_gen}"
  args=(--repo "$REPO" --title "$title" --body-file "$f" --label "$lbl")
  [[ "$base" == *pdf* ]] && args+=(--label pdf)
  if gh issue create "${args[@]}"; then echo "  ✓ $title  [$lbl]"; else echo "  ✗ $title"; fi
done

# Optional: GitHub Projects (v2) boards (needs the `project` scope on the token):
#   gh project create --owner dataengy --title "preza_gen"
#   gh project create --owner dataengy --title "MLInside-course"
# then add issues via: gh project item-add <num> --owner dataengy --url <issue-url>

[[ -n "$PREV" ]] && gh auth switch --user "$PREV" >/dev/null 2>&1
echo "restored active gh: $(gh api user --jq .login 2>/dev/null)"
