"""Общая оснастка тестов демо 1.

Тесты проверяют КАНОН — stash/ml.py, а не рабочую копию defs/ml.py: рабочая появляется
только на шаге 2 демо (`just add-assets`) и по ходу показа правится вживую.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]  # ml-platform/
DEMO = ROOT.parent  # 01-quickstart/


def _load_by_path(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def ml():
    """Канонический defs/ml.py демо — три ассета, проверка и политика свежести."""
    return _load_by_path("demo1_ml", DEMO / "stash" / "ml.py")


@pytest.fixture(scope="session")
def make_features():
    """scripts/make_features.py — сборка витрины признаков на pandas."""
    return _load_by_path("demo1_make_features", DEMO / "scripts" / "make_features.py")


@pytest.fixture
def in_project(tmp_path, monkeypatch):
    """Ассеты демо читают и пишут по ОТНОСИТЕЛЬНЫМ путям (features.parquet, models/).

    Это осознанно: на слайдах не должно быть возни с путями. Цена — тесты обязаны
    задавать рабочую папку сами, иначе прогон затрёт состояние демо.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def features(in_project, make_features) -> pd.DataFrame:
    """Витрина признаков на срезе по умолчанию, положенная рядом как features.parquet."""
    df = make_features.build(make_features.DEFAULT_CUTOFF)
    df.to_parquet(in_project / "features.parquet")
    return df
