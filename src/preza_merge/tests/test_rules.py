"""Rule detectors: a systematic change becomes a profile key, a one-off does not."""

from pathlib import Path

import pytest
from pptx import Presentation

from preza_merge import diff, model, rules

_REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def cfg():
    return rules.MergeConfig.load(_REPO / "settings" / "merge.yml")


def _found(findings, rule):
    return next((f for f in findings if f.rule == rule), None)


def test_r1_fires_when_explicit_sizes_are_cleared(make_deck, cfg):
    base = model.load(make_deck("b", [("A", ["раз", "два"]), ("B", ["три"])], sizes=20))
    theirs = model.load(make_deck("t", [("A", ["раз", "два"]), ("B", ["три"])]))
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R1")
    assert found is not None
    assert found.key == "body_font" and found.value == "inherit"
    assert "3" in found.evidence  # three runs lost their explicit size


def test_r1_stays_silent_below_the_share_threshold(make_deck, cfg):
    """One slide out of five is a one-off, not a rule."""
    from pptx.util import Pt

    slides = [(f"S{i}", ["раз"]) for i in range(5)]
    base = model.load(make_deck("b", slides, sizes=20))
    path = make_deck("t", slides, sizes=20)
    prs = Presentation(str(path))
    for run in prs.slides[0].placeholders[1].text_frame.paragraphs[0].runs:
        run.font.size = None
    prs.save(str(path))
    theirs = model.load(path)
    assert _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R1") is None


def test_r4_fires_when_the_bullet_column_widens(make_deck, cfg):
    """A code panel on the slide is what makes it eligible for R4 at all."""
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    def _with_panel(name, width):
        path = make_deck(name, [("A", ["x"]), ("B", ["y"])], body_width=width)
        prs = Presentation(str(path))
        for slide in prs.slides:
            slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(1), Inches(2), Inches(1)
            )
        prs.save(str(path))
        return model.load(path)

    base = _with_panel("b", 6.2)
    theirs = _with_panel("t", 10.0)
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R4")
    assert found is not None and found.key == "bullets_width" and found.value == "adaptive"


def test_r4_stays_silent_when_no_slide_carries_a_visual(make_deck, cfg):
    """Bullets can widen all they like; without a code panel or picture on the slide R4's
    cohort is empty — the rule must not fire on a bullets-only slide."""
    base = model.load(make_deck("b", [("A", ["x"]), ("B", ["y"])], body_width=6.2))
    theirs = model.load(make_deck("t", [("A", ["x"]), ("B", ["y"])], body_width=10.0))
    assert _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R4") is None


def test_r1_denominator_is_slides_with_explicit_sizes_not_all_paragraphs(make_deck, cfg):
    """4 of 8 slides start with explicit run sizes; the other 4 never had one. Clearing all
    4 sized slides must read as share=1.0 (4/4), not 0.5 (4/8) — the unsized slides, which
    would dilute an "any paragraph" cohort, must not enter R1's denominator at all."""
    sized = [(f"S{i}", ["раз"]) for i in range(4)]
    unsized = [(f"U{i}", ["два"]) for i in range(4)]

    base_path = make_deck("b", sized, sizes=20)
    prs = Presentation(str(base_path))
    for title, bullets in unsized:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title
        body = slide.placeholders[1]
        body.name = "Text Placeholder 2"
        body.text_frame.text = bullets[0]  # no explicit run size set
    prs.save(str(base_path))
    base = model.load(base_path)

    # theirs never had explicit sizes anywhere — every sized run in base gets cleared.
    theirs = model.load(make_deck("t", sized + unsized))

    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R1")
    assert found is not None
    assert found.share == 1.0


def test_merge_config_threshold_uses_override_or_falls_back_to_min_share(cfg):
    assert cfg.threshold("R4") == 0.75
    assert cfg.threshold("R6") == 0.70
    assert cfg.threshold("R1") == cfg.min_share


def test_r11_fires_when_the_panel_border_goes_dark(make_deck, cfg):
    """The manager removed the blue outline on every code panel."""
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    def _with_panels(name, color):
        path = make_deck(name, [("A", ["x"]), ("B", ["y"])])
        prs = Presentation(str(path))
        for slide in prs.slides:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(1), Inches(2), Inches(1)
            )
            shape.line.color.rgb = RGBColor.from_string(color)
        prs.save(str(path))
        return model.load(path)

    base = _with_panels("b", "2419FF")
    theirs = _with_panels("t", "1A1A1A")
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R11")
    assert found is not None
    assert found.key == "code_border" and found.value == "dark"


def test_r8_regression_on_theme_font_swap(make_deck, cfg):
    """A theme-font swap is an export artefact — reported, never merged."""
    base = model.load(make_deck("b", [("A", ["x"])]))
    loaded = model.load(make_deck("t", [("A", ["x"])]))
    theirs = model.Deck(
        path=loaded.path,
        slides=loaded.slides,
        theme_fonts={"major": "Calibri Light", "minor": "Calibri"},
        master_body_sizes=loaded.master_body_sizes,
    )
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R8")
    assert found is not None and found.kind == "regression" and found.key is None


def test_r10_regression_when_notes_are_lost(make_deck, cfg):
    base_path = make_deck("b", [("A", ["x"])])
    prs = Presentation(str(base_path))
    prs.slides[0].notes_slide.notes_text_frame.text = "заметка"
    prs.save(str(base_path))
    base = model.load(base_path)
    theirs = model.load(make_deck("t", [("A", ["x"])]))
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R10")
    assert found is not None and found.kind == "regression"


def test_config_loads_thresholds_from_yaml(cfg):
    assert cfg.min_share == 0.8
    assert cfg.tolerances["left"] == 0.4
    assert cfg.min_share_overrides["R4"] == 0.75
    assert cfg.min_share_overrides["R6"] == 0.70
