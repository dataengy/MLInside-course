"""preza_merge.cli — propose / apply / verify / run. Canonical entry: just preza-merge-*."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
import yaml

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


def _scratch_settings(deck_settings: Path, tmp_path: Path) -> Path:
    """Copy a deck settings yaml with out_dir redirected into a scratch dir."""
    doc = yaml.safe_load(deck_settings.read_text(encoding="utf-8"))
    doc["settings"]["out_dir"] = str(tmp_path / "generated")
    out = tmp_path / "settings.yml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return out


def _drop_downloads_dir(content_path: Path) -> None:
    """Blank a scratch content's downloads_dir so the build cannot hardlink into ~/Downloads."""
    doc = yaml.safe_load(content_path.read_text(encoding="utf-8"))
    doc["deck"]["downloads_dir"] = None
    content_path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


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


@main.command("apply")
@click.argument("proposal_path")
@click.option("--patch-of", required=True, help="version being patched, e.g. 3.19")
@click.option("--descr", required=True, help="build tag, e.g. alina-fmt")
@click.option("--settings", "settings_path", default=str(_SETTINGS), show_default=True)
@click.option(
    "--deck-settings",
    default="content/build_deck_v3-settings.yml",
    show_default=True,
    help="settings yaml the deck renders with",
)
@click.option("--formats", "formats_path", default="settings/formats.yml", show_default=True)
@click.option("--backend", default="settings", show_default=True, help="settings | graft")
def apply_cmd(proposal_path, patch_of, descr, settings_path, deck_settings, formats_path, backend):
    """Write the profile, switch the deck, build the patch version."""
    from . import apply as apply_mod

    cfg = MergeConfig.load(settings_path)
    doc = report.load_proposal(proposal_path)
    out = apply_mod.run(
        doc,
        cfg,
        settings_yml=Path(deck_settings),
        formats_path=Path(formats_path),
        patch_of=patch_of,
        descr=descr,
        backend=backend,
    )
    click.echo(f"собрано: {out}")


@main.command("verify")
@click.argument("proposal_path")
@click.argument("merged_pptx")
@click.option("--settings", "settings_path", default=str(_SETTINGS), show_default=True)
@click.option(
    "--deck-settings", default="content/build_deck_v3-settings.yml", show_default=True
)
@click.option("--contact-sheet", "want_sheet", is_flag=True, help="also render PNG pages")
def verify_cmd(proposal_path, merged_pptx, settings_path, deck_settings, want_sheet):
    """Rebuild the base content with the profile and check it against the fork."""
    import tempfile

    from preza_gen import pipeline

    from . import verify as verify_mod

    cfg = MergeConfig.load(settings_path)
    doc = report.load_proposal(proposal_path)["proposal"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        base_content = _content_at_rev(doc["base_content_rev"], doc["deck"], tmp_path / "base.yml")
        # The verification build is scratch: redirect out_dir (and drop the ~/Downloads
        # hardlink) so it never lands beside the real versions the publisher scans.
        scratch_settings = _scratch_settings(Path(deck_settings), tmp_path)
        _drop_downloads_dir(base_content)
        res = pipeline.build_deck(scratch_settings, base_content, pptx=True)
        rebuilt = model.load(res.out_path)
        theirs = model.load(doc["theirs_pptx"])
        ours = model.load(doc["ours_pptx"])
        merged = model.load(merged_pptx)

        out = verify_mod.structural(rebuilt, theirs, cfg).merge(
            verify_mod.invariants(ours, merged)
        )
        if want_sheet:
            sheet = verify_mod.contact_sheet(Path(merged_pptx), cfg.report_dir / "contact")
            click.echo(f"contact-sheet: {sheet or 'LibreOffice не найден — пропущено'}")

    for line in out.lines:
        click.echo(line)
    for bad in out.mismatches:
        click.echo(f"✗ {bad}", err=True)
    if not out.ok:
        sys.exit(1)
    click.echo("✓ верификация пройдена")


@main.command()
@click.pass_context
@click.option("--deck", required=True)
@click.option("--base", "base_pptx", required=True)
@click.option("--ours", "ours_pptx", required=True)
@click.option("--theirs", "theirs_pptx", required=True)
@click.option("--base-content-rev", required=True)
@click.option("--profile", default=None)
def run(ctx, deck, base_pptx, ours_pptx, theirs_pptx, base_content_rev, profile):
    """propose, then stop at the decisions — apply/verify are deliberate follow-ups."""
    ctx.invoke(
        propose,
        deck=deck,
        base_pptx=base_pptx,
        ours_pptx=ours_pptx,
        theirs_pptx=theirs_pptx,
        base_content_rev=base_content_rev,
        profile=profile,
        settings_path=str(_SETTINGS),
    )
    click.echo("\nдальше: проставьте decision: в *.proposal.yml → just preza-merge-apply …")


if __name__ == "__main__":
    main()
