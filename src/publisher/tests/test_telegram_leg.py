"""telegram_leg: size guard fires before the file send; text/file failures isolate."""

import subprocess

import pytest

from publisher import telegram_leg as tg
from publisher.settings import TelegramSettings


@pytest.fixture()
def pptx(tmp_path):
    p = tmp_path / "X_v1.2.pptx"
    p.write_bytes(b"x" * 1024)
    return p


@pytest.fixture()
def calls(monkeypatch):
    seen = {"text": [], "file": []}
    monkeypatch.setattr(tg, "send_text", lambda slug, kind, body: seen["text"].append(body))
    monkeypatch.setattr(tg, "publish_deck", lambda p, **kw: seen["file"].append((p, kw)))
    return seen


def test_notify_sends_text_then_file(pptx, calls):
    ok, detail = tg.notify(
        TelegramSettings(), topic="dbt", version="3.14", slides=52, pptx=pptx, drive_url="https://v"
    )
    assert ok and detail == "text+file sent"
    assert calls["text"] == ["📎 dbt — v3.14 · 52 слайдов\nhttps://v"]
    assert len(calls["file"]) == 1
    assert calls["file"][0][1] == {"open_app": False, "send": True, "chat": None, "thread": None}


def test_size_guard_blocks_file_but_not_text(pptx, calls):
    ok, detail = tg.notify(
        TelegramSettings(max_upload_mb=0), topic="dbt", version="3.14", slides=52,
        pptx=pptx, drive_url=None,
    )
    assert not ok
    assert "exceeds the 0MB send cap" in detail
    assert calls["text"] and not calls["file"]  # text still went out


def test_text_failure_does_not_block_file(pptx, monkeypatch):
    sent = []
    monkeypatch.setattr(
        tg, "send_text",
        lambda *a: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "tg-inform")),
    )
    monkeypatch.setattr(tg, "publish_deck", lambda p, **kw: sent.append(p))
    ok, detail = tg.notify(
        TelegramSettings(), topic="dbt", version="1.0", slides=1, pptx=pptx, drive_url=None
    )
    assert not ok and detail.startswith("text:") and sent == [pptx]
