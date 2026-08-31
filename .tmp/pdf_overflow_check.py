#!/usr/bin/env python3
"""Пост-сборочный визуальный QA: что реально вылезло за края и что на что наехало.

Работает по PDF, который делает LibreOffice из собранной .pptx, — это единственный способ
увидеть настоящую вёрстку (переносы строк, подстановку шрифта, позицию логотипа), а не
оценку рендерера. Два вида замечаний:

  * OVERFLOW — блок текста выходит за границы страницы;
  * FOOTER   — прямоугольник (панель кода/диаграммы) перекрывает логотип MLINSIDE внизу.

    soffice --headless --convert-to pdf --outdir /tmp/qa data/drafts/DECK.pptx
    python3 .tmp/pdf_overflow_check.py /tmp/qa/DECK.pdf

Нужен pymupdf (в зависимостях проекта его нет — ставится отдельно в venv для QA).
Написан при сборке v4 деки; в Justfile намеренно не заведён.
"""

from __future__ import annotations

import sys

import pymupdf

PT = 72.0
EPS = 1.0  # допуск в пунктах на округление рендерера


def _footer_logo(page) -> tuple[float, float, float, float] | None:
    """bbox логотипа MLINSIDE: самая нижняя картинка страницы в левой трети."""
    cands = [im["bbox"] for im in page.get_image_info()
             if im["bbox"][1] > page.rect.height * 0.85 and im["bbox"][0] < page.rect.width * 0.35]
    return max(cands, key=lambda b: b[1]) if cands else None


def main(pdf_path: str) -> int:
    doc = pymupdf.open(pdf_path)
    W, H = doc[0].rect.width, doc[0].rect.height
    issues: list[str] = []

    for n, page in enumerate(doc, 1):
        for b in page.get_text("blocks"):
            x0, y0, x1, y1 = b[:4]
            if y1 > H - EPS or x1 > W - EPS or y0 < -EPS or x0 < -EPS:
                issues.append(f"  OVERFLOW стр.{n:3d}  y1={y1 / PT:.2f}in  {b[4][:40]!r}")

        logo = _footer_logo(page)
        if not logo:
            continue
        lx0, ly0, lx1, ly1 = logo
        for dr in page.get_drawings():
            r = dr["rect"]
            if r.width < W * 0.3 or r.height < 20:      # интересуют только крупные панели
                continue
            if r.width > W * 0.98 and r.height > H * 0.9:   # подложка страницы, не панель
                continue
            if r.y1 > ly0 + EPS and r.x0 < lx1 and r.x1 > lx0:
                issues.append(
                    f"  FOOTER   стр.{n:3d}  панель до {r.y1 / PT:.3f}in, логотип с {ly0 / PT:.3f}in"
                )
                break

    for line in issues:
        print(line)
    print(f"{pdf_path}: {doc.page_count} стр., {len(issues)} замечаний")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
