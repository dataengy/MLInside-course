"""publisher.auth — headless Google credentials (service account, else authorized_user).

Two non-interactive lanes, in resolution order:

1. **Service account** — when ``auth.service_account_file`` (or ``$GOOGLE_SERVICE_ACCOUNT_FILE``)
   points at a key. Needs no browser at all, but the target must be shared with the SA
   address as Editor, and a SA cannot upload to a personal Drive (no storage quota) — so
   this lane serves the SHEET leg while the Drive leg keeps failing in isolation.
2. **authorized_user JSON** — gcloud's ADC file by default (client id/secret + a long-lived
   refresh token), refreshed in memory when expired. Serves every leg.

Deliberately NEVER imports ``google_auth_oauthlib``: an interactive consent flow inside a
hook or pipeline is a hang, not a fallback — when the token is dead this module raises
RuntimeError carrying the exact fix-it command instead. googleapiclient imports are deferred
into function bodies so ``import publisher`` works without the ``gsheets`` extra installed
(same contract as ``schedule.gsheet``).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from publisher.settings import PublishConfig

FIX_IT = "just -f ~/.ai/scripts/gcloud/Justfile adc-login account=hnkovr@gmail.com"


def load_credentials(
    token_cache: Path, scopes: list[str], service_account_file: Path | None = None
) -> Any:
    """Service-account key when configured, else cached authorized_user token."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as e:  # pragma: no cover - env misconfiguration
        raise RuntimeError("google client libs missing — run: uv sync --extra gsheets") from e

    if service_account_file:
        if not service_account_file.is_file():
            raise RuntimeError(f"service-account key not found: {service_account_file}")
        from google.oauth2 import service_account

        return service_account.Credentials.from_service_account_file(
            str(service_account_file), scopes=scopes
        )

    if not token_cache.is_file():
        raise RuntimeError(f"no Google token at {token_cache} — complete a consent: {FIX_IT}")
    creds = Credentials.from_authorized_user_file(str(token_cache), scopes=scopes)
    if not creds.valid:
        if not creds.refresh_token:
            raise RuntimeError(f"token at {token_cache} has no refresh_token — re-consent: {FIX_IT}")
        try:
            creds.refresh(Request())
        except Exception as e:
            raise RuntimeError(f"Google token refresh failed ({e}) — re-consent: {FIX_IT}") from e
    return creds


def get_service(api: str, version: str, cfg: PublishConfig) -> Any:
    """``googleapiclient`` service for ``drive``/``sheets`` with the pipeline's credentials."""
    from googleapiclient.discovery import build

    creds = load_credentials(cfg.token_cache, cfg.scopes, cfg.service_account_file)
    return build(api, version, credentials=creds, cache_discovery=False)
