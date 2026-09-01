"""orchestration.flows — Prefect flows/tasks, each a thin wrapper over preza_gen.

  preza-scan            : diff watched inputs vs a cursor; emit event_name if anything changed.
  preza-build-and-publish: build the deck (pptx+html) and publish it; reacts to the scan event.

Business logic is in preza_gen.{scan,pipeline,publish}; these only orchestrate.
"""

from __future__ import annotations

from prefect import flow, task

from preza_gen import pipeline, publish, scan

from .config import OrchestrationConfig, load_orchestration


@task
def scan_task(o: OrchestrationConfig) -> list[str]:
    """Return the changed watched inputs and advance the cursor (raises on write failure)."""
    watched = scan.expand_watch(o.watch, o.repo_root)
    state = scan.read_state(o.cursor_file)
    changed, new_state = scan.scan_changed(watched, state)
    if changed:
        scan.write_state_atomic(o.cursor_file, new_state)
    return [c.path for c in changed]


@flow(name="preza-scan", log_prints=True)
def preza_scan() -> None:
    """Interval 'sensor': emit event_name (once) when any watched input changed."""
    from prefect.events import emit_event

    o = load_orchestration()
    changed = scan_task(o)
    if not changed:
        print("scan: no input changes")
        return
    emit_event(
        event=o.event_name,
        resource={"prefect.resource.id": f"preza.deck.{o.deck_id}"},
        payload={"settings": o.settings_yml, "content": o.content_yml, "changed": changed},
    )
    print(f"scan: emitted {o.event_name} — {len(changed)} input(s) changed")


@flow(name="preza-build-and-publish", log_prints=True)
def build_and_publish(settings: str | None = None, content: str | None = None) -> str:
    """Build the deck and publish it. settings/content come from the event, else from config."""
    o = load_orchestration()
    res = pipeline.build_deck(
        settings or o.settings_yml, content or o.content_yml, pptx=True, html=True
    )
    if res.out_path:
        publish.publish_deck(res.out_path, open_app=o.publish_open, send=o.publish_send)
    print(f"built{' + published' if res.out_path else ''}: {res.out_name}")
    return res.out_name


def seed() -> int:
    """Mark current watched inputs as seen (no build). Run once after starting `serve`."""
    o = load_orchestration()
    watched = scan.expand_watch(o.watch, o.repo_root)
    n = scan.seed(watched, o.cursor_file)
    print(f"seeded {n} inputs → {o.cursor_file}")
    return n
