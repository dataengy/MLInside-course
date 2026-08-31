#!/usr/bin/env python3
"""Одноразовый посев поля `origin` в реестре картинок — откуда каждый файл взялся.

`images_manifest.py sync` заполняет всё, кроме происхождения: он видит только имя файла
в контенте и не знает, из какого экспорта или по какой ссылке файл приехал. Дальше sync
эти поля СОХРАНЯЕТ (запись копируется целиком), поэтому посеять их достаточно один раз.

Источник данных — .tmp/stage_pictures.py (оригинал → имя ассета) плюс одна картинка,
скачанная по ссылке из задачи.

    python3 .tmp/seed_image_origins.py content/preza-dbt-v4-images.yml
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

PHOTOS = "/Users/user/Pictures/MLInside (202608..)"

# имя ассета → (kind, source, url, note)
ORIGINS: dict[str, tuple[str, str | None, str | None, str]] = {
    "image62.png": ("source-deck", "data/source/NEW_ВШЭ_Семинар9-Практикум-по-dbt.pptx", None,
                    "media исходной деки, переиспользуется с v3"),
    "pic-ae-dataduel.png": (
        "url", None,
        "https://i0.wp.com/www.dataduel.co/wp-content/uploads/2024/07/image-3.png?w=1320&ssl=1",
        "скачана по ссылке из задачи (Data Engineering / Analytics Engineering / Analytics)"),
    "pic-ideal-data-architecture.png": (
        "local", f"{PHOTOS}/ideal-data-stack-architecture-whats-your-view-v0-q5mn1rnwnhna1.webp", None,
        "webp перекодирован в png: python-pptx кладёт байты как есть, PowerPoint webp не рисует"),
    "pic-dbt-layers-flow.png": ("local", f"{PHOTOS}/1_IYYe23xvVfLCd7jCC83Utw.png", None,
                                "выбрана заказчиком под слайд про слои"),
    "pic-model-layers-principles.jpg": ("local", f"{PHOTOS}/1764912126391.jpeg", None, ""),
    "pic-elt-roles-split.jpg": ("local", f"{PHOTOS}/Picture2.jpg", None, ""),
    "pic-roles-de-ae-da.png": ("local", f"{PHOTOS}/Picture3.png", None,
                               "подобрана вместо пустого «to:» в задаче"),
    "pic-dbt-overview.png": ("local", f"{PHOTOS}/Picture4.png", None, ""),
    "pic-data-platform-arch.jpg": ("local", f"{PHOTOS}/Picture1.jpg", None, ""),
    "pic-olist-er.png": ("local", f"{PHOTOS}/HRhd2Y0.png", None, ""),
    "pic-olist-db-schema.png": (
        "local", f"{PHOTOS}/inbox_2473556_23a7d4d8cd99e36e32e57303eb804fff_db-schema.png", None, ""),
    "pic-dbt-run-terminal.png": ("local", f"{PHOTOS}/Picture11.png", None, ""),
    "pic-dbt-lineage-graph.png": ("local", f"{PHOTOS}/Picture12.png", None, ""),
    "pic-lineage-model-monitor.png": ("local", f"{PHOTOS}/Picture16.png", None, ""),
    "pic-dbt-docs-model.png": ("local", f"{PHOTOS}/Picture21-docs.png", None, ""),
    "pic-dbt-hub-packages.jpg": ("local", f"{PHOTOS}/Picture31-пакеты.jpg", None, ""),
    "pic-jinja-target-name.png": ("local", f"{PHOTOS}/Picture13.png", None, ""),
    "pic-jinja-source.png": ("local", f"{PHOTOS}/Picture15.png", None, "пара к pic-jinja-compiled"),
    "pic-jinja-compiled.png": ("local", f"{PHOTOS}/Picture15.2.png", None, "пара к pic-jinja-source"),
    "pic-dbt-dag-large.png": ("local", f"{PHOTOS}/Picture0.png", None, ""),
    "pic-olist-csv-files.png": (
        "local", f"{PHOTOS}/179500856-363711c0-2b7f-465e-bd68-be96a4c59e93.png", None, ""),
    "pic-dbt-package-page.png": ("local", f"{PHOTOS}/Picture32-.png", None, ""),
}


def main(path_str: str) -> int:
    path = Path(path_str)
    text = path.read_text(encoding="utf-8")
    header = "".join(ln for ln in text.splitlines(keepends=True) if ln.startswith("#"))
    doc = yaml.safe_load(text)
    missing = []
    for entry in doc["images"]:
        found = ORIGINS.get(entry["file"])
        if not found:
            missing.append(entry["file"])
            continue
        kind, source, url, note = found
        entry["origin"] = {"kind": kind, "source": source, "url": url}
        if note and not entry.get("note"):
            entry["note"] = note
    path.write_text(
        header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"{path}: происхождение проставлено для {len(doc['images']) - len(missing)} записей")
    for m in missing:
        print(f"  без происхождения: {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
