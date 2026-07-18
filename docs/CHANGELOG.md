# CHANGELOG — MLInside-course

Canonical project changelog (finalize-issue passes migrate shipped work here).

## 2026-07-19 — Librarian: data library, dedupe, catalog

- [`2645a9a`](https://github.com/dataengy/MLInside-course/commit/2645a9a) — new submodule
  [hnkovr/librarian](https://github.com/hnkovr/librarian) → `src/librarian`
  (inventory → plan → apply → catalog; settings-SSoT, sha256 dedupe, version stacks,
  deterministic docprops; 24 tests) + `just librarian-*`; LFS extended
  (mp4/zip/docx/xlsx/mov/key); `*.zip`, `*.mp4`, `data/source/` un-ignored
  (data/source now holds the only copies of ingested originals);
  [`docs/data-structure.md`](data-structure.md).
- [`077da45`](https://github.com/dataengy/MLInside-course/commit/077da45) — ingest:
  `assets/` + iCloud `_2025-11-ВШЭ_ВНЕШНЕЕ_ОБУЧЕНИЕ` + dbt-materials from `~/Downloads`
  → `data/` (46 moves: 11 current decks + 21 `.history/` versions, 13 docs, 2 recordings);
  16 exact sha256 duplicates deleted from iCloud after verification, marker
  `_MOVED-TO-REPO.md` left; `data/CATALOG.md` (deterministic props) +
  curated `data/reviews.yml`; ~825MB pushed via git LFS.
- [`f3d8ca4`@preza_gen](https://github.com/hnkovr/preza_gen/commit/f3d8ca4) — committed
  WIP: soffice→pdf engine (`renderers/pdf.py`), `_fit_code_box` wrap-aware sizing
  (`renderers/pptx.py`), `preza_refactoring/` finalize pipeline; paths `assets/` →
  `data/decks/` (`dbt_final.yml`, verify → `.history` v4 snapshot).
- [`03ef26a`](https://github.com/dataengy/MLInside-course/commit/03ef26a) — root README;
  dropped `egg-info`, `.bak1`, stale `~$` locks.
- Closed backlog: `0001-pdf-weasyprint`, `0002-pdf-chromium` → `.ai/tasks/.done/`
  (superseded by the LibreOffice pdf engine).
- Deferred (iCloud blocked: hotspot can't reach `p219-content.icloud.com`, quota exceeded):
  ~33 evicted files (Dagster mp4, Семинар12/14 pptx, ДЗ zips) and
  `ДЗ 4-5/{dbt_project,clickhouse_hw}` → submodules under `data/code/`.

## 2026-07-17 and earlier — deck generator v3

- [`e4736e7`](https://github.com/dataengy/MLInside-course/commit/e4736e7) — generator
  extracted to submodule [hnkovr/preza_gen](https://github.com/hnkovr/preza_gen)
  (`src/preza_gen`); deck source split: `content/*-settings.yml` (HOW) +
  `content/*-content.yml` (WHAT).
- [`7089812`](https://github.com/dataengy/MLInside-course/commit/7089812) — toolkit:
  pipeline/ingest/scan/publish + Prefect orchestration (`src/orchestration/`) +
  auto-versioned output names.
- [`e86d36d`](https://github.com/dataengy/MLInside-course/commit/e86d36d) — render:
  code panels, «Материалы» block bottom-right, larger fonts on list slides.
- [`faf62ef`](https://github.com/dataengy/MLInside-course/commit/faf62ef) — initial
  commit: MLInside dbt seminar rework (deck generators + docs).
