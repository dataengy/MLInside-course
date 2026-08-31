"""Деки чужих лекторов не правятся нашим инструментом — запрет и его источник.

Исключение живёт в настройках (`deck_generation.editing_excluded`), а срабатывает на
единственной точке записи контента, поэтому тест проверяет обе стороны: что список
действительно содержит чужую деку и что запись по ней не проходит.
"""

import sys
from pathlib import Path

import click
import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "preza"))

import edit_slides  # noqa: E402

AIRFLOW = "content/preza-apache-airflow-content.yml"


def _excluded() -> list[str]:
    doc = yaml.safe_load((REPO / "settings" / "config.yml").read_text(encoding="utf-8")) or {}
    return list((doc.get("deck_generation") or {}).get("editing_excluded") or [])


def test_airflow_deck_is_excluded_in_settings():
    """Предмет ведёт Влад Бояджи — его содержание правим не мы."""
    assert AIRFLOW in _excluded()


def test_excluded_paths_exist():
    """Мёртвая запись в списке = молчаливо снятый запрет, поэтому пути проверяются."""
    for rel in _excluded():
        assert (REPO / rel).is_file(), rel


def test_write_refuses_an_excluded_deck():
    with pytest.raises(click.ClickException, match="вне нашей зоны правки"):
        edit_slides.refuse_if_excluded(REPO / AIRFLOW)


def test_write_allows_our_own_decks():
    edit_slides.refuse_if_excluded(REPO / "content" / "preza-dagster-content.yml")


def test_unreadable_settings_do_not_unlock_the_guard(monkeypatch, tmp_path):
    """Битые настройки должны падать, а не разрешать правку по умолчанию."""
    monkeypatch.setattr(edit_slides, "SETTINGS", tmp_path / "nope.yml")
    with pytest.raises(click.ClickException, match="не читаются настройки"):
        edit_slides.refuse_if_excluded(REPO / AIRFLOW)
