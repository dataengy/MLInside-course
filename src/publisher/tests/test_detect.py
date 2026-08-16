"""detect: version parsing over data/generated fixtures (style: preza_gen/tests/test_scan.py)."""

from pathlib import Path

from publisher import detect


def _touch(d: Path, name: str, payload: bytes = b"x") -> Path:
    p = d / name
    p.write_bytes(payload)
    return p


def test_find_versions_sorted_and_stem_exact(tmp_path):
    _touch(tmp_path, "MLInside_X_v1.2.pptx")
    _touch(tmp_path, "MLInside_X_v1.10.pptx")
    _touch(tmp_path, "MLInside_X_v2.1.pptx")
    _touch(tmp_path, "MLInside_X-extra_v9.9.pptx")  # different deck
    _touch(tmp_path, "MLInside_X_v2-old_v1.3.pptx")  # stem mismatch after regex strip
    _touch(tmp_path, "MLInside_X_v1.2.html")  # wrong extension

    versions = detect.find_versions(tmp_path, "MLInside_X")
    assert [(v.major, v.minor) for v in versions] == [(1, 2), (1, 10), (2, 1)]
    assert versions[-1].version == "2.1"


def test_newest_none_for_never_built(tmp_path):
    assert detect.newest(tmp_path, "MLInside_Never") is None
    assert detect.newest(tmp_path / "missing-dir", "X") is None


def test_sig_changes_with_content(tmp_path):
    p = _touch(tmp_path, "MLInside_X_v1.1.pptx", b"aa")
    s1 = detect.sig(p)
    p.write_bytes(b"aaaa")
    assert detect.sig(p) != s1
