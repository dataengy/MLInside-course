#!/usr/bin/env python3
"""Подрезать буллеты и схемы на R12-слайдах (картинка + схема на одном слайде).

На таком слайде буллеты и панель схемы делят ЛЕВУЮ колонку: текст сверху, схема снизу,
картинка занимает правую. Плейсхолдер текст не обрезает — он переливается прямо на панель,
поэтому длина блока буллетов здесь жёсткое ограничение, а не вопрос вкуса.
Границу считает .tmp/fit_check.py (правило «буллеты не помещаются над схемой»).

Скрипт правит content-YAML построчно по id слайда: заменяет блок bullets и, где схема
слишком высокая, сам блок code. Формат остальных слайдов не трогается.

    python3 .tmp/v41_trim_split.py content/preza-dbt-v4-content.yml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER = "- kind:"

# id → новые буллеты (None = убрать блок целиком)
BULLETS: dict[str, list[str] | None] = {
    "005-full-stack-data-specialist": [
        "Между DE и потребителем данных всегда есть слой трансформаций",
        "Исторически его вели Analytics Engineer и Data Analyst",
        "У ML Engineer тот же слой — потребитель не дашборд, а обучение",
        "Выигрывает тот, кто может закрыть этот слой сам",
    ],
    "006-pochemu-voznik-analytics-engineering": [
        "DE приносит данные в хранилище — это E и L",
        "Analytics Engineer отвечает за T: трансформации и модель данных",
        "Аналитик и DS работают уже поверх готового слоя",
    ],
    "006b-elt-vmesto-etl": [
        "Storage и compute в облачных DWH разъехались и подешевели",
        "Сырьё грузим как есть, переделка модели — новый SELECT",
        "Практики нужны вокруг SQL, а не вокруг ETL-движка",
        "ETL остаётся там, где сырое класть нельзя",
    ],
    "006c-dbt-viewpoint": [
        "Аналитическая работа — это разработка ПО, а не набор запросов",
        "Код в git, ревью, окружения, тесты, доки, переиспользование",
        "Viewpoint написан ДО продукта: сначала практики, потом инструмент",
    ],
    "012-skvoznaya-arhitektura": [
        "Ingestion остаётся снаружи и сверху — dbt не грузит данные",
        "dbt отвечает за рамку: sources → staging → intermediate → marts",
        "Ниже рамки начинается ML: выборка, обучение, реестр, инференс",
        "Граница ответственности проходит по training dataset",
    ],
    "015a-sloi-dbt-proekta-obzor": [
        "sources — объявленные внешние таблицы, dbt их не строит",
        "staging — чистка и типы, одна модель на источник, без джойнов",
        "intermediate — соединения и явно названная гранулярность",
        "marts — витрины под потребителя: BI и feature marts",
    ],
    "015b-pravila-sloev": [
        "Витрина читает source мимо staging — ломается на смене источника",
        "Джойн в staging — гранулярность поехала там, где её не проверяют",
        "Rejoin и fanout — дубли, которые не видно глазами",
        "Всё это ловится машинно: dbt_project_evaluator, блок CI",
    ],
    "015e-olist-dataset": [
        "Бразильский маркетплейс, 2016–2018, публичный датасет Kaggle",
        "Девять CSV: заказы, позиции, продавцы, клиенты, товары, гео",
        "99 441 заказ и 112 650 позиций — гранулярности РАЗНЫЕ",
        "Задача: предсказать просрочку относительно обещанной даты",
    ],
    "023-jinja-zachem-full-stack": [
        "Jinja — шаблонизатор: dbt рендерит модель ДО отправки в базу",
        "Отсюда всё: ref(), source(), config(), is_incremental()",
        "Цена: SQL в редакторе больше не равен SQL в базе",
        "Поэтому дальше показываем обе половины",
    ],
    "033-docs-i-lineage-pasport-priznaka": [
        "description модели и колонки — рядом с кодом, в одном PR с ним",
        "meta — владелец, тип признака, список потребителей",
        "dbt docs generate → сайт с описаниями, типами и тестами",
    ],
    "033b-lineage-dva-voprosa": [
        "Граф строится сам — из ref() и source()",
        "«Откуда взялось» — вверх по графу: +модель",
        "«Что сломается» — вниз по графу: модель+",
        "exposure добавляет в граф то, что живёт вне dbt",
    ],
    "058-a-esli-dagster": [
        "Другая ментальная модель: не задачи, а data assets",
        "Модель dbt = asset; манифест разворачивается в ассеты",
        "Витрина признаков и обученная модель — узлы одного графа",
    ],
    "061e-dbt-run-selektory": None,
}

# id → новая схема (там, где панель была слишком высокой и съедала место под буллеты)
CODE: dict[str, str] = {
    "012-skvoznaya-arhitektura": """\
     RAW  olist_raw: orders · items · sellers
     ┌─── D B T   Z O N E ───────────────┐
     │ sources → staging → intermediate  │
     │              → feature marts      │
     └───────────────┬───────────────────┘
                     ↓
     training dataset → train → registry
""",
    "023-jinja-zachem-full-stack": """\
     models/*.sql (SQL + Jinja)
              ↓  dbt compile
     target/compiled/… (чистый SQL)
              ↓  dbt run
     таблица или вью в базе
""",
    "033-docs-i-lineage-pasport-priznaka": """\
    models:
      - name: mart_delivery_features
        description: '{{ doc("delivery_features") }}'
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
     «что делать»   «что должно
                     существовать»
     dbt-модель     dbt-модель = asset
       = task            ↓
                    training dataset
                         ↓
                    trained model
""",
}


def _blocks(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(MARKER)]
    bounds = starts + [len(lines)]
    return "".join(lines[: starts[0]]), ["".join(lines[a:b]) for a, b in zip(bounds, bounds[1:])]


def _replace_list(block: str, key: str, items: list[str] | None) -> str:
    """Заменить YAML-список `key:` в блоке слайда; items=None удаляет ключ целиком."""
    pat = re.compile(rf"^  {key}:\n(?:  - .*\n|    .*\n)*", re.M)
    if not pat.search(block):
        raise SystemExit(f"нет ключа {key} в блоке")
    if items is None:
        return pat.sub("", block, count=1)
    body = "".join(f"  - {_quote(i)}\n" for i in items)
    return pat.sub(f"  {key}:\n{body}", block, count=1)


def _quote(value: str) -> str:
    """Экранировать значение так, чтобы YAML прочитал его как строку, а не как мапу."""
    return f"'{value}'" if (":" in value or value.startswith(("«", "-"))) else value


def _replace_code(block: str, code: str) -> str:
    pat = re.compile(r"^  code: \|2\n(?:(?:    .*)?\n)*?(?=^  \w)", re.M)
    if not pat.search(block):
        raise SystemExit("нет блока code")
    return pat.sub("  code: |2\n" + code, block, count=1)


def main(path_str: str) -> int:
    path = Path(path_str)
    header, blocks = _blocks(path.read_text(encoding="utf-8"))
    touched = 0
    for i, block in enumerate(blocks):
        m = re.search(r"^  id:\s*(\S+)", block, re.M)
        sid = m.group(1) if m else ""
        if sid in CODE:
            block = _replace_code(block, CODE[sid])
        if sid in BULLETS:
            block = _replace_list(block, "bullets", BULLETS[sid])
        if block is not blocks[i]:
            blocks[i] = block
            touched += 1
    out = header + "".join(blocks)
    import yaml

    yaml.safe_load(out)  # fail-loud до записи
    path.write_text(out, encoding="utf-8")
    print(f"{path}: подрезано слайдов — {touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
