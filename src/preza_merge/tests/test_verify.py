"""Verification: residual geometry within tolerance, content invariants exact."""

from pathlib import Path

import pytest

from preza_merge import model, rules, verify

_REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def cfg():
    return rules.MergeConfig.load(_REPO / "settings" / "merge.yml")


def test_small_residuals_pass(make_deck, cfg):
    a = model.load(make_deck("a", [("T", ["раз"])], body_width=6.2))
    b = model.load(make_deck("b", [("T", ["раз"])], body_width=6.4))  # 0.2" < 0.4" tolerance
    res = verify.structural(a, b, cfg)
    assert res.ok


def test_large_residuals_fail_with_a_slide_reference(make_deck, cfg):
    a = model.load(make_deck("a", [("T", ["раз"])], body_width=6.2))
    b = model.load(make_deck("b", [("T", ["раз"])], body_width=11.0))
    res = verify.structural(a, b, cfg)
    assert not res.ok
    assert any("1" in m for m in res.mismatches)


def test_invariants_catch_content_drift(make_deck):
    ours = model.load(make_deck("o", [("T", ["раз", "два"])]))
    merged_same = model.load(make_deck("m", [("T", ["раз", "два"])]))
    merged_drift = model.load(make_deck("d", [("T", ["раз", "ТРИ"])]))

    assert verify.invariants(ours, merged_same).ok
    bad = verify.invariants(ours, merged_drift)
    assert not bad.ok
    assert any("буллет" in m or "текст" in m for m in bad.mismatches)


def test_invariants_catch_a_lost_slide(make_deck):
    ours = model.load(make_deck("o", [("A", ["x"]), ("B", ["y"])]))
    merged = model.load(make_deck("m", [("A", ["x"])]))
    res = verify.invariants(ours, merged)
    assert not res.ok
    assert any("слайд" in m for m in res.mismatches)


def test_invariants_catch_lost_notes_and_links(make_deck):
    from pptx import Presentation

    ours_path = make_deck("o", [("A", ["x"])])
    prs = Presentation(str(ours_path))
    prs.slides[0].notes_slide.notes_text_frame.text = "заметка"
    run = prs.slides[0].placeholders[1].text_frame.paragraphs[0].runs[0]
    run.hyperlink.address = "https://example.com"
    prs.save(str(ours_path))

    ours = model.load(ours_path)
    merged = model.load(make_deck("m", [("A", ["x"])]))
    res = verify.invariants(ours, merged)
    assert not res.ok
    assert any("ссыл" in m for m in res.mismatches)
    assert any("заметк" in m for m in res.mismatches)
