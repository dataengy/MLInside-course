#!/usr/bin/env python3
"""Хронометраж лекции по меткам `[~N мин]` в заметках, с разбивкой по секциям.

Конвенция v4-деки: каждый содержательный слайд начинает заметку с `[~N мин]`, а слайды
после секции с id `900-*` считаются appendix и в хронометраж не входят. Скрипт печатает
сумму по блокам — так видно, куда уехал бюджет из PROMPT §22, — и ловит слайды без метки.

    python3 .tmp/deck_timing.py content/preza-dbt-v4-content.yml

Написан при сборке v4 деки; в Justfile намеренно не заведён.
"""

from __future__ import annotations

import collections
import re
import sys

import yaml

APPENDIX_PREFIX = "900-"
STAMP = re.compile(r"\[~([\d.]+)\s*мин")


def main(path: str) -> int:
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    blocks: dict[str, float] = collections.OrderedDict()
    section, total, main_n, missing = "Вступление", 0.0, 0, []

    for spec in doc["content"]:
        if spec["id"].startswith(APPENDIX_PREFIX):
            break
        main_n += 1
        if spec["kind"] == "section":
            section = spec["title"]
        m = STAMP.search(spec.get("notes") or "")
        if not m:
            missing.append(spec["id"])
            continue
        blocks[section] = blocks.get(section, 0.0) + float(m.group(1))
        total += float(m.group(1))

    for name, minutes in blocks.items():
        print(f"  {minutes:5.1f} мин  {name}")
    print(f"  {total:5.1f} мин  ИТОГО · основных слайдов {main_n} · "
          f"appendix {len(doc['content']) - main_n}")
    if missing:
        print("  без метки времени:", ", ".join(missing))
    return 0 if 90 <= total <= 105 and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
