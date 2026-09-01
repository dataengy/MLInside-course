"""Config loading for the schedule reader.

Two sources, both non-secret:

* ``settings/config.yml``  — project SSoT; supplies ``planning.schedule_gsheet``.
* ``settings/gsheet.yml``  — how to read that sheet (which tab, header row, column mapping).
  Optional: sensible defaults are used when it is absent, so the very first ``dump`` works
  before anyone knows the sheet's real column names.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from schedule.gsheet import REPO_ROOT

CONFIG_YML = REPO_ROOT / "settings" / "config.yml"
GSHEET_YML = REPO_ROOT / "settings" / "gsheet.yml"

_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]+)")

#: Fallback column mapping — candidate header names per field, matched case/space-insensitively.
#: Overridden wholesale by ``settings/gsheet.yml`` once the real headers are known.
DEFAULT_MAPPING: dict[str, Any] = {
    "tab": None,  # None → first tab
    "header_row": 1,
    "columns": {
        "n": ["№", "номер", "no", "#", "n"],
        "date": ["дата", "date"],
        "topic": ["тема", "topic", "название", "лекция", "семинар"],
        "owner": ["лектор", "owner", "ответственный", "автор", "преподаватель"],
        "status": ["статус", "status"],
        "accents": ["акценты", "accents", "ключевые моменты", "содержание", "что рассказать"],
        "notes": ["комментарий", "комментарии", "notes", "заметки"],
    },
    "accents_split": ["\n", ";", "•"],
}

DEFAULT_READ: dict[str, Any] = {"tabs": [], "max_rows": 500, "max_cols": 40}

DEFAULT_OUTPUTS: dict[str, Any] = {
    "raw": "settings/schedule.yml",
    "plan": "content/presentations.yml",
}


def spreadsheet_id_from_url(url: str) -> str:
    """Extract the spreadsheet id from a Google Sheets URL.

    >>> spreadsheet_id_from_url("https://docs.google.com/spreadsheets/d/1AbC-_9/edit#gid=0")
    '1AbC-_9'
    >>> spreadsheet_id_from_url("1AbC-_9")
    '1AbC-_9'
    """
    m = _SHEET_ID_RE.search(url)
    if m:
        return m.group(1)
    if "/" in url or url.startswith("http"):
        raise ValueError(f"Not a Google Sheets URL: {url!r}")
    return url


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_config() -> dict:
    """Parsed ``settings/config.yml``."""
    if not CONFIG_YML.exists():
        raise FileNotFoundError(f"Project config not found: {CONFIG_YML}")
    return _read_yaml(CONFIG_YML)


def load() -> dict:
    """Merged reader settings.

    Returns a dict with ``spreadsheet`` (``id`` + ``url``), ``read``, ``mapping`` and
    ``outputs``. ``settings/gsheet.yml`` wins over the defaults; the spreadsheet id falls back
    to ``settings/config.yml`` → ``planning.schedule_gsheet``.
    """
    gs = _read_yaml(GSHEET_YML)
    sheet = dict(gs.get("spreadsheet") or {})

    url = sheet.get("url")
    if not sheet.get("id"):
        if not url:
            url = (load_config().get("planning") or {}).get("schedule_gsheet")
        if not url:
            raise ValueError(
                "No spreadsheet id — set spreadsheet.id in settings/gsheet.yml or "
                "planning.schedule_gsheet in settings/config.yml"
            )
        sheet["id"] = spreadsheet_id_from_url(url)
    sheet.setdefault("url", url or f"https://docs.google.com/spreadsheets/d/{sheet['id']}/edit")

    mapping = {**DEFAULT_MAPPING, **(gs.get("mapping") or {})}
    if gs.get("mapping", {}).get("columns"):
        mapping["columns"] = gs["mapping"]["columns"]

    return {
        "spreadsheet": sheet,
        "read": {**DEFAULT_READ, **(gs.get("read") or {})},
        "mapping": mapping,
        "outputs": {**DEFAULT_OUTPUTS, **(gs.get("outputs") or {})},
    }


def out_path(settings: dict, key: str) -> Path:
    """Absolute path for an ``outputs`` entry."""
    return REPO_ROOT / settings["outputs"][key]


def dump_yaml(path: Path, data: Any, header: str = "") -> None:
    """Write YAML with Cyrillic kept readable and key order preserved.

    ВНИМАНИЕ: комментарии НЕ переживают этот путь — ``safe_dump`` их не знает.
    Для файлов, которые человек читает и комментирует (``content/presentations.yml``),
    берите :func:`load_roundtrip` / :func:`dump_roundtrip`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    path.write_text(f"{header}{body}" if header else body, encoding="utf-8")


# ── round-trip: файлы, где комментарии — часть содержимого ────────────────────
#
# ЗАЧЕМ. content/presentations.yml правят и машины, и руки. Комментарии в нём несут то,
# чего нет в данных: почему блок записи нарезан именно так, что за блок demos, почему
# приложение разбито на три части. Пара safe_load + safe_dump сносит их молча — файл
# остаётся валидным, диff выглядит как «переформатирование», и пояснение исчезает.
# Так уже случалось: 2026-09-01 один прогон publisher снёс 19 строк комментариев.
#
# ruamel в round-trip-режиме держит комментарии, порядок ключей и стиль скаляров,
# если МУТИРОВАТЬ загруженный документ, а не собирать новый: комментарии живут на
# самих объектах (CommentedMap/CommentedSeq), и подмена объекта их теряет.


def _rt() -> Any:
    """YAML-процессор round-trip с настройками под этот репозиторий.

    Настройки подобраны так, чтобы выдача совпадала с прежней (``safe_dump``) и первая же
    запись не давала диff из одного переформатирования: та же ширина, тот же отступ и
    ``null`` вместо пустого значения (ruamel по умолчанию печатает ``None`` пустотой).
    """
    from ruamel.yaml import YAML
    from ruamel.yaml.representer import RoundTripRepresenter

    class _Representer(RoundTripRepresenter):
        pass

    _Representer.add_representer(
        type(None),
        lambda self, _: self.represent_scalar("tag:yaml.org,2002:null", "null"),
    )

    y = YAML()  # round-trip по умолчанию
    y.Representer = _Representer
    y.preserve_quotes = True
    y.width = 100
    y.allow_unicode = True
    y.indent(mapping=2, sequence=2, offset=0)  # как выгружал safe_dump
    return y


def load_roundtrip(path: Path) -> Any:
    """Прочитать YAML, сохранив комментарии и стиль. Нет файла → ``{}``."""
    if not path.exists():
        return {}
    return _rt().load(path.read_text(encoding="utf-8")) or {}


def dump_roundtrip(path: Path, data: Any, header: str = "") -> None:
    """Записать документ, полученный из :func:`load_roundtrip`, не потеряв комментарии.

    ``header`` дописывается сверху ОДИН раз: шапка файла — не часть документа, она
    канонична и обновляется в коде. Поэтому ведущий комментарий, который ruamel
    подобрал при чтении, снимается — иначе шапка удваивалась бы с каждой записью.
    Запись атомарная: у файла два писателя (schedule и publisher).
    """
    import io

    if header and getattr(data, "ca", None) is not None:
        data.ca.comment = None

    buf = io.StringIO()
    _rt().dump(data, buf)
    # Перенос длинного простого скаляра ruamel ставит ПОСЛЕ пробела, и тот остаётся в конце
    # строки. Смысла он не несёт, а диff и линтеры от него шумят.
    body = "".join(f"{ln.rstrip()}\n" for ln in buf.getvalue().splitlines())

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(f"{header}{body}" if header else body, encoding="utf-8")
    os.replace(tmp, path)
