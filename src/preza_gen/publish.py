"""preza_gen.publish — fail-loud wrapper over ~/.ai/scripts/publish/publish-deck.sh (prefect-free).

publish-deck.sh composes open-in-app.sh (open) + tg-send-file.sh (send). This wrapper calls it
with subprocess check=True so a Prefect task SEES failures — unlike deck-watch.sh, which swallows
them. Defaults are daemon-safe: no open (GUI is unavailable from a background process).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .utils import log

_PUBLISH_SH = os.path.expanduser("~/.ai/scripts/publish/publish-deck.sh")


def publish_deck(
    pptx: Path | str,
    *,
    open_app: bool = False,
    send: bool = True,
    chat: str | None = None,
    thread: str | None = None,
    script: str = _PUBLISH_SH,
) -> None:
    """Open/send a deck via publish-deck.sh. Fail-loud: raises on missing file/script or non-zero."""
    pptx = Path(pptx)
    if not pptx.is_file():
        raise FileNotFoundError(f"deck to publish not found: {pptx}")
    if not os.path.isfile(script):
        raise FileNotFoundError(f"publish helper missing: {script}")
    cmd = ["bash", script, "--file", str(pptx)]
    if not open_app:
        cmd.append("--no-open")
    if not send:
        cmd.append("--no-send")
    if chat:
        cmd += ["--chat", chat]
    if thread:
        cmd += ["--thread", str(thread)]
    log.info(f"publish: {pptx.name}  (open={open_app} send={send})")
    subprocess.run(cmd, check=True)
