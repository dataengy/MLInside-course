"""preza_merge.apply — turn accepted decisions into a profile, a deck switch and a build.

Two writes, обе намеренно узкие:
  * settings/formats.yml обновляется ЧЕРЕЗ ROUND-TRIP: профиль правится на месте, а
    комментарии и порядок ключей остаются. Раньше файл переписывался целиком, а шапка
    объявляла это правилом («keep prose out of it») — то есть инструмент запрещал файлу
    иметь объяснения, потому что сам не умел иначе. Умеет;
  * the deck's content yaml gets a SURGICAL one-line edit, because it is hand-authored and
    a yaml round-trip would strip its comments and reflow every block scalar.
"""

from __future__ import annotations

import re
from pathlib import Path

from schedule.settings import dump_roundtrip, load_roundtrip

from .report import accepted_keys, undecided
from .rules import MergeConfig

_HEADER = """# formats.yml — named FORMATTING profiles for preza_gen. Referenced from a deck settings
# yaml via `settings.formats_file`; a deck picks one with `deck.format`.
#
# `just preza-merge-apply` обновляет ОДИН профиль и не трогает остальной файл, включая
# ваши комментарии. Объяснения профилей держите прямо здесь, рядом с числами;
# развёрнутый разбор лейна — docs/preza-merge-lane.md.
"""


def write_profile(formats_path: Path, name: str, base_profile: str, keys: dict) -> None:
    """Upsert profile ``name`` = ``base_profile`` + ``keys``. Остальной файл не трогается.

    Round-trip (ruamel), а не ``safe_load`` + ``safe_dump``: последняя пара молча сносит
    комментарии, оставляя валидный YAML и дифф, похожий на безобидное переформатирование.
    Профиль вёрстки без объяснения, почему у него именно такие числа, через месяц читается
    как случайный набор.

    Профиль обновляется ПО КЛЮЧАМ внутри существующей мапы, а не подменяется новым
    объектом: комментарии в ruamel живут на самих CommentedMap, и присваивание выбросило бы
    их вместе со старым объектом. Тот же приём и по той же причине применён в
    ``publisher.plan_writer``.
    """
    path = Path(formats_path)
    doc = load_roundtrip(path)
    profiles = doc["formats"]
    if base_profile not in profiles:
        raise KeyError(f"base profile {base_profile!r} not in {path}")
    merged = dict(profiles[base_profile])
    unknown = set(keys) - set(merged)
    if unknown:
        raise KeyError(f"unknown profile keys {sorted(unknown)} — not in {base_profile!r}")
    merged.update(keys)

    current = profiles.get(name)
    if hasattr(current, "keys"):
        for key in [k for k in current if k not in merged]:
            del current[key]
        for key, value in merged.items():
            current[key] = value
    else:
        profiles[name] = merged
    dump_roundtrip(path, doc, _HEADER)


def set_deck_format(content_path: Path, profile: str) -> bool:
    """Point a deck's content yaml at ``profile``. Returns True when the file changed.

    Surgical on purpose: the content yaml is hand-authored (comments, folded notes), so it
    is edited as TEXT rather than round-tripped through a yaml dump.

    Bounded to the ``deck:`` block on purpose: every deck content yaml opens with `deck:`
    then a top-level `content:` key (verified across content/*.yml), so the text BEFORE
    `content:` is exactly the deck header. Without this bound, the existing-`format:` regex
    or the `out_name:` anchor could match text deep inside a slide's code-panel body — e.g. a
    Data Engineering lecture is entirely likely to carry a line like `format: parquet` inside
    a fenced code block, which an unscoped regex would silently rewrite.
    """
    path = Path(content_path)
    text = path.read_text(encoding="utf-8")
    content_key = re.search(r"^content:", text, flags=re.M)
    if not content_key:
        raise ValueError(f"cannot locate top-level `content:` key in {path}")
    head, tail = text[: content_key.start()], text[content_key.start() :]

    existing = re.search(r"^(\s+)format:\s*\S.*$", head, flags=re.M)
    if existing:
        new_head = re.sub(
            r"^(\s+)format:\s*\S.*$", rf"\1format: {profile}", head, count=1, flags=re.M
        )
    else:
        anchor = re.search(r"^(\s+)out_name:.*$", head, flags=re.M)
        if not anchor:
            raise ValueError(f"cannot locate deck.out_name in {path}")
        indent = anchor.group(1)
        new_head = head[: anchor.end()] + f"\n{indent}format: {profile}" + head[anchor.end() :]
    new = new_head + tail
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def run(
    proposal: dict,
    cfg: MergeConfig,
    *,
    settings_yml: Path,
    formats_path: Path,
    patch_of: str,
    descr: str,
    backend: str = "settings",
) -> Path:
    """Apply a decided proposal and build the patch version. Returns the built .pptx path."""
    if backend == "graft":
        raise NotImplementedError(
            "backend 'graft' (copying slides between .pptx files) is iteration 2 — "
            "see docs/preza-merge-lane.md § Границы"
        )
    if backend != "settings":
        raise ValueError(f"unknown backend: {backend!r}")

    pending = undecided(proposal)
    if pending:
        raise SystemExit(
            f"нерешённые правила: {', '.join(pending)} — проставьте decision: accept|reject"
        )

    p = proposal["proposal"]
    profile = p["profile"]
    keys = accepted_keys(proposal)
    write_profile(Path(formats_path), profile, cfg.base_profile, keys)
    set_deck_format(Path(p["deck"]), profile)

    from preza_gen import pipeline  # deferred: keeps the merge lane importable without a build

    res = pipeline.build_deck(
        settings_yml, p["deck"], pptx=True, html=True, patch_of=patch_of, descr=descr
    )
    if res.out_path is None:
        raise SystemExit("сборка не дала .pptx — смотрите вывод build_deck")
    return res.out_path
