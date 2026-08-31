# `.tmp/` — dev/QA helper scripts for the deck generator

Throwaway-but-reusable scripts used while building/checking the `preza_gen` decks. Not part of the
package (`src/preza_gen/`); safe to delete. Run via the local Justfile from the **repo root**.

## Scripts
| Script | What it does |
|--------|--------------|
| `verify_deck.py` | Counts slides/images/notes/materials, note-emphasis runs (bold/underline/italic), checks no author strings. |
| `render_slides.py` | Moves chosen 1-based slides to the front of a throwaway copy and `qlmanage`-renders each to PNG (qlmanage only thumbnails slide 1). |
| `render_pdf_pages.py` | Renders selected pages from the LibreOffice-produced PDF with Poppler: the authoritative visual QA path. |
| `lint_content_scalars.py` | Ловит значения контент-YAML, которые YAML разобрал как мапу/число вместо строки (буллет или ячейка с двоеточием без кавычек). Схема-валидатор и `preza-review` это пропускают — падает только билд. |
| `audit_code_slides.py` | Reports code length, bullets and resulting side/full layout for each code slide. |
| `publish` | Build the deck, open the newest version locally, then send it to Telegram. |
| `contact_sheet.py` | Labeled montage of a source deck's media (source-slide → image) — to pick correct images per slide. |
| `extract_source.py` | Per-slide text + URLs / "Доп материалы" blocks from a source deck. |
| `probe_google_access.py` | Read-only gate check for the publish pipeline, per credential lane: Drive account + free space + folder, sheet read/`canEdit`, and a rehearsal of the sheet write (tab, topic column, which columns append where, deck → row). Re-run after changing sharing, Drive quota or the consent. |

## Скрипты v4-деки (ad-hoc, в Justfile не заведены)

Написаны при переработке dbt-деки в `v4.01`. Лежат здесь «на всякий случай» — под
переиспользование специально не приспособлены, но каждый самодостаточен и с шапкой.

| Script | What it does |
|--------|--------------|
| `fit_check.py` | До сборки: подобранный кегль код-панели, её высота против безопасной зоны профиля, ширина строки против реальной Consolas (0.55em — рендерер закладывает пессимистичные 0.72em), нижняя граница таблицы, зазор `visual_bottom` до подвала (логотип + строка «Материалы»), высота буллетов над схемой на R12-слайдах и наезд заголовка в две строки на подпись код-панели. |
| `pdf_overflow_check.py` | После сборки, по PDF от LibreOffice: блоки за краями страницы, панели, перекрывающие логотип MLINSIDE, и панели с зазором до подвала меньше 0.3in. Требует `pymupdf`. |
| `stage_pictures.py` | Раскладывает картинки из фотоэкспорта лектора в `data/source/media/` под говорящими именами — запись о том, какой оригинал стал каким ассетом слайда. |
| `v41_patch.py` + `v41/` | План правок v4.1 (замена / вставка / перенос / удаление слайда по `id`, подстановки по тексту) и сами блоки слайдов. Режет контент-YAML по `- kind:`, поэтому нетронутые слайды остаются байт-в-байт. |
| `v41_trim_split.py`, `v41_trim_split2.py` | Подрезка буллетов и схем на R12-слайдах (картинка + схема): на них текст стоит НАД панелью и при переполнении переливается прямо на неё. |
| `wrap_report.py` | Построчный отчёт о переносах в код-панелях по ХУДШЕМУ случаю (0.72em — так ведёт себя LibreOffice без Consolas). Вывод стабилен и предназначен для diff-а до/после правки кода. |
| `picture_slots.py` | Какие слайды могут принять картинку без порчи кода: считает высоту панели в узкой колонке и место, остающееся буллетам. |
| `v43_validate.py` | Проверки §10 брифа v4.4: основная часть (до `Спасибо за внимание!` включительно) — часы `MM:SS-MM:SS` у каждого слайда, стык `previous.end == next.start`, старт с `00:00`; после закрывающего слайда часов быть не должно; заметка не повторяет буллет дословно. |
| `v43/` + `v41_patch.py` | План v4.4: «dbt за 60 секунд», таймлайн появления dbt, onboarding-блок, переработка моделирования, Airflow 3 + Cosmos. Тот же патчер. |
| `v42/` + `v41_patch.py` | План второго прохода: раздел «Картинки» в конце деки и разрез слайда про пакеты. Тот же патчер, блоки берутся из каталога рядом с планом. |
| `seed_image_origins.py` | Одноразовый посев поля `origin` в `content/preza-dbt-v4-images.yml` — откуда приехал каждый файл. Дальше `images_manifest.py sync` эти поля сохраняет. |
| `deck_timing.py` | Сумма меток `[~N мин]` из заметок с разбивкой по секциям; слайды после `900-*` не считает. Абсолютное время слайда ставит `just preza-notes` (`scripts/preza/notes_fix.py`), метку `[~N мин]` он не трогает — она остаётся входом для этого отчёта. |
| `v4_diagrams.py` | Генератор ASCII-схем (`code_lang: diagram`) — рамки строит `box()`, поэтому строки одной длины по построению. |
| `patch_slide_code.py` | Замена блока `code:` одного слайда по `id`, без переформатирования всего контент-YAML. |
| `v4_build_settings.yml` | Копия настроек сборки с `out_dir: .tmp/build` — черновая сборка мимо `data/generated`, чтобы Stop-хук не отправил её в Telegram. |

## Usage
```bash
just -f .tmp/Justfile verify                 # verify the current v3.9 deck
just -f .tmp/Justfile render 4 32 33         # render slides 4, 32, 33 → .tmp/render/*.png
just -f .tmp/Justfile render-pdf data/generated/MLInside_Введение-в-dbt_v3.9.pdf 13 16
                                                # true-layout PNGs → .tmp/render-pdf/
just -f .tmp/Justfile lint-scalars           # скалярные поля всех контент-YAML
just -f .tmp/Justfile audit-code              # code length/layout audit of the content YAML
just -f .tmp/Justfile publish                 # build → open → Telegram send of the latest deck
just -f .tmp/Justfile contact-sheet          # → .tmp/contact_sheet.png
just -f .tmp/Justfile extract-source         # source materials/URL blocks
just -f .tmp/Justfile clean                  # drop generated PNG/pptx artifacts
```

## Git
Scripts + docs are tracked; generated artifacts (`.tmp/render/`, `.tmp/render-pdf/`, `.tmp/media/`,
`*.png`, `*.pptx`) are git-ignored (see repo `.gitignore`).
