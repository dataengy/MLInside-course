"""publisher.gdrive — one stable Drive file per subject, content replaced in place.

The persistent-URL contract: ``{out_name}.pptx`` (no version in the name) lives in the
course folder; a new version is ``files().update`` on the SAME fileId, so ``webViewLink``
never changes. The cursor remembers the fileId, but the id is recoverable: a lost cursor
falls back to find-by-name-in-folder (adopt, never duplicate), and only then to create.
googleapiclient imports are deferred (see publisher.auth for the contract).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger as log

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
FOLDER_MIME = "application/vnd.google-apps.folder"


@dataclass(frozen=True)
class DriveResult:
    file_id: str
    web_view_link: str


def _q_escape(name: str) -> str:
    """Escape a value for a Drive v3 ``q`` string literal.

    >>> _q_escape("O'Brien")
    "O\\\\'Brien"
    """
    return name.replace("\\", "\\\\").replace("'", "\\'")


def find_by_name(service: Any, folder_id: str, filename: str) -> str | None:
    """fileId of a non-trashed ``filename`` inside ``folder_id``, else None."""
    q = f"name = '{_q_escape(filename)}' and '{folder_id}' in parents and trashed = false"
    r = service.files().list(q=q, fields="files(id,name)", pageSize=5).execute()
    files = r.get("files", [])
    if len(files) > 1:
        log.warning(f"drive: {len(files)} files named {filename!r} in folder — using the first")
    return files[0]["id"] if files else None


def ensure_shared(service: Any, file_id: str, mode: str) -> None:
    """Idempotently apply the share policy (list first, create only when absent)."""
    if mode != "anyone_reader":
        return
    perms = service.permissions().list(fileId=file_id, fields="permissions(type,role)").execute()
    if any(p.get("type") == "anyone" for p in perms.get("permissions", [])):
        return
    service.permissions().create(
        fileId=file_id, body={"type": "anyone", "role": "reader"}
    ).execute()
    log.info(f"drive: anyone-with-link reader set on {file_id}")


def upload_or_update(
    service: Any,
    *,
    file_path: Path,
    folder_id: str,
    filename: str,
    description: str,
    existing_file_id: str | None,
    share: str = "anyone_reader",
) -> DriveResult:
    """Create-or-update the subject's stable file; returns the (stable) id + webViewLink."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    def _media() -> Any:
        return MediaFileUpload(str(file_path), mimetype=PPTX_MIME, resumable=True)

    meta = {"name": filename, "description": description}
    fields = "id,webViewLink"

    file_id = existing_file_id
    if file_id:
        try:
            f = (
                service.files()
                .update(fileId=file_id, body=meta, media_body=_media(), fields=fields)
                .execute()
            )
            ensure_shared(service, f["id"], share)
            return DriveResult(f["id"], f["webViewLink"])
        except HttpError as e:
            if getattr(getattr(e, "resp", None), "status", None) != 404:
                raise
            log.warning(f"drive: recorded fileId {file_id} is gone (404) — re-resolving by name")

    found = find_by_name(service, folder_id, filename)
    if found:
        f = (
            service.files()
            .update(fileId=found, body=meta, media_body=_media(), fields=fields)
            .execute()
        )
    else:
        f = (
            service.files()
            .create(body={**meta, "parents": [folder_id]}, media_body=_media(), fields=fields)
            .execute()
        )
        log.info(f"drive: created {filename!r} → {f['id']}")
    ensure_shared(service, f["id"], share)
    return DriveResult(f["id"], f["webViewLink"])


def ensure_folder(service: Any, *, name: str, parent_id: str = "root") -> str:
    """Search-or-create the course folder; returns its id (used by ``publish-init-drive``)."""
    q = (
        f"name = '{_q_escape(name)}' and '{parent_id}' in parents "
        f"and mimeType = '{FOLDER_MIME}' and trashed = false"
    )
    r = service.files().list(q=q, fields="files(id,name)", pageSize=5).execute()
    files = r.get("files", [])
    if files:
        return files[0]["id"]
    f = (
        service.files()
        .create(body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}, fields="id")
        .execute()
    )
    log.info(f"drive: created folder {name!r} → {f['id']}")
    return f["id"]
