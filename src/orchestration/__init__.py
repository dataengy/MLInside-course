"""orchestration — Prefect-only wrappers over the preza_gen core.

Kept in a package named `orchestration` (NOT `prefect`, which would shadow the library). Every
flow/task here is a thin wrapper over preza_gen.{scan,pipeline,publish}; the business logic lives
there, prefect-free, so a Dagster port would be a decorator swap and `just check` stays green
without the (heavy) orchestration extra installed.
"""
