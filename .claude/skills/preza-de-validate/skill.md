---
name: preza-de-validate
description: 'Validate a preza_gen deck content YAML before building — checks the SlideSpec schema (known kinds/keys), table headers+rows, slide count within the course range, the model/harness/effort/version provenance stamp in the first+last slide notes, and the image policy for the chosen visual profile. Triggers on "validate the deck", "проверь preza content yml", "check slides before build", or as step 5 of create-preza-about-de-tool.'
---

Gate a `content/<slug>-content.yml` before `preza_gen` renders it. Sub-skill of
`create-preza-about-de-tool`; safe to run standalone.

## Run

```bash
S=~/.ai/skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts
python "$S/validate_content.py" content/preza-dagster-content.yml \
  --settings settings/config.yml \
  --visuals code-tables            # or reuse-source | image-pipeline
  # --media-dir data/source/media  # resolve image: refs (non code-tables profiles)
```

Exit 0 = clean. Exit 1 = errors printed as `[error]` lines; `[warn]` lines never fail the run.

## What it checks

- top-level `deck:` + `content:`; `deck` has `out_name`/`naming`/`source_deck`
  (+ `version_major` when `naming: increment`)
- every slide: mapping, known `kind`, only known `SlideSpec` keys
- `kind: table` slides carry non-empty `headers` + `rows`
- slide count within `deck_generation.slides_{min,max}` (course default 20..50)
- provenance stamp `— Сгенерировано:` present in FIRST and LAST slide notes
- image policy: `code-tables` rejects any `image:`; other profiles warn on missing files
- warns on empty speaker notes

Schema SSoT: `src/preza_gen/settings.py` → mirrored in
`../create-preza-about-de-tool/references/content-schema.md`.
