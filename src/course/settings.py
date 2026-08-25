"""Пути и скаляры ленты «правила продакшена курса». Fail-loud: нет ключа — нет дефолта."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_YML = REPO_ROOT / "settings" / "config.yml"
PLAN_YML = REPO_ROOT / "content" / "presentations.yml"

#: Секция settings/config.yml с правилами менеджера курса (SSoT скаляров).
SECTION = "course_production"


class MissingSetting(KeyError):
    """Ключ правил не задан — правило нельзя применить молча с выдуманным дефолтом."""


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def require(rules: dict, dotted: str) -> Any:
    """``rules['a']['b']`` по ``'a.b'`` с понятным сообщением вместо голого KeyError.

    >>> require({"lecture": {"block_max_min": 25}}, "lecture.block_max_min")
    25
    >>> require({"lecture": {}}, "lecture.block_max_min")
    Traceback (most recent call last):
    ...
    course.settings.MissingSetting: 'settings/config.yml → course_production.lecture.block_max_min: ключ не задан'
    """
    node: Any = rules
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            raise MissingSetting(f"settings/config.yml → {SECTION}.{dotted}: ключ не задан")
        node = node[key]
    return node


def load_rules(config_yml: Path = CONFIG_YML) -> dict:
    """``course_production`` из settings/config.yml (см. docs/course-rules.md)."""
    cfg = read_yaml(config_yml)
    if SECTION not in cfg:
        raise MissingSetting(
            f"{config_yml} → {SECTION}: секция не задана (см. docs/course-rules.md)"
        )
    return cfg[SECTION] or {}


def load_plan(plan_yml: Path = PLAN_YML) -> list[dict]:
    """Записи ``presentations:`` из content/presentations.yml."""
    return list(read_yaml(plan_yml).get("presentations") or [])
