---
name: preza-de-stamp
description: 'Inject or refresh the generation-provenance stamp (model, harness, effort, version, date) in the first and last speaker-notes of a preza_gen deck content YAML. Idempotent — replaces an existing stamp instead of duplicating it. Triggers on "stamp the deck provenance", "поставь модель/версию в заметки презы", "update deck provenance", or as step 4 of create-preza-about-de-tool.'
---

Write one provenance paragraph into the FIRST and LAST slide `notes` of a deck content YAML.
`preza-de-validate` asserts it is present. Sub-skill of `create-preza-about-de-tool`.

## Run

```bash
S=~/.ai/skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts
python "$S/stamp_provenance.py" content/preza-dagster-content.yml \
  --model claude-opus-4-8 --harness "Claude Code" --effort max \
  --version v1.0 --date 2026-07-20 [--dry]
```

`--date` is **required and explicit** — the script never reads the wall clock, so runs stay
reproducible. `--dry` prints the stamp and its targets without writing.

## Stamp format

```
— Сгенерировано: model=<id> · harness=<name> · effort=<level> · version=<vN.m> · <YYYY-MM-DD>
```

## Caveat

Writing re-serialises the YAML via `safe_dump` (key order preserved; block scalars normalised).
Hand-authored decks that already carry the stamp inline don't need this — run it on the
generative path, or when the model/version changes.
