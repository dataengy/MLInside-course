#!/usr/bin/env python3
"""Какие слайды МОГУТ принять картинку без порчи кода — до того, как её туда ставить.

Постановка картинки на слайд переводит его в R12: панель кода уезжает в левую колонку
(6.2in), а буллеты обязаны уместиться НАД ней. Дешевле проверить это арифметикой, чем
поставить картинку, собрать деку и увидеть текст поверх панели.

Печатает по слайду: ширину колонки сейчас и после постановки картинки, высоту панели,
сколько места останется буллетам и вердикт. `ok` — картинку можно ставить как есть.

    PYTHONPATH=src python3 .tmp/picture_slots.py content/preza-dbt-v4-content.yml

Написан при доработке v4.1 деки; в Justfile намеренно не заведён.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preza_gen import settings as S  # noqa: E402
from preza_gen.renderers import pptx as R  # noqa: E402

SETTINGS = "content/build_deck_v3-settings.yml"
BODY_TOP = 1.79


def main(content_yml: str) -> int:
    cfg, content = S.load(SETTINGS, content_yml)
    fmt = cfg.fmt
    from pptx import Presentation

    sizes = R._master_body_sizes(Presentation(str(cfg.template)))
    free = 0
    for spec in content.slides:
        if spec.kind not in ("content", "agenda") or spec.image:
            continue
        if not spec.code:
            print(f"{spec.id:38s} ok  (кода нет — картинка встаёт в правую колонку)")
            free += 1
            continue
        safe = R.ImageBox(cfg.code_box_full.left, fmt.visual_top_min,
                          fmt.bullets_width_narrow, fmt.visual_bottom - fmt.visual_top_min)
        box = R._anchor_bottom(
            R._fit_code_box(spec.code, safe, cfg.code_style, min_height=1.4),
            fmt.visual_bottom, fmt.visual_top_min,
        )
        room = box.top - fmt.bullets_gap - BODY_TOP
        need = R._bullets_height(spec.bullets, fmt.bullets_width_narrow, sizes) if spec.bullets else 0.0
        limit = int((safe.width - R._MARGIN_IN) / (box.height and 13 / 72 * R._CHAR_W_EM or 1))
        widest = max(len(ln) for ln in spec.code.rstrip("\n").split("\n"))
        verdict = "ok " if need <= room and widest <= limit else "нет"
        if verdict == "ok ":
            free += 1
        print(f"{spec.id:38s} {verdict} панель {box.height:4.2f}in top={box.top:4.2f} "
              f"место буллетам {room:5.2f} нужно {need:5.2f} · строка {widest:3d}/{limit}")
    print(f"# слайдов, готовых принять картинку: {free}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
