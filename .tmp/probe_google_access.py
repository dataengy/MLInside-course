"""Google write-lane diagnostics for the deck publish pipeline (docs/deck-publish-pipeline.md).

Read-only: never writes to the sheet or Drive. Answers the two questions that gate the
drive/sheet legs — can a credential SEE the course sheet, and may it EDIT it?

Provenance: session 2026-08-19, when both service accounts turned out to read the sheet
(canEdit=False), which is why the sheet leg still waits on either an ADC consent or an
Editor share to the SA address. Re-run after changing sharing or completing the consent:
    uv run --extra gsheets python .tmp/probe_google_access.py
"""

import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

SID = "1cxYGtU36nbmO5DhjtNkm_HMESiNPwoWdd6QY8yb2JaU"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
KEYS = {
    "prodamus-main": Path.home() / ".secrets/google-sa-for-prodamus-1-494316.json",
    "agd-gen": Path.home() / "AGD-gen/conf/google-service-account.json",
}

for name, key in KEYS.items():
    if not key.is_file():
        print(f"{name}: NO KEY at {key}")
        continue
    email = json.loads(key.read_text()).get("client_email")
    print(f"\n{name}: {email}")
    try:
        creds = service_account.Credentials.from_service_account_file(str(key), scopes=SCOPES)
        svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
        meta = svc.spreadsheets().get(spreadsheetId=SID, fields="properties.title,sheets.properties.title").execute()
        tabs = [s["properties"]["title"] for s in meta["sheets"]]
        print(f"  READ OK · title={meta['properties']['title']!r} · tabs={tabs}")
    except Exception as e:
        msg = str(e).replace("\n", " ")[:160]
        print(f"  READ FAILED · {type(e).__name__}: {msg}")


# ── can it EDIT? (Drive capabilities — still read-only, no mutation) ─────────
for name, key in KEYS.items():
    if not key.is_file():
        continue
    try:
        creds = service_account.Credentials.from_service_account_file(
            str(key), scopes=["https://www.googleapis.com/auth/drive.readonly"])
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        cap = drive.files().get(fileId=SID, fields="capabilities(canEdit)").execute()
        print(f"{name}: canEdit={cap['capabilities']['canEdit']}")
    except Exception as e:
        print(f"{name}: canEdit probe failed — {type(e).__name__}: {str(e)[:100]}")
