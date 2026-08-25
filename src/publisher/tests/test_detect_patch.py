"""The publisher must see a patch build as a newer version than its parent."""

from publisher import detect


def _touch(d, name):
    p = d / name
    p.write_bytes(b"x")
    return p


def test_patch_version_is_newer_than_its_parent(tmp_path):
    _touch(tmp_path, "Deck_v3.19.pptx")
    _touch(tmp_path, "Deck_v3.19.1+alina-fmt.pptx")

    newest = detect.newest(tmp_path, "Deck")
    assert newest is not None
    assert (newest.major, newest.minor, newest.patch) == (3, 19, 1)
    assert newest.descr == "alina-fmt"
    assert newest.version == "3.19.1+alina-fmt"


def test_plain_versions_keep_their_shape(tmp_path):
    _touch(tmp_path, "Deck_v3.19.pptx")
    newest = detect.newest(tmp_path, "Deck")
    assert newest.version == "3.19"
    assert newest.patch == 0


def test_exact_stem_still_required(tmp_path):
    _touch(tmp_path, "Deck-old_v9.9.pptx")
    _touch(tmp_path, "Deck_v3.19.1+x.pptx")
    assert detect.newest(tmp_path, "Deck").version == "3.19.1+x"


def test_ordering_ignores_the_build_tag(tmp_path):
    _touch(tmp_path, "Deck_v3.19.1+aaa.pptx")
    _touch(tmp_path, "Deck_v3.20.pptx")
    assert detect.newest(tmp_path, "Deck").version == "3.20"
