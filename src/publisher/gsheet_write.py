"""publisher.gsheet_write — URL/version/slides columns in the course schedule sheet.

Write mechanics mirror the proven pnf write lane (values().batchUpdate, USER_ENTERED,
per-cell ranges — the three columns are not guaranteed adjacent). Identity mechanics mirror
the READ lane: the topic column is located with ``mapper.resolve_columns`` and rows are
matched with ``mapper.normalize`` — one identity model for both directions. The tab title is
always resolved LIVE (the cached settings/schedule.yml dump once came from a non-API
transport and cannot be trusted).
"""

from __future__ import annotations

from typing import Any

from loguru import logger as log

from publisher import gapi
from schedule.gsheet import sheet_utils
from schedule.mapper import normalize, resolve_columns

MAX_SCAN_ROWS = 200  # topic-row search depth below the header


def resolve_tab_title(service: Any, spreadsheet_id: str, want: str | None) -> str:
    """The tab to write to: explicit ``mapping.tab`` override wins, else the first tab."""
    names = gapi.call(sheet_utils().list_sheet_names, service, spreadsheet_id)
    if not names:
        raise ValueError(f"spreadsheet {spreadsheet_id} has no tabs")
    if want:
        if want in names:
            return want
        raise ValueError(f"mapping.tab {want!r} not found; available: {names}")
    return names[0]


def sheet_locale(service: Any, spreadsheet_id: str) -> str | None:
    meta = gapi.run(
        service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="properties.locale")
    )
    return (meta.get("properties") or {}).get("locale")


def read_header(service: Any, spreadsheet_id: str, tab: str, header_row: int) -> list[str]:
    """Current header row, ragged (API omits trailing empties) — same shape the reader sees."""
    utils = sheet_utils()
    rng = f"'{tab}'!A{header_row}:ZZ{header_row}"
    values = gapi.call(utils.get_sheet_values, service, spreadsheet_id, rng)
    return ["" if c is None else str(c) for c in (values[0] if values else [])]


def ensure_columns(
    header: list[str],
    tab: str,
    header_row: int,
    wanted: dict[str, str],
    known: dict[str, int],
) -> tuple[dict[str, int], list[dict]]:
    """Resolve (or plan to append) the wanted columns. Pure — no API calls.

    Returns ``({field: 0-based index}, pending_header_writes)`` where the pending writes are
    ``values().batchUpdate`` data entries the caller folds into the SAME batch as the data
    cells. Resolution order per field: cursor-known index whose header text still matches
    (survives column moves elsewhere / repeated runs) → normalized text search (adopts a
    manually pre-added column) → append after the last used header cell.

    >>> cols, pending = ensure_columns(["тема", "лектор"], "S", 1, {"url": "pptx"}, {})
    >>> cols, [p["range"] for p in pending]
    ({'url': 2}, ["'S'!C1"])
    >>> ensure_columns(["тема", "pptx"], "S", 1, {"url": "pptx"}, {})[0]
    {'url': 1}
    """
    utils = sheet_utils()
    headers = list(header)
    norm = [normalize(h) for h in headers]
    cols: dict[str, int] = {}
    pending: list[dict] = []
    for field_name, title in wanted.items():
        want_n = normalize(title)
        idx: int | None = None
        k = known.get(field_name)
        if k is not None and k < len(headers) and normalize(headers[k]) == want_n:
            idx = k
        if idx is None:
            idx = next((i for i, h in enumerate(norm) if h and h == want_n), None)
        if idx is None:
            idx = len(headers)
            headers.append(title)
            norm.append(want_n)
            pending.append({"range": f"'{tab}'!{utils.a1(header_row, idx + 1)}", "values": [[title]]})
        cols[field_name] = idx
    return cols, pending


def topic_column(header: list[str], columns_map: dict[str, list[str]]) -> int:
    """0-based topic column index, via the reader's own candidate map."""
    resolved = resolve_columns(header, columns_map)
    if "topic" not in resolved:
        raise ValueError(f"no topic column among headers {header!r}")
    return resolved["topic"]


def find_row_by_topic(
    service: Any,
    spreadsheet_id: str,
    tab: str,
    header_row: int,
    topic_col: int,
    topic: str,
) -> int | None:
    """1-based row whose topic cell normalizes equal to ``topic``; None when absent."""
    utils = sheet_utils()
    col = utils.col_letter(topic_col)
    rng = f"'{tab}'!{col}{header_row + 1}:{col}{header_row + MAX_SCAN_ROWS}"
    values = gapi.call(sheet_utils().get_sheet_values, service, spreadsheet_id, rng)
    want = normalize(topic)
    matches = [
        header_row + 1 + i
        for i, row in enumerate(values)
        if row and row[0] is not None and normalize(str(row[0])) == want
    ]
    if not matches:
        return None
    if len(matches) > 1:
        log.warning(f"sheet: topic {topic!r} matches rows {matches} — writing the first")
    return matches[0]


def row_updates(
    tab: str,
    row: int,
    cols: dict[str, int],
    *,
    url: str,
    version: str,
    slides: int,
    link_style: str = "url",
    locale: str | None = None,
) -> list[dict]:
    """The three per-cell batch entries for one deck's row. Pure — no API calls.

    >>> [u["range"] for u in row_updates("S", 5, {"url": 4, "version": 5, "slides": 6},
    ...                                  url="https://x", version="3.14", slides=52)]
    ["'S'!E5", "'S'!F5", "'S'!G5"]
    """
    utils = sheet_utils()
    if link_style == "hyperlink":
        sep = utils.formula_sep(locale)
        url_value = f'=HYPERLINK("{url}"{sep} "pptx")'
    else:
        url_value = url
    values = {"url": url_value, "version": f"v{version}", "slides": slides}
    return [
        {"range": f"'{tab}'!{utils.a1(row, cols[f] + 1)}", "values": [[values[f]]]}
        for f in ("url", "version", "slides")
        if f in cols
    ]


def apply_updates(service: Any, spreadsheet_id: str, updates: list[dict]) -> None:
    """One ``values().batchUpdate`` for header + data cells together."""
    if not updates:
        return
    gapi.run(
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates},
        )
    )
