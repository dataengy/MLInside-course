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
_dagster_content := "content/preza-dagster-content.yml"
_prefect_content := "content/preza-prefect-content.yml"
_cicd_obs_content := "content/preza-cicd-observability-content.yml"
_airflow_content := "content/preza-apache-airflow-content.yml"

# Deck-generation skill (canonical catalog) — scripts used by the validate/new targets below.
_preza_skill := "~/.ai/skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts"

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

# Build the Dagster lecture deck (PPTX + HTML).
dagster-build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html \
      --settings {{_settings}} --content {{_dagster_content}}

# Build all Dagster formats (PPTX + HTML + PDF when LibreOffice is available).
dagster-build-all:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --all \
      --settings {{_settings}} --content {{_dagster_content}}

prefect-build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html \
      --settings {{_settings}} --content {{_prefect_content}}

cicd-observability-build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html \
      --settings {{_settings}} --content {{_cicd_obs_content}}

# Build the Apache Airflow lecture deck (PPTX + HTML).
airflow-build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html \
      --settings {{_settings}} --content {{_airflow_content}}

# ── deck generation skill (create-preza-about-de-tool) ──────────────────────
# Validate one deck content file against the schema, slide bounds and provenance stamp.
preza-validate content:
    cd {{_dir}} && python3 {{_preza_skill}}/validate_content.py {{content}} \
      --settings settings/config.yml --visuals code-tables

# Validate every generated DE-tool deck at once.
preza-validate-all:
    cd {{_dir}} && for f in {{_dagster_content}} {{_prefect_content}} {{_cicd_obs_content}} {{_airflow_content}}; do \
      python3 {{_preza_skill}}/validate_content.py "$f" \
        --settings settings/config.yml --visuals code-tables || exit 1; \
    done

# Resolve the slug/out_name a new topic would get (dry helper for the skill).
preza-slug topic:
    cd {{_dir}} && python3 {{_preza_skill}}/resolve_slug.py {{quote(topic)}}

# Re-stamp provenance (model/harness/effort/version) into a deck's first+last notes.
preza-stamp content version date:
    cd {{_dir}} && python3 {{_preza_skill}}/stamp_provenance.py {{content}} \
      --model claude-opus-4-8 --harness "Claude Code" --effort max \
      --version {{version}} --date {{date}}

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

# ── picstore (src/picstore submodule): find/catalog/apply deck illustrations ──
_picstore := "PYTHONPATH=src python3 -m picstore.cli"

# Provider availability matrix (keys, browsers, local roots). Run this FIRST —
# an empty search is almost always a provider that quietly reported unavailable.
picstore-doctor:
    cd {{_dir}} && {{_picstore}} doctor

# Decks under management (slug, visual profile, content path)
picstore-decks:
    cd {{_dir}} && {{_picstore}} decks

# Picture types and styles usable with --types / --styles (omit = search all)
picstore-taxonomy:
    cd {{_dir}} && {{_picstore}} taxonomy

# Index deck slides into the catalog (needs ids — see picstore-ids-backfill)
picstore-scan deck="":
    cd {{_dir}} && {{_picstore}} scan {{ if deck == "" { "" } else { "--deck " + deck } }}

# Write the deterministic XML projection (the MERGEABLE source of truth)
picstore-export:
    cd {{_dir}} && {{_picstore}} export

# Recover from an unmergeable catalog.sqlite conflict: take either binary, hand-merge
# catalog.xml, then rebuild the sqlite from it.
picstore-rebuild:
    cd {{_dir}} && {{_picstore}} import --rebuild

# Assign the opaque `id:` slide key (assigned once, never rewritten). Dry by default.
picstore-ids-backfill-dry:
    cd {{_dir}} && {{_picstore}} ids backfill

picstore-ids-backfill:
    cd {{_dir}} && {{_picstore}} ids backfill --execute

# Fail on missing / duplicate / malformed slide ids
picstore-ids-check:
    cd {{_dir}} && {{_picstore}} ids check

# Slides whose position moved since their id was minted (informational)
picstore-ids-drift:
    cd {{_dir}} && {{_picstore}} ids drift

# ── picstore (src/picstore submodule): find/catalog/apply deck illustrations ──
_picstore := "PYTHONPATH=src python3 -m picstore.cli"

# Provider availability matrix (keys, browsers, local roots). Run this FIRST —
# an empty search is almost always a provider that quietly reported unavailable.
picstore-doctor:
    cd {{_dir}} && {{_picstore}} doctor

# Decks under management (slug, visual profile, content path)
picstore-decks:
    cd {{_dir}} && {{_picstore}} decks

# Picture types and styles usable with --types / --styles (omit = search all)
picstore-taxonomy:
    cd {{_dir}} && {{_picstore}} taxonomy

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
