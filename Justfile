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
_ogip_content := "content/preza-ogip-content.yml"

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

# Build the dbt deck (all formats), open locally, then publish it (TG + GDrive + sheet).
publish:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --all --open \
      --settings {{_settings}} --content {{_content}}
    just publish-new --deck {{_content}}

# Publish every built version newer than the cursor: Telegram + GDrive (stable URL) +
# schedule-sheet columns. Idempotent; spec: docs/deck-publish-pipeline.md
publish-new *ARGS:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m publisher run {{ARGS}}

# Same, print intent only (no network, no writes)
publish-new-dry:
    just publish-new --dry

# Cursor vs newest built version, per deck
publish-status:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m publisher status

# One-time: search-or-create the course Drive folder, prints id for settings/publish.yml
publish-init-drive *ARGS:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m publisher init-drive {{ARGS}}

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

# Build the OGIP showcase deck (PPTX + HTML) — portfolio artifact, not a course lecture.
ogip-build:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_gen.build_deck --pptx --html \
      --settings {{_settings}} --content {{_ogip_content}}

# ── deck generation skill (create-preza-about-de-tool) ──────────────────────
# Validate one deck content file against the schema, slide bounds and provenance stamp.
preza-validate content:
    cd {{_dir}} && python3 {{_preza_skill}}/validate_content.py {{content}} \
      --settings settings/config.yml --visuals code-tables

# Validate every generated DE-tool deck at once.
preza-validate-all:
    cd {{_dir}} && for f in {{_dagster_content}} {{_prefect_content}} {{_cicd_obs_content}} {{_airflow_content}} {{_ogip_content}}; do \
      python3 {{_preza_skill}}/validate_content.py "$f" \
        --settings settings/config.yml --visuals code-tables || exit 1; \
    done

# Скалярный линт контент-YAML — ловит то, что схема-валидатор и preza-review пропускают:
# буллет/ячейку с двоеточием без кавычек YAML читает как мапу, и падает только билд.
preza-lint *files:
    cd {{_dir}} && python3 .tmp/lint_content_scalars.py {{files}}

# Правки деки по id слайда без переформатирования файла (list/extract/remove/move/insert).
# Пример: just preza-slides content/preza-dbt-v3-content.yml move --id 045-x --after 044-y
preza-slides content *ARGS:
    cd {{_dir}} && python3 scripts/preza/edit_slides.py {{content}} {{ARGS}}

# Реестр картинок деки: где какая стоит, откуда взялась, что снято/перенесено вручную.
# sync пишет content/<deck>-images.yml и помечает снятые руками картинки manual-removed —
# после этого их больше никто не поставит обратно. check ничего не пишет и падает, если
# реестр разошёлся с контентом; spare печатает, что ещё можно поставить.
# Пример: just preza-images sync content/preza-dbt-v4-content.yml --settings=.tmp/v4_build_settings.yml
preza-images cmd content *ARGS:
    cd {{_dir}} && python3 scripts/preza/images_manifest.py {{cmd}} {{content}} {{ARGS}}

# Подстрочники докладчика: абсолютное время «10:00-11:30» перед меткой [~N мин] и короткие
# разделы («Главное», «Переход»…) меткой на своей строке + буллетами по предложениям.
# Идемпотентно: повторный apply даёт «изменено 0». Та же логика (preza_gen/notes.py) работает
# на каждой сборке, поэтому apply нужен лишь чтобы часы были видны в самом контенте.
# check ничего не пишет и падает при расхождении — годится для CI.
# Пример: just preza-notes apply content/preza-dbt-v4-content.yml --scope=all
preza-notes cmd content *ARGS:
    cd {{_dir}} && python3 scripts/preza/notes_fix.py {{cmd}} {{content}} {{ARGS}}

# Import a FOREIGN .pptx (one this repo did not generate) into a reviewable content YAML.
# Lossy and one-way — never build from the result. Add a plan entry with `generated: false`.
preza-import-pptx pptx out="":
    cd {{_dir}} && python3 {{_preza_skill}}/pptx_to_content.py {{quote(pptx)}} \
      -o {{ if out == "" { "content/imported/" + file_stem(pptx) + ".yml" } else { out } }}

# Review a deck against its lecture's accents (content/presentations.yml) + the DE-tool outline.
# Writes docs/reviews/<out_name>.{md,findings.yml}; exits 1 on a missing must-have accent.
preza-review content *ARGS:
    cd {{_dir}} && python3 {{_preza_skill}}/review_content.py {{content}} \
      --plan content/presentations.yml --settings settings/config.yml {{ARGS}}

# Review every deck the plan maps to a content file.
preza-review-all *ARGS:
    #!/usr/bin/env bash
    set -uo pipefail
    cd {{_dir}}
    mapfile -t decks < <(python3 -c "import yaml,pathlib; d=yaml.safe_load(pathlib.Path('content/presentations.yml').read_text()) or {}; [print(e['content']) for e in (d.get('presentations') or []) if e.get('content')]")
    if [ ${#decks[@]} -eq 0 ]; then
      echo "No decks mapped in content/presentations.yml — run 'just presentations-plan' and fill content:" >&2
      exit 1
    fi
    rc=0
    for f in "${decks[@]}"; do
      python3 {{_preza_skill}}/review_content.py "$f" \
        --plan content/presentations.yml --settings settings/config.yml {{ARGS}} || rc=1
    done
    exit $rc

# Resolve the slug/out_name a new topic would get (dry helper for the skill).
preza-slug topic:
    cd {{_dir}} && python3 {{_preza_skill}}/resolve_slug.py {{quote(topic)}}

# Re-stamp provenance (model/harness/effort/version) into a deck's first+last notes.
preza-stamp content version date:
    cd {{_dir}} && python3 {{_preza_skill}}/stamp_provenance.py {{content}} \
      --model claude-opus-4-8 --harness "Claude Code" --effort max \
      --version {{version}} --date {{date}}

# План блоков записи (монтаж режет уроки до 25 мин → паузы между блоками): покрытие слайдов
# + оценка минут. План — content/presentations.yml → recording.blocks; лимиты — settings/config.yml
# → course_production. Флаги: --md (таблица для docs), --strict (длинный блок = ошибка).
preza-blocks content *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m course blocks {{content}} {{ARGS}}

# …для всех дек, у которых задан recording.blocks
preza-blocks-all *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m course blocks {{ARGS}}

# Статус правил продакшена курса (то же, что SessionStart-хук): дедлайн записи, деки без плана
# блоков, длинные блоки, открытые вопросы менеджеру (docs/course-qa.md). Spec: docs/course-rules.md
course-status *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m course status {{ARGS}}

# Напоминания курса в Todoist из settings/reminders.yml (идемпотентно по `key:` в описании).
# Без --apply — только план. Логика: src/course/reminders.py; вход: scripts/todoist/.
course-reminders *ARGS:
    cd {{_dir}} && python3 scripts/todoist/upsert_reminders.py {{ARGS}}

# …применить план (создать недостающие, синхронизировать сроки/приоритеты/текст)
course-reminders-apply *ARGS:
    just course-reminders --apply {{ARGS}}

# Build the distribution-ready HSU deck from the reviewed template-native dbt deck.
dbt-final:
    just -f src/preza_gen/preza_refactoring/Justfile build

dbt-final-verify:
    just -f src/preza_gen/preza_refactoring/Justfile verify

# ── слияние версий и форков дек (preza_merge) — docs/preza-merge-lane.md ──
# Пути (base/ours/theirs/proposal/...) — именованные параметры через {{quote(...)}}: имя
# форка ревьюера всегда содержит пробел и скобки ("... v3.15 (1).pptx"), а *ARGS их не
# переживает (just склеивает variadic-аргументы голыми пробелами перед sh -c).
# Разобрать форк ревьюера против своей ветки: отчёт + предложение с решениями человека.
preza-merge-propose deck base ours theirs rev *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge propose \
      --deck {{quote(deck)}} --base {{quote(base)}} --ours {{quote(ours)}} \
      --theirs {{quote(theirs)}} --base-content-rev {{quote(rev)}} {{ARGS}}

# Применить решения: профиль в settings/formats.yml, deck.format, сборка патч-версии.
preza-merge-apply proposal *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge apply {{quote(proposal)}} {{ARGS}}

# Проверить результат: base-контент новым профилем ↔ форк + инвариант мержа.
preza-merge-verify proposal merged *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge verify {{quote(proposal)}} {{quote(merged)}} {{ARGS}}

# propose → (решения) → apply → verify одной командой.
preza-merge-run deck base ours theirs rev *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge run \
      --deck {{quote(deck)}} --base {{quote(base)}} --ours {{quote(ours)}} \
      --theirs {{quote(theirs)}} --base-content-rev {{quote(rev)}} {{ARGS}}

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

# uv: sync the venv from pyproject (incl. dev extras)
# ── course schedule sheet → presentations plan (src/schedule + integrations/google/sheets) ──
# One-time auth (opens a browser): just -f integrations/google/sheets/Justfile auth
# Smoke-test auth: print the schedule sheet's tab names.
gsheet-tabs:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m schedule tabs

# Fetch the sheet verbatim → settings/schedule.yml (generated; never hand-edit)
gsheet-dump *ARGS:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m schedule dump {{ARGS}}

# Upsert content/presentations.yml from the dump (hand-curated fields survive)
presentations-plan *ARGS:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m schedule plan {{ARGS}}

presentations-plan-dry:
    just presentations-plan --dry

# Print the current lecture → deck plan
presentations-show:
    cd {{_dir}} && PYTHONPATH=src uv run --extra gsheets python -m schedule show

sync:
    cd {{_dir}} && uv sync --extra dev --extra gsheets

# ── whole-repo update (docs in scripts/repo-update.sh header) ────────────────
# Fresh clone or stale checkout → working state: git-lfs, index repair, fetch,
# private submodules (hnkovr/*), uv sync. Idempotent.
update *ARGS:
    cd {{_dir}} && bash scripts/repo-update.sh {{ARGS}}

# Read-only: is this checkout healthy? (lfs / index / submodules / cleanliness)
repo-doctor:
    cd {{_dir}} && bash scripts/repo-update.sh doctor

# ── cross-account repo sharing (docs in scripts/repo-share.sh header) ────────
# Both hnkovr and dataengy admin on the umbrella repo + every hnkovr/* submodule,
# so whichever identity the keychain hands git can always clone and push.

# Read-only: access matrix for every submodule + related repo, per account
repo-share-doctor:
    cd {{_dir}} && bash scripts/repo-share.sh doctor

# Invite + accept whatever the matrix is missing. Idempotent.
repo-share:
    cd {{_dir}} && bash scripts/repo-share.sh sync

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

# ── secrets sync (Bitwarden ⇄ settings/.env.secrets ⇄ git-secret) — docs/secrets-sync.md ──
# Bitwarden lane needs an unlocked vault first: export BW_SESSION=$(bw unlock --raw)

# Health check: tools, vault, GPG key, template drift, file-typed secrets
secrets-doctor:
    cd {{_dir}} && bash scripts/secrets-sync.sh doctor

# New workstation: pull secrets (Bitwarden first, git-secret fallback) + doctor
secrets-bootstrap:
    cd {{_dir}} && bash scripts/secrets-sync.sh bootstrap

# Old workstation → vault: .env.secrets as a secure note
secrets-push:
    cd {{_dir}} && bash scripts/secrets-sync.sh bw-push

# Vault → this workstation: overwrite settings/.env.secrets
secrets-pull:
    cd {{_dir}} && bash scripts/secrets-sync.sh bw-pull

# One-time: generate/enroll the GPG key for the git-secret lane
secrets-gpg-init:
    cd {{_dir}} && bash scripts/secrets-sync.sh gpg-init

# Encrypt settings/.env.secrets → .env.secrets.secret (committed to git)
secrets-hide:
    cd {{_dir}} && bash scripts/secrets-sync.sh hide

# Decrypt .env.secrets.secret → settings/.env.secrets
secrets-reveal:
    cd {{_dir}} && bash scripts/secrets-sync.sh reveal

# Посадка ветки worktree в main + удаление ветки и каталога — с семью проверками.
# По умолчанию ТОЛЬКО проверяет: `git worktree remove` уничтожает untracked-файлы без следа,
# а в одном worktree здесь обычно работают несколько сессий сразу. Удаление требует явного
# --force-remove. Живые сессии bash не видит — проверьте ListAgents (скилл worktree-land).
# Пример: just worktree-land check   ·   just worktree-land remove . --force-remove
worktree-land cmd="check" *ARGS:
    cd {{_dir}} && bash scripts/worktree_land.sh {{cmd}} {{ARGS}}
