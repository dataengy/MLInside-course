"""publisher.cli — ``python -m publisher`` (run / status / init-drive).

Heavy imports live inside the commands so importing this module (pytest doctest collection)
stays dependency-free.
"""

from __future__ import annotations

import sys

import click


@click.group()
def main() -> None:
    """Deck publish pipeline: Telegram + GDrive (stable URL) + schedule-sheet columns."""


@main.command()
@click.option("--deck", default=None, help="Limit to one deck (content path or out_name).")
@click.option("--only", "only_", type=click.Choice(["tg", "drive", "sheet"]), multiple=True)
@click.option("--force", is_flag=True, help="Re-run legs already ok for this version.")
@click.option("--dry", is_flag=True, help="Print intent only — no network, no writes.")
def run(deck: str | None, only_: tuple[str, ...], force: bool, dry: bool) -> None:
    """Publish every built version newer than the cursor (or retry its failed legs)."""
    from publisher import runner, settings

    cfg = settings.load()
    outcomes, failed = runner.run(cfg, deck=deck, only=set(only_) or None, force=force, dry=dry)
    if not outcomes:
        click.echo("nothing to publish — no plan entry has a built deck")
    for o in outcomes:
        click.echo(f"— {o.out_name} · v{o.version}")
        for line in o.lines:
            click.echo(f"    {line}")
    sys.exit(1 if failed else 0)


@main.command()
def status() -> None:
    """Cursor vs newest built version, per deck."""
    from publisher import runner, settings

    for line in runner.status(settings.load()):
        click.echo(line)


@main.command("init-drive")
@click.option("--name", default=None, help="Folder name (default: drive.folder_name).")
@click.option("--parent", default=None, help="Parent folder id (default: drive.parent_folder_id).")
def init_drive(name: str | None, parent: str | None) -> None:
    """Search-or-create the course Drive folder; prints its id to paste into publish.yml."""
    from publisher import auth, gdrive, settings

    cfg = settings.load()
    service = auth.get_service("drive", "v3", cfg)
    fid = gdrive.ensure_folder(
        service,
        name=name or cfg.drive.folder_name,
        parent_id=parent or cfg.drive.parent_folder_id,
    )
    click.echo(fid)
    click.echo(f"→ settings/publish.yml: drive.folder_id: {fid}", err=True)
