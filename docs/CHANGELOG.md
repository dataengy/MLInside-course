# CHANGELOG — MLInside-course

Canonical project changelog (finalize-issue passes migrate shipped work here).

## 2026-07-27 — Librarian: deferred iCloud ingest completed + ДЗ submodules

- iCloud recovered (downloads work again; upload-quota still exceeded) — all 647 evicted
  files materialized; **32 planned actions applied**: 9 decks (Семинар12/14 Airbyte 27/80MB,
  Практикум-по-dbt 76MB, dbt & Analytics Engineering, Docker/FastAPI, Kafka, VC),
  12 docs (лекции 3–4, семинары 1/2/4, ДЗ 5–6, ведомость), 3 archives (семинар-зипы,
  ДЗ 4-5), Dagster & Taipy recording + ДЗ images → media; 5+5 exact duplicates removed.
- **ДЗ 4-5 repos → submodules**: private archive mirrors
  [hnkovr/hse-dz45-dbt-project](https://github.com/hnkovr/hse-dz45-dbt-project) and
  [hnkovr/hse-dz45-clickhouse-hw](https://github.com/hnkovr/hse-dz45-clickhouse-hw)
  (upstream kre1ses/*, `ARCHIVE-NOTE.md` inside each) mounted at `data/code/`;
  originals removed from iCloud after HEAD verification (full snapshot kept in
  `data/archives/ДЗ-4-5,-вложения.zip`).
- librarian: catalog collapses git submodules to one summary row per repo.
- iCloud dir now holds only the `_MOVED-TO-REPO.md` marker + 2 junk tmp files —
  safe to delete entirely.

## 2026-07-20 — Deck generation skill + DE-tool lecture decks

- **New canonical skill** `create-preza-about-de-tool`
  (`~/.ai/skills/_catalog/docs/pptx/`) + sub-skills `preza-de-outline`, `preza-de-stamp`,
  `preza-de-validate`. Generates a Russian DE-tool lecture deck as a preza_gen content YAML
  and builds pptx+html. Deterministic scripts: `preza_schema.py` (schema SSoT),
  `resolve_slug.py`, `stamp_provenance.py`, `validate_content.py`, `build_deck.sh`,
  `port-skill-local.sh`. References: deck outline, content schema, visual profiles.
  All four pass the catalog authoring standard; registered in both INDEX files.
- **Project-local ports (both ways)** — `.claude/skills/<slug>/skill.md` as a **hardlink**
  (same inode as the catalog `SKILL.md`) and `.claude/skills-canonical/<slug>` as a **dir
  symlink**, each with a `NOTES.md` explaining the trade-off.
- **Three new decks** (visual profile `code-tables` — `code:` panels + `table:` comparisons,
  no `image:` keys, so they build with zero source assets):
  - `content/preza-dagster-content.yml` — **50 слайдов**: контекст/история/персоны
    (Ник Шрок, Elementl → Dagster Labs), все сущности (assets, ops/graphs/jobs, schedules,
    sensors, resources/IO managers, partitions, backfills, code locations, daemon/webserver/
    instance, asset checks, dg CLI + Components), dev vs prod, Dagster OSS vs Dagster+,
    dbt (сценарии интеграции, multi-dbt, кастомный translator), Airflow+Cosmos, SQLMesh,
    dlt и Airbyte, CLI и MCP, покупка со стороны Prefect (13.07.2026) и перспективы,
    конкуренты, мульти-оркестраторные ландшафты, ДЗ на базе dbt-задания.
  - `content/preza-prefect-content.yml` — **30 слайдов**: Jeremiah Lowin, Prefect 1→2→3,
    flows/tasks/deployments/work pools/blocks/results/artifacts/automations, dev vs prod,
    Prefect Cloud vs OSS, `prefect-dbt`, сравнение с Dagster и Airflow, сделка с Dagster, ДЗ.
  - `content/preza-cicd-observability-content.yml` — **40 слайдов**: CI/CD (GitLab CI +
    GitHub Actions + сравнение, `glab`/`gh`, self-hosted раннеры на VM и их безопасность,
    AI-тренды в CI) и Observability (три столпа, SLI/SLO, Prometheus/PromQL, Grafana,
    ELK vs Loki vs Victoria vs Thanos/Mimir, OpenTelemetry, Jaeger/Tempo, алертинг в
    Telegram/Mattermost, AIOps, MLOps drift + LLMOps evals/трейсинг), ДЗ.
  - `content/preza-apache-airflow-content.yml` — **40 слайдов**: контекст и история
    (Максим Бошмен, Airbnb 2014 → ASF → Airflow 2.0), архитектура (Scheduler/Worker/
    Webserver/метабаза, executors), DAG и операторы (TaskFlow API, сенсоры, провайдеры,
    dynamic task mapping), расписание и ETL (logical_date, catchup/backfill,
    идемпотентность, регулярный прогон dbt + Cosmos, сбор сырых данных, батч-прогнозы,
    Assets), передача данных (XCom и его ограничения, метаданные вместо датафреймов),
    обработка сбоев (retries/backoff, trigger rules, `on_failure_callback` → Telegram,
    SLA, зомби-задачи), сравнение с Dagster/Prefect, ДЗ на базе dbt-задания.
  - Сборка: `data/generated/MLInside_*_v1.{1,2}.{pptx,html}` → хардлинк в `~/Downloads`.
- **Policy** — `settings/config.yml → deck_generation`: `slides_min: 20`, `slides_max: 50`,
  `visuals_default: code-tables`, provenance marker; deck registry. Every deck carries a
  `model/harness/effort/version` stamp in the **first and last** speaker notes.
- **Justfile** — `preza-validate`, `preza-validate-all`, `preza-slug`, `preza-stamp`;
  `_dagster_content`/`_prefect_content`/`_cicd_obs_content` repointed to the new files.
- ⚠️ **Unreconciled**: earlier Codex-session drafts `content/preza-{dagster,prefect,
  cicd-observability}-v1-content.yml` (31/17/17 slides) remain uncommitted on disk. The two
  17-slide ones are below the 20-slide minimum. Left untouched — decide keep/archive.

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
