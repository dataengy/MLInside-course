"""publisher.telegram_leg — notify + send the deck through the existing ~/.ai lanes.

Text goes through ``tg-project-inform.sh`` (routes by slug to the MLInside chat/topic);
the file goes through ``preza_gen.publish.publish_deck`` (→ publish-deck.sh → tg-send-file.sh,
same destination). Both are called after the Drive leg so the message can carry the
persistent URL. The size guard fires before the bash lane's own 50MB cap so an oversized
deck fails with a size delta instead of a CalledProcessError.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from preza_gen.publish import publish_deck
from publisher.settings import TelegramSettings

_INFORM_SH = os.path.expanduser("~/.ai/scripts/telegram/tg-project-inform.sh")


def compose_body(topic: str, version: str, slides: int, drive_url: str | None) -> str:
    """
    >>> compose_body("dbt", "3.14", 52, "https://x")
    '📎 dbt — v3.14 · 52 слайдов\\nhttps://x'
    >>> compose_body("dbt", "3.14", 52, None)
    '📎 dbt — v3.14 · 52 слайдов'
    """
    body = f"📎 {topic} — v{version} · {slides} слайдов"
    return f"{body}\n{drive_url}" if drive_url else body


def send_text(slug: str, kind: str, body: str) -> None:
    if not os.path.isfile(_INFORM_SH):
        raise FileNotFoundError(f"tg inform helper missing: {_INFORM_SH}")
    subprocess.run(["bash", _INFORM_SH, "--slug", slug, "--kind", kind, "--body", body], check=True)


def guard_size(pptx: Path, max_upload_mb: int) -> None:
    size_mb = pptx.stat().st_size / (1024 * 1024)
    if size_mb > max_upload_mb:
        raise ValueError(f"{pptx.name}: {size_mb:.1f}MB exceeds the {max_upload_mb}MB send cap")


def notify(
    t: TelegramSettings,
    *,
    topic: str,
    version: str,
    slides: int,
    pptx: Path,
    drive_url: str | None,
) -> tuple[bool, str]:
    """Text then file, each failure isolated; ok only when both landed."""
    errors: list[str] = []
    try:
        send_text(t.slug, t.kind, compose_body(topic, version, slides, drive_url))
    except Exception as e:  # noqa: BLE001 — leg isolation, reported upward as text
        errors.append(f"text: {e}")
    try:
        guard_size(pptx, t.max_upload_mb)
        publish_deck(pptx, open_app=False, send=True, chat=t.chat, thread=t.thread)
    except Exception as e:  # noqa: BLE001
        errors.append(f"file: {e}")
    return (not errors, "; ".join(errors) or "text+file sent")
