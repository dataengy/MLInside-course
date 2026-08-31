#!/usr/bin/env python3
"""Второй проход подрезки R12-слайдов: короткие буллеты вместо переносимых.

Высоту блока буллетов определяет число ОТРИСОВАННЫХ строк, а не число пунктов: в колонке
6.2in при кегле мастера в строку влезает около сорока знаков. Поэтому здесь буллеты не
удаляются, а укорачиваются до одной строки — смысл остаётся, высота падает вдвое.
Границу считает .tmp/fit_check.py.

    python3 .tmp/v41_trim_split2.py content/preza-dbt-v4-content.yml
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".tmp")

from v41_trim_split import _blocks, _replace_code, _replace_list  # noqa: E402

BULLETS: dict[str, list[str]] = {
    "006b-elt-vmesto-etl": [
        "Storage и compute разъехались и подешевели",
        "Сырьё грузим как есть, переделка — новый SELECT",
        "Практики нужны вокруг SQL, а не вокруг движка",
        "ETL остаётся там, где сырое класть нельзя",
    ],
    "012-skvoznaya-arhitektura": [
        "Ingestion остаётся снаружи — dbt не грузит",
        "dbt отвечает за рамку в середине",
        "Ниже рамки начинается ML-пайплайн",
        "Граница проходит по training dataset",
    ],
    "015a-sloi-dbt-proekta-obzor": [
        "sources — внешние таблицы, dbt их не строит",
        "staging — типы и чистка, без джойнов",
        "intermediate — join и гранулярность",
        "marts — BI-витрины и feature marts",
    ],
    "015b-pravila-sloev": [
        "mart читает source мимо staging — ломается",
        "Джойн в staging — гранулярность поехала",
        "Rejoin и fanout — невидимые дубли",
        "Ловится машинно: dbt_project_evaluator",
    ],
    "033-docs-i-lineage-pasport-priznaka": [
        "description модели и колонки — рядом с кодом",
        "meta — владелец, тип признака, потребители",
        "dbt docs generate → сайт с описаниями и тестами",
    ],
    "058-a-esli-dagster": [
        "Ментальная модель: не задачи, а data assets",
        "Модель dbt = asset, манифест → набор ассетов",
        "Витрина и обученная модель — один граф",
    ],
}

CODE: dict[str, str] = {
    "033-docs-i-lineage-pasport-priznaka": """\
    models:
      - name: mart_delivery_features
        meta:
          owner: ml-platform
          consumers: [delivery_delay_model]
        columns:
          - name: seller_avg_delay_90d
            description: >
              Средняя просрочка продавца за 90 дней
              ДО момента покупки. Point-in-time.
""",
    "058-a-esli-dagster": """\
     Airflow        Dagster
     ──────────     ──────────────
     задача         ассет
     dbt-модель     dbt-модель = asset
       = task            ↓
                    training dataset
                         ↓
                    trained model
""",
}


def main(path_str: str) -> int:
    from pathlib import Path

    import yaml

    path = Path(path_str)
    header, blocks = _blocks(path.read_text(encoding="utf-8"))
    import re

    touched = 0
    for i, block in enumerate(blocks):
        m = re.search(r"^  id:\s*(\S+)", block, re.M)
        sid = m.group(1) if m else ""
        new = block
        if sid in CODE:
            new = _replace_code(new, CODE[sid])
        if sid in BULLETS:
            new = _replace_list(new, "bullets", BULLETS[sid])
        if new != block:
            blocks[i] = new
            touched += 1
    out = header + "".join(blocks)
    yaml.safe_load(out)
    path.write_text(out, encoding="utf-8")
    print(f"{path}: подрезано слайдов — {touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
