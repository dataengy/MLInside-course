#!/usr/bin/env python3
"""Хронометраж слайдов, ДОБАВЛЕННЫХ в основную часть в v4.1 — чтобы видеть, чем оплачен рост.

`deck_timing.py` считает деку целиком; здесь нужен ответ на другой вопрос: если лекция
перестала укладываться в 1:30–1:45, какие именно новые слайды это стоило и что дешевле
всего снять. Список id зафиксирован вручную по .tmp/v41/plan.yml.

    python3 .tmp/v41_new_timing.py content/preza-dbt-v4-content.yml
"""

from __future__ import annotations

import re
import sys

import yaml

NEW = [
    "006b-elt-vmesto-etl",
    "006c-dbt-viewpoint",
    "015a-sloi-dbt-proekta-obzor",
    "015b-pravila-sloev",
    "015c-podhody-k-modelirovaniyu",
    "015d-raw-sloj-i-mle-vitriny",
    "015e-olist-dataset",
    "033b-lineage-dva-voprosa",
    "046b-dbt-pandas-i-spark",
    "061b-ci-barrier-actions-gitlab",
    "061c-slim-ci",
    "061d-osnovnye-komandy-dbt",
    "061e-dbt-run-selektory",
    "061f-kachestvo-proekta",
    "061g-logirovanie-v-dbt",
    "061h-dop-poleznye-vozmozhnosti",
    "061i-dbt-i-ai",
    "061j-agentic-data-pipelines",
]


def main(path: str) -> int:
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    total = 0.0
    for slide in doc["content"]:
        if slide.get("id") not in NEW:
            continue
        m = re.search(r"\[~([\d.]+) мин\]", slide.get("notes", ""))
        minutes = float(m.group(1)) if m else 0.0
        total += minutes
        print(f"  {minutes:4.1f}  {slide['id']:34s} {slide.get('title', '')[:50]}")
    print(f"  ----  новых слайдов в основной части: {len(NEW)}, суммарно {total:.1f} мин")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
