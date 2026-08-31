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
# Требуемый зазор (дюймы) между нижней кромкой панели и верхом подвала. Меньше —
# и панель зрительно упирается в логотип и в строку «📚 Материалы», даже если
# геометрически не пересекается: LibreOffice дорисовывает обводку ниже прямоугольника.
CLEARANCE = 0.3


def _footer_logo(page) -> tuple[float, float, float, float] | None:
    """bbox логотипа MLINSIDE: самая нижняя картинка страницы в левой трети."""
    cands = [im["bbox"] for im in page.get_image_info()
             if im["bbox"][1] > page.rect.height * 0.85 and im["bbox"][0] < page.rect.width * 0.35]
    return max(cands, key=lambda b: b[1]) if cands else None


def _materials_blocks(page) -> list[tuple[float, float, float, float]]:
    """bbox строки «📚 Материалы» — правый нижний угол; её тоже нельзя подпирать панелью."""
    return [b[:4] for b in page.get_text("blocks")
            if b[1] > page.rect.height * 0.88 and "Материалы" in b[4]]


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
        # Подвал — это не только логотип: строка «📚 Материалы» стоит правее и ниже, и
        # панель кода/картинка обязаны кончиться ВЫШЕ обеих с запасом CLEARANCE.
        band_top = min(ly0, *( [b[1] for b in _materials_blocks(page)] or [ly0] ))
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
            if r.y1 > band_top - CLEARANCE * PT:
                issues.append(
                    f"  ЗАЗОР    стр.{n:3d}  панель до {r.y1 / PT:.3f}in, подвал с "
                    f"{band_top / PT:.3f}in — меньше {CLEARANCE}in"
                )
                break

    for line in issues:
        print(line)
    print(f"{pdf_path}: {doc.page_count} стр., {len(issues)} замечаний")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
