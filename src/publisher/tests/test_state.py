"""state: cursor roundtrip, atomicity, tolerance (style: preza_gen/tests/test_scan.py)."""

from publisher import state as st


def test_roundtrip_atomic(tmp_path):
    cur = tmp_path / "deep" / "cursor.json"
    ds = st.DeckState(version="1.2", sig="1:2", slides=52, drive_file_id="F1", drive_url="https://v")
    ds.tg = st.LegStatus("ok", "2026-08-16T00:00:00+00:00")
    ds.sheet_cols = {"url": 4}
    st.write_state_atomic(cur, {"X": ds})

    back = st.read_state(cur)
    assert back["X"].version == "1.2"
    assert back["X"].tg.status == "ok"
    assert back["X"].drive.status == "pending"
    assert back["X"].sheet_cols == {"url": 4}
    assert not cur.with_suffix(cur.suffix + ".tmp").exists()


def test_read_missing_and_corrupt(tmp_path):
    assert st.read_state(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert st.read_state(bad) == {}
    bad.write_text('["a list, not a dict"]', encoding="utf-8")
    assert st.read_state(bad) == {}


def test_reset_keeps_identities():
    ds = st.DeckState(version="1.1", sig="a", slides=50, drive_file_id="F1", drive_url="https://v")
    ds.tg = st.LegStatus("ok")
    ds.sheet_cols = {"url": 4}
    ds.published_at = "t"
    ds.reset_for("1.2", "b")
    assert (ds.version, ds.sig) == ("1.2", "b")
    assert ds.tg.status == "pending" and ds.published_at is None and ds.slides is None
    # identities survive a version bump — they are what keeps the Drive URL stable
    assert ds.drive_file_id == "F1" and ds.sheet_cols == {"url": 4}
