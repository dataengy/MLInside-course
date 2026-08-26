"""Three-way slide alignment by title sequence."""

from preza_merge import align, model


def _deck(make_deck, name, titles):
    return model.load(make_deck(name, [(t, ["x"]) for t in titles]))


def test_new_slides_on_our_side_are_ours_only(make_deck):
    base = _deck(make_deck, "b", ["A", "B"])
    ours = _deck(make_deck, "o", ["A", "NEW", "B"])
    theirs = _deck(make_deck, "t", ["A", "B"])

    res = align.align3(base, ours, theirs)
    new = next(r for r in res.rows if r.title == "NEW")
    assert new.status == "ours-only"
    assert new.base is None and new.ours == 2 and new.theirs is None


def test_slides_present_everywhere_are_unchanged(make_deck):
    base = _deck(make_deck, "b", ["A", "B"])
    res = align.align3(base, _deck(make_deck, "o", ["A", "B"]), _deck(make_deck, "t", ["A", "B"]))
    assert {r.status for r in res.rows} == {"unchanged"}


def test_reviewer_only_slide_is_theirs_only(make_deck):
    base = _deck(make_deck, "b", ["A"])
    ours = _deck(make_deck, "o", ["A"])
    theirs = _deck(make_deck, "t", ["A", "THEIRS"])
    res = align.align3(base, ours, theirs)
    assert next(r for r in res.rows if r.title == "THEIRS").status == "theirs-only"


def test_slide_dropped_on_our_side(make_deck):
    base = _deck(make_deck, "b", ["A", "GONE"])
    ours = _deck(make_deck, "o", ["A"])
    theirs = _deck(make_deck, "t", ["A", "GONE"])
    res = align.align3(base, ours, theirs)
    assert next(r for r in res.rows if r.title == "GONE").status == "dropped"


def test_duplicate_titles_are_reported_not_guessed(make_deck):
    base = _deck(make_deck, "b", ["DUP", "DUP"])
    ours = _deck(make_deck, "o", ["DUP", "DUP"])
    theirs = _deck(make_deck, "t", ["DUP", "DUP"])
    res = align.align3(base, ours, theirs)
    assert "DUP" in res.unaligned
