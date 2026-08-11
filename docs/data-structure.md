# data/ — structure & conventions (Librarian)

Managed by the [`src/librarian`](../src/librarian/) submodule
([hnkovr/librarian](https://github.com/hnkovr/librarian)). Binary content is stored via
**git LFS** (`.gitattributes`: pptx, pdf, mp4, zip, docx, xlsx, mov, key).

## Current scaffold

```
data/
├── CATALOG.md          # generated: just librarian-catalog
├── reviews.yml         # curated per-file reviews (merged into CATALOG.md)
├── decks/              # presentations (current version of each stack)
│   └── .history/       #   older versions of the same stacks
├── templates/          # deck templates (name rule: "шаблон"/"template")
├── docs/               # pdf / docx / md / xlsx handouts, homework, lectures
│   └── .history/
├── media/              # mp4 recordings, standalone images
├── archives/           # zip bundles (seminar materials)
├── code/               # course code; embedded git repos live here as SUBMODULES
│   ├── dbt_project/    #   ДЗ 4-5 dbt project (submodule)
│   └── clickhouse_hw/  #   ДЗ 4-5 ClickHouse homework (submodule)
├── misc/               # uncategorized leftovers (should stay ~empty)
├── source/             # preza_gen ingest landing zone (provenance: settings/files.yml)
│   └── media/          #   extracted deck media
├── drafts/             # work-in-progress inputs (NotebookLM exports etc.)
├── generated/          # preza_gen build outputs
├── .archive/           # retired content kept out of the active tree
└── .state/             # librarian/preza_gen state (inventory, plan, cursors)
```

## Conventions

- **Version stacks**: per (category, stack-base) the highest `vN[.M]` (tie → newest mtime)
  sits at the category root; every other member goes to the sibling `.history/`.
  Stack base = filename stem without the `-vN` / `_vN.M` / ` (N)` suffix.
- **Dedupe**: exact sha256 duplicates are never stored twice; the canonical copy wins
  (existing repo content beats incoming, non-`(N)`-copy shortest name beats the rest).
- **Naming**: destination filenames replace spaces with `-` (repo convention).
- **Never hand-move files** between categories — rerun `just librarian-plan` /
  `just librarian-apply` so the plan stays the audit trail (`data/.state/librarian-plan.yml`).
- **`homework/` is outside this tree.** Authored course assignments live in a
  sibling top-level directory (`homework/mlinside-hw-olist`, a submodule), *not*
  under `data/code/`. Librarian's `data_root` is `data`, so it neither scans nor
  catalogs `homework/` — no `CATALOG.md` row appears for it, and that is intended.
  `data/code/` stays what it is: mirrors of *incoming* student submissions
  (ДЗ 4-5), which librarian does track.

## Proposed next iteration (not yet applied)

1. **Per-course nesting** once a second course lands: `data/decks/<course>/…`
   (e.g. `mlinside-2026/`, `hse-2025/`) — the flat tree works while everything is dbt/HSE.
2. **`data/source` → `data/.ingest`**: it is pipeline state, not library content;
   hiding it keeps `CATALOG.md` purely about curated materials.
3. **Recording index**: `media/` entries are large (LFS); consider replacing >100MB
   recordings with a `*.md` link stub (YC Object Storage / Google Drive) + checksum.
4. **CI check**: a `just librarian-catalog --check` mode failing when CATALOG.md is stale.
