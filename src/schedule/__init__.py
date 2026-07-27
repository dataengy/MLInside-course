"""Course schedule reader — Google Sheet → settings/schedule.yml → content/presentations.yml.

The lecture plan lives in a Google Sheet (``settings/config.yml`` → ``planning.schedule_gsheet``).
This package pulls it into the repo in two layers:

* ``settings/schedule.yml``    — generated, verbatim dump; never hand-edited.
* ``content/presentations.yml`` — curated lecture → deck mapping; hand-edited fields survive
  re-runs (see :func:`schedule.mapper.upsert`).

CLI: ``PYTHONPATH=src python3 -m schedule {tabs,dump,plan,show}`` (or the root ``just gsheet-*``
and ``just presentations-plan`` targets).
"""

__all__ = ["gsheet", "mapper", "reader", "settings"]
