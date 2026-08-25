"""Applying a proposal: profile written, deck switched, patch built — and refusals."""

from pathlib import Path

import pytest
import yaml

from preza_merge import apply, rules

_REPO = Path(__file__).resolve().parents[3]


def _formats(tmp_path) -> Path:
    src = yaml.safe_load((_REPO / "settings" / "formats.yml").read_text(encoding="utf-8"))
    p = tmp_path / "formats.yml"
    p.write_text(yaml.safe_dump(src, allow_unicode=True), encoding="utf-8")
    return p


def test_profile_inherits_the_base_and_overrides_accepted_keys(tmp_path):
    path = _formats(tmp_path)
    apply.write_profile(path, "merged", "classic", {"body_font": "inherit", "table_top": 2.45})

    data = yaml.safe_load(path.read_text(encoding="utf-8"))["formats"]["merged"]
    assert data["body_font"] == "inherit"
    assert data["table_top"] == 2.45
    assert data["bullets_width_narrow"] == 6.2  # inherited from classic
    assert set(data) == set(yaml.safe_load(path.read_text(encoding="utf-8"))["formats"]["classic"])


def test_existing_profiles_survive_a_rewrite(tmp_path):
    path = _formats(tmp_path)
    apply.write_profile(path, "merged", "classic", {"table_top": 2.45})
    apply.write_profile(path, "other", "classic", {"table_top": 3.0})
    formats = yaml.safe_load(path.read_text(encoding="utf-8"))["formats"]
    assert {"classic", "merged", "other"} <= set(formats)
    assert formats["merged"]["table_top"] == 2.45


def test_deck_format_is_set_surgically(tmp_path):
    content = tmp_path / "deck.yml"
    content.write_text(
        "deck:\n  out_name: X   # keep me\n  naming: increment\n  version_major: 3\n"
        "content:\n- kind: title\n  title: T\n",
        encoding="utf-8",
    )
    assert apply.set_deck_format(content, "merged") is True
    text = content.read_text(encoding="utf-8")
    assert "format: merged" in text
    assert "# keep me" in text  # the surgical edit must not reformat the file
    assert yaml.safe_load(text)["deck"]["format"] == "merged"


def test_deck_format_replaces_an_existing_value(tmp_path):
    content = tmp_path / "deck.yml"
    content.write_text(
        "deck:\n  out_name: X\n  format: classic\ncontent: []\n", encoding="utf-8"
    )
    apply.set_deck_format(content, "merged")
    assert yaml.safe_load(content.read_text(encoding="utf-8"))["deck"]["format"] == "merged"


def test_apply_refuses_while_a_decision_is_missing(tmp_path):
    doc = {
        "proposal": {
            "deck": "content/x.yml",
            "base_pptx": "b.pptx",
            "ours_pptx": "o.pptx",
            "theirs_pptx": "t.pptx",
            "base_content_rev": "abc",
            "profile": "merged",
            "rules": [{"rule": "R1", "key": "body_font", "value": "inherit", "decision": None}],
            "regressions": [],
        }
    }
    cfg = rules.MergeConfig.load(_REPO / "settings" / "merge.yml")
    with pytest.raises(SystemExit, match="R1"):
        apply.run(
            doc,
            cfg,
            settings_yml=_REPO / "content" / "build_deck_v3-settings.yml",
            formats_path=_formats(tmp_path),
            patch_of="3.19",
            descr="x",
        )


def test_graft_backend_is_not_implemented(tmp_path):
    cfg = rules.MergeConfig.load(_REPO / "settings" / "merge.yml")
    with pytest.raises(NotImplementedError, match="graft"):
        apply.run(
            {"proposal": {"rules": [], "regressions": [], "profile": "merged",
                          "deck": "content/x.yml"}},
            cfg,
            settings_yml=_REPO / "content" / "build_deck_v3-settings.yml",
            formats_path=_formats(tmp_path),
            patch_of="3.19",
            descr="x",
            backend="graft",
        )
