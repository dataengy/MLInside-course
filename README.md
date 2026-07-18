# MLInside-course

MLInside 2026 course development (HSE / ВШЭ external education) — dbt & Dagster
lecture materials, deck generators and the course data library.

## Layout

| path | what |
|---|---|
| `content/` | deck source of truth: `*-settings.yml` (HOW) + `*-content.yml` (WHAT) |
| `src/preza_gen/` | deck generator — submodule [hnkovr/preza_gen](https://github.com/hnkovr/preza_gen) |
| `src/librarian/` | data librarian — submodule [hnkovr/librarian](https://github.com/hnkovr/librarian) |
| `src/orchestration/` | Prefect flow (scan → build → publish) |
| `data/` | course data library (git LFS) — see [`data/CATALOG.md`](data/CATALOG.md) and [`docs/data-structure.md`](docs/data-structure.md) |
| `settings/` | project SSoT (`config.yml`) + ingest provenance (`files.yml`) |

## Common commands (`just --list` for all)

```bash
just build           # build the deck (pptx + html) from content/
just publish         # build all formats, open, send to Telegram
just check           # lint + typecheck + tests
just librarian-plan "<root>"   # plan dedupe/categorize/version moves into data/
just librarian-apply           # execute the reviewed plan
just librarian-catalog         # regenerate data/CATALOG.md
```

## Data library

`data/` is managed by librarian: sha256 dedupe, categories
(`decks/docs/media/archives/code/templates`), version stacks (current at category
root, older in `.history/`), generated `CATALOG.md` with deterministic doc-props
(slides/pages/pictures/code blocks, word stats incl. speaker notes) + curated
reviews from `data/reviews.yml`. Do not move files in `data/` by hand.
