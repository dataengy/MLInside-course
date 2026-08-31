#!/usr/bin/env python3
"""Реестр картинок деки: где какая стоит, откуда взялась и что с ней сделали руками.

ЗАЧЕМ. Картинки на слайды расставляются полуавтоматически, а правит деку человек — в
контент-YAML или прямо в PowerPoint. Без реестра эти две стороны воюют: автор убирает
картинку со слайда, следующий проход «замечает», что файл не использован, и ставит её
обратно. Реестр фиксирует НАМЕРЕНИЕ: снятая руками картинка получает статус
``manual-removed`` и больше не предлагается к постановке никогда — пока человек сам не
вернёт ей ``spare``.

СТАТУСЫ

    placed          картинка стоит на слайде, и реестр с контентом согласны
    manual-removed  была на слайде, из контента убрана руками → не предлагать снова
    manual-moved    переехала на другой слайд руками → реестр запомнил откуда и куда
    spare           файл лежит в media, на слайдах не используется, поставить можно
    wanted          картинки ещё нет, есть только ссылка на поиск (жёлтая 🔍 в подвале)

КОМАНДЫ

    python3 scripts/preza/images_manifest.py sync  CONTENT.yml   # обновить реестр
    python3 scripts/preza/images_manifest.py sync  CONTENT.yml --settings=.tmp/v4_build_settings.yml
    python3 scripts/preza/images_manifest.py check CONTENT.yml   # exit 1, если разошлись
    python3 scripts/preza/images_manifest.py spare CONTENT.yml   # что можно ставить

``sync`` — единственная команда, которая пишет реестр; она же переводит записи в
``manual-removed`` / ``manual-moved``. ``check`` ничего не меняет и годится для CI.

Реестр лежит рядом с контентом: content/<deck>-images.yml.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))

from preza_gen import settings as S  # noqa: E402
from preza_gen.utils import fit_image_box  # noqa: E402

# Настройки сборки задают image_box и media_dir, а значит и координаты в реестре: их
# надо брать ТЕ ЖЕ, что у реальной сборки деки, иначе layout.placed описывает не тот слайд.
DEFAULT_SETTINGS = _ROOT / "content" / "build_deck_v3-settings.yml"
EMU = 914400

HEADER = """\
# {name} — РЕЕСТР КАРТИНОК деки {deck}.
#
# Пишется командой `python3 scripts/preza/images_manifest.py sync {deck}`; правится и руками.
#
# Зачем файл существует: картинку со слайда может снять человек — в контент-YAML или в
# PowerPoint. Без реестра следующий проход расстановки увидел бы «неиспользованный файл»
# и вернул картинку обратно. Здесь фиксируется НАМЕРЕНИЕ, а не факт.
#
#   placed          стоит на слайде; реестр и контент согласны
#   manual-removed  снята со слайда руками → НЕ предлагать к постановке снова
#   manual-moved    перенесена на другой слайд руками → видно откуда и куда
#   spare           файл есть, на слайдах не используется, поставить можно
#   wanted          картинки ещё нет — есть жёлтая 🔍-ссылка на поиск в подвале слайда
#
# Чтобы вернуть снятую картинку в оборот, поменяйте её state на `spare` руками.
#
# layout.box    — рамка из настроек сборки (settings.image_box), дюймы
# layout.placed — фактический прямоугольник после вписывания, дюймы
# layout.fit    — contain: вписать целиком с сохранением пропорций (fit_image_box)
# layout.anchor — bottom: нижняя кромка прижата к fmt.visual_bottom
"""


def _rel(path: Path) -> str:
    """Путь относительно корня репозитория — реестр коммитится и должен быть переносим."""
    p = Path(path)
    with __import__("contextlib").suppress(ValueError):
        return str(p.resolve().relative_to(_ROOT))
    return str(p)


def _load(path: Path) -> dict:
    if not path.is_file():
        return {"deck": "", "images": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"deck": "", "images": []}


def _manifest_path(content_yml: Path) -> Path:
    return content_yml.with_name(content_yml.stem.replace("-content", "") + "-images.yml")


def _placement(cfg, media: Path, filename: str) -> dict[str, Any]:
    """Где и какого размера картинка окажется на слайде — тем же расчётом, что в рендерере."""
    box = cfg.image_box
    fmt = cfg.fmt
    out: dict[str, Any] = {
        "box": {k: round(getattr(box, k), 2) for k in ("left", "top", "width", "height")},
        "fit": "contain",
        "anchor": fmt.visual_anchor,
    }
    src = media / filename
    if not src.is_file():
        out["placed"] = None
        return out
    from PIL import Image

    with Image.open(src) as im:
        px_w, px_h = im.size
    out["natural_px"] = [px_w, px_h]
    w, h = fit_image_box(px_w, px_h, int(box.width * EMU), int(box.height * EMU))
    w_in, h_in = w / EMU, h / EMU
    top = (fmt.visual_bottom - h_in) if fmt.visual_anchor == "bottom" else box.top + (box.height - h_in) / 2
    out["scale"] = round(w_in * 96 / px_w, 4)  # экранных пикселей на пиксель оригинала
    out["placed"] = {
        "left": round(box.left + (box.width - w_in) / 2, 2),
        "top": round(top, 2),
        "width": round(w_in, 2),
        "height": round(h_in, 2),
    }
    return out


def _search_links(content) -> list[dict]:
    """Жёлтые 🔍-ссылки — слайды, где картинка нужна, но её ещё нет."""
    out = []
    for spec in content.slides:
        for m in spec.materials or []:
            if m.get("highlight"):
                out.append({"slide_id": spec.id, "label": m.get("label", ""), "url": m["url"]})
    return out


def sync(content_yml: Path, *, write: bool, settings: Path) -> int:
    cfg, content = S.load(settings, content_yml)
    media = Path(cfg.media_dir) if cfg.media_dir else _ROOT / "data" / "source" / "media"
    manifest_path = _manifest_path(content_yml)
    old = _load(manifest_path)
    known = {e["file"]: e for e in old.get("images", [])}

    # где какой файл стоит СЕЙЧАС, по контенту
    current = {spec.image: spec.id for spec in content.slides if spec.image}
    today = date.today().isoformat()
    changes: list[str] = []
    entries: list[dict] = []

    for filename, slide_id in sorted(current.items()):
        prev = known.pop(filename, None)
        entry = dict(prev) if prev else {
            "file": filename,
            "origin": {"kind": "unknown", "source": None, "url": None},
            "note": "",
        }
        if prev and prev.get("state") in ("placed", "manual-moved") and prev.get("slide_id") != slide_id:
            entry["state"] = "manual-moved"
            entry["moved_from"] = prev.get("slide_id")
            entry["changed"] = today
            changes.append(f"manual-moved: {filename} {prev.get('slide_id')} → {slide_id}")
        elif prev and prev.get("state") == "manual-removed":
            # человек вернул картинку в контент — реестр не спорит, а фиксирует факт
            entry["state"] = "placed"
            entry.pop("removed_from", None)
            entry["changed"] = today
            changes.append(f"placed снова: {filename} → {slide_id}")
        elif not prev:
            entry["state"] = "placed"
            entry["changed"] = today
            changes.append(f"new: {filename} → {slide_id}")
        else:
            entry["state"] = "placed"
        entry["slide_id"] = slide_id
        entry["layout"] = _placement(cfg, media, filename)
        entries.append(entry)

    # то, что осталось в реестре, но исчезло из контента
    for filename, prev in sorted(known.items()):
        entry = dict(prev)
        if prev.get("state") == "placed":
            entry["state"] = "manual-removed"
            entry["removed_from"] = prev.get("slide_id")
            entry["slide_id"] = None
            entry["changed"] = today
            changes.append(f"manual-removed: {filename} (был на {prev.get('slide_id')})")
        entry.pop("layout", None)
        entries.append(entry)

    # файлы в media, которых реестр вообще не знает → spare
    seen = {e["file"] for e in entries}
    for src in sorted(media.glob("pic-*")):
        if src.name in seen:
            continue
        entries.append({
            "file": src.name,
            "slide_id": None,
            "state": "spare",
            "origin": {"kind": "unknown", "source": None, "url": None},
            "changed": today,
            "note": "",
        })
        changes.append(f"spare: {src.name}")

    doc = {
        "deck": str(content_yml),
        "settings": _rel(settings),
        "media_dir": _rel(media),
        "generated": today,
        "images": sorted(entries, key=lambda e: (e.get("slide_id") or "~", e["file"])),
        "wanted": _search_links(content),
    }
    text = HEADER.format(name=manifest_path.name, deck=content_yml) + yaml.safe_dump(
        doc, allow_unicode=True, sort_keys=False, width=100
    )
    if write:
        manifest_path.write_text(text, encoding="utf-8")
    for line in changes:
        print(f"  {line}")
    verb = "обновлён" if write else "разошёлся" if changes else "совпадает"
    print(f"{manifest_path}: {verb}, записей {len(entries)}, изменений {len(changes)}")
    return 1 if (changes and not write) else 0


def spare(content_yml: Path) -> int:
    """Что можно ставить на слайды: файл есть, на слайдах не используется, руками не снят."""
    doc = _load(_manifest_path(content_yml))
    free = [e for e in doc.get("images", []) if e.get("state") == "spare"]
    blocked = [e for e in doc.get("images", []) if e.get("state") == "manual-removed"]
    for e in free:
        print(f"  свободна        {e['file']}")
    for e in blocked:
        print(f"  снята вручную   {e['file']}  (была на {e.get('removed_from')}) — НЕ ставить")
    for w in doc.get("wanted", []):
        print(f"  нужна картинка  {w['slide_id']}  {w['label']}")
    print(f"# свободных {len(free)}, заблокированных вручную {len(blocked)}")
    return 0


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    opts = [a for a in argv[1:] if a.startswith("--settings=")]
    if len(args) < 2 or args[0] not in ("sync", "check", "spare"):
        print(__doc__)
        return 2
    cmd, content_yml = args[0], Path(args[1])
    if cmd == "spare":
        return spare(content_yml)
    settings = Path(opts[0].split("=", 1)[1]) if opts else DEFAULT_SETTINGS
    return sync(content_yml, write=(cmd == "sync"), settings=settings)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
