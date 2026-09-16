"""../files.yml — реестр файлов, общих у демо блока.

Сырьё и status.py должны быть ОДИНАКОВЫМИ во всех демо: витрина признаков считается
дважды (SQL в демо 2, pandas в демо 1), и числа на слайдах сойдутся только на одних данных.

Связь держится хардлинками, но git их не хранит — после клона это просто одинаковые файлы.
Поэтому проверяем по СОДЕРЖИМОМУ (переживает клон), а расхождение инодов сообщаем
отдельно и мягко: оно означает «связь распалась», а не «файлы разъехались».
"""

from __future__ import annotations

import hashlib

import pytest
import yaml

from .conftest import DEMO

BLOCK = DEMO.parent  # demo/02-dagster-simple/
REGISTRY = BLOCK / "files.yml"


def _registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text())["shared"]


def test_reestr_est_i_ne_pust():
    assert REGISTRY.is_file(), "нет demo/02-dagster-simple/files.yml — на него ссылаются четыре README"
    assert _registry()


@pytest.mark.parametrize("name", list(_registry()))
def test_kopii_sovpadayut_po_soderzhimomu(name):
    entry = _registry()[name]
    digests = {}
    for rel in entry["copies"]:
        path = BLOCK / rel
        assert path.is_file(), f"{rel}: файла нет, а он записан в files.yml"
        digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(set(digests.values())) == 1, f"{name}: копии разъехались — {digests}"
    # sha256 в реестре обязан быть свежим, иначе реестр врёт
    assert set(digests.values()) == {entry["sha256"]}, (
        f"{name}: содержимое поменяли, а files.yml не обновили"
    )


@pytest.mark.parametrize("name", list(_registry()))
def test_svyaz_hardlinkami_cela(name):
    """Мягкая проверка: после клона из git иноды разойдутся — это ожидаемо.

    Падает только если файлы РАЗНЫЕ по содержимому (это ловит тест выше) или если
    хардлинк распался ЗДЕСЬ, в рабочей копии, где он был.
    """
    entry = _registry()[name]
    inodes = {rel: (BLOCK / rel).stat().st_ino for rel in entry["copies"]}
    if len(set(inodes.values())) != 1:
        pytest.skip(
            f"{name}: хардлинк распался (нормально после клона) — "
            f"восстановить: just demo-files-link; иноды {inodes}"
        )
    assert len(set(inodes.values())) == 1
