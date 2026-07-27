# integrations/google/sheets

Google Sheets client used to read the course schedule sheet
(`settings/config.yml` → `planning.schedule_gsheet`).

## What is what

| File | Ownership |
|---|---|
| `connector.py`, `utils.py`, `__init__.py` | **HARDLINKED** from `~/pdp.deploy_dev/scripts/tools-utils/gsheets/` — one shared inode. Editing them changes pdp too. Never save-via-rename; if an editor severs the link, restore with `ln -f <canonical> <copy>` and check `ls -li`. |
| `auth.py` | **project-owned** — the ADC branch this repo needs. Edit freely. |
| `README.md`, `Justfile` | project-owned. |

The link is registered in `~/.ai/integrations/_relink-actualized.py` (`GROUPS`). Re-run it after
adding files:

```bash
python3 ~/.ai/integrations/_relink-actualized.py --dry-run   # inspect
python3 ~/.ai/integrations/_relink-actualized.py             # apply
python3 ~/.ai/integrations/_relink-actualized.py --repair-identical   # re-link severed-but-identical
```

Deliberately **not** linked: `pnf/` (Jira/Tempo-specific), the upstream `Justfile` (its recipes
target `scripts/tools-utils/gsheets/pnf/*`, which this repo has no counterpart for), and
`gc-setup-sa.sh` (needs a sibling `scripts/utils/{log,asserts,input}.sh` tree).

## Auth (once per machine)

Reads the sheet **as you** — no service account, no secret file, no sharing step:

```bash
just -f integrations/google/sheets/Justfile auth
# → gcloud auth application-default login --account=hnkovr@gmail.com \
#     --scopes=openid,https://www.googleapis.com/auth/cloud-platform,\
#              https://www.googleapis.com/auth/spreadsheets.readonly,\
#              https://www.googleapis.com/auth/drive.readonly
```

`cloud-platform` is there because `application-default login` **rejects** any scope list without
it. It widens the stored credential, not this reader: `auth.py` requests only the two readonly
Sheets/Drive scopes when it builds the service.

Then smoke-test from the repo root:

```bash
just gsheet-tabs
```

`auth.py` falls back to `connector.py` (service account from `~/.ai/settings/gcloud.yml`, then an
OAuth client-secret flow) and logs which credential it used. The registry's `default:` account is
the **Prodamus** SA, which has no access to this sheet — if you see it in the log, the ADC login
above did not take.

## Usage

```python
from schedule.gsheet import get_service, utils   # src/schedule/gsheet.py owns the sys.path shim

service = get_service()
utils.list_sheet_names(service, spreadsheet_id)
```

Dependencies come from the `gsheets` extra: `uv sync --extra gsheets` (or `just sync`).
