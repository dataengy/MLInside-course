"""Ingestor tests — hardlink_or_copy + manifest generation (tmp_path; no network/iCloud)."""

import os

import yaml

from preza_gen import ingest, utils


def test_hardlink_or_copy_same_volume(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"hello")
    dst = tmp_path / "sub" / "dst.bin"
    method = utils.hardlink_or_copy(src, dst)
    assert method == "hardlink"  # same tmp volume → hardlink
    assert dst.read_bytes() == b"hello"
    assert os.stat(src).st_ino == os.stat(dst).st_ino


def test_ingest_writes_manifest(tmp_path):
    # a tiny repo: settings/config.yml + a local source file to ingest
    (tmp_path / "settings").mkdir()
    (tmp_path / "data" / "source").mkdir(parents=True)
    src = tmp_path / "orig.pptx"
    src.write_bytes(b"deck-bytes")
    cfg = {
        "ingest": {
            "manifest": "settings/files.yml",
            "targets": [{"src": str(src), "dst": "data/source/deck.pptx"}],
        }
    }
    config_path = tmp_path / "settings" / "config.yml"
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    entries = ingest.ingest(config_path)
    assert len(entries) == 1
    e = entries[0]
    assert e.method == "hardlink"
    assert e.bytes == len(b"deck-bytes")
    assert e.inode == os.stat(tmp_path / "data" / "source" / "deck.pptx").st_ino

    manifest = yaml.safe_load((tmp_path / "settings" / "files.yml").read_text())
    assert "data/source/deck.pptx" in manifest["ingested"]
    assert manifest["ingested"]["data/source/deck.pptx"]["method"] == "hardlink"
