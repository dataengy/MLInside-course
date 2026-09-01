"""orchestration.serve — one process serving both deployments (scan on an interval + build).

The event trigger is declared ON the build deployment, so Prefect auto-creates the linked
automation on deploy — no hand-written Automation, no work pool, no separate worker.

Run (needs a Prefect server; `orchestration` extra installed):
    prefect server start                                  # terminal 1
    PREFECT_API_URL=http://127.0.0.1:4200/api \\
      PYTHONPATH=src python -m orchestration.serve        # terminal 2
    PYTHONPATH=src python -m orchestration.serve --seed    # once: mark current inputs as seen
"""

from __future__ import annotations

import sys

from prefect import serve
from prefect.events import DeploymentEventTrigger

from .config import load_orchestration
from .flows import build_and_publish, preza_scan, seed


def main() -> None:
    if "--seed" in sys.argv:
        seed()
        return

    o = load_orchestration()
    scan_dep = preza_scan.to_deployment(name="scan", interval=o.scan_interval_s)
    build_dep = build_and_publish.to_deployment(
        name="build-and-publish",
        triggers=[
            DeploymentEventTrigger(
                enabled=True,
                match={"prefect.resource.id": f"preza.deck.{o.deck_id}"},
                expect={o.event_name},
                parameters={
                    "settings": "{{ event.payload.settings }}",
                    "content": "{{ event.payload.content }}",
                },
            )
        ],
    )
    print(
        f"serving preza pipeline — scan every {o.scan_interval_s}s; "
        f"publish(open={o.publish_open}, send={o.publish_send})"
    )
    # to_deployment is @sync_compatible → typed `RunnerDeployment | Coroutine`; it's sync here.
    serve(scan_dep, build_dep)  # ty: ignore[invalid-argument-type]


if __name__ == "__main__":
    main()
