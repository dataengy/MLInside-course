# 0001 · PDF-рендерер через WeasyPrint (HTML→PDF)

**Приоритет:** p2 · **Область:** preza_gen/renderers/pdf

LibreOffice на машине не работает → pptx→pdf через него невозможен. Путь — HTML→PDF.

- Установить: `uv pip install weasyprint` (extra `.[pdf]` уже в pyproject).
- `renderers/pdf.py` уже пытается импортировать `weasyprint.HTML` и рендерит `HTML(filename).write_pdf(out)` — проверить на нашем HTML (`data/generated/*.html`).
- Учесть: WeasyPrint слабее по сложной вёрстке (flex/grid) — подогнать print-CSS (`@media print`), проверить split-слайды (текст+картинка) и таблицы.
- Готово: `just build-all` даёт `data/generated/*.pdf` без предупреждения.

Альтернатива — задача 0002 (Chromium/Playwright, точнее по вёрстке).

---
**CLOSED 2026-07-19** — superseded: pptx→pdf работает через LibreOffice (`soffice_path()`/`_render_with_soffice()` в `renderers/pdf.py`, preza_gen `f3d8ca4`). WeasyPrint остаётся опциональным fallback (`.[pdf]`).
