#!/usr/bin/env python3
# ───────────────────────────────────────────────────────────────────────────
# HARDLINK-CANONICAL: ~/pdp.deploy_dev/scripts/tools-utils/gsheets/utils.py
# HARDLINK — one shared inode; editing changes EVERY copy. Do NOT save-via-rename
# (breaks the link): re-link `ln -f <canonical> <copy>`, verify inodes with `ls -li`.
#   canonical : ~/pdp.deploy_dev/scripts/tools-utils/gsheets/utils.py
#   linked    : ~/.ai/integrations/google/sheets/utils.py
#   linked-at : 2026-07-12  ·  via: ~/.ai/integrations/_relink-actualized.py
# ───────────────────────────────────────────────────────────────────────────
"""Common Google Sheets helpers: reading ranges, resolving cell addresses."""
from typing import Any


def col_letter(idx: int) -> str:
    """0-based column index → A1-notation letter (0→A, 25→Z, 26→AA…)."""
    result = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def a1(row: int, col: int) -> str:
    """1-based (row, col) → A1 notation string."""
    return f"{col_letter(col - 1)}{row}"


def formula_sep(locale: str | None) -> str:
    """Return the formula argument separator for a spreadsheet locale.

    Google Sheets uses ';' as the formula arg separator for locales whose
    number format uses ',' as the decimal mark (ru_RU and most of Europe),
    and ',' for en_* / C-style locales. Fetch the locale once via
    ``spreadsheets().get(fields="properties.locale")`` and pass it here, then
    build formulas like ``f'=HYPERLINK("{url}"{sep}"{label}")'``.

    >>> formula_sep("ru_RU")
    ';'
    >>> formula_sep("de_DE")
    ';'
    >>> formula_sep("en_US")
    ','
    >>> formula_sep(None)
    ','
    """
    if not locale:
        return ","
    lang = locale.replace("-", "_").split("_", 1)[0].lower()
    # Locales that render decimals with a comma → formula separator is ';'
    comma_decimal = {
        "ru", "de", "fr", "es", "it", "pt", "nl", "pl", "uk", "cs", "sk",
        "hu", "ro", "bg", "hr", "sl", "sr", "lt", "lv", "et", "fi", "sv",
        "da", "nb", "nn", "no", "tr", "el", "be", "kk",
    }
    return ";" if lang in comma_decimal else ","


def get_sheet_values(
    service,
    spreadsheet_id: str,
    range_str: str,
    value_render: str = "FORMATTED_VALUE",
) -> list[list[Any]]:
    """Fetch a range and return rows as list-of-lists (empty rows included)."""
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=range_str,
            valueRenderOption=value_render,
        )
        .execute()
    )
    return result.get("values", [])


def get_sheet_metadata(service, spreadsheet_id: str) -> dict:
    """Return spreadsheet metadata (title, sheets list, etc.)."""
    return (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="properties,sheets.properties")
        .execute()
    )


def list_sheet_names(service, spreadsheet_id: str) -> list[str]:
    """Return all sheet tab names in order."""
    meta = get_sheet_metadata(service, spreadsheet_id)
    return [s["properties"]["title"] for s in meta.get("sheets", [])]
