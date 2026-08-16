"""publisher — post-build deck publish pipeline (Telegram + GDrive + GSheet write-back).

On an explicitly requested run (``just publish-new``; the builder mints a new minor on EVERY
build, so nothing here fires automatically) it detects built versions in ``data/generated/``
newer than the publish cursor and, per deck: sends a Telegram notification + the pptx file,
uploads the pptx to Google Drive updating one stable per-subject file in place (persistent
URL), and writes URL/version/slide-count into the course schedule sheet.

Entry point: ``python -m publisher`` (see ``cli.py``). Spec: docs/deck-publish-pipeline.md.
"""
