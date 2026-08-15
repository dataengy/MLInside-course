---
name: preza-review
description: 'Review a preza_gen deck content YAML against the lecture accents recorded in content/presentations.yml (synced from the course schedule Google Sheet) and the canonical 12-section DE-tool outline — reports each accent as hit/partial/missing with slide numbers, checks structure and code/table/notes density, and writes docs/reviews/<out_name>.md + <out_name>.findings.yml. Triggers on "review the deck", "проверь презентацию по плану", "does this deck cover the lecture accents", "рецензия на преза-контент", or as the post-build sibling of preza-de-validate.'
hardlink_source: ~/.ai/skills/_catalog/docs/pptx/preza-review/SKILL.md
---

Judge a finished `content/<slug>-content.yml` against what the course plan promised the lecture
would cover. Sibling of `preza-de-validate` (schema/bounds/provenance): this skill does not
re-derive the schema rules, it calls the validator and folds its output in as findings, so a deck
with a stale stamp is still reviewed rather than refused.

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

## Getting the rubric from the sheet (proven live 2026-08-13, MLInside-course)

The accent axis is only as good as `accents:` in the plan. The sync lane, end to end:

```bash
just -f ~/.ai/scripts/gcloud/Justfile adc-status        # user-ADC prerequisite (see /reset-google-account-creds)
just gsheet-tabs                                        # smoke + tab names
just gsheet-dump                                        # raw dump → settings/schedule.yml — inspect the accents cell
just presentations-plan-dry                             # verify: targets in `updated`, N accents each
just presentations-plan                                 # write accents into content/presentations.yml
```

Traps that cost real debugging time:

- `settings/gsheet.yml → mapping.columns` **replaces** the reader's default map wholesale —
  restate every field, not just the delta, or `topic` stops resolving and the plan comes back empty.
- A sheet may name the accents column anything («тезисы» on the MLInside sheet) — the default
  candidates don't include it; without the mapping the sync silently yields zero accents.
- A cell holding one numbered paragraph («1. … 2. …») needs the reader's numbered-boundary
  split (`accents_split_numbering: true` in the MLInside reader), else the whole paragraph
  becomes ONE giant accent that can never hit.
- Upsert matches plan entries by **normalized topic** — the plan entry's `topic:` must equal the
  sheet's title up to case/punctuation/ё, or the sync creates a bare duplicate row instead.
- Free-text columns must not be mapped to `n:` — a numeric key would bypass topic matching.

When editing a deck to close an accent, restate the accent's own vocabulary on ONE slide: the
matcher stems words to `stem_len` (5) chars and does not bridge ru/en synonyms or ё/е.

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

**Unfinished deck** — titles still holding outline scaffolding (`Слайд 28: …`, `TODO`, `WIP`) and
slides repeated verbatim. Scaffolding is an **error**: a deck with placeholder headings cannot be
presented. Patterns live in `settings/review.yml → draft_scaffolding` and are scanned across
`title` *and* `bullets`, because a heading longer than `pptx_import.title_max_chars` lands in
bullets — scanning titles alone made the wordiest drafts look cleanest.

## Reviewing a deck that has no content source

A deck that arrived as a finished `.pptx` (a colleague's lecture, a prior-year course deck) is
imported first — lossy and one-way:

```bash
just preza-import-pptx data/decks/<deck>.pptx     # → content/imported/<deck>.yml
```

Then add a plan entry pointing at the imported YAML with:

- `generated: false` — an imported deck has no `— Сгенерировано:` stamp and must never be given a
  fake one. This demotes the two provenance errors to `info`; every other schema error still fails.
- `visuals: image-pipeline` when the deck carries pictures, else `code-tables` flags each one.

Never build from an imported file and never hand-edit it — fix the `.pptx` and re-import. Code
shown as *screenshots* is invisible to the importer, so the code-panel metric under-reports on
imported decks.

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
