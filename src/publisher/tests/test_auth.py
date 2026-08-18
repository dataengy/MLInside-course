"""auth: credential-lane resolution and loud failures (no network, no real keys)."""

import json
from pathlib import Path

import pytest

from publisher import auth

pytest.importorskip("google.oauth2")


def _token(tmp_path, **over):
    p = tmp_path / "token.json"
    data = {
        "type": "authorized_user",
        "client_id": "cid",
        "client_secret": "sec",
        "refresh_token": "rt",
        **over,
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_missing_token_names_the_fix(tmp_path):
    with pytest.raises(RuntimeError, match="adc-login"):
        auth.load_credentials(tmp_path / "nope.json", ["s"])


def test_token_without_refresh_token_is_loud(tmp_path):
    p = _token(tmp_path, refresh_token=None)
    with pytest.raises(RuntimeError, match="no refresh_token.*adc-login"):
        auth.load_credentials(p, ["s"])


def test_refresh_failure_is_wrapped_with_fix_it(tmp_path, monkeypatch):
    p = _token(tmp_path)

    def boom(self, request):
        raise ValueError("invalid_grant")

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", boom)
    with pytest.raises(RuntimeError, match="invalid_grant.*adc-login"):
        auth.load_credentials(p, ["s"])


def test_service_account_lane_takes_precedence(tmp_path, monkeypatch):
    sa = tmp_path / "sa.json"
    sa.write_text("{}", encoding="utf-8")
    seen = {}

    class FakeCreds:
        @staticmethod
        def from_service_account_file(path, scopes):
            seen["path"], seen["scopes"] = path, scopes
            return "SA-CREDS"

    monkeypatch.setattr("google.oauth2.service_account.Credentials", FakeCreds)
    got = auth.load_credentials(_token(tmp_path), ["sc"], service_account_file=sa)
    assert got == "SA-CREDS" and seen == {"path": str(sa), "scopes": ["sc"]}


def test_missing_service_account_key_is_loud(tmp_path):
    with pytest.raises(RuntimeError, match="service-account key not found"):
        auth.load_credentials(tmp_path / "t.json", ["s"], service_account_file=tmp_path / "no.json")


def test_never_imports_interactive_flow():
    """A hook must never open a browser — the oauthlib flow is code-absent, not guarded."""
    code = [
        ln for ln in Path(auth.__file__).read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith(("import ", "from "))
    ]
    assert not [ln for ln in code if "oauthlib" in ln or "InstalledAppFlow" in ln], code
