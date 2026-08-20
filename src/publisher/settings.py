"""publisher.settings — settings/publish.yml + facts reused from the schedule reader.

``settings/publish.yml`` owns only what is NEW to publishing (Drive folder, sheet column
headers, Telegram routing, auth scopes/token path). Spreadsheet id, header row and the tab
override are NOT restated here — they come from ``schedule.settings.load()`` (a pure, cheap,
offline call), so the fact lives in one place (``settings/gsheet.yml`` / ``config.yml``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from schedule import settings as sched_settings
from schedule.gsheet import REPO_ROOT

PUBLISH_YML = REPO_ROOT / "settings" / "publish.yml"

# drive.file, not full drive: the restricted `drive` scope is blocked on the gcloud
# consent screen; drive.file covers everything this pipeline creates (see publish.yml).
WRITE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


@dataclass
class DriveSettings:
    folder_id: str | None = None  # required before the first real run (publish-init-drive)
    folder_name: str = "MLInside 2026 — decks"
    parent_folder_id: str = "root"
    share: str = "anyone_reader"  # anyone_reader | none


@dataclass
class SheetSettings:
    # Header text per written field; dict order = append order for missing columns.
    columns: dict[str, str] = field(
        default_factory=lambda: {"url": "pptx (GDrive)", "version": "версия", "slides": "слайдов"}
    )
    link_style: str = "url"  # url | hyperlink


@dataclass
class TelegramSettings:
    slug: str = "mlinside_course"
    kind: str = "milestone"
    max_upload_mb: int = 49  # pre-flight guard under tg-send-file.sh's hard 50MB cap
    chat: str | None = None  # None → deck-publish.yml default (MLInside topic 118)
    thread: str | None = None


@dataclass
class AuthLane:
    """One credential recipe: what to authenticate with, for which scopes, billed where."""

    scopes: list[str]
    token_cache: Path
    # Set → service-account lane (no browser; target must be shared with the SA as Editor;
    # a SA cannot upload to a personal Drive, so it can serve the sheet, never the upload).
    service_account_file: Path | None = None
    # Drive rejects user-ADC calls without one; attached per credential so the machine-wide
    # ADC quota project stays untouched. Irrelevant for service accounts.
    quota_project: str | None = None


@dataclass
class PublishConfig:
    drive: DriveSettings
    sheet: SheetSettings
    telegram: TelegramSettings
    scopes: list[str]
    token_cache: Path
    service_account_file: Path | None
    state_file: Path
    out_dir: Path  # data/generated — where built versions live
    plan_path: Path  # content/presentations.yml
    spreadsheet_id: str
    header_row: int
    sheet_tab_override: str | None
    # The reader's candidate-header map (settings/gsheet.yml) — the write lane locates the
    # topic column with the exact same rules (mapper.resolve_columns), one identity model.
    columns_map: dict[str, list[str]] = field(default_factory=dict)
    quota_project: str | None = None
    # Sheet-leg credential override (auth.sheet in publish.yml). None → default lane.
    sheet_auth: AuthLane | None = None

    def lane(self, api: str) -> AuthLane:
        """Credential recipe for ``api`` — the sheet override when set, else the default.

        >>> cfg = PublishConfig(DriveSettings(), SheetSettings(), TelegramSettings(), ["a"],
        ...                     Path("t"), None, Path("s"), Path("o"), Path("p"), "id", 1, None)
        >>> cfg.lane("sheets").scopes, cfg.lane("drive").scopes
        (['a'], ['a'])
        >>> cfg.sheet_auth = AuthLane(scopes=["b"], token_cache=Path("t2"))
        >>> cfg.lane("sheets").scopes, cfg.lane("drive").scopes
        (['b'], ['a'])
        """
        if api == "sheets" and self.sheet_auth is not None:
            return self.sheet_auth
        return AuthLane(
            scopes=self.scopes,
            token_cache=self.token_cache,
            service_account_file=self.service_account_file,
            quota_project=self.quota_project,
        )


def _get(raw: dict, key: str) -> dict:
    v = raw.get(key)
    return v if isinstance(v, dict) else {}


def load(path: str | Path = PUBLISH_YML) -> PublishConfig:
    """Merged publish config; every key optional except what the sheet lane derives."""
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else {}
    raw = raw or {}

    d, s, t, a = _get(raw, "drive"), _get(raw, "sheet"), _get(raw, "telegram"), _get(raw, "auth")

    drive = DriveSettings(
        folder_id=d.get("folder_id"),
        folder_name=d.get("folder_name") or DriveSettings.folder_name,
        parent_folder_id=d.get("parent_folder_id") or "root",
        share=d.get("share") or "anyone_reader",
    )
    sheet = SheetSettings(
        columns={str(k): str(v) for k, v in (s.get("columns") or {}).items()}
        or SheetSettings().columns,
        link_style=s.get("link_style") or "url",
    )
    telegram = TelegramSettings(
        slug=t.get("slug") or "mlinside_course",
        kind=t.get("kind") or "milestone",
        max_upload_mb=int(t.get("max_upload_mb") or 49),
        chat=t.get("chat"),
        thread=str(t["thread"]) if t.get("thread") is not None else None,
    )

    token_env = a.get("token_cache_env") or "GOOGLE_OAUTH_TOKEN_CACHE"
    token_cache = Path(
        os.environ.get(token_env)
        or a.get("token_cache_default")
        or "~/.config/gcloud/application_default_credentials.json"
    ).expanduser()

    sa_env = a.get("service_account_file_env") or "GOOGLE_SERVICE_ACCOUNT_FILE"
    sa_raw = os.environ.get(sa_env) or a.get("service_account_file")
    service_account_file = Path(sa_raw).expanduser() if sa_raw else None

    sheet_raw = a.get("sheet")
    sheet_auth = None
    if isinstance(sheet_raw, dict):
        sheet_sa = sheet_raw.get("service_account_file")
        sheet_auth = AuthLane(
            scopes=list(sheet_raw.get("scopes") or a.get("scopes") or WRITE_SCOPES),
            token_cache=Path(sheet_raw.get("token_cache") or token_cache).expanduser(),
            service_account_file=Path(sheet_sa).expanduser() if sheet_sa else None,
            quota_project=sheet_raw.get("quota_project"),
        )

    sched = sched_settings.load()
    return PublishConfig(
        drive=drive,
        sheet=sheet,
        telegram=telegram,
        scopes=list(a.get("scopes") or WRITE_SCOPES),
        token_cache=token_cache,
        service_account_file=service_account_file,
        state_file=REPO_ROOT / (raw.get("state_file") or "data/.state/deck-publish-state.json"),
        out_dir=REPO_ROOT / "data" / "generated",
        plan_path=sched_settings.out_path(sched, "plan"),
        spreadsheet_id=sched["spreadsheet"]["id"],
        header_row=int(sched["mapping"].get("header_row") or 1),
        sheet_tab_override=sched["mapping"].get("tab"),
        columns_map=dict(sched["mapping"].get("columns") or {}),
        quota_project=a.get("quota_project"),
        sheet_auth=sheet_auth,
    )
