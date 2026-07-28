# CLAUDE-curr-status — MLInside-course

## Session 2026-07-27/28 — schedule-sheet reader + `/preza-review` (committed, NOT pushed)

**Shipped** (5 commits `547b499..7765d86` here + `a8ad588` in `~/.ai`):

- `integrations/google/sheets/` — first `integrations/` dir. `connector.py`/`utils.py`/`__init__.py`
  **hardlinked** from `~/pdp.deploy_dev/scripts/tools-utils/gsheets` (registry:
  `~/.ai/integrations/_relink-actualized.py`). Editing them changes pdp too — re-link with
  `ln -f` after any editor save. Project-owned `auth.py` = ADC-first branch.
- `src/schedule/` — `python -m schedule {tabs,dump,plan,show}`; `content/presentations.yml`
  seeded by hand with the 5 decks. `just gsheet-*` / `presentations-*` / `preza-review*`.
- `/preza-review` — catalog skill + `create-preza-about-de-tool/scripts/review_content.py`;
  tunables in `preza-review/settings/review.yml`. Reports → `docs/reviews/`.

**⚠️ BLOCKER — the accent axis is untested.** `just gsheet-tabs` needs Application Default
Credentials. Two `gcloud auth application-default login --account=hnkovr@gmail.com` runs were
started and both stopped before consent, so `~/.config/gcloud/application_default_credentials.json`
does not exist. gcloud **forces** `cloud-platform` into the scope list (a sheets-only list is
rejected), and `print-access-token --scopes=…sheets` cannot mint one non-interactively.
Alternative that needs no gcloud login: share the sheet with
`gsheets-reader@for-prodamus-1-494316.iam.gserviceaccount.com` and add this repo to that
account's `projects:` in `~/.ai/settings/gcloud.yml`.
Next: `just gsheet-tabs` → `gsheet-dump` → write `settings/gsheet.yml` with the real headers →
`just presentations-plan` → `just preza-review-all`.

**⚠️ PUSH BLOCKED — needs a decision.** 8 commits ahead on protected `main`:
- the tracker gate marks all 8 unbound (this repo has never used tracker refs);
- pushing carries the parallel session's 3 picstore commits along with mine.

**Parallel-session collision (resolved, worth knowing).** `ffab5c2` committed a `Justfile` newer
than the copy on disk; committing the working copy would have deleted three `picstore-*` recipes.
It also appended a **second** picstore block without removing the first → duplicate `_picstore`
variable + duplicate recipes → `just` refused to parse *anything*. `c1b267a` restores their
version, re-applies my recipes and removes the redundant block (all 10 unique picstore recipes
kept). **Lesson: re-read the Justfile from disk and run `just --list` before every commit here.**

**Known-red:** `just preza-review content/preza-dbt-v3-content.yml` exits 1 — that deck has no
provenance stamp in its first/last notes (pre-existing; it is the one deck excluded from
`preza-validate-all`). Fix with `just preza-stamp`.

**Left uncommitted on purpose:** `.ai/.codex/`, `.tmp/.last-review-nudge`, the three
`content/preza-*-v1-content.yml` Codex drafts, `src/preza_gen.egg-info/` (wants gitignoring),
`src/picstore` submodule pointer.

## Interrupted Task

> Interrupted: 2026-07-27 — resume with: `claude --resume 799821fd-9e53-4233-b48d-7962c4feaacb`

**Task:** три задачи по колодам (dbt / Dagster / Prefect / CI/CD+Observability / Airflow),
каждая с директивой «предложи скрипт/скилл + `/save-all-deterministic-for-skill-as-scripts` + code standards + хуки при необходимости»:

1. **Отправить последнюю версию каждой колоды в Telegram** (топик MLInside 118, `~/.ai/scripts/telegram/tg-send-file.sh`, чат `-1002281796095`).
2. **Заархивировать все НЕпоследние версии** в `.archive/` внутри их исходного пути (`data/generated/.archive/`).
3. **Убедиться, что весь сгенерированный контент в git через git-LFS.**

**Reached (обследование готово, ничего ещё не сделано):**
- `data/generated/` содержит 26 файлов, но **целиком в `.gitignore`** (строка 20) → ничего не трекается.
- `.gitattributes`: есть LFS-правила для pptx/pdf/mov/key/mp4/zip/docx/xlsx — **нет правила для `*.html`**.
- Последнее в TG (топик 118) уходило **v3.4** dbt; на диске **v3.13**.

**⚠️ БЛОКЕР — по каждому сюжету на диске ДВЕ конкурирующие семьи колод (мои vs Codex-сессии):**

| сюжет | Codex-билд | мой билд (совпадает с закоммиченными content/) |
|---|---|---|
| Dagster | `MLInside_Dagster_v1.4` | `MLInside_Современная-оркестрация-ML-пайплайнов-Dagster_v1.2` |
| Prefect | `MLInside_Prefect_v1.1` | `MLInside_Современная-оркестрация-ML-пайплайнов-Prefect_v1.2` |
| CI/CD | `MLInside_CICD_Observability_v1.1` | `MLInside_Автоматизация-и-мониторинг-CICD-Prometheus-Grafana_v1.2` |
| Airflow | — | `MLInside_Оркестрация-данных-Apache-Airflow_v1.1` |
| dbt | — | `MLInside_Введение-в-dbt_v3.13` |

Наивный «max version per name» отправит ОБЕ Dagster-колоды, и Codex-овская v1.4 > моей v1.2 (но это 31-слайдовый черновик). **Нужно решение пользователя, какая семья каноническая, ПЕРЕД отправкой/архивацией.**

**Remains:**
- Получить решение по конкурирующим семьям (это тот же незакрытый вопрос про `preza-*-v1-content.yml`).
- Реализовать 3 задачи скриптами (предложить: `deck-publish-latest.sh`, `deck-archive-old.sh`, git-LFS через существующий скилл `git-lfs-setup` + un-ignore `data/generated/` с LFS для html).
- ⚠️ **DISK-CRITICAL: 4Gi свободно** — писать осторожно, LFS-добавление больших файлов может упасть.

**Resume CLI:**
```bash
claude --resume 799821fd-9e53-4233-b48d-7962c4feaacb
```

---

> Автогенерируемая часть (git/submodule/env/deck) — `just ctx` (см. «Как обновлять»).
> Обновлено: 2026-07-19. Ведётся **несколькими агентами** (Claude Code + Codex) в одном рабочем дереве.

## Кто и где работает (важно!)

Задача велась **параллельно в Claude Code и Codex** в одном worktree. Отсюда:
- версии колоды скачут (каждый билд бампит `_v3.N` — автоинкремент), контент при этом может быть идентичным;
- правки одних и тех же файлов из двух агентов → **перед правкой всегда перечитывай файл с диска**, не доверяй контексту.

Свежие Codex-сессии: `~/.codex/sessions/2026/07/17/rollout-2026-07-17T01-45-*.jsonl`, `…T01-11-*.jsonl`.

## Последние 3 завершённые задачи

1. **`077da45`** (2026-07-19) — **Librarian-ингест**: iCloud `_2025-11-ВШЭ_ВНЕШНЕЕ_ОБУЧЕНИЕ` +
   dbt-материалы из `~/Downloads` + бывший `assets/` → `data/` (46 перемещений: 11 текущих дек +
   21 в `.history/`, 13 docs, 2 записи; sha256-дедуп, 16 точных дублей удалено из iCloud,
   маркер `_MOVED-TO-REPO.md`); `data/CATALOG.md` + `data/reviews.yml`; git LFS (~800MB).
2. **`2645a9a`** (2026-07-19) — сабмодуль **`hnkovr/librarian`** → `src/librarian`
   (dedupe/categorize/version-stack/catalog, 24 теста) + `just librarian-*` + `docs/data-structure.md`.
3. **`f3d8ca4`@preza_gen** — закоммичена и запушена вся WIP-работа Codex в сабмодуле
   (soffice-pdf, `_fit_code_box`, preza_refactoring) + пути `assets/` → `data/decks/`.

## Текущее состояние

**Новое (2026-07-20): генератор дек по DE-инструментам.**
Канонический скилл `create-preza-about-de-tool` (+ саб-скиллы `preza-de-outline`/`-stamp`/`-validate`)
в `~/.ai/skills/_catalog/docs/pptx/`; в репо проброшен **двумя способами** —
хардлинк `.claude/skills/<slug>/skill.md` и симлинк-директория `.claude/skills-canonical/<slug>`
(в каждом `NOTES.md` с объяснением). Детерминированные скрипты: `validate_content.py`,
`stamp_provenance.py`, `resolve_slug.py`, `build_deck.sh`, `port-skill-local.sh`.
Политика в `settings/config.yml → deck_generation` (20..50 слайдов, профиль `code-tables`,
штамп `model/harness/effort/version` в заметках первого и последнего слайда).
Новые деки: **Dagster — 50 слайдов** (25 код-панелей, 10 таблиц), **Prefect — 30**,
**CI/CD + Observability — 40**, **Apache Airflow — 40** (см. `docs/CHANGELOG.md`).
Гейт: `just preza-validate-all` (4 деки, все зелёные).

⚠️ **Требует решения:** на диске лежат незакоммиченные черновики прошлой Codex-сессии
`content/preza-{dagster,prefect,cicd-observability}-v1-content.yml` (31/17/17 слайдов).
Два из них **ниже минимума в 20 слайдов**. Justfile перенаправлен на новые файлы;
черновики **не тронуты** — нужно решить: оставить, слить или отправить в `.stash/`.

**Колода (dbt):** 48 слайдов · 13 код-слайдов · 16 картинок · 7 таблиц.
Сборка: `data/generated/MLInside_Введение-в-dbt_v3.N.{pptx,html,pdf}` → хардлинк в `~/Downloads`.
В TG (топик 118) последним уходил **v3.4** (43 слайда) — **новые 48-слайдовые версии ещё не отправлялись**.

**Окружение:** LibreOffice 26.2.4 (`soffice`) + poppler (`pdftoppm`) установлены → доступен
честный QA: `pptx → pdf → png` настоящими шрифтами (qlmanage даёт serif-фолбэк — **не баг колоды**).
Диск: ~3.4Gi свободно (79% занято) — **узкое место**, уже ловили `ENOSPC`.

## Незакрытое (последние 2 рабочих дня)

- ✅ **iCloud-ингест ЗАВЕРШЁН (2026-07-27)**: все evicted-файлы скачаны и перенесены
  (32 действия: Семинар12/14, Практикум-по-dbt 76MB, лекции/ДЗ/зипы, Dagster mp4);
  ДЗ-репо → приватные зеркала `hnkovr/hse-dz45-{dbt-project,clickhouse-hw}` + submodules
  `data/code/`. В iCloud остался только маркер + 2 tmp-мусора — папку можно удалять.
  (upload-квота iCloud всё ещё исчерпана — на нас не влияет.)
- ⚠️ `just typecheck` — 22 pre-existing диагностик в `preza_gen/preza_refactoring` (lint/тесты зелёные, 49 passed).
- ⚠️ v6-дека: метаданные автора не очищены; `dbt-final-verify` завязан на v4-снапшот (см. `data/reviews.yml`).
- 🐞 **Пофикшен overflow код-панелей** (в сабмодуле, тоже незакоммичено): `_fit_code_box` считал
  **логические** строки, а длинные строки **переносятся** → код вылезал за пределы панели
  (на «dbt_utils в деле» обрезался `{% endif %}`). Теперь: `_visual_lines`/`_code_height` учитывают
  перенос, `_fit_code_size` **уменьшает шрифт** (13 → до `min_size: 9`), пока обёрнутый текст не влезет.
  `_CHAR_W_EM = 0.72` — worst-case ширина моноширинного глифа (LibreOffice подставляет шрифт шире
  Consolas; замер по реальной панели). Тесты: `src/preza_gen/tests/test_layout.py` (+3 регрессии).
  Ужимаются 2 слайда: «Инкрементальная модель», «dbt_utils в деле» → 12.5pt.
- 🧹 Мусор: `content/preza-dbt-v3-content.yml.bak1`, `src/preza_gen.egg-info/`,
  `~$*.pptx` (lock-файлы открытого PowerPoint) в `data/generated/` и `assets/decks/`.
- ⛔ **Task #1** — GitHub projects/issues для MLInside-course & preza_gen: заблокировано gh-идентичностью,
  handoff-скрипт `.tmp/create-github-issues.sh` (запускает пользователь).
- 📋 Бэклог: `.ai/tasks/0001-pdf-weasyprint`, `0002-pdf-chromium` (**частично закрыты** soffice-путём),
  `0003-mle-content`, `0004-prefect-and-claude-move`.

## Полезные скрипты

| Скрипт | Что делает |
|---|---|
| `.tmp/render_pdf_pages.py` | pptx→pdf→png выбранных страниц (**честный** QA через LibreOffice+poppler) |
| `.tmp/audit_code_slides.py` | плотность код-слайдов и итоговая раскладка (side/full) |
| `.tmp/render_slides.py` | qlmanage-превью слайда (быстро, но **serif-фолбэк**) |
| `.tmp/verify_deck.py`, `extract_source.py` | проверка колоды / извлечение текста исходника |

## Следующие шаги

1. Починить iCloud (сеть/квота) → дозагрузить evicted-файлы (#8), затем ДЗ-репо → submodules (#5).
2. Честный QA (`.tmp/render_pdf_pages.py`) по 48-слайдовой колоде; TG-топик 118 (там всё ещё v3.4).
3. Очистка метаданных v6 + перевод `dbt-final-verify` на конфиг; типчек preza_refactoring.
4. Рассмотреть `docs/data-structure.md` (per-course nesting, link-stubs для >100MB записей).

## Как обновлять

Детерминированная часть — скриптом (см. `scripts/ctx-snapshot.*` / `just ctx`), а не руками:
git-лог, submodule-статус, факты колоды, версии инструментов, диск, следы Codex/Claude-сессий.
