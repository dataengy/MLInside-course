"""runner: leg isolation, retry-only-failed, drive→sheet dependency, seeding, dry mode.

Legs are monkeypatched at the module seams (gdrive/telegram_leg/gsheet_write/auth) so these
tests exercise ONLY control flow — zero network, per the repo test policy.
"""

from unittest.mock import MagicMock

import pytest
import yaml

from publisher import detect, gdrive, runner, telegram_leg
from publisher import state as st
from publisher.settings import DriveSettings, PublishConfig, SheetSettings, TelegramSettings
from schedule.cli import PLAN_HEADER


def _cfg(tmp_path, folder_id="D1") -> PublishConfig:
    return PublishConfig(
        drive=DriveSettings(folder_id=folder_id),
        sheet=SheetSettings(),
        telegram=TelegramSettings(),
        scopes=[],
        token_cache=tmp_path / "token.json",
        service_account_file=None,
        state_file=tmp_path / "state.json",
        out_dir=tmp_path / "generated",
        plan_path=tmp_path / "presentations.yml",
        spreadsheet_id="SID",
        header_row=1,
        sheet_tab_override=None,
        columns_map={"topic": ["название"]},
    )


def _write_plan(cfg, entries):
    doc = {"source": {"tab": "S"}, "presentations": entries}
    cfg.plan_path.write_text(
        PLAN_HEADER + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), "utf-8"
    )


def _build(cfg, out_name, ver="1.2"):
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    p = cfg.out_dir / f"{out_name}_v{ver}.pptx"
    p.write_bytes(b"pptx")
    return p


@pytest.fixture()
def env(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    _write_plan(cfg, [{"topic": "Тема dbt", "out_name": "X", "content": "content/x.yml"}])
    _build(cfg, "X")

    seen = {"drive": [], "tg": [], "sheet": []}
    monkeypatch.setattr(detect, "slide_count", lambda p: 52)
    monkeypatch.setattr(
        gdrive, "upload_or_update",
        lambda svc, **kw: (seen["drive"].append(kw), gdrive.DriveResult("F1", "https://v/F1"))[1],
    )
    monkeypatch.setattr(
        telegram_leg, "notify",
        lambda t, **kw: (seen["tg"].append(kw), (True, "text+file sent"))[1],
    )
    monkeypatch.setattr(runner.auth, "get_service", lambda *a, **kw: MagicMock())

    gw = runner.gsheet_write
    monkeypatch.setattr(gw, "resolve_tab_title", lambda *a: "S")
    monkeypatch.setattr(gw, "read_header", lambda *a: ["название", "лектор"])
    monkeypatch.setattr(gw, "find_row_by_topic", lambda *a: 5)
    monkeypatch.setattr(gw, "apply_updates", lambda svc, sid, ups: seen["sheet"].append(ups))
    return cfg, seen


def test_full_publish_records_everything(env):
    cfg, seen = env
    outcomes, failed = runner.run(cfg)
    assert not failed and len(outcomes) == 1
    assert len(seen["drive"]) == 1 and len(seen["tg"]) == 1 and len(seen["sheet"]) == 1
    assert seen["tg"][0]["drive_url"] == "https://v/F1"  # drive ran first

    ds = st.read_state(cfg.state_file)["X"]
    assert ds.published_at and ds.drive_file_id == "F1" and ds.slides == 52
    doc = yaml.safe_load(cfg.plan_path.read_text("utf-8"))
    pub = doc["presentations"][0]["published"]
    assert pub["version"] == "1.2" and pub["url"] == "https://v/F1"
    assert pub["legs"] == {"tg": "ok", "drive": "ok", "sheet": "ok"}


def test_rerun_is_idempotent_no_resend(env):
    cfg, seen = env
    runner.run(cfg)
    outcomes, failed = runner.run(cfg)
    assert not failed
    assert len(seen["tg"]) == 1  # no duplicate Telegram send
    assert "nothing to do" in outcomes[0].lines[0]


def test_drive_failure_isolates_tg_and_skips_sheet(env, monkeypatch):
    cfg, seen = env
    monkeypatch.setattr(
        gdrive, "upload_or_update",
        lambda svc, **kw: (_ for _ in ()).throw(RuntimeError("quota")),
    )
    outcomes, failed = runner.run(cfg)
    assert failed
    ds = st.read_state(cfg.state_file)["X"]
    assert ds.drive.status == "error" and "quota" in ds.drive.error
    assert ds.tg.status == "ok"  # tg still attempted (without a URL)
    assert seen["tg"][0]["drive_url"] is None
    assert ds.sheet.status == "skipped" and "drive not ok" in ds.sheet.error
    assert ds.published_at is None


def test_retry_runs_only_failed_legs(env, monkeypatch):
    cfg, seen = env
    boom = {"on": True}

    def flaky(svc, **kw):
        if boom["on"]:
            raise RuntimeError("transient")
        seen["drive"].append(kw)
        return gdrive.DriveResult("F1", "https://v/F1")

    monkeypatch.setattr(gdrive, "upload_or_update", flaky)
    runner.run(cfg)
    assert len(seen["tg"]) == 1

    boom["on"] = False
    outcomes, failed = runner.run(cfg)
    assert not failed
    assert len(seen["tg"]) == 1  # tg NOT re-sent — only drive+sheet retried
    assert len(seen["drive"]) == 1 and len(seen["sheet"]) == 1
    assert st.read_state(cfg.state_file)["X"].published_at


def test_version_bump_resets_and_keeps_drive_identity(env):
    cfg, seen = env
    runner.run(cfg)
    _build(cfg, "X", "1.3")
    outcomes, failed = runner.run(cfg)
    assert not failed and len(seen["tg"]) == 2
    assert seen["drive"][1]["existing_file_id"] == "F1"  # stable URL: update, not create
    ds = st.read_state(cfg.state_file)["X"]
    assert ds.version == "1.3"


def test_seed_from_published_prevents_fresh_clone_resend(env):
    cfg, seen = env
    _write_plan(cfg, [{
        "topic": "Тема dbt", "out_name": "X", "content": "content/x.yml",
        "published": {"version": "1.2", "slides": 52, "url": "https://v/F1",
                      "drive_file_id": "F1", "at": "2026-08-16T00:00:00+00:00",
                      "legs": {"tg": "ok", "drive": "ok", "sheet": "ok"}},
    }])
    outcomes, failed = runner.run(cfg)  # cursor file absent — fresh clone
    assert not failed
    assert seen["tg"] == [] and seen["drive"] == []  # nothing re-sent
    assert "nothing to do" in outcomes[0].lines[0]


def test_no_sheet_row_still_counts_as_served(env, monkeypatch):
    cfg, seen = env
    monkeypatch.setattr(runner.gsheet_write, "find_row_by_topic", lambda *a: None)
    outcomes, failed = runner.run(cfg)
    assert not failed
    ds = st.read_state(cfg.state_file)["X"]
    assert ds.sheet.status == "skipped" and ds.sheet.error == runner.NO_ROW
    assert ds.published_at  # OGIP/Prefect case: fully served without a sheet row


def test_only_and_force_flags(env):
    cfg, seen = env
    runner.run(cfg, only={"drive"})
    ds = st.read_state(cfg.state_file)["X"]
    assert ds.drive.status == "ok" and ds.tg.status == "pending" and seen["tg"] == []

    runner.run(cfg, only={"drive"}, force=True)
    assert len(seen["drive"]) == 2  # force re-ran an ok leg

    outcomes, failed = runner.run(cfg)  # finish the rest
    assert not failed and len(seen["tg"]) == 1 and len(seen["sheet"]) == 1


def test_dry_lists_intent_without_side_effects(env):
    cfg, seen = env
    outcomes, failed = runner.run(cfg, dry=True)
    assert not failed
    assert outcomes[0].lines == ["would run: tg, drive, sheet"]
    assert seen == {"drive": [], "tg": [], "sheet": []}
    assert not cfg.state_file.exists()


def test_missing_folder_id_fails_drive_leg_only(env, tmp_path):
    cfg, seen = env
    cfg.drive.folder_id = None
    outcomes, failed = runner.run(cfg)
    assert failed
    ds = st.read_state(cfg.state_file)["X"]
    assert "publish-init-drive" in ds.drive.error
    assert ds.tg.status == "ok"
