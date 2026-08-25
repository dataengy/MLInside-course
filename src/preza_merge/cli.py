"""preza_merge.cli — propose / apply / verify / run. Canonical entry: just preza-merge-*."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from . import align, diff, model, report, rules
from .rules import MergeConfig

_SETTINGS = Path("settings/merge.yml")


def _content_at_rev(rev: str, path: str, dest: Path) -> Path:
    """Materialize `path` as of `rev` into `dest`. Fail-loud — verification depends on it."""
    out = subprocess.run(
        ["git", "show", f"{rev}:{path}"], capture_output=True, check=False
    )
    if out.returncode != 0:
        raise SystemExit(
            f"cannot read {path} at {rev}: {out.stderr.decode('utf-8', 'ignore').strip()}"
        )
    dest.write_bytes(out.stdout)
    return dest


@click.group()
def main() -> None:
    """Merge a reviewer's .pptx fork back into the deck generator."""


@main.command()
@click.option("--deck", required=True, help="content yaml of the deck being merged")
@click.option("--base", "base_pptx", required=True, help="the .pptx that went out for review")
@click.option("--ours", "ours_pptx", required=True, help="our newest built .pptx")
@click.option("--theirs", "theirs_pptx", required=True, help="the reviewer's fork")
@click.option("--base-content-rev", required=True, help="git rev whose content built --base")
@click.option("--profile", default=None, help="profile name to write (default: merge.yml)")
@click.option("--settings", "settings_path", default=str(_SETTINGS), show_default=True)
def propose(deck, base_pptx, ours_pptx, theirs_pptx, base_content_rev, profile, settings_path):
    """Diff the three sides, derive rules, write the report + proposal."""
    cfg = MergeConfig.load(settings_path)
    base = model.load(base_pptx)
    ours = model.load(ours_pptx)
    theirs = model.load(theirs_pptx)

    fork_diff = diff.compare(base, theirs)
    ours_diff = diff.compare(base, ours)
    alignment = align.align3(base, ours, theirs)
    findings = rules.detect(base, theirs, fork_diff, cfg)

    # Build the report stem as a STRING first — Path.replace is a filesystem rename and
    # rejects two arguments, so `cfg.report_dir / f"...".replace(...)` would crash on join.
    stem_name = f"{Path(ours_pptx).stem}_x_{Path(theirs_pptx).stem}".replace(" ", "_")
    stem = cfg.report_dir / stem_name
    md, prop = report.write(
        stem,
        report.ProposalContext(
            deck=deck,
            base_pptx=Path(base_pptx),
            ours_pptx=Path(ours_pptx),
            theirs_pptx=Path(theirs_pptx),
            base_content_rev=base_content_rev,
            profile_name=profile or cfg.default_profile,
            findings=findings,
            alignment=alignment,
            diffs={"fork": fork_diff.counts, "ours": ours_diff.counts},
        ),
    )
    click.echo(f"отчёт:      {md}")
    click.echo(f"предложение: {prop}")
    click.echo(f"правил: {sum(1 for f in findings if f.kind == 'format')} · "
               f"регрессий: {sum(1 for f in findings if f.kind == 'regression')}")
    if alignment.unaligned:
        click.echo(f"⚠ неоднозначные заголовки: {alignment.unaligned}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
