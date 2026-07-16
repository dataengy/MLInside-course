"""orchestration.config — fail-loud OrchestrationConfig from settings/config.yml `orchestration:`.

Mirrors preza_gen.settings.load(): every field required (KeyError on missing), paths resolved
absolute against the repo root so `serve` works regardless of its CWD. No prefect import here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from preza_gen.utils import expand_path, load_yaml

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "settings" / "config.yml"


@dataclass
class OrchestrationConfig:
    repo_root: Path
    scan_interval_s: int
    deck_id: str
    event_name: str
    watch: list[str]  # repo-relative files/dirs to watch
    cursor_file: Path  # absolute
    settings_yml: str  # absolute — passed to pipeline.build_deck
    content_yml: str  # absolute
    publish_open: bool
    publish_send: bool


def load_orchestration(config_path: str | Path | None = None) -> OrchestrationConfig:
    """Load the `orchestration:` section, fail-loud, with paths made absolute to the repo root."""
    cfg_path = Path(config_path) if config_path else _DEFAULT_CONFIG
    o = load_yaml(cfg_path)["orchestration"]
    root = expand_path(cfg_path).resolve().parents[1]  # settings/config.yml → repo root
    pub = o["publish"]
    return OrchestrationConfig(
        repo_root=root,
        scan_interval_s=o["scan_interval_s"],
        deck_id=o["deck_id"],
        event_name=o["event_name"],
        watch=o["watch"],
        cursor_file=root / o["cursor_file"],
        settings_yml=str(root / o["settings_yml"]),
        content_yml=str(root / o["content_yml"]),
        publish_open=pub["open"],
        publish_send=pub["send"],
    )
