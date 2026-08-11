---
name: design-de-tool-architecture
description: Design a teaching narrative and architecture review for a data-engineering tool, covering entities, runtime boundaries, dev/prod, ownership, and operational failure modes.
---

Start from the tool's unit of ownership: asset, task, flow, model, or workflow. Map definitions, control plane, user code, storage, compute, automation, and deployment boundaries. Explain every core entity with one concrete example, then contrast local development with production. Include idempotency, retries, partitions/backfills, observability, and multi-team boundaries.
