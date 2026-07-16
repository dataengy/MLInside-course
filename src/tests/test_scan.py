"""Scan cursor tests — change detection + atomic state + seed (tmp_path; prefect-free)."""

from preza_gen import scan


def test_scan_detects_new_and_changed(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    d = tmp_path / "drafts"
    d.mkdir()
    (d / "b.txt").write_text("x")
    watched = scan.expand_watch(["a.txt", "drafts", "missing.txt"], tmp_path)
    assert len(watched) == 2  # missing.txt skipped

    changed, new_state = scan.scan_changed(watched, {})
    assert len(changed) == 2  # everything new on first pass

    changed2, _ = scan.scan_changed(watched, new_state)
    assert changed2 == []  # nothing changed second time

    (tmp_path / "a.txt").write_text("22")  # size change → new signature
    changed3, _ = scan.scan_changed(watched, new_state)
    assert len(changed3) == 1
    assert changed3[0].path.endswith("a.txt")


def test_state_roundtrip_atomic(tmp_path):
    cursor = tmp_path / ".state" / "cursor.json"
    scan.write_state_atomic(cursor, {"k": "1:2"})
    assert scan.read_state(cursor) == {"k": "1:2"}
    assert scan.read_state(tmp_path / "nope.json") == {}  # missing → empty


def test_seed_writes_without_flagging(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    watched = scan.expand_watch(["a.txt"], tmp_path)
    cursor = tmp_path / "cur.json"
    assert scan.seed(watched, cursor) == 1
    changed, _ = scan.scan_changed(watched, scan.read_state(cursor))
    assert changed == []  # seeded current state → no changes flagged
