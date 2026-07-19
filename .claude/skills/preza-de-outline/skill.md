---
name: preza-de-outline
description: 'Produce the standard section outline for a Data-Engineering-tool lecture deck (context/history/persons → architecture & entities → dev-vs-prod → integrations → CLI/MCP → ecosystem & trends → homework), scaled to a target slide count. Triggers on "outline a deck about <DE tool>", "структура презы про <инструмент>", "what sections for a Dagster/Prefect deck", or as step 2 of create-preza-about-de-tool.'
---

Emit the section plan for a DE-tool deck before any slide is authored. Sub-skill of
`create-preza-about-de-tool`.

## Use

Read `../create-preza-about-de-tool/references/deck-outline-de-tool.md` — it holds the
canonical 12-section template plus the note-writing standard and the comparison-table habit.
Then:

1. Map the topic onto the sections; **drop** what doesn't apply (e.g. no "multi-project"
   section for a tool without one). Never pad with invented material.
2. Allocate slides to hit the target range (course default 20..50): title + agenda + closing
   are fixed; each `kind: section` divider costs one; the rest split across sections by weight.
3. Mark which slides will be `kind: table` (every "X vs Y") and which carry a `code:` panel
   (architecture schemes, CLI, config).
4. Hand the outline to the authoring step, which writes the content YAML to
   `../create-preza-about-de-tool/references/content-schema.md`.

## Sizing rule of thumb

| target | sections | slides per section |
|---|---|---|
| ~24 | 6–7 | 2–3 |
| ~34 | 8–9 | 3–4 |
| ~45 | 10–12 | 3–5 |

Verify volatile facts (current major version, M&A news, MCP availability) **before** the
outline promises a slide about them.
