# `.tmp/` — dev/QA helper scripts for the deck generator

Throwaway-but-reusable scripts used while building/checking the `preza_gen` decks. Not part of the
package (`src/preza_gen/`); safe to delete. Run via the local Justfile from the **repo root**.

## Scripts
| Script | What it does |
|--------|--------------|
| `verify_deck.py` | Counts slides/images/notes/materials, note-emphasis runs (bold/underline/italic), checks no author strings. |
| `render_slides.py` | Moves chosen 1-based slides to the front of a throwaway copy and `qlmanage`-renders each to PNG (qlmanage only thumbnails slide 1). |
| `render_pdf_pages.py` | Renders selected pages from the LibreOffice-produced PDF with Poppler: the authoritative visual QA path. |
| `audit_code_slides.py` | Reports code length, bullets and resulting side/full layout for each code slide. |
| `publish` | Build the deck, open the newest version locally, then send it to Telegram. |
| `contact_sheet.py` | Labeled montage of a source deck's media (source-slide → image) — to pick correct images per slide. |
| `extract_source.py` | Per-slide text + URLs / "Доп материалы" blocks from a source deck. |
| `probe_google_access.py` | Read-only gate check for the publish pipeline: can each credential SEE the course sheet, and may it EDIT it (`canEdit`)? Re-run after changing sharing or finishing the ADC consent. |

## Usage
```bash
just -f .tmp/Justfile verify                 # verify the current v3.9 deck
just -f .tmp/Justfile render 4 32 33         # render slides 4, 32, 33 → .tmp/render/*.png
just -f .tmp/Justfile render-pdf data/generated/MLInside_Введение-в-dbt_v3.9.pdf 13 16
                                                # true-layout PNGs → .tmp/render-pdf/
just -f .tmp/Justfile audit-code              # code length/layout audit of the content YAML
just -f .tmp/Justfile publish                 # build → open → Telegram send of the latest deck
just -f .tmp/Justfile contact-sheet          # → .tmp/contact_sheet.png
just -f .tmp/Justfile extract-source         # source materials/URL blocks
just -f .tmp/Justfile clean                  # drop generated PNG/pptx artifacts
```

## Git
Scripts + docs are tracked; generated artifacts (`.tmp/render/`, `.tmp/render-pdf/`, `.tmp/media/`,
`*.png`, `*.pptx`) are git-ignored (see repo `.gitignore`).
