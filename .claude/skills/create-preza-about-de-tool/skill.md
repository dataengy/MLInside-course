---
name: create-preza-about-de-tool
description: 'Generate a detailed Russian Data-Engineering-tool lecture deck for the MLInside course — authors a preza_gen content YAML (20–50 slides, code panels + comparison tables, very detailed speaker notes, provenance stamp) and builds pptx+html. Triggers on "create-preza-about-de-tool ''<topic>''", "сделай презу про <DE-инструмент>", "deck about Dagster/Prefect/Airflow/dbt/observability". Composes sub-skills preza-de-outline, preza-de-stamp, preza-de-validate.'
---

Generate a course lecture deck about any Data-Engineering tool (orchestrator, transform,
ingestion, CI/observability) as a preza_gen `content/<slug>-content.yml`, then build it to
pptx + html. Run from the MLInside-course project root.

## Signature

```
create-preza-about-de-tool "<topic>" \
  [--visuals code-tables|reuse-source|image-pipeline]  # default code-tables
  [--lang ru]                                          # default ru
  [--slides-min N --slides-max M]                       # default from settings/config.yml (20..50)
  [--build | --dry]                                     # default --build
```

## Flow

1. **Resolve names** — `scripts/resolve_slug.py "<topic>"` → `slug` + `out_name`.
   Content file = `content/preza-<slug>-content.yml`.
2. **Outline** — build the section list from `references/deck-outline-de-tool.md` (sub-skill
   `preza-de-outline`). Scale to the slide range; drop sections that don't apply.
3. **Author** — write the content YAML to the schema in `references/content-schema.md`, using the
   chosen profile from `references/visual-profiles.md`. Every slide gets **very detailed** 2-paragraph
   `notes` with emphasis markup; every "X vs Y" is a `kind: table`; architecture schemes and code
   examples go in `code:` panels. Verify volatile facts (versions, M&A, MCP) before asserting them.
4. **Stamp provenance** — `scripts/stamp_provenance.py <file> --model <id> --harness <name>
   --effort <level> --version <vN.m> --date <YYYY-MM-DD>` writes the model/harness/effort/version
   line into the first + last slide notes (sub-skill `preza-de-stamp`). Pass the date explicitly.
5. **Validate** — `scripts/validate_content.py <file> --settings settings/config.yml --visuals <p>`
   (sub-skill `preza-de-validate`). Fix every `[error]` before building.
6. **Build** — `scripts/build_deck.sh --content <file> --visuals <p>` (validate + `preza_gen
   --pptx --html`), or `--dry` to stop after validation. Also exposed as project `just` targets.

## Deterministic scripts

| script | role |
|---|---|
| `scripts/preza_schema.py` | shared schema constants + loaders (imported by validate/stamp) |
| `scripts/resolve_slug.py` | topic → slug + out_name (transliterates Cyrillic) |
| `scripts/stamp_provenance.py` | inject/update the provenance stamp (idempotent) |
| `scripts/validate_content.py` | schema + slide-count + provenance + image-policy gate |
| `scripts/build_deck.sh` | validate → `preza_gen.build_deck --pptx --html` |
| `scripts/port-skill-local.sh` | mirror this skill into a project (symlink + hardlink, with NOTES) |

## References

- `references/deck-outline-de-tool.md` — standard sections + note-writing standard.
- `references/content-schema.md` — exact preza_gen slide schema + emphasis markup.
- `references/visual-profiles.md` — code-tables / reuse-source / image-pipeline.

## Notes

- **No mermaid / no chart generation** — visuals are `code:` panels or reused raster `image:`
  files only. Default `code-tables` forbids `image:` so decks build with zero source assets.
- **Never fabricate** screenshots or facts; phrase forward-looking items as such.
- The HOW-file `content/build_deck_v3-settings.yml` (theme/layouts/boxes) is shared — do not edit it
  per-deck.
