"""Fetch the schedule sheet verbatim. No interpretation happens here — see ``mapper``."""

from __future__ import annotations

from typing import Any

from loguru import logger as log

from schedule.gsheet import sheet_utils


def fetch_raw(
    service: Any,
    spreadsheet_id: str,
    tabs: list[str] | None = None,
    max_rows: int = 500,
    max_cols: int = 40,
) -> dict:
    """Read every requested tab and return a plain, dumpable structure.

    ``tabs=None`` or ``[]`` reads all tabs. Rows are returned exactly as the API gives them:
    ragged (trailing empty cells omitted), formatted values, blank rows included.
    """
    utils = sheet_utils()
    meta = utils.get_sheet_metadata(service, spreadsheet_id)
    props = meta.get("properties", {})
    all_sheets = meta.get("sheets", [])

    wanted = [t for t in (tabs or []) if t]
    out_tabs = []
    for sh in all_sheets:
        p = sh.get("properties", {})
        title = p.get("title", "")
        if wanted and title not in wanted:
            continue
        grid = p.get("gridProperties", {}) or {}
        rows = min(int(grid.get("rowCount", max_rows) or max_rows), max_rows)
        cols = min(int(grid.get("columnCount", max_cols) or max_cols), max_cols)
        rng = f"'{title}'!{utils.a1(1, 1)}:{utils.a1(rows, cols)}"
        values = utils.get_sheet_values(service, spreadsheet_id, rng)
        log.info(f"tab {title!r}: {len(values)} rows")
        out_tabs.append(
            {
                "title": title,
                "gid": p.get("sheetId"),
                "index": p.get("index"),
                "rows": values,
            }
        )

    missing = [t for t in wanted if t not in [s["title"] for s in out_tabs]]
    if missing:
        raise ValueError(
            f"Tabs not found in the spreadsheet: {missing}. "
            f"Available: {[s['properties']['title'] for s in all_sheets]}"
        )

    return {
        "spreadsheet": {
            "id": spreadsheet_id,
            "title": props.get("title"),
            "locale": props.get("locale"),
            "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
        },
        "tabs": out_tabs,
    }


def list_tabs(service: Any, spreadsheet_id: str) -> list[str]:
    """Tab names, in sheet order."""
    return sheet_utils().list_sheet_names(service, spreadsheet_id)
