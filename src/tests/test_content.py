"""Content-model tests for the settings + content yamls (fast; no rendering)."""

from pathlib import Path

from preza_gen import settings

# deck config lives in the course repo's content/ (the generator is a submodule)
_CONTENT = Path(__file__).resolve().parents[2] / "content"
SETTINGS_YML = _CONTENT / "build_deck_v3-settings.yml"
CONTENT_YML = _CONTENT / "preza-dbt-v3-content.yml"


def load():
    return settings.load(SETTINGS_YML, CONTENT_YML)


def test_content_loads():
    cfg, content = load()
    assert len(content.slides) == 70
    assert content.slides[0].kind == "title"
    assert content.slides[-1].kind == "closing"
    assert cfg.theme.accent == "2419FF"


def test_code_slides_present():
    _, content = load()
    # 13 from the source deck + 1 in the Olist ДЗ section + 3 in the packages block
    # + 1 moved in with SQLMesh from the Dagster deck (2026-08-24)
    # + пакеты в CI, slim CI, SQLMesh поверх dbt − схлопнутый SQLMesh-слайд (2026-08-25)
    # + моделирование/DV, MV в ClickHouse, микробатчинг, стриминг, гранты,
    #   dbt_project_evaluator (2026-08-25)
    assert sum(1 for s in content.slides if s.code) == 26
    assert all(s.bullets for s in content.slides if s.code)


def test_typed_config_and_naming():
    cfg, _ = load()
    # base stem carries no version — pipeline resolves it at build time
    assert cfg.out_name == "MLInside_Введение-в-dbt"
    assert cfg.naming == "increment"
    assert cfg.version_major == 3
    assert cfg.generation.parallel is False
    assert cfg.image_box.width == 5.5
    assert cfg.layouts["title"] == cfg.layouts.title  # subscript == attribute


def test_no_author_strings():
    _, content = load()
    blob = " ".join(
        s.title + s.subtitle + " ".join(map(str, s.bullets)) + s.notes for s in content.slides
    )
    # author identifiers only — "Data Engineer" is a legitimate role term in the content
    for bad in ("Крупий", "hnkovr", "NikolayKrupiy", "t.me/Nikolay"):
        assert bad not in blob, f"author string leaked: {bad}"


def test_kinds_and_layouts_valid():
    cfg, content = load()
    valid = {"title", "agenda", "section", "content", "table", "closing"}
    for s in content.slides:
        assert s.kind in valid
        assert s.kind in cfg.layouts  # every kind maps to a template layout


def test_title_has_no_subtitle():
    _, content = load()
    assert content.slides[0].subtitle == ""  # reference-aligned: title-only


def test_dbt_deck_uses_the_merged_format_profile():
    """The dbt deck ships with the reviewer-derived profile (docs/preza-merge-lane.md)."""
    cfg, _ = load()
    assert cfg.format_name == "alina-2026-08"
    assert cfg.fmt.body_font == "inherit"
    assert cfg.fmt.visual_anchor == "bottom"
