# Justfile — preza_gen v3 (deck generator). Run from repo root.
_dir := justfile_directory()

default:
    @just --list

# Ingest external source material into data/ + regenerate settings/files.yml provenance
ingest:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.ingest

# Deck config lives in content/ (course-specific); the generator is the src/preza_gen submodule.
_settings := "content/build_deck_v3-settings.yml"
_content := "content/preza-dbt-v3-content.yml"

# Build the deck (pptx + html)
build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html \
      --settings {{_settings}} --content {{_content}}

# Build all formats (pptx + html + PDF via LibreOffice; WeasyPrint is the optional fallback)
build-all:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --all \
      --settings {{_settings}} --content {{_content}}

# Build, open the latest deck locally, then send it to Telegram.
publish:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --all --open \
      --settings {{_settings}} --content {{_content}}
    just send

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

# Build the distribution-ready HSU deck from the reviewed template-native dbt deck.
dbt-final:
    just -f src/preza_gen/preza_refactoring/Justfile build

dbt-final-verify:
    just -f src/preza_gen/preza_refactoring/Justfile verify

# Serve the Prefect pipeline (scan interval + build-and-publish trigger). Needs a running
# `prefect server start` and the orchestration extra. Publishing obeys config.yml orchestration.publish.
serve:
    cd {{_dir}} && PYTHONPATH=src python3 -m orchestration.serve

# Seed the scan cursor: mark current watched inputs as seen (no build). Run once after `serve`.
seed:
    cd {{_dir}} && PYTHONPATH=src python3 -m orchestration.serve --seed

# ── librarian (src/librarian submodule): dedupe/categorize/version/catalog ──
# Scan source roots into data/.state/librarian-inventory.yml
librarian-inventory +roots:
    cd {{_dir}} && PYTHONPATH=src python3 -m librarian.cli inventory {{roots}}

# Compute the move plan (no changes) → data/.state/librarian-plan.yml
librarian-plan +roots:
    cd {{_dir}} && PYTHONPATH=src python3 -m librarian.cli plan {{roots}}

# Dry-run the reviewed plan
librarian-apply-dry:
    cd {{_dir}} && PYTHONPATH=src python3 -m librarian.cli apply

# Execute the reviewed plan (moves files!)
librarian-apply:
    cd {{_dir}} && PYTHONPATH=src python3 -m librarian.cli apply --execute

# Regenerate data/CATALOG.md from current data/ + data/reviews.yml
librarian-catalog:
    cd {{_dir}} && PYTHONPATH=src python3 -m librarian.cli catalog

# Deterministic doc properties for given files (YAML to stdout)
librarian-docprops +paths:
    cd {{_dir}} && PYTHONPATH=src python3 -m librarian.cli docprops {{paths}}

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
