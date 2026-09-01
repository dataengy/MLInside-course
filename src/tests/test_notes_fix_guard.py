"""Страж `notes_fix`: правка заметок обязана менять форматирование, а не содержание.

Скрипт переносит строки, ставит часы и поднимает первую букву буллета. Перед записью он
сравнивает «плоский» текст до и после и отказывается писать файл, если разошлось. У стража
две противоположные ошибки, и тесты стерегут обе: пропустить настоящую потерю текста —
и упасть на честной переверстке. Второе однажды уже случилось: частичная нормализация
регистра была асимметрична (в прозе фраза стоит в середине строки, в буллетах — в начале),
и `apply` падал на КАЖДОЙ деке, которую ещё не прогоняли.
"""

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "preza"))

import notes_fix  # noqa: E402  # ty: ignore[unresolved-import]  # путь добавлен выше

PROSE = "[~1 мин] **Главное:** это не конкурс подходов. Ни один из них не требование dbt."
BULLETS = (
    "[00:00–01:00 · ~1 мин] **Главное:**\n"
    "- Это не конкурс подходов.\n"
    "- Ни один из них не требование dbt."
)


def test_guard_accepts_prose_reflowed_into_bullets():
    """Проза и она же буллетами — одно содержание, страж обязан пропустить."""
    assert notes_fix._plain(PROSE) == notes_fix._plain(BULLETS)


def test_guard_still_catches_a_real_change_of_text():
    assert notes_fix._plain(PROSE) != notes_fix._plain(BULLETS.replace("конкурс", "конкурсы"))
    assert notes_fix._plain(PROSE) != notes_fix._plain(
        BULLETS.replace("- Ни один из них не требование dbt.", "")
    )


def _deck(tmp_path: Path, notes: str) -> Path:
    doc = {
        "deck": {"out_name": "Prose", "naming": "fixed", "version_major": 4,
                 "format": "alina-2026-08", "source_deck": "data/source/шаблон.pptx"},
        "content": [{"kind": "content", "id": "001-proza", "title": "Слайд",
                     "bullets": ["раз"], "notes": notes + "\n"}],
    }
    path = tmp_path / "content.yml"
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _run(path: Path, cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "preza" / "notes_fix.py"), cmd, str(path)],
        capture_output=True, text=True, cwd=REPO,
    )


def test_apply_processes_a_deck_whose_notes_are_still_prose(tmp_path):
    """Дека, которую ещё не прогоняли, — основной сценарий, а не краевой."""
    path = _deck(tmp_path, PROSE)
    first = _run(path, "apply")
    assert first.returncode == 0, first.stdout + first.stderr

    notes = yaml.safe_load(path.read_text(encoding="utf-8"))["content"][0]["notes"]
    assert notes.startswith("[00:00–01:00 · ~1 мин] **Главное:**\n- Это не конкурс подходов.")

    second = _run(path, "check")
    assert second.returncode == 0, "второй прогон обязан сказать «совпадает»"
    assert "совпадает" in second.stdout
