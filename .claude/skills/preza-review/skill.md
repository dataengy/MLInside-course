---
name: preza-review
description: 'Review a preza_gen deck content YAML against the lecture accents recorded in content/presentations.yml (synced from the course schedule Google Sheet) and the canonical 12-section DE-tool outline — reports each accent as hit/partial/missing with slide numbers, checks structure and code/table/notes density, and writes docs/reviews/<out_name>.md + <out_name>.findings.yml. Triggers on "review the deck", "проверь презентацию по плану", "does this deck cover the lecture accents", "рецензия на преза-контент", or as the post-build sibling of preza-de-validate.'
---

Judge a finished `content/<slug>-content.yml` against what the course plan promised the lecture
would cover. Sibling of `preza-de-validate` (schema/bounds/provenance) — this skill assumes the
deck is already schema-valid and never re-checks that; it refuses to review an invalid file.

## Run

```bash
just preza-review content/preza-dagster-content.yml     # from the course repo root
just preza-review-all                                    # every deck in the plan
```

Direct:

```bash
S=~/.ai/skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts
python "$S/review_content.py" content/preza-dbt-v3-content.yml \
  --plan content/presentations.yml \
  --settings settings/config.yml \
  --out-dir docs/reviews \
  # --advisory     # never fail the run
```

Exit 0 = clean. Exit 1 = at least one `error` finding (a must-have accent is missing), so the
command can gate a build. `--advisory` always exits 0.

## What it checks

**Accent coverage** — the rubric is `accents:` on the matching entry in
`content/presentations.yml` (kept in sync with the schedule sheet by `just presentations-plan`).
The deck is matched to its lecture by `content:` path, else by `deck.out_name`. Each accent is
term-stemmed and searched across slide titles, bullets, code, tables, materials and notes:

| verdict | meaning |
|---|---|
| ✅ hit | one slide carries ≥ `hit_ratio` of the accent's terms |
| 🟡 partial | best slide ≥ `partial_ratio`, or the terms are spread across several slides |
| ❌ missing | the terms appear nowhere — **error**, fails the run |

No plan entry → accents are skipped with a warning; structure is still reviewed.

**Subject structure** — presence of the canonical 12-section DE-tool outline (context/history →
architecture & entities → dev-vs-prod → integrations → CLI/MCP → ecosystem → homework →
closing). Missing *required* sections warn; optional ones are informational. Outline SSoT:
`../create-preza-about-de-tool/references/deck-outline-de-tool.md`.

**Deck health** — speaker-notes coverage, comparison-table share, code-panel share, materials
share, slide count against `deck_generation.slides_{min,max}`.

## Output

- `docs/reviews/<out_name>.md` — coverage table (accent → slides → match %), structure table,
  and a severity-sorted "что поправить" list.
- `docs/reviews/<out_name>.findings.yml` — `{severity, kind, accent|section, slides, message}`
  records plus stats, for downstream tooling.

## Tuning

Every threshold, section keyword and stopword lives in `settings/review.yml` — nothing is
hardcoded in the script. When a deck plainly covers an accent the report calls missing, widen
that section's `keywords` or lower `matching.hit_ratio`; do **not** downgrade
`severity.accent_missing`, which is what makes the gate meaningful.
