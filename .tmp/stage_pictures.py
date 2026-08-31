#!/usr/bin/env python3
"""Stage the lecturer's picture library into the deck's media dir under speaking names.

`preza_gen` resolves `SlideSpec.image` against `settings.media_dir`, so every picture a
deck references has to live there under a stable filename. The originals sit in a Photos
export whose names (`Picture15.2.png`, `HRhd2Y0.png`) say nothing about the content — this
script is the record of which original became which slide asset.

    python3 .tmp/stage_pictures.py

Written for the v4.1 deck pass; deliberately not wired into the Justfile.
"""

from __future__ import annotations

import pathlib
import shutil

from PIL import Image

SRC = pathlib.Path("/Users/user/Pictures/MLInside (202608..)")
DST = pathlib.Path("data/source/media")

# original filename → name the deck references
COPIES = {
    "1_IYYe23xvVfLCd7jCC83Utw.png": "pic-dbt-layers-flow.png",
    "1764912126391.jpeg": "pic-model-layers-principles.jpg",
    "Picture2.jpg": "pic-elt-roles-split.jpg",
    "Picture3.png": "pic-roles-de-ae-da.png",
    "Picture4.png": "pic-dbt-overview.png",
    "Picture1.jpg": "pic-data-platform-arch.jpg",
    "HRhd2Y0.png": "pic-olist-er.png",
    "inbox_2473556_23a7d4d8cd99e36e32e57303eb804fff_db-schema.png": "pic-olist-db-schema.png",
    "Picture11.png": "pic-dbt-run-terminal.png",
    "Picture12.png": "pic-dbt-lineage-graph.png",
    "Picture16.png": "pic-lineage-model-monitor.png",
    "Picture21-docs.png": "pic-dbt-docs-model.png",
    "Picture31-пакеты.jpg": "pic-dbt-hub-packages.jpg",
    "Picture13.png": "pic-jinja-target-name.png",
    "Picture15.png": "pic-jinja-source.png",
    "Picture15.2.png": "pic-jinja-compiled.png",
    "Picture0.png": "pic-dbt-dag-large.png",
    "179500856-363711c0-2b7f-465e-bd68-be96a4c59e93.png": "pic-olist-csv-files.png",
    "Picture32-.png": "pic-dbt-package-page.png",
}

# webp has no place in a .pptx — python-pptx embeds the bytes as-is and PowerPoint
# will not render them, so it is transcoded here rather than at build time.
WEBP = "ideal-data-stack-architecture-whats-your-view-v0-q5mn1rnwnhna1.webp"


def main() -> None:
    for original, staged in COPIES.items():
        shutil.copy2(SRC / original, DST / staged)
        print("copied", staged)
    Image.open(SRC / WEBP).convert("RGB").save(DST / "pic-ideal-data-architecture.png")
    print("transcoded pic-ideal-data-architecture.png")
    downloaded = pathlib.Path(".tmp/dataduel.png")
    if downloaded.is_file():
        shutil.copy2(downloaded, DST / "pic-ae-dataduel.png")
        print("copied pic-ae-dataduel.png")


if __name__ == "__main__":
    main()
