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
| `fit_check.py` | До сборки: подобранный кегль код-панели, её высота против безопасной зоны профиля, ширина строки против реальной Consolas (0.55em — рендерер закладывает пессимистичные 0.72em), нижняя граница таблицы, и не наезжает ли `visual_bottom` профиля на логотип подвала. |
| `pdf_overflow_check.py` | После сборки, по PDF от LibreOffice: блоки за краями страницы + панели, перекрывающие логотип MLINSIDE. Требует `pymupdf`. |
| `deck_timing.py` | Сумма меток `[~N мин]` из заметок с разбивкой по секциям; слайды после `900-*` не считает. |
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
