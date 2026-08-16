"""gsheet_write: header-ensure algebra, topic matching (ё/е), A1 ranges, batch shape."""

from unittest.mock import MagicMock

from publisher import gsheet_write as gw


def test_ensure_columns_all_present_no_writes():
    header = ["старая запись", "название", "тезисы", "лектор", "pptx (GDrive)", "версия", "слайдов"]
    wanted = {"url": "pptx (GDrive)", "version": "версия", "slides": "слайдов"}
    cols, pending = gw.ensure_columns(header, "S", 1, wanted, known={})
    assert cols == {"url": 4, "version": 5, "slides": 6}
    assert pending == []


def test_ensure_columns_appends_missing_in_order():
    header = ["старая запись", "название", "тезисы", "лектор"]
    wanted = {"url": "pptx (GDrive)", "version": "версия", "slides": "слайдов"}
    cols, pending = gw.ensure_columns(header, "Лист1", 1, wanted, known={})
    assert cols == {"url": 4, "version": 5, "slides": 6}
    assert [p["range"] for p in pending] == ["'Лист1'!E1", "'Лист1'!F1", "'Лист1'!G1"]
    assert [p["values"][0][0] for p in pending] == ["pptx (GDrive)", "версия", "слайдов"]


def test_ensure_columns_known_position_reused_and_normalized():
    # header text was hand-edited («Версия» vs «версия») but position matches → reuse, no append
    header = ["название", "Версия"]
    cols, pending = gw.ensure_columns(header, "S", 1, {"version": "версия"}, known={"version": 1})
    assert cols == {"version": 1} and pending == []


def test_ensure_columns_adopts_manually_added_column():
    header = ["название", "слайдов"]
    cols, pending = gw.ensure_columns(header, "S", 1, {"slides": "Слайдов"}, known={})
    assert cols == {"slides": 1} and pending == []


def test_topic_column_via_reader_candidates():
    header = ["старая запись", "название", "тезисы", "лектор"]
    cmap = {"topic": ["тема", "topic", "название"], "owner": ["лектор"]}
    assert gw.topic_column(header, cmap) == 1


def _sheet_service(values):
    svc = MagicMock()
    svc.spreadsheets().values().get().execute.return_value = {"values": values}
    return svc


def test_find_row_by_topic_normalizes_yo():
    svc = _sheet_service([["Оркестрация данных (Apache Airflow)"], [], ["Трансформация данных и витрины (dbt)"]])
    row = gw.find_row_by_topic(svc, "SID", "S", 1, 1, "трансформация данных и витрины (dbt)")
    assert row == 4  # header_row 1 + offset 3
    assert gw.find_row_by_topic(svc, "SID", "S", 1, 1, "нет такой темы") is None


def test_row_updates_plain_url_and_hyperlink_ru_locale():
    cols = {"url": 4, "version": 5, "slides": 6}
    ups = gw.row_updates("S", 5, cols, url="https://x", version="3.14", slides=52)
    assert [u["range"] for u in ups] == ["'S'!E5", "'S'!F5", "'S'!G5"]
    assert [u["values"][0][0] for u in ups] == ["https://x", "v3.14", 52]

    hyp = gw.row_updates(
        "S", 5, cols, url="https://x", version="3.14", slides=52,
        link_style="hyperlink", locale="ru_RU",
    )
    assert hyp[0]["values"][0][0] == '=HYPERLINK("https://x"; "pptx")'


def test_apply_updates_single_batch_user_entered():
    svc = MagicMock()
    gw.apply_updates(svc, "SID", [{"range": "'S'!E5", "values": [["u"]]}])
    body = svc.spreadsheets().values().batchUpdate.call_args.kwargs["body"]
    assert body["valueInputOption"] == "USER_ENTERED" and len(body["data"]) == 1
    svc.reset_mock()
    gw.apply_updates(svc, "SID", [])
    svc.spreadsheets().values().batchUpdate.assert_not_called()
