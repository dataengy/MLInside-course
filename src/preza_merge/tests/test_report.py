"""The proposal is the human's decision surface — it must be complete and machine-readable."""

from pathlib import Path

import yaml

from preza_merge import report, rules

_REPO = Path(__file__).resolve().parents[3]


def _ctx(tmp_path):
    findings = [
        rules.Finding("R1", "format", "body_font", "inherit", 1.0, "сняты явные размеры", [1, 2]),
        rules.Finding("R8", "regression", None, {"minor": "Calibri"}, 1.0, "шрифты темы", []),
    ]
    return report.ProposalContext(
        deck="content/x.yml",
        base_pptx=tmp_path / "b.pptx",
        ours_pptx=tmp_path / "o.pptx",
        theirs_pptx=tmp_path / "t.pptx",
        base_content_rev="abc1234",
        profile_name="merged",
        findings=findings,
        alignment=None,
        diffs={},
    )


def test_proposal_carries_a_decision_slot_per_format_rule(tmp_path):
    _, prop = report.write(tmp_path / "case", _ctx(tmp_path))
    data = yaml.safe_load(prop.read_text(encoding="utf-8"))

    rules_block = data["proposal"]["rules"]
    assert rules_block[0]["rule"] == "R1"
    assert rules_block[0]["decision"] is None  # awaits the human
    assert rules_block[0]["key"] == "body_font"
    assert "regressions" in data["proposal"]
    assert data["proposal"]["regressions"][0]["rule"] == "R8"
    assert "decision" not in data["proposal"]["regressions"][0]


def test_markdown_report_states_the_evidence(tmp_path):
    md, _ = report.write(tmp_path / "case", _ctx(tmp_path))
    text = md.read_text(encoding="utf-8")
    assert "R1" in text and "сняты явные размеры" in text
    assert "R8" in text and "шрифты темы" in text


def test_undecided_rules_are_detectable(tmp_path):
    _, prop = report.write(tmp_path / "case", _ctx(tmp_path))
    assert report.undecided(report.load_proposal(prop)) == ["R1"]


def test_accepted_rules_become_profile_keys(tmp_path):
    _, prop = report.write(tmp_path / "case", _ctx(tmp_path))
    data = report.load_proposal(prop)
    data["proposal"]["rules"][0]["decision"] = "accept"
    assert report.accepted_keys(data) == {"body_font": "inherit"}


def test_two_ours_versions_get_two_different_report_stems(tmp_path):
    """Regression: deck filenames carry a version dot (v3.18, v3.19). Path.with_suffix
    treats the LAST dot in the whole stem as an existing extension and replaces everything
    after it — so two different `ours` versions merged against the same fork used to
    collapse onto the SAME report filename, silently overwriting one another.
    """
    stem_18 = tmp_path / "MLInside_x_v3.18_x_fork_v3.15"
    stem_19 = tmp_path / "MLInside_x_v3.19_x_fork_v3.15"
    md_18, prop_18 = report.write(stem_18, _ctx(tmp_path))
    md_19, prop_19 = report.write(stem_19, _ctx(tmp_path))

    assert md_18 != md_19
    assert prop_18 != prop_19
    assert md_18.name == "MLInside_x_v3.18_x_fork_v3.15.md"
    assert prop_18.name == "MLInside_x_v3.18_x_fork_v3.15.proposal.yml"
    assert md_19.name == "MLInside_x_v3.19_x_fork_v3.15.md"
