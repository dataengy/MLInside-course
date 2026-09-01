"""publisher.runner — detect → drive → tg → sheet → record, per deck, legs isolated.

Philosophy: one leg's failure must neither abort the batch nor block independent legs
(deliberate divergence from preza_gen.publish's fail-loud — this orchestrator spans three
independent channels × many decks). The only ordering dependency: the sheet row must
describe one consistent artifact, so the sheet leg requires the Drive leg to be ``ok`` for
the current version (this run or recorded). Re-runs retry only non-ok legs — a retry never
re-sends Telegram for a version it already delivered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger as log

from publisher import auth, detect, errors, gdrive, gsheet_write, plan_writer, telegram_leg
from publisher import state as st
from publisher.settings import PublishConfig

NO_ROW = "no matching sheet row"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Outcome:
    out_name: str
    version: str
    lines: list[str] = field(default_factory=list)
    failed: bool = False


def load_plan_entries(plan_path: Path) -> list[dict]:
    doc = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    return [e for e in doc.get("presentations") or [] if e.get("content") and e.get("out_name")]


def seed_from_published(entry: dict, built: detect.BuiltDeck) -> st.DeckState | None:
    """Adopt the git-tracked record when it already describes the newest local build.

    Fresh clone / lost cursor: without this, every workstation would re-send Telegram.
    """
    pub = entry.get("published") or {}
    if not isinstance(pub, dict) or str(pub.get("version") or "") != built.version:
        return None
    ds = st.DeckState(
        version=built.version,
        sig=built.sig,
        slides=pub.get("slides"),
        drive_file_id=pub.get("drive_file_id"),
        drive_url=pub.get("url"),
        published_at=pub.get("at"),
    )
    legs_raw = pub.get("legs")
    legs = legs_raw if isinstance(legs_raw, dict) else {}
    default = "ok" if pub.get("at") else "pending"
    for name in st.LEGS:
        raw = legs.get(name)
        setattr(ds, name, st.LegStatus(status=raw if isinstance(raw, str) else default))
    return ds


def published_block(ds: st.DeckState) -> dict:
    return {
        "version": ds.version,
        "slides": ds.slides,
        "url": ds.drive_url,
        "drive_file_id": ds.drive_file_id,
        "at": ds.published_at,
        "legs": {name: ds.leg(name).status for name in st.LEGS},
    }


def _fully_served(ds: st.DeckState) -> bool:
    sheet_done = ds.sheet.status == "ok" or (
        ds.sheet.status == "skipped" and ds.sheet.error == NO_ROW
    )
    return ds.tg.status == "ok" and ds.drive.status == "ok" and sheet_done


class _SheetCtx:
    """Live sheet facts resolved once per run (tab, header, topic column), lazily."""

    def __init__(self, cfg: PublishConfig, service: Any):
        self.cfg, self.service = cfg, service
        self.tab = gsheet_write.resolve_tab_title(service, cfg.spreadsheet_id, cfg.sheet_tab_override)
        self.header = gsheet_write.read_header(service, cfg.spreadsheet_id, self.tab, cfg.header_row)
        self.topic_col = gsheet_write.topic_column(self.header, cfg.columns_map)
        self.locale = (
            gsheet_write.sheet_locale(service, cfg.spreadsheet_id)
            if cfg.sheet.link_style == "hyperlink"
            else None
        )


class Runner:
    def __init__(self, cfg: PublishConfig):
        self.cfg = cfg
        self._services: dict[str, Any] = {}
        self._sheet_ctx: _SheetCtx | None = None

    def service(self, api: str, version: str) -> Any:
        if api not in self._services:
            self._services[api] = auth.get_service(api, version, self.cfg)
        return self._services[api]

    def sheet_ctx(self) -> _SheetCtx:
        if self._sheet_ctx is None:
            self._sheet_ctx = _SheetCtx(self.cfg, self.service("sheets", "v4"))
        return self._sheet_ctx

    # ── legs ────────────────────────────────────────────────────────────────

    def _leg_drive(self, built: detect.BuiltDeck, ds: st.DeckState) -> None:
        if not self.cfg.drive.folder_id:
            ds.drive = st.LegStatus(
                "error", _now(), "drive.folder_id not set — run `just publish-init-drive`"
            )
            return
        res = gdrive.upload_or_update(
            self.service("drive", "v3"),
            file_path=built.path,
            folder_id=self.cfg.drive.folder_id,
            filename=f"{built.out_name}.pptx",
            description=f"v{built.version} · {ds.slides} слайдов · MLInside 2026",
            existing_file_id=ds.drive_file_id,
            share=self.cfg.drive.share,
        )
        ds.drive_file_id, ds.drive_url = res.file_id, res.web_view_link
        ds.drive = st.LegStatus("ok", _now())

    def _leg_tg(self, entry: dict, built: detect.BuiltDeck, ds: st.DeckState) -> None:
        ok, detail = telegram_leg.notify(
            self.cfg.telegram,
            topic=str(entry.get("topic") or built.out_name),
            version=built.version,
            slides=ds.slides or 0,
            pptx=built.path,
            drive_url=ds.drive_url,
        )
        ds.tg = st.LegStatus("ok" if ok else "error", _now(), None if ok else detail)

    def _leg_sheet(self, entry: dict, ds: st.DeckState) -> None:
        if ds.drive.status != "ok" or not ds.drive_url:
            ds.sheet = st.LegStatus("skipped", _now(), "drive not ok for this version")
            return
        ctx = self.sheet_ctx()
        cfg = self.cfg
        row = gsheet_write.find_row_by_topic(
            ctx.service, cfg.spreadsheet_id, ctx.tab, cfg.header_row, ctx.topic_col,
            str(entry.get("topic") or ""),
        )
        if row is None:
            ds.sheet = st.LegStatus("skipped", _now(), NO_ROW)
            return
        cols, pending = gsheet_write.ensure_columns(
            ctx.header, ctx.tab, cfg.header_row, cfg.sheet.columns, ds.sheet_cols
        )
        updates = pending + gsheet_write.row_updates(
            ctx.tab, row, cols,
            url=ds.drive_url, version=ds.version, slides=ds.slides or 0,
            link_style=cfg.sheet.link_style, locale=ctx.locale,
        )
        gsheet_write.apply_updates(ctx.service, cfg.spreadsheet_id, updates)
        if pending:  # appended headers are now part of the live header row
            for p in pending:
                ctx.header.append(p["values"][0][0])
        ds.sheet_cols = cols
        ds.sheet = st.LegStatus("ok", _now())

    # ── per-deck orchestration ──────────────────────────────────────────────

    def publish_one(
        self,
        entry: dict,
        built: detect.BuiltDeck,
        ds: st.DeckState,
        *,
        only: set[str] | None,
        force: bool,
    ) -> Outcome:
        out = Outcome(built.out_name, built.version)
        if ds.slides is None:
            ds.slides = detect.slide_count(built.path)
        # Drive first: the TG message and the sheet row want the persistent URL.
        for name in ("drive", "tg", "sheet"):
            if only and name not in only:
                out.lines.append(f"{name}: not requested (--only)")
                continue
            if not force and ds.leg(name).status == "ok":
                out.lines.append(f"{name}: already ok for v{ds.version}")
                continue
            try:
                if name == "drive":
                    self._leg_drive(built, ds)
                elif name == "tg":
                    self._leg_tg(entry, built, ds)
                else:
                    self._leg_sheet(entry, ds)
            except Exception as e:  # noqa: BLE001 — leg isolation is the product requirement
                setattr(ds, name, st.LegStatus("error", _now(), errors.explain(e)))
            leg = ds.leg(name)
            out.lines.append(f"{name}: {leg.status}" + (f" — {leg.error}" if leg.error else ""))
            if leg.status == "error":
                out.failed = True
        if _fully_served(ds) and not ds.published_at:
            ds.published_at = _now()
        return out


def run(
    cfg: PublishConfig,
    *,
    deck: str | None = None,
    only: set[str] | None = None,
    force: bool = False,
    dry: bool = False,
) -> tuple[list[Outcome], bool]:
    """Returns (outcomes, any_failure). ``dry`` prints intent — no network, no writes."""
    entries = load_plan_entries(cfg.plan_path)
    if deck:
        entries = [
            e for e in entries
            if deck in (str(e.get("content")), str(e.get("out_name"))) or deck in str(e.get("content"))
        ]
        if not entries:
            raise ValueError(f"--deck {deck!r} matches no plan entry with content+out_name")
    cursor = st.read_state(cfg.state_file)
    runner = Runner(cfg)
    outcomes: list[Outcome] = []
    any_fail = False

    for entry in entries:
        out_name = entry["out_name"]
        built = detect.newest(cfg.out_dir, out_name)
        if built is None:
            log.debug(f"{out_name}: never built — skip")
            continue
        ds = cursor.get(out_name)
        if ds is None:
            ds = seed_from_published(entry, built) or st.DeckState()
        if (ds.version, ds.sig) != (built.version, built.sig):
            ds.reset_for(built.version, built.sig)
        if not force and not only and ds.published_at:
            outcomes.append(Outcome(out_name, built.version, [f"v{built.version}: published {ds.published_at} — nothing to do"]))
            continue

        if dry:
            todo = [
                n for n in st.LEGS
                if (not only or n in only) and (force or ds.leg(n).status != "ok")
            ]
            outcomes.append(Outcome(out_name, built.version, [f"would run: {', '.join(todo) or 'nothing'}"]))
            continue

        out = runner.publish_one(entry, built, ds, only=only, force=force)
        any_fail = any_fail or out.failed
        cursor[out_name] = ds
        st.write_state_atomic(cfg.state_file, cursor)  # after EVERY deck, not batched
        try:
            plan_writer.update_published_block(cfg.plan_path, out_name, published_block(ds))
        except Exception as e:  # noqa: BLE001 — the record must not kill the batch
            log.warning(f"{out_name}: presentations.yml record failed: {e}")
        outcomes.append(out)

    return outcomes, any_fail


def status(cfg: PublishConfig) -> list[str]:
    """One line per plan deck: newest built vs cursor: legs + url."""
    cursor = st.read_state(cfg.state_file)
    lines = []
    for entry in load_plan_entries(cfg.plan_path):
        out_name = entry["out_name"]
        built = detect.newest(cfg.out_dir, out_name)
        if built is None:
            lines.append(f"{out_name}: not built")
            continue
        ds = cursor.get(out_name) or seed_from_published(entry, built)
        if ds is None or (ds.version, ds.sig) != (built.version, built.sig):
            lines.append(f"{out_name}: v{built.version} UNPUBLISHED (cursor: {ds.version if ds else '—'})")
            continue
        legs = " ".join(f"{n}={ds.leg(n).status}" for n in st.LEGS)
        lines.append(f"{out_name}: v{built.version} {legs} {ds.drive_url or ''}".rstrip())
    return lines
