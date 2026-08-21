"""Gate check for the deck publish pipeline (spec: docs/deck-publish-pipeline.md).

Read-only — never writes to the sheet or Drive. Answers everything that gates a real
`just publish-new`, per credential lane, and rehearses the sheet write so the first real
one holds no surprises:

1. **drive lane** (user-ADC) — whose Drive, how full, may the upload even start;
2. **sheet lane** (service account) — can it read the sheet, may it EDIT it (`canEdit`);
3. **sheet write plan** — resolved tab, topic column, which columns would be appended and
   at which letters, and which deck matches which row (`skipped` decks are expected: not
   every built deck has a lecture row).

Config comes from `settings/publish.yml` + `settings/gsheet.yml` through
`publisher.settings` — nothing is restated here, so the probe cannot drift from the lane
the pipeline actually uses.

Provenance: session 2026-08-19 (both SAs read but `canEdit=False`), rewritten 2026-08-20
when the two-lane model landed and the Drive leg turned out to be blocked by storage
quota rather than permissions. Re-run after changing sharing, quota or the consent:

    PYTHONPATH=src uv run --extra gsheets python .tmp/probe_google_access.py
"""

import json

from publisher import auth, settings
from publisher.detect import newest, slide_count
from schedule.gsheet import sheet_utils

DRIVE_RO = ["https://www.googleapis.com/auth/drive.readonly"]


def gib(v) -> str:
    return "—" if v is None else f"{int(v) / 2**30:.2f} GiB"


def main() -> None:
    cfg = settings.load()
    utils = sheet_utils()

    print("── drive lane (upload) ─────────────────────────────────────────")
    lane = cfg.lane("drive")
    print(f"  cred: {'SA ' + str(lane.service_account_file) if lane.service_account_file else 'user-ADC ' + str(lane.token_cache)}")
    print(f"  scopes: {[s.rsplit('/', 1)[-1] for s in lane.scopes]} · quota_project: {lane.quota_project}")
    try:
        drive = auth.get_service("drive", "v3", cfg)
        about = drive.about().get(fields="storageQuota,user(emailAddress)").execute()
        q, who = about["storageQuota"], about["user"]["emailAddress"]
        full = int(q["usage"]) >= int(q.get("limit") or 0) if q.get("limit") else False
        print(f"  account: {who} · usage {gib(q.get('usage'))} / limit {gib(q.get('limit'))}")
        print(f"  UPLOAD: {'BLOCKED — storageQuotaExceeded (место, не права)' if full else 'OK'}")
        if cfg.drive.folder_id:
            f = drive.files().get(fileId=cfg.drive.folder_id, fields="name,webViewLink").execute()
            print(f"  folder: {f['name']} · {f['webViewLink']}")
    except Exception as e:
        print(f"  FAILED · {type(e).__name__}: {str(e).replace(chr(10), ' ')[:200]}")

    print("\n── sheet lane (columns) ────────────────────────────────────────")
    lane = cfg.lane("sheets")
    key = lane.service_account_file
    email = json.loads(key.read_text()).get("client_email") if key and key.is_file() else None
    print(f"  cred: {'SA ' + (email or str(key)) if key else 'user-ADC ' + str(lane.token_cache)}")
    try:
        svc = auth.get_service("sheets", "v4", cfg)
        meta = svc.spreadsheets().get(
            spreadsheetId=cfg.spreadsheet_id, fields="properties.title,sheets.properties.title"
        ).execute()
        tabs = [s["properties"]["title"] for s in meta["sheets"]]
        print(f"  READ OK · {meta['properties']['title']!r} · tabs={tabs}")
    except Exception as e:
        print(f"  READ FAILED · {type(e).__name__}: {str(e)[:160]}")
        return

    can_edit = None
    try:
        creds = auth.load_credentials(lane.token_cache, DRIVE_RO, key, lane.quota_project)
        from googleapiclient.discovery import build

        cap = build("drive", "v3", credentials=creds, cache_discovery=False).files().get(
            fileId=cfg.spreadsheet_id, fields="capabilities(canEdit)"
        ).execute()
        can_edit = cap["capabilities"]["canEdit"]
    except Exception as e:
        print(f"  canEdit probe failed · {type(e).__name__}: {str(e)[:120]}")
    if can_edit is False:
        print(f"  WRITE: BLOCKED — выдать Редактора: {email}")
    elif can_edit:
        print("  WRITE: OK")

    print("\n── sheet write plan (rehearsal, ничего не пишется) ──────────────")
    from publisher import gsheet_write as gw
    from publisher import runner

    tab = gw.resolve_tab_title(svc, cfg.spreadsheet_id, cfg.sheet_tab_override)
    header = gw.read_header(svc, cfg.spreadsheet_id, tab, cfg.header_row)
    topic_col = gw.topic_column(header, cfg.columns_map)
    cols, pending = gw.ensure_columns(header, tab, cfg.header_row, cfg.sheet.columns, {})
    print(f"  tab={tab!r} · header_row={cfg.header_row} · topic column "
          f"{utils.col_letter(topic_col)} ({header[topic_col]!r})")
    for field, idx in cols.items():
        where = "append" if any(f"!{utils.col_letter(idx)}" in p["range"] for p in pending) else "есть"
        print(f"  {field:8s} → {utils.col_letter(idx)} ({cfg.sheet.columns[field]!r}, {where})")

    entries = [e for e in runner.load_plan_entries(cfg.plan_path) if e.get("out_name")]
    for e in entries:
        built = newest(cfg.out_dir, e["out_name"])
        if not built:
            continue
        row = gw.find_row_by_topic(
            svc, cfg.spreadsheet_id, tab, cfg.header_row, topic_col, e.get("topic") or ""
        )
        v = f"v{built.major}.{built.minor}"
        n = slide_count(built.path)
        print(f"  {e['out_name'][:52]:52s} {v:6s} {n:3d} слайд. → "
              f"{'строка ' + str(row) if row else 'НЕТ СТРОКИ (leg skipped)'}")


if __name__ == "__main__":
    main()
