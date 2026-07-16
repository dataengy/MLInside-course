# `.tmp/` — dev/QA helper scripts for the deck generator

Throwaway-but-reusable scripts used while building/checking the `preza_gen` decks. Not part of the
package (`src/preza_gen/`); safe to delete. Run via the local Justfile from the **repo root**.

## Scripts
| Script | What it does |
|--------|--------------|
| `verify_deck.py` | Counts slides/images/notes/materials, note-emphasis runs (bold/underline/italic), checks no author strings. |
| `render_slides.py` | Moves chosen 1-based slides to the front of a throwaway copy and `qlmanage`-renders each to PNG (qlmanage only thumbnails slide 1). |
| `contact_sheet.py` | Labeled montage of a source deck's media (source-slide → image) — to pick correct images per slide. |
| `extract_source.py` | Per-slide text + URLs / "Доп материалы" blocks from a source deck. |

## Usage
```bash
just -f .tmp/Justfile verify                 # verify the current v3.1 deck
just -f .tmp/Justfile render 4 32 33         # render slides 4, 32, 33 → .tmp/render/*.png
just -f .tmp/Justfile contact-sheet          # → .tmp/contact_sheet.png
just -f .tmp/Justfile extract-source         # source materials/URL blocks
just -f .tmp/Justfile clean                  # drop generated PNG/pptx artifacts
```

## Git
Scripts + docs are tracked; generated artifacts (`.tmp/render/`, `.tmp/media/`, `*.png`, `*.pptx`)
are git-ignored (see repo `.gitignore`).
