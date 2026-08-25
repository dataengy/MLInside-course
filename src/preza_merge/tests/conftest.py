"""Synthetic decks for merge-lane tests — built on python-pptx's own template.

Deliberately independent of the course template (data/ is git-lfs): the merge lane must be
testable on any checkout.
"""

from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Inches, Pt


def _add(prs, title, bullets, *, sizes=None, body_width=None, body_top=None):
    slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title and Content
    slide.shapes.title.text = title
    body = slide.placeholders[1]
    if body_width is not None:
        body.width = Inches(body_width)
    if body_top is not None:
        body.top = Inches(body_top)
    tf = body.text_frame
    tf.clear()
    for i, text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        if sizes is not None:
            for r in p.runs:
                r.font.size = Pt(sizes)
    return slide


@pytest.fixture
def make_deck(tmp_path):
    """make_deck("name", [(title, [bullets]), ...], sizes=20) -> Path to a .pptx"""

    def _make(name: str, slides, *, sizes=None, body_width=None, body_top=None) -> Path:
        prs = Presentation()
        for title, bullets in slides:
            _add(prs, title, bullets, sizes=sizes, body_width=body_width, body_top=body_top)
        out = tmp_path / f"{name}.pptx"
        prs.save(str(out))
        return out

    return _make
