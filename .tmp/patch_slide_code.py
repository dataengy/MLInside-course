#!/usr/bin/env python3
"""Заменить блок `code:` одного слайда, не переформатируя весь контент-YAML.

`yaml.safe_load` + `yaml.dump` переписали бы файл целиком и убили ручную вёрстку заметок,
поэтому правка идёт по тексту: находим блок слайда по `id:`, внутри него — скаляр
`code: |2`, и подменяем только его тело. Использовалось при сборке v4, чтобы вливать
сгенерированные схемы (см. v4_diagrams.py) и подрезать длинные сниппеты.

Как библиотека:

    from patch_slide_code import patch
    patch("content/preza-dbt-v4-content.yml", "012-skvoznaya-arhitektura", new_code)

Ограничение: рассчитан ровно на стиль `code: |2` с телом в 4 пробела — так написан
preza-dbt-v4-content.yml. На файле с другим отступом молча ничего не найдёт (упадёт на assert).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SLIDE = r"(?m)^- kind: .*\n(?:  .*\n|\n)*?  id: {sid}\n(?:  .*\n|\n)*?(?=^- kind: |\Z)"
_CODE = re.compile(r"(?m)^  code: \|2\n((?:    .*\n|\n)*)")


def patch(path: str | Path, slide_id: str, code: str) -> None:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    m = re.search(_SLIDE.format(sid=re.escape(slide_id)), raw)
    assert m, f"слайд не найден: {slide_id}"
    block = m.group(0)
    cm = _CODE.search(block)
    assert cm, f"у слайда нет блока `code: |2`: {slide_id}"
    body = "".join(("    " + line).rstrip() + "\n" for line in code.rstrip("\n").split("\n"))
    p.write_text(raw[: m.start()] + block[: cm.start(1)] + body + block[cm.end(1):] + raw[m.end():],
                 encoding="utf-8")


if __name__ == "__main__":  # patch_slide_code.py CONTENT SLIDE_ID < new_code
    patch(sys.argv[1], sys.argv[2], sys.stdin.read())
