"""preza_merge.report — the human's decision surface: a markdown story + a YAML proposal.

The markdown explains WHY each rule fired (the evidence); the YAML is what `apply` reads.
Every format rule carries `decision: null` until a human writes accept/reject — apply
refuses to run while any decision is missing, so a rule can never slip in unread.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .rules import Finding


@dataclass
class ProposalContext:
    deck: str
    base_pptx: Path
    ours_pptx: Path
    theirs_pptx: Path
    base_content_rev: str
    profile_name: str
    findings: list[Finding]
    alignment: Any
    diffs: dict


def _rule_row(f: Finding) -> dict:
    return {
        "rule": f.rule,
        "key": f.key,
        "value": f.value,
        "share": round(f.share, 3),
        "evidence": f.evidence,
        "slides": f.slides,
        "decision": None,  # accept | reject — filled in by the human
    }


def _regression_row(f: Finding) -> dict:
    return {"rule": f.rule, "evidence": f.evidence, "slides": f.slides, "value": f.value}


def _md(ctx: ProposalContext) -> str:
    fmt = [f for f in ctx.findings if f.kind == "format"]
    reg = [f for f in ctx.findings if f.kind == "regression"]
    lines = [
        f"# Слияние деки — {ctx.deck}",
        "",
        f"- base: `{ctx.base_pptx.name}` (контент: `{ctx.base_content_rev}`)",
        f"- ours: `{ctx.ours_pptx.name}`",
        f"- theirs: `{ctx.theirs_pptx.name}`",
        f"- профиль: `{ctx.profile_name}`",
        "",
        "## Правила форматирования",
        "",
    ]
    if fmt:
        lines += ["| # | ключ | значение | доля | доказательство |", "|---|---|---|---|---|"]
        lines += [
            f"| {f.rule} | `{f.key}` | `{f.value}` | {f.share:.0%} | {f.evidence} |" for f in fmt
        ]
    else:
        lines.append("Системных правил не найдено.")
    lines += ["", "## Регрессии форка — не переносятся", ""]
    if reg:
        lines += ["| # | что | почему в отчёте |", "|---|---|---|"]
        lines += [
            f"| {f.rule} | {f.evidence} | перенос испортил бы деку |" for f in reg
        ]
    else:
        lines.append("Регрессий не обнаружено.")
    if ctx.alignment is not None:
        rows = ctx.alignment.rows
        lines += [
            "",
            "## Выравнивание слайдов",
            "",
            f"- всего строк: {len(rows)}",
            f"- только у нас: {len(ctx.alignment.by_status('ours-only'))}",
            f"- только у ревьюера: {len(ctx.alignment.by_status('theirs-only'))}",
            f"- неоднозначные заголовки: {ctx.alignment.unaligned or '—'}",
        ]
    lines += [
        "",
        "## Что дальше",
        "",
        "1. Проставить `decision:` (accept | reject) у каждого правила в `*.proposal.yml`.",
        "2. `just preza-merge-apply <proposal.yml>`",
        "3. `just preza-merge-verify <proposal.yml> <merged.pptx>`",
        "",
        "Спека ленты: [docs/preza-merge-lane.md](../../preza-merge-lane.md)",
        "",
    ]
    return "\n".join(lines)


def write(out_stem: Path, ctx: ProposalContext) -> tuple[Path, Path]:
    """Write ``<stem>.md`` + ``<stem>.proposal.yml``; return both paths."""
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    # NOT Path.with_suffix: real stems here carry a dot from the deck version (e.g. "v3.19"),
    # and with_suffix treats the LAST dot in the whole name as an existing extension — it
    # would silently truncate "..._v3.19_x_..._v3.15" down to "..._v3", colliding two
    # different merges onto the same report file. Plain string suffixing keeps the full name.
    md_path = out_stem.parent / f"{out_stem.name}.md"
    yml_path = out_stem.parent / f"{out_stem.name}.proposal.yml"
    md_path.write_text(_md(ctx), encoding="utf-8")
    doc = {
        "proposal": {
            "deck": ctx.deck,
            "base_pptx": str(ctx.base_pptx),
            "ours_pptx": str(ctx.ours_pptx),
            "theirs_pptx": str(ctx.theirs_pptx),
            "base_content_rev": ctx.base_content_rev,
            "profile": ctx.profile_name,
            "rules": [_rule_row(f) for f in ctx.findings if f.kind == "format"],
            "regressions": [_regression_row(f) for f in ctx.findings if f.kind == "regression"],
        }
    }
    yml_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8"
    )
    return md_path, yml_path


def load_proposal(path: str | Path) -> dict:
    """Read a proposal yaml. Fail-loud when it is missing or malformed."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"proposal not found: {p}")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "proposal" not in doc:
        raise ValueError(f"not a merge proposal: {p}")
    return doc


def undecided(doc: dict) -> list[str]:
    """Rules still awaiting a human decision."""
    return [r["rule"] for r in doc["proposal"]["rules"] if r.get("decision") is None]


def accepted_keys(doc: dict) -> dict:
    """Profile keys implied by the accepted rules.

    A rule whose `value` is a mapping contributes ALL of its keys (R2 sets both the anchor
    and the edge); otherwise the rule's own `key` takes its `value`.
    """
    out: dict = {}
    for row in doc["proposal"]["rules"]:
        if row.get("decision") != "accept":
            continue
        value = row["value"]
        if isinstance(value, dict):
            out.update(value)
        else:
            out[row["key"]] = value
    return out
