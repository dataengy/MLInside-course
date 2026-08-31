#!/usr/bin/env python3
"""Отчёт о ПЕРЕНОСАХ строк в код-панелях — построчно, по всем слайдам деки.

`fit_check.py` меряет ширину по реальной Consolas (0.55em) и молчит, пока строка влезает
именно в неё. Здесь берётся ХУДШИЙ случай, который закладывает сам рендерер (0.72em): так
ведёт себя LibreOffice, когда Consolas в системе нет и подставляется более широкий моно.
Строка, влезающая в Consolas, но не влезающая в худший случай, перенесётся на чужой машине —
и это ровно то, что не должно появляться при правке кода под узкую колонку.

Печатает по одной строке на слайд: ширина колонки, подобранный кегль, лимит и число
строк-нарушителей. Вывод стабилен и предназначен для diff-а до/после правки:

    PYTHONPATH=src python3 .tmp/wrap_report.py content/preza-dbt-v4-content.yml > /tmp/before.txt
    # ...правки...
    PYTHONPATH=src python3 .tmp/wrap_report.py content/preza-dbt-v4-content.yml | diff /tmp/before.txt -

Написан при доработке v4.1 деки; в Justfile намеренно не заведён.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preza_gen import settings as S  # noqa: E402
from preza_gen.renderers import pptx as R  # noqa: E402

SETTINGS = "content/build_deck_v3-settings.yml"


def _column(cfg, fmt, spec) -> R.ImageBox:
    """Та же развилка колонок, что и в рендерере: полная ширина / правая / левая при R12."""
    if spec.image:
        box = R.ImageBox(cfg.code_box_full.left, cfg.code_box_full.top,
                         fmt.bullets_width_narrow, cfg.code_box_full.height)
    else:
        box = cfg.code_box if spec.bullets else cfg.code_box_full
    return R.ImageBox(box.left, fmt.visual_top_min, box.width,
                      fmt.visual_bottom - fmt.visual_top_min)


def main(content_yml: str, *, verbose: bool = False) -> int:
    cfg, content = S.load(SETTINGS, content_yml)
    fmt = cfg.fmt
    offenders = 0
    for spec in content.slides:
        if not spec.code:
            continue
        safe = _column(cfg, fmt, spec)
        size = R._fit_code_size(spec.code, safe, cfg.code_style)
        # тот же расчёт, что в R._visual_lines: худший случай моноширинного шрифта
        limit = int((safe.width - R._MARGIN_IN) / (size / 72 * R._CHAR_W_EM))
        lines = spec.code.rstrip("\n").split("\n")
        over = [ln for ln in lines if len(ln) > limit]
        offenders += len(over)
        print(f"{spec.id:38s} w={safe.width:5.2f} size={size:4.1f} limit={limit:3d} "
              f"widest={max(len(ln) for ln in lines):3d} wraps={len(over)}")
        if verbose:
            for ln in over:
                print(f"    ({len(ln)}) {ln}")
    print(f"# строк с переносом (худший случай): {offenders}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    raise SystemExit(main(args[0], verbose="-v" in sys.argv))
