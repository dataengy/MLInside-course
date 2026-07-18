# CLAUDE-curr-status — MLInside-course

> Автогенерируемая часть (git/submodule/env/deck) — `just ctx` (см. «Как обновлять»).
> Обновлено: 2026-07-17. Ведётся **несколькими агентами** (Claude Code + Codex) в одном рабочем дереве.

## Кто и где работает (важно!)

Задача велась **параллельно в Claude Code и Codex** в одном worktree. Отсюда:
- версии колоды скачут (каждый билд бампит `_v3.N` — автоинкремент), контент при этом может быть идентичным;
- правки одних и тех же файлов из двух агентов → **перед правкой всегда перечитывай файл с диска**, не доверяй контексту.

Свежие Codex-сессии: `~/.codex/sessions/2026/07/17/rollout-2026-07-17T01-45-*.jsonl`, `…T01-11-*.jsonl`.

## Последние 3 завершённые задачи

1. **`e4736e7`** — Phase D: генератор вынесен в сабмодуль **`hnkovr/preza_gen`** → `src/preza_gen`;
   контент переехал в **`content/`** (`build_deck_v3-settings.yml` = HOW, `preza-dbt-v3-content.yml` = WHAT).
2. **`7089812`** — тулкит: `pipeline/ingest/scan/publish` + **Prefect-оркестрация** (`src/orchestration/`) + авто-версии имён.
3. **`e86d36d`** — рендер: код-панели, блок «Материалы» → правый нижний угол, крупный шрифт на слайдах-списках.

## Текущее состояние

**Колода:** 48 слайдов · 13 код-слайдов · 16 картинок · 7 таблиц.
Сборка: `data/generated/MLInside_Введение-в-dbt_v3.N.{pptx,html,pdf}` → хардлинк в `~/Downloads`.
В TG (топик 118) последним уходил **v3.4** (43 слайда) — **новые 48-слайдовые версии ещё не отправлялись**.

**Окружение:** LibreOffice 26.2.4 (`soffice`) + poppler (`pdftoppm`) установлены → доступен
честный QA: `pptx → pdf → png` настоящими шрифтами (qlmanage даёт serif-фолбэк — **не баг колоды**).
Диск: ~3.4Gi свободно (79% занято) — **узкое место**, уже ловили `ENOSPC`.

## Незакрытое (последние 2 рабочих дня)

- ⚠️ **Незакоммиченная работа Codex в сабмодуле** `src/preza_gen` (` m` в `git status`):
  `build_deck.py`, `pipeline.py`, `pyproject.toml`, `renderers/{html,pdf,pptx}.py`, `README.md`,
  `examples/settings.example.yml` + новые `preza_refactoring/`, `tests/test_layout.py`, `tests/test_pdf.py`.
  Среди них — **soffice→pdf** в `renderers/pdf.py` (`soffice_path()`, `_render_with_soffice()`) и
  `_fit_code_box()` в `pptx.py` (компактные код-панели). **Нужен коммит+пуш в сабмодуле, затем бамп указателя.**
- ⚠️ Незакоммичено в курсовом репо: `content/*.yml` (+5 код-слайдов, 43→48), `src/tests/test_content.py`,
  `Justfile`, `.tmp/*`.
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

1. Закоммитить+запушить сабмодуль `hnkovr/preza_gen`, бампнуть указатель в курсовом репо, затем коммит курсового.
2. Прогнать `just check` + честный QA (`.tmp/render_pdf_pages.py`) по 48-слайдовой колоде.
3. Отправить актуальную версию в TG-топик 118 (там всё ещё v3.4/43 слайда).
4. Почистить `.bak1`, `egg-info/`, `~$*` lock-файлы; следить за диском.

## Как обновлять

Детерминированная часть — скриптом (см. `scripts/ctx-snapshot.*` / `just ctx`), а не руками:
git-лог, submodule-статус, факты колоды, версии инструментов, диск, следы Codex/Claude-сессий.
