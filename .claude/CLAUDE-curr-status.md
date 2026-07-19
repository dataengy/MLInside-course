# CLAUDE-curr-status — MLInside-course

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
**CI/CD + Observability** (см. `docs/CHANGELOG.md`). Гейт: `just preza-validate-all`.

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

- ⛔ **iCloud заблокирован**: сеть (iPhone-hotspot) не достаёт `p219-content.icloud.com`,
  квота iCloud исчерпана (uploads висят 60ч, `brctl status`). Отсюда отложено:
  **~33 evicted-файла** (+Dagster mp4, Семинар12/14 pptx, зипы ДЗ) и **ДЗ-репо
  `dbt_project`/`clickhouse_hw` → submodules `data/code/`** (их `.git` тоже evicted).
  После починки: `brctl download` → `just librarian-plan "<iCloud root>" && just librarian-apply`.
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
