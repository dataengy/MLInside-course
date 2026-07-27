#!/usr/bin/env python3
# ───────────────────────────────────────────────────────────────────────────
# HARDLINK-CANONICAL: ~/pdp.deploy_dev/scripts/tools-utils/gsheets/connector.py
# HARDLINK — one shared inode; editing changes EVERY copy. Do NOT save-via-rename
# (breaks the link): re-link `ln -f <canonical> <copy>`, verify inodes with `ls -li`.
#   canonical : ~/pdp.deploy_dev/scripts/tools-utils/gsheets/connector.py
#   linked    : ~/.ai/integrations/google/sheets/connector.py
#   linked-at : 2026-07-12  ·  via: ~/.ai/integrations/_relink-actualized.py
# ───────────────────────────────────────────────────────────────────────────
"""Google Sheets auth connector — service account primary, OAuth fallback."""
import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger as log


_REGISTRY = Path("~/.ai/settings/gcloud.yml").expanduser()
_FAIL_FAST = True #+by me

def _resolve_from_registry() -> str | None:
    """Auto-resolve SA file from ~/.ai/settings/gcloud.yml for cwd."""
    if not _REGISTRY.exists():
        return None
    try:
        import yaml
        cfg = yaml.safe_load(_REGISTRY.read_text())
        cwd = Path.cwd().resolve()
        accounts = cfg.get("accounts", [])
        best: tuple[int, str | None] = (0, None)
        for a in accounts:
            for proj in a.get("projects", []):
                proj_path = Path(proj).expanduser().resolve()
                try:
                    cwd.relative_to(proj_path)
                    depth = len(proj_path.parts)
                    if depth > best[0]:
                        best = (depth, a.get("sa_file"))
                except ValueError:
                    pass
        if best[1]:
            log.info(f"Auth: resolved SA from registry for {cwd}")
            return str(Path(best[1]).expanduser())
        # fallback to default account
        default_id = cfg.get("default")
        for a in accounts:
            if a["id"] == default_id:
                log.debug(f"Auth: using default registry account {default_id!r}")
                return str(Path(a["sa_file"]).expanduser())
    except Exception as e:
        log.debug(f"Registry resolve failed: {e}")
        if _FAIL_FAST: raise
    return None


def _build_service(credentials: Any):
    try:
        from googleapiclient.discovery import build
    except ImportError:
        log.error("Missing: pip install google-api-python-client")
        sys.exit(1)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def get_service(
    sa_file: str | None = None,
    oauth_client_secret: str | None = None,
    token_cache: str = ".ai/GSheets/.token.json",
    scopes: list[str] | None = None,
):
    """Return authenticated Google Sheets v4 service.

    Tries service account first, falls back to OAuth if SA file is absent.
    """
    scopes = scopes or [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    sa_file = sa_file or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")

    # Auto-resolve from ~/.ai/settings/gcloud.yml if env not set
    if not sa_file or not Path(sa_file).expanduser().exists():
        sa_file = _resolve_from_registry() or sa_file

    if sa_file and Path(sa_file).expanduser().exists():
        return _service_account(str(Path(sa_file).expanduser()), scopes)

    log.warning("Service account file not found or not set — falling back to OAuth")
    oauth_secret = oauth_client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "")
    return _oauth(oauth_secret, token_cache, scopes)


def _service_account(sa_file: str, scopes: list[str]):
    try:
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.error("Missing: pip install google-auth")
        sys.exit(1)

    creds = Credentials.from_service_account_file(sa_file, scopes=scopes)
    log.info(f"Auth: service account {creds.service_account_email}")
    return _build_service(creds)


def _oauth(client_secret_file: str, token_cache: str, scopes: list[str]):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        log.error("Missing: pip install google-auth-oauthlib")
        sys.exit(1)

    creds = None
    token_path = Path(token_cache)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing expired OAuth token…")
            creds.refresh(Request())
        else:
            if not client_secret_file or not Path(client_secret_file).exists():
                log.error(f"OAuth client secret not found: {client_secret_file!r}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        log.info(f"OAuth token saved → {token_path}")

    log.info("Auth: OAuth user credentials")
    return _build_service(creds)
