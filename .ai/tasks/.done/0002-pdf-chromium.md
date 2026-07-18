# 0002 · PDF-рендерер через headless Chromium / Playwright (HTML→PDF)

**Приоритет:** p3 · **Область:** preza_gen/renderers/pdf

Альтернатива задаче 0001: точнее рендерит сложную HTML-вёрстку (flex/grid как в браузере).

- `uv pip install playwright && playwright install chromium` (тяжёлая зависимость ~150 МБ).
- В `renderers/pdf.py` добавить ветку engine=chromium: открыть `file://<html>` в headless-Chromium, `page.pdf(path, print_background=True, prefer_css_page_size=True)`.
- Флаг движка в settings (`build_deck_v3.yml → settings.pdf_engine: weasyprint|chromium`).
- Сравнить результат с 0001 на split-слайдах и таблицах; выбрать дефолт.

---
**CLOSED 2026-07-19** — superseded: основной pdf-движок — LibreOffice (см. 0001); Chromium-ветка не нужна, если только не потребуется пиксель-точный HTML-рендер.
