---
name: create-preza-about-de-tool
description: Create or update a research-backed MLInside presentation about a data-engineering tool, including architecture, integrations, comparisons, examples, visuals, speaker notes, and homework.
---

# Create a DE-tool presentation

Use the repository's `preza_gen` YAML format. Inspect the existing dbt deck and shared settings before editing. Create one content file under `content/`, keep the shared theme stable, and add a dedicated Justfile target only when it improves repeatability.

Apply the supporting skills in this order:

1. `research-de-tool` — establish dated facts and primary-source links.
2. `design-de-tool-architecture` — turn concepts into a coherent asset/entity and runtime narrative.
3. `compare-de-tool-integrations` — compare adjacent engines and orchestrators by ownership and trade-offs.
4. `author-de-tool-deck` — write YAML slides, code examples, notes, visuals, and homework.

Required deck coverage: context/history/people/present state; architecture and entities; development and production; CLI; integrations; competitors; operational risks; and a practical assignment based on existing course material.

Prefer local screenshots/media when available. Use code panels for executable examples and tables only for compact comparisons. Mark forecasts and interpretations as perspectives, not facts. Validate YAML and build PPTX + HTML before handoff.
