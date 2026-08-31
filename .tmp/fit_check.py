#!/usr/bin/env python3
"""Проверка «влезет ли» — до сборки, средствами самого рендерера.

Считает для каждого слайда контент-YAML: подобранный кегль код-панели, её высоту против
безопасной зоны формат-профиля, ширину самой длинной строки против реальной Consolas
(0.55em — рендерер закладывает пессимистичные 0.72em, поэтому его cpl не показатель),
и нижнюю границу таблицы. Ловит ровно то, что потом видно как обрезанный код и перенос
строки посреди SQL.

    PYTHONPATH=src python3 .tmp/fit_check.py content/preza-dbt-v4-content.yml

Написан при сборке v4 деки; в Justfile намеренно не заведён.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preza_gen import settings as S  # noqa: E402
from preza_gen.renderers import pptx as R  # noqa: E402

SETTINGS = "content/build_deck_v3-settings.yml"
CONSOLAS_EM = 0.55  # фактическая ширина знака Consolas; 0.72 в рендерере — худший случай
# Верхняя кромка логотипа MLINSIDE, дюймы от верха слайда (измерено по PDF LibreOffice:
# bbox картинки 6.954..7.144in, x 0.60..1.85 — то есть прямо под левым краем панели кода).
# Панель кода/диаграммы шириной во весь слайд обязана закончиться выше этой отметки.
FOOTER_LOGO_TOP = 6.95
TABLE_BOTTOM = 6.95


def main(content_yml: str) -> int:
    cfg, content = S.load(SETTINGS, content_yml)
    f = cfg.fmt
    problems: list[tuple[str, str]] = []

    # профильная проверка, одна на деку: где вообще заканчивается прижатый вниз визуал
    if f.visual_anchor == "bottom" and f.visual_bottom > FOOTER_LOGO_TOP:
        problems.append(
            ("<профиль %s>" % cfg.format_name,
             f"visual_bottom={f.visual_bottom} наезжает на логотип подвала ({FOOTER_LOGO_TOP})")
        )

    for spec in content.slides:
        if spec.code:
            box = cfg.code_box if spec.bullets else cfg.code_box_full
            safe = R.ImageBox(box.left, f.visual_top_min, box.width, f.visual_bottom - f.visual_top_min)
            size = R._fit_code_size(spec.code, safe, cfg.code_style)
            height = R._code_height(spec.code, safe.width, size)
            cpl = int((safe.width - 0.28) / (size / 72 * CONSOLAS_EM))
            widest = max(len(line) for line in spec.code.split("\n"))
            if height > safe.height + 0.01:
                problems.append((spec.id, f"код не влезает по высоте: {height:.2f} > {safe.height:.2f} при {size}pt"))
            if widest > cpl:
                problems.append((spec.id, f"строка {widest} знаков при лимите {cpl} — будет перенос"))
            if size <= float(cfg.code_style["min_size"]):
                problems.append((spec.id, f"кегль упёрся в min_size ({size}pt)"))
        if spec.table:
            bottom = f.table_top + 0.45 + 0.4 * len(spec.table["rows"])
            if bottom > TABLE_BOTTOM:
                problems.append((spec.id, f"таблица уходит вниз до {bottom:.2f}in ({len(spec.table['rows'])} строк)"))
        if spec.bullets and len(spec.bullets) > 11:
            problems.append((spec.id, f"{len(spec.bullets)} буллетов"))

    for sid, msg in problems:
        print(f"  {sid:52s} {msg}")
    print(f"{content_yml}: {len(problems)} замечаний по вёрстке")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "content/preza-dbt-v3-content.yml"))
