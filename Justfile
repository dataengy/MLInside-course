# Justfile — preza_gen v3 (deck generator). Run from repo root.
_dir := justfile_directory()

default:
    @just --list

# Ingest external source material into data/ + regenerate settings/files.yml provenance
ingest:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.ingest

# Build the deck (pptx + html) from build_deck_v3-settings.yml + preza-dbt-v3-content.yml
build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html

# Build all formats (pptx + html + pdf; pdf warns until an engine is installed)
build-all:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --all

# Send the newest built deck (auto-versioned) to the MLInside Telegram topic (118)
send:
    #!/usr/bin/env bash
    set -euo pipefail
    f=$(ls -t ~/Downloads/MLInside_Введение-в-dbt_v*.pptx | head -1)
    ver=$(basename "$f" .pptx | sed 's/.*_v/v/')
    bash ~/.ai/scripts/telegram/tg-send-file.sh \
      --file "$f" \
      --caption "📎 Введение в dbt — $ver · MLInside" \
      --chat -1002281796095 --thread 118

build-send: build send

# Serve the Prefect pipeline (scan interval + build-and-publish trigger). Needs a running
# `prefect server start` and the orchestration extra. Publishing obeys config.yml orchestration.publish.
serve:
    cd {{_dir}} && PYTHONPATH=src python3 -m orchestration.serve

# Seed the scan cursor: mark current watched inputs as seen (no build). Run once after `serve`.
seed:
    cd {{_dir}} && PYTHONPATH=src python3 -m orchestration.serve --seed

# uv: sync the venv from pyproject (incl. dev extras)
sync:
    cd {{_dir}} && uv sync --extra dev

test:
    cd {{_dir}} && python3 -m pytest

lint:
    cd {{_dir}} && ruff check src

fmt:
    cd {{_dir}} && ruff format src && ruff check --fix src

typecheck:
    cd {{_dir}} && ty check src

# lint + typecheck + tests
check: lint typecheck test
