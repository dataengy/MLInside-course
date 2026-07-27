"""Bridge to ``integrations/google/sheets`` — the only place that knows the path shim.

``integrations/google/sheets/`` holds the Sheets client hardlinked from pdp
(``connector.py``, ``utils.py``) plus this repo's ``auth.py``. Putting
``integrations/google`` on ``sys.path`` makes them importable as the ``sheets`` package,
mirroring pdp's own ``from gsheets import connector``.

Imports are deferred into the functions so that merely importing this module (pytest
collects it for doctests) never needs the ``gsheets`` extra installed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
INTEGRATIONS_GOOGLE = REPO_ROOT / "integrations" / "google"


def _ensure_path() -> None:
    """Put ``integrations/google`` on ``sys.path`` (idempotent)."""
    p = str(INTEGRATIONS_GOOGLE)
    if p not in sys.path:
        if not (INTEGRATIONS_GOOGLE / "sheets" / "auth.py").exists():
            raise RuntimeError(
                f"Sheets integration missing at {INTEGRATIONS_GOOGLE / 'sheets'} — restore the "
                "hardlinks: python3 ~/.ai/integrations/_relink-actualized.py"
            )
        sys.path.insert(0, p)


def get_service(scopes: list[str] | None = None) -> Any:
    """Authenticated Sheets v4 service (ADC first — see ``integrations/google/sheets/auth.py``)."""
    _ensure_path()
    from sheets import auth

    return auth.get_service(scopes)


def sheet_utils() -> Any:
    """The hardlinked ``utils`` module (``get_sheet_values``, ``list_sheet_names``, …)."""
    _ensure_path()
    from sheets import utils

    return utils
