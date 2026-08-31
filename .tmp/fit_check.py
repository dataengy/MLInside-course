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

import math
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
# Верхняя кромка строки «📚 Материалы» (_add_materials: textbox top=6.98). Панель кода и
# картинка стоят прямо над ней, поэтому подвал начинается не с логотипа, а отсюда.
FOOTER_BAND_TOP = 6.98
# Требуемый зазор между нижней кромкой визуала и подвалом. LibreOffice рисует обводку
# скруглённого прямоугольника на ~0.08in ниже его геометрии, и при зазоре меньше этого
# панель зрительно упирается в логотип и в строку материалов.
FOOTER_CLEARANCE = 0.35
# Верхняя кромка body-плейсхолдера шаблона (layout «Title and body»), дюймы.
BODY_TOP = 1.79
# Заголовок шаблона печатается КАПСОМ; по PDF LibreOffice в строку влезает 46 знаков,
# одна строка занимает 0.79..1.22in, каждая следующая добавляет 0.47in.
TITLE_CPL = 46
TITLE_TOP = 0.79
TITLE_LINE = 0.47
TITLE_FIRST = 0.43
# Подпись код-панели рендерер ставит на 0.34in выше её верхней кромки (_add_code).
CAPTION_OFFSET = 0.34


def _body_sizes(cfg) -> dict[int, float]:
    """Размеры буллетов по уровням — из мастера шаблона при body_font: inherit."""
    if cfg.fmt.body_font != "inherit":
        return {int(k): float(v) for k, v in cfg.fmt.body_font["with_image"].items()}
    from pptx import Presentation

    return R._master_body_sizes(Presentation(str(cfg.template)))


def main(content_yml: str) -> int:
    cfg, content = S.load(SETTINGS, content_yml)
    f = cfg.fmt
    problems: list[tuple[str, str]] = []
    body_sizes = _body_sizes(cfg)

    # профильная проверка, одна на деку: где вообще заканчивается прижатый вниз визуал
    if f.visual_anchor == "bottom" and f.visual_bottom > FOOTER_LOGO_TOP:
        problems.append(
            ("<профиль %s>" % cfg.format_name,
             f"visual_bottom={f.visual_bottom} наезжает на логотип подвала ({FOOTER_LOGO_TOP})")
        )
    if f.visual_anchor == "bottom" and f.visual_bottom > FOOTER_BAND_TOP - FOOTER_CLEARANCE:
        problems.append(
            ("<профиль %s>" % cfg.format_name,
             f"visual_bottom={f.visual_bottom}: зазор до подвала "
             f"{FOOTER_BAND_TOP - f.visual_bottom:.2f}in < {FOOTER_CLEARANCE}in")
        )

    for spec in content.slides:
        if spec.code:
            # R12: картинка забирает правую колонку, панель кода уезжает под буллеты влево
            if spec.image:
                box = R.ImageBox(cfg.code_box_full.left, cfg.code_box_full.top,
                                 f.bullets_width_narrow, cfg.code_box_full.height)
            else:
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
            # Подпись панели стоит НАД ней и ничем не отталкивается от заголовка:
            # длинный заголовок переносится на вторую строку и наезжает на подпись.
            if spec.code_caption:
                code_box = R._fit_code_box(
                    spec.code, safe, cfg.code_style,
                    min_height=1.4 if spec.image else (2.0 if spec.bullets else 2.6),
                )
                code_box = R._anchor_bottom(code_box, f.visual_bottom, f.visual_top_min)
                lines = math.ceil(len(spec.title) / TITLE_CPL) or 1
                title_bottom = TITLE_TOP + TITLE_FIRST + (lines - 1) * TITLE_LINE
                caption_top = code_box.top - CAPTION_OFFSET
                if caption_top < title_bottom:
                    problems.append(
                        (spec.id, f"подпись панели ({caption_top:.2f}in) под заголовком в "
                                  f"{lines} строк(и) до {title_bottom:.2f}in")
                    )
        if spec.table:
            bottom = f.table_top + 0.45 + 0.4 * len(spec.table["rows"])
            if bottom > TABLE_BOTTOM:
                problems.append((spec.id, f"таблица уходит вниз до {bottom:.2f}in ({len(spec.table['rows'])} строк)"))
        if spec.bullets and len(spec.bullets) > 11:
            problems.append((spec.id, f"{len(spec.bullets)} буллетов"))
        # R12-слайд: буллеты стоят НАД схемой в той же левой колонке, и места у них
        # ровно до её верхней кромки. Плейсхолдер текст не обрезает — он переливается
        # прямо на панель, поэтому пересчёт высоты здесь обязателен.
        if spec.image and spec.code and spec.bullets:
            box = R.ImageBox(cfg.code_box_full.left, cfg.code_box_full.top,
                             f.bullets_width_narrow, cfg.code_box_full.height)
            safe = R.ImageBox(box.left, f.visual_top_min, box.width,
                              f.visual_bottom - f.visual_top_min)
            code_box = R._fit_code_box(spec.code, safe, cfg.code_style, min_height=1.4)
            code_box = R._anchor_bottom(code_box, f.visual_bottom, f.visual_top_min)
            need = R._bullets_height(spec.bullets, f.bullets_width_narrow, body_sizes)
            room = code_box.top - f.bullets_gap - BODY_TOP
            if need > room:
                problems.append(
                    (spec.id, f"буллеты не помещаются над схемой: {need:.2f} > {room:.2f}in "
                              f"({len(spec.bullets)} шт.)")
                )

    for sid, msg in problems:
        print(f"  {sid:52s} {msg}")
    print(f"{content_yml}: {len(problems)} замечаний по вёрстке")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "content/preza-dbt-v3-content.yml"))
