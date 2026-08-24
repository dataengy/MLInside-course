#!/usr/bin/env python3
"""lint_content_scalars — ловит значения контент-YAML, которые YAML разобрал как мапу.

Строка вида ``- Поддержано не всё: часть jinja-методов`` без кавычек — это **мапа**,
а не текст. Ни ``validate_content.py`` (он проверяет ключи слайда, а не типы значений),
ни ``preza-review`` этого не видят: падает только билд, поздно и с непрозрачным
``TypeError: expected string or bytes-like object, got 'dict'``.

Проверка читающая: печатает id слайда, поле и подсказку (обернуть значение в одинарные
кавычки). Exit 1 — если нашлось хоть одно значение.

    python3 .tmp/lint_content_scalars.py content/preza-dbt-v3-content.yml
    just -f .tmp/Justfile lint-scalars
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCALAR_FIELDS = ("title", "subtitle", "notes", "code", "code_caption", "id", "kind")


def _findings(path: Path) -> list[str]:
    """Вернуть человекочитаемые находки для одного контент-YAML."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: list[str] = []
    for pos, slide in enumerate(doc.get("content") or [], start=1):
        if not isinstance(slide, dict):
            out.append(f"слайд #{pos}: не мапа, а {type(slide).__name__}")
            continue
        tag = slide.get("id") or f"#{pos}"
        for field in SCALAR_FIELDS:
            if field in slide and not isinstance(slide[field], str):
                out.append(f"{tag}.{field}: {type(slide[field]).__name__}, ожидалась строка")
        # bullets: строка или список (вложенный уровень) — всё остальное ошибка
        for i, bullet in enumerate(slide.get("bullets") or []):
            if not isinstance(bullet, (str, list)):
                out.append(f"{tag}.bullets[{i}]: {_hint(bullet)}")
        table = slide.get("table") or {}
        for h, header in enumerate(table.get("headers") or []):
            if not isinstance(header, str):
                out.append(f"{tag}.table.headers[{h}]: {_hint(header)}")
        for r, row in enumerate(table.get("rows") or []):
            if not isinstance(row, list):
                out.append(f"{tag}.table.rows[{r}]: {_hint(row)}")
                continue
            for c, cell in enumerate(row):
                if not isinstance(cell, str):
                    out.append(f"{tag}.table.rows[{r}][{c}]: {_hint(cell)}")
        for m, mat in enumerate(slide.get("materials") or []):
            if not isinstance(mat, dict) or not {"label", "url"} <= set(mat):
                out.append(f"{tag}.materials[{m}]: ожидались ключи label + url")
    return out


def _hint(value: object) -> str:
    """Описание находки + готовое исправление для самого частого случая (двоеточие)."""
    if isinstance(value, dict) and len(value) == 1:
        (key, val), = value.items()
        return f"мапа вместо строки → закавычить: '{key}: {val}'"
    return f"{type(value).__name__}, ожидалась строка"


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or sorted(Path("content").glob("preza-*-content.yml"))
    rc = 0
    for path in paths:
        try:
            found = _findings(path)
        except yaml.YAMLError as exc:
            print(f"✗ {path}: YAML не парсится: {exc}")
            rc = 1
            continue
        if found:
            rc = 1
            print(f"✗ {path}: {len(found)} значение(й) не строка")
            for line in found:
                print(f"    {line}")
        else:
            print(f"✓ {path}: скалярные поля в порядке")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
