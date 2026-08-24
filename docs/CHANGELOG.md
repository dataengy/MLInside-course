# CHANGELOG — MLInside-course

Canonical project changelog (finalize-issue passes migrate shipped work here).

## 2026-08-25 — Транзиентные отказы Google больше не пишутся как настоящие ([#6](https://github.com/dataengy/MLInside-course/issues/6))

- Живьём поймано: чтение листа упало на **503**, немедленный повтор прошёл. До этой правки
  такой чих записался бы в git-tracked `published.legs` как `error`, а прогон вышел бы с
  ненулевым кодом из-за икоты датацентра.
- **`publisher/gapi.py`** — единственная точка, где просят ретрай: `gapi.run` передаёт
  `num_retries` (в клиенте уже есть рандомизированный экспоненциальный backoff), `gapi.call`
  оборачивает помощники чтения из hardlink-модуля `~/.ai`, куда `num_retries` не пробросить.
  Все 13 вызовов ленты переведены на них. Ретраятся ТОЛЬКО 429/500/502/503/504 — 403
  (квота/права) и 404 падают сразу, иначе повтор лишь оттягивает сообщение о том, что
  чинить человеку. Количество — `api.retries` в `settings/publish.yml`.
- `errors.py`: последним правилом — «транзиентное пережило все ретраи → просто повторить
  прогон». Тесты: 261 passed, 4 skipped (+13).

## 2026-08-22 — Репетиция записи в лист по живым данным + отказы, переведённые в действие ([#6](https://github.com/dataengy/MLInside-course/issues/6))

- **Лист-лег отрепетирован на настоящем листе** (чтение работает, запись ещё нет):
  таб `Sheet1`, колонка темы **B** («название»), три новых колонки встанут в **E/F/G**,
  четыре деки находят строки 5/6/7/9, Prefect и OGIP — без строки (законный `skipped`).
  Совпало с офлайн-реконструкцией; первая живая запись сюрпризов не несёт.
- **`.tmp/probe_google_access.py` переписан в единую проверку ворот** — по лентам:
  чей Drive и сколько места, папка, чтение листа, `canEdit`, и та самая репетиция.
  Конфиг тянется из `publisher.settings`, поэтому проба не может разъехаться с лентой.
- **`publisher/errors.py`**: каждый реальный отказ этой ленты был политикой в одежде
  API-ошибки. Теперь к ошибке спереди подставляется действие («место, а не права —
  расширить квоту», «выдать роль Редактор», «перелогинить ADC», «включить API в
  quota-проекте»), оригинал сохраняется. Хинт уезжает и в `published.legs`, так что
  git-запись остаётся самообъяснимой. Тесты: 248 passed, 4 skipped.

## 2026-08-20 — Google-запись открыта: две ленты кредлов, Drive-папка создана ([#6](https://github.com/dataengy/MLInside-course/issues/6))

- **Найдено, что именно блокировал экран согласия**: `spreadsheets` — *sensitive*-скоуп, и
  gcloud-клиент на нём получает «This app is blocked» ровно так же, как на restricted
  `drive`. Тот же `adc-login` **без** `spreadsheets` прошёл с первого раза → ADC-файл с
  долгоживущим refresh-токеном есть.
- **Отсюда две ленты кредлов** (`PublishConfig.lane` / `auth.get_service` выбирают по API):
  Drive ← user-ADC `hnkovr@gmail.com` (`drive.file`), лист ← сервис-аккаунт
  `gsheets-reader@…` (`spreadsheets`). Список `auth.scopes` теперь обязан совпадать с
  выданным: google-auth роняет `RefreshError`, если запрошенный скоуп не выдан.
- **Quota-project** вешается на кредл (`with_quota_project`), а не на ADC-файл: Drive API
  отказывает user-ADC без quota-проекта, а машинный ADC (`stambul-tts`, Drive API выключен)
  используют другие проекты — его настройку не трогаем.
- **Drive-папка создана**: «MLInside 2026 — decks» (`drive.folder_id` в `settings/publish.yml`).
- **Осталось два внешних условия**: место на Drive `hnkovr@gmail.com` (98.69 GiB при лимите
  15 — аплоад отвечает `storageQuotaExceeded`; владелец расширяет квоту) и роль **Редактор**
  для `gsheets-reader@for-prodamus-1-494316.iam.gserviceaccount.com` на листе расписания
  (сейчас Viewer, `canEdit=false`).

## 2026-08-20 — Нагающий хук перестал противоречить сам себе ([#6](https://github.com/dataengy/MLInside-course/issues/6))

- `deck-publish-status.sh` печатал «не опубликованы свежие версии: … v3.14 (издано: 3.14)» —
  версия совпадает, а хук ругается: он валил в одну строку два разных состояния. Теперь
  раздельно: **⚠ собрано новее опубликованного** (нужен полный `just publish-new`) и
  **ⓘ версии актуальны, не завершены леги drive+sheet** (нужен ретрай именно этих легов;
  хук печатает готовую команду с `--only`). Незавершённые леги группируются по набору,
  так что шесть дек с одинаковым хвостом дают одну строку, а не шесть.
- Статусы `ok`/`skipped` считаются закрытыми (`skipped` — легитимный исход для лекций без
  строки в листе), источник статуса — курсор, иначе git-tracked `published.legs`.

## 2026-08-19 — Лист читается штатным API; TG-лег отработал вживую ([#6](https://github.com/dataengy/MLInside-course/issues/6))

- **Найден настоящий блокер google-ленты**: рецепты звали системный `python3` без
  `google-api-python-client` — падение на импортах ДО всякой авторизации (поэтому и
  первый дамп пришлось делать через Drive-коннектор). Все google-рецепты переведены на
  `uv run --extra gsheets python`. Итог: `just gsheet-tabs` → `Sheet1`, `just gsheet-dump`
  → настоящий `fetch_raw` (лист `mlinside-mlops`, locale en_US) через сервис-аккаунт,
  **без браузера**. Оговорка про Drive-коннектор снята; отличие реального дампа от
  реконструкции ровно одно — перенос строки в ячейке лекции по ClickHouse (не наша).
  `mapping.tab` запинен в `Sheet1`.
- **Пересинк на реальных данных подтвердил контракт**: `just presentations-plan` (+0/~1/3
  stale) сохранил `published:`-блоки нетронутыми; `preza-review-all` — dbt/Dagster/CI-CD
  по-прежнему **4/4** каждый.
- **TG-лег отработал вживую**: 6 дек (dbt v3.14 · 52, Dagster v1.3 · 51, CI/CD v1.3 · 42,
  Airflow v1.1 · 40, Prefect v1.2 · 30, OGIP v1.2 · 31) — текст + файл в топик 118.
  Повторный прогон: «already ok» по всем шести, дублей нет.
- **Запись пока закрыта**: у обоих сервис-аккаунтов `canEdit=false`, ADC-консент не добит.
  Полный `.../auth/drive` — restricted, gcloud-экран отвечает «Приложение заблокировано»;
  перешли на `drive.file` (не-чувствительный, покрывает свои папку и файлы). Добавлена
  SA-лента в `publisher.auth` как безбраузерный запасной путь для колонок листа.

## 2026-08-18 — Deck publish pipeline: TG + GDrive (вечный URL) + колонки листа ([#6](https://github.com/dataengy/MLInside-course/issues/6))

- **`src/publisher/`** (`just publish-new{,-dry}`, `publish-status`, `publish-init-drive`):
  detect по `data/generated/*_v{maj}.{min}.pptx` → **drive** (`files().update` того же
  fileId — URL на предмет вечный; adopt-by-name при потере курсора; шаринг anyone_reader
  идемпотентно) → **tg** (`tg-project-inform` + `preza_gen.publish`→топик 118, гард 49MB)
  → **sheet** (живой резолв таба; колонки «pptx (GDrive)»/«версия»/«слайдов» дозаводятся
  идемпотентно; строка по `mapper.normalize`; один `batchUpdate`). Леги изолированы,
  ретрай только не-ok (TG не шлётся дважды); курсор `data/.state/deck-publish-state.json`
  + git-tracked `published:`-блок в `presentations.yml` (сид свежего клона — без
  повторных отправок). Триггер только явный: билдер мятит новую minor каждым билдом.
  Захардкоженный dbt-only `just send`/`build-send` удалён, `publish` перенаправлен.
  SessionStart-хук `deck-publish-status.sh` нагает про неопубликованное. 43 теста
  (моки, без сети), suite 251 зелёный. Spec:
  [`docs/deck-publish-pipeline.md`](deck-publish-pipeline.md).
- **Транспорт**: user-ADC hnkovr@gmail.com c write-скоупами drive+spreadsheets (токен-кэш =
  ADC-файл). OAuth-токен AGD-gen мёртв (`invalid_grant`, Testing-status 7-day expiry);
  SA отпал (нет storage-квоты на Drive у личного аккаунта). **Починен корневой баг
  ADC-ленты**: `just` не имеет именованных args — `adc-login account=X` кормил gcloud
  `--account="account=X"`, каждый консент ломался
  ([hnkovr/.ai#8](https://github.com/hnkovr/.ai/issues/8), fix запушен в ~/.ai
  `de2c45b`); write-скоупы закреплены в дефолтах `reset-google-account-creds`.
- **Отложено до консента** (браузерный ADC-логин не добит): живой прогон — smoke,
  `publish-init-drive` (реальный folder_id), первая публикация OGIP → все деки, пин
  имени таба. Чек-лист — в спеке.

## 2026-08-16 — Accent axis live: GSheet тезисы → accents → 12/12 hit ([#3](https://github.com/dataengy/MLInside-course/issues/3), [#4](https://github.com/dataengy/MLInside-course/issues/4))

- **Рубрика приехала с листа**: `settings/gsheet.yml` (полная карта колонок — loader замещает
  дефолт целиком; «тезисы»→accents; «старая запись» сознательно не мапится в `n`),
  `mapper.split_accents` научился резать нумерованные абзацы (`accents_split_numbering`,
  регэксп `_NUMBERED_ITEM`, юнит-тест), topic dbt-записи переименован в точное «название»
  листа — upsert матчится без дублей. Итог `just presentations-plan`: 4 updated / 4 added
  (чужие лекции, `content: null`) / 3 stale (Prefect, внешний Airflow, OGIP).
  Транспорт первого дампа — claude.ai Drive-коннектор (ADC-консент не добит; после
  `adc-login` пересинк = `just gsheet-dump && just presentations-plan`); формат дампа —
  штатный `fetch_raw`, остальная лента — штатный код. Spec:
  [`docs/schedule-gsheet-lane.md`](schedule-gsheet-lane.md).
- **Целевые правки трёх дек под 12 акцентов** (все — hit, 0 error/0 warn;
  [`docs/reviews/`](reviews/)): dbt 51→**52** слайда (новый `052-sloi-dbt-proekta`
  sources→staging→marts; Analytics-Engineering-буллет на 004; качество данных на 028;
  инкрементальность-в-ClickHouse на 018 — дека рукописная, без штампа); Dagster 50→**51**
  (новый `051-ml-pajplajn-kak-cepochka-assetov` Загрузка→Препроцессинг→Обучение→Валидация;
  SDA-vs-Airflow на 009; фабрики ресурсов на 016; lineage в notes 012; штамп v1.1);
  CI/CD+Obs 40→**42** (новые `051-sborka-docker-obraza-v-ci` и
  `052-fastapi-instrumentaciya-prometheus` RPS/latency/5xx; бизнес-метрики на 034;
  Telegram/Slack на 027; штамп v1.1). `slides_max` 50→55. Пересборка: dbt v3.14,
  Dagster v1.3, CICD v1.3.
- **Закрыта [.ai/tasks/0006](../.ai/tasks/.done/0006-review-accents-axis.md)** — акцентная
  ось прогнана на живых данных; `hit_ratio: 0.75` подгонки не потребовал (лексика акцентов
  повторена в деках буквально). Наш Airflow-дек — 3/4 (лекция Влада, вне скоупа).
- **Обвязка**: SessionStart-хук `scripts/hooks/preza-accents-status.sh` (лента не
  настроена / sheet-matched дека без акцентов); проектный суб-агент
  `.claude/agents/preza-accents-keeper.md`; память + `~/.ai/projects/MLInside-course/`;
  скилл `preza-review` дополнен разделом про синк-ленту и заново захардлинкен
  (каталог=глобал=репо, один инод).

## 2026-08-11 — Secrets sync + workstation bootstrap; Olist homework wired in

- **Secrets sync, two lanes** (`scripts/secrets-sync.sh`, `just secrets-*`, runbook
  [`docs/secrets-sync.md`](secrets-sync.md)): Bitwarden secure notes as transport
  (`secrets-push`/`secrets-pull`, plus base64 file notes for service-account JSONs and the
  GPG key itself) and git-secret as the in-repo fallback — `settings/.env.secrets.secret`
  (GPG, recipient hnkovr@gmail.com) is committed, plaintext never is.
  `settings/.env.secrets.template` is the blank-value names contract;
  `just secrets-doctor` flags template drift and missing file-typed secrets.
  New workstation = `git clone --recurse-submodules` → `just secrets-bootstrap`.
- **Origin access repaired**: github.com/dataengy/MLInside-course is a PRIVATE repo under
  the `dataengy` account; hnkovr (the keychain identity that pushes) had lost access —
  reads 404'd, which looked like a deleted repo. Fixed by re-inviting hnkovr as
  collaborator (admin) via the dataengy gh keyring account and accepting the invite.
  The failure mode and repair are recorded in the `workstation-bootstrapper` agent.
- **`workstation-bootstrapper` agent** (`.claude/agents/`) — owns the "whole repo
  committed, pushed, reproducible on a new workstation" invariant: worktree/submodule/
  clone inventory, submodules-first push order, secrets lanes, origin-access repair.
- **SessionStart hook** (`scripts/hooks/repo-sync-status.sh`, `.claude/settings.json`) —
  prints ahead/behind, dirty count, submodule gitlink drift and secrets staleness
  (`.env.secrets` newer than its `.secret` blob) at session start; fail-open, offline.
- **Olist homework submodule** — `homework/mlinside-hw-olist`
  ([hnkovr/mlinside-hw-olist](https://github.com/hnkovr/mlinside-hw-olist)) recorded in
  `.gitmodules`; `docs/data-structure.md` documents why `homework/` lives outside
  librarian's `data/` tree.
- **Deck content**: dbt-v3 deck gains the Olist ДЗ section; Dagster deck ДЗ reworked to
  the Olist orchestration skeleton; three new deck sources committed
  (`preza-dagster-v1`, `preza-prefect-v1`, `preza-cicd-observability-v1`).
  `.ai/.codex/skills/` ports the five de-tool deck skills for Codex parity.

## 2026-07-28 — Foreign-deck import + unfinished-deck detection

- **`just preza-import-pptx <pptx>`** (`pptx_to_content.py`, beside `review_content.py`) — imports
  a deck this repo did not generate into a review-shaped content YAML under `content/imported/`.
  Lossy and one-way: layout, theme and picture bytes are dropped; only what the reviewer searches
  survives. Never build from the result. All scalars in `review.yml → pptx_import`.
- **`generated: false`** on a plan entry marks a deck the course did not generate. Its missing
  `— Сгенерировано:` stamp is demoted to `info` instead of failing the run — the alternative was
  stamping a hand-authored deck with an authorship that never happened. Every other schema error
  still fails. Applied to the hand-authored dbt deck (its 2 long-standing errors are now info)
  and to the imported Airflow deck.
- **Unfinished-deck detection** — titles still carrying outline scaffolding (`Слайд 28: …`,
  `TODO`, `WIP`) are an **error**; verbatim-repeated slides a warning. Scanned across `title` and
  `bullets`, since a long heading lands in bullets. Patterns: `review.yml → draft_scaffolding`,
  one SSoT shared by the reviewer and the importer.
- **Lecture 5 Airflow deck** (`data/decks/5_Оркестрация_данных_Apache_Airflow.pptx`, ingested by
  librarian) reviewed: 43 slides, **10 placeholder slides** (30, 34–42), slide 40 a verbatim dupe
  of 39, **zero speaker notes**. Whether it supersedes or complements our generated Airflow deck
  is an open decision — [`.ai/tasks/0005`](../.ai/tasks/0005-airflow-external-deck.md). Its file
  author is **Любовь**, same as `1_`/`2_` in `data/decks/` — a colleague's deck from the same
  numbered course series.
- Three bugs found and fixed while wiring this up: the scaffolding scan missed a placeholder that
  the 120-char title rule had pushed into `bullets`; stringifying preza_gen's nested-bullet form
  `["текст", 1]` made a finished dbt slide read as scaffolding; and the importer wrote
  `code_caption` while the reviewer counts `code`, so a deck with 16 code panels reported 0.
  Monospace frames now become real `code:` blocks (font list kept in sync with librarian's).
  The first two are covered by tests.
- **Tracker policy recorded globally**: this repo binds to **GitHub Issues only** — "JT" here
  means a GH Issue, never a Jira task. Written to `~/.ai/skills/settings/tracker_binding.yml`
  (`projects.MLInside-course`), `docs_standards.yml` (`jt_title.term_resolution` + a
  `github_issue` link pattern), `~/.ai/docs/tracker-binding.md`, the `tracker-hygiene-keeper`
  agent, `/smart-commit`, `/open-all-mentioned-jts`, and project memory.
- `src/*.egg-info/` gitignored. Backlog: [`0005`](../.ai/tasks/0005-airflow-external-deck.md),
  [`0006`](../.ai/tasks/0006-review-accents-axis.md) (accent axis still never run on real data).

## 2026-07-27 — Course schedule sheet reader + `/preza-review`

- **`integrations/google/sheets/`** — first `integrations/` dir in this repo. `connector.py`,
  `utils.py`, `__init__.py` **hardlinked** from `~/pdp.deploy_dev/scripts/tools-utils/gsheets`
  (registered in `~/.ai/integrations/_relink-actualized.py`; same inode, nlink 3). Deliberately
  not linked: `pnf/` (Jira/Tempo-specific), the upstream Justfile, `gc-setup-sa.sh`.
  Project-owned `auth.py` adds an **ADC-first** branch — the course sheet belongs to a personal
  Google account, so the registry's Prodamus service account cannot read it. New `gsheets` extra.
- **`src/schedule/`** — `python -m schedule {tabs,dump,plan,show}`: schedule sheet →
  `settings/schedule.yml` (generated, verbatim) → `content/presentations.yml` (curated). The
  upsert overwrites sheet-sourced fields only; `content:`/`out_name:`/`visuals:` and hand-added
  keys survive, entries that leave the sheet are reported and kept. Column mapping is
  header-driven config (`settings/gsheet.yml`), not code.
- **`/preza-review`** (`~/.ai/skills/_catalog/docs/pptx/preza-review/`, script beside
  `validate_content.py`) — scores a deck on two axes: accent coverage against the lecture's
  `accents:` (✅ hit / 🟡 partial / ❌ missing, with slide numbers) and the canonical 12-section
  DE-tool outline, plus notes/table/code/materials density. Writes
  `docs/reviews/<out_name>.{md,findings.yml}`; a missing must-have accent exits non-zero.
  All thresholds/keywords/stopwords in `settings/review.yml`.
- `content/presentations.yml` seeded by hand with the five existing decks so the reviewer works
  before the first sheet sync; the upsert adopts them by topic when the numbered rows arrive.
- Justfile: `gsheet-tabs`, `gsheet-dump`, `presentations-plan[-dry]`, `presentations-show`,
  `preza-review`, `preza-review-all`; `sync` now pulls the `gsheets` extra.
- Known: the dbt deck reviews with 2 errors — it has no provenance stamp (pre-existing; it is
  the one deck excluded from `preza-validate-all`). Its `visuals: reuse-source` is recorded in
  the plan so image slides are no longer mis-flagged.

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
