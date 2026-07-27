#!/usr/bin/env python3
"""Google Sheets auth for this repo — ADC first, connector.py's SA/OAuth as fallback.

PROJECT-OWNED file: unlike its siblings ``connector.py`` / ``utils.py`` / ``__init__.py``
(hardlinked from ``~/pdp.deploy_dev/scripts/tools-utils/gsheets/`` — editing those changes
every copy), this module lives only here and is safe to edit.

Why it exists: ``connector.py`` resolves a service account from ``~/.ai/settings/gcloud.yml``
and falls back to an OAuth *client-secret* flow. Neither fits the course sheet, which is owned
by a personal Google account. Application Default Credentials read the sheet **as you** with no
new secret file and no sharing step:

    gcloud auth application-default login --account=hnkovr@gmail.com \\
      --scopes=openid,https://www.googleapis.com/auth/spreadsheets.readonly,\\
https://www.googleapis.com/auth/drive.readonly

The registry's ``default:`` account is the Prodamus SA, which has no access to this sheet — so
a silent fall-through would 403 confusingly. Every path logs which credential it picked.
"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as log

READONLY_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

_ADC_HINT = (
    "Run: gcloud auth application-default login --account=<you>@gmail.com "
    "--scopes=openid,https://www.googleapis.com/auth/spreadsheets.readonly,"
    "https://www.googleapis.com/auth/drive.readonly"
)


def _build(credentials):
    try:
        from googleapiclient.discovery import build
    except ImportError:
        log.error("Missing dependency — run: uv sync --extra gsheets")
        sys.exit(1)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _adc(scopes: list[str]):
    """Application Default Credentials (`gcloud auth application-default login`)."""
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    try:
        creds, project = google.auth.default(scopes=scopes)
    except DefaultCredentialsError as e:
        log.debug(f"ADC unavailable: {e}")
        return None

    who = getattr(creds, "service_account_email", None) or getattr(creds, "quota_project_id", None)
    log.info(f"Auth: ADC ({who or project or 'user credentials'})")
    return _build(creds)


def get_service(scopes: list[str] | None = None):
    """Return an authenticated Sheets v4 service.

    Order: ADC → ``connector.get_service`` (service account from the gcloud registry, then
    an OAuth client-secret flow). Raises ``RuntimeError`` if every path is exhausted.
    """
    scopes = scopes or READONLY_SCOPES

    service = _adc(scopes)
    if service is not None:
        return service

    log.warning(f"No ADC credentials found — falling back to service account. {_ADC_HINT}")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import connector
    except ImportError as e:  # pragma: no cover — the hardlinked sibling is always present
        raise RuntimeError(f"Neither ADC nor connector.py is usable: {e}") from e

    return connector.get_service(scopes=scopes)
