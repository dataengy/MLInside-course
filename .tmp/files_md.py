#!/usr/bin/env python3
"""Собрать человекочитаемый `settings/files.md` из раздела `presentation` в `settings/files.yml`.

ЗАЧЕМ ГЕНЕРАТОР, А НЕ ВТОРОЙ ТЕКСТ. Оба файла отвечают на один вопрос — «какую деку править
и что уже слито». Два текста об одном разъезжаются: правят один, забывают другой, и дальше
непонятно, какому верить. Здесь YAML — единственный источник правды, .md всегда производный.

Правки вносят в `settings/files.yml`, затем перегенерируют:
    just -f .tmp/Justfile files-md          # переписать settings/files.md
    just -f .tmp/Justfile files-md --check  # проверить, что .md не отстал (exit 1, если отстал)

`--check` нужен, чтобы забытая перегенерация ловилась, а не жила месяц: расхождение видно
сразу, а не когда кто-то поверит устаревшему .md и откроет не ту деку.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "settings" / "files.yml"
OUT = ROOT / "settings" / "files.md"

STATUS = {
    "current-manual": "🟢 текущая ручная",
    "current-generated": "🟢 текущая сборка",
    "merged-and-retired": "⚪️ слита и убрана",
    "archived-in-git": "⚪️ в git, не в работе",
}
OP = {
    "insert": "вставлен",
    "replace": "заменил",
    "drop-shape": "снята фигура",
    "renumber-notes": "пересчёт часов",
}
REASON = {"duplicate": "дубль", "superseded": "устарело", "junk": "мусор"}
VERIFIED = {
    "slides": "слайдов",
    "notes_with_clock_monotonic": "часы в заметках идут по возрастанию",
    "emphasis_runs": "выделения в заметках",
    "pdf_overflow_findings": "замечаний по вылетам в PDF",
    "pdf_overflow_note": "про замечания",
}


def _p(out, *lines):
    out.extend(lines)


def _wrap(text):
    """Свернуть многострочный YAML-скаляр в одну строку — в markdown переносы лишние."""
    return " ".join(str(text).split()) if text else ""


def _slides(n: int) -> str:
    """«1 слайд · 2 слайда · 5 слайдов» — иначе таблица читается как машинный вывод."""
    tail = n % 100
    if 11 <= tail <= 14:
        word = "слайдов"
    elif n % 10 == 1:
        word = "слайд"
    elif n % 10 in (2, 3, 4):
        word = "слайда"
    else:
        word = "слайдов"
    return f"{n} {word}"


def render(doc) -> str:
    pr = doc["presentation"]
    L: list[str] = []
    _p(L, "# Деки: какая в работе, что с чем слито",
       "",
       "<!-- ГЕНЕРИРУЕТСЯ из settings/files.yml — `just -f .tmp/Justfile files-md`.",
       "     Правки вносите в YAML, не сюда: этот файл перезаписывается целиком. -->",
       "")

    _p(L, "## Что открывать и править", "")
    for deck, cur in pr["current"].items():
        _p(L, f"**{deck}**", "")
        for lane, path in cur.items():
            label = {"manual": "правят руками", "generated": "собирает генератор"}.get(lane, lane)
            _p(L, f"- `{path}` — {label}")
        _p(L, "")
    _p(L, "Ручная и генераторская головы РАЗНЫЕ, и это нормально: пока правки из ручной деки",
       "не уехали в контент, у линий нет общей вершины. Путать их нельзя.", "")

    _p(L, "## Линии", "")
    for key, line in pr["lines"].items():
        chain = " → ".join(line.get("chain", []))
        _p(L, f"- **{key}** ({line['kind']}) — {_wrap(line['descr'])}", f"  - {chain}")
    _p(L, "", f"Общий предок всех линий: **{pr['common_ancestor']}**.", "")

    open_todos, open_issues = [], []
    for f in pr["forks"]:
        for t in f.get("todo") or []:
            open_todos.append((f["id"], t))
        for i in f.get("issues") or []:
            if i.get("status") == "open":
                open_issues.append((f["id"], i))

    if open_todos or open_issues:
        _p(L, "## Что осталось сделать", "")
        for fid, t in open_todos:
            blocked = t.get("blocked_by")
            tail = f" — ждёт `{blocked}`" if blocked else ""
            _p(L, f"- **{t['id']}** ({fid}){tail}", f"  - {_wrap(t['what'])}",
               f"  - зачем: {_wrap(t['why'])}")
            if t.get("note"):
                _p(L, f"  - {_wrap(t['note'])}")
        for fid, i in open_issues:
            _p(L, f"- **{i['id']}** ({fid}) — {_wrap(i['symptom'])}")
            if i.get("cause"):
                _p(L, f"  - причина: {_wrap(i['cause'])}")
        _p(L, "")

    _p(L, "## Версии", "")
    for f in pr["forks"]:
        status = STATUS.get(f["status"], f["status"])
        line = f" · линия {f['line']}" if f.get("line") else ""
        _p(L, f"### {f['id']} — {status}", "",
           f"`{f['path']}`", "",
           f"{_slides(f['slides'])} · {f['timestamp']}{line}", "",
           _wrap(f.get("summary", "")), "")

        if f.get("parents"):
            _p(L, f"- родители: {', '.join(f['parents'])}")
        if f.get("merged_into"):
            _p(L, f"- слита в: **{f['merged_into']}** ({f.get('strategy', '?')})")
        if f.get("superseded_by"):
            _p(L, f"- перекрыта: **{f['superseded_by']}**")
        if f.get("built_from"):
            _p(L, f"- собирается из: `{f['built_from']}`")
        if f.get("restore_from"):
            _p(L, f"- восстановить из коммитов: {', '.join(f'`{c}`' for c in f['restore_from'])}")
        if f.get("tool"):
            _p(L, f"- команда: `{f['tool']}`")
        if f.get("own_content"):
            _p(L, "- своё содержимое:")
            for c in f["own_content"]:
                _p(L, f"  - {_wrap(c)}")
        if f.get("note"):
            _p(L, f"- {_wrap(f['note'])}")
        if f.get("rescue"):
            _p(L, f"- как спасена: {_wrap(f['rescue'])}")
        if f.get("diff_result"):
            _p(L, f"- сверка ({', '.join(f.get('diffed_by', []))}): {_wrap(f['diff_result'])}")
        if f.get("not_diffed"):
            _p(L, f"- не сверялось: {_wrap(f['not_diffed'])}")
        if f.get("ported_to_content"):
            _p(L, "- перенесено в контент:")
            for c in f["ported_to_content"]:
                head = f"`{c['slide']}`" if c.get("slide") else ""
                _p(L, f"  - {head} {_wrap(c.get('note', ''))}".strip())
        _p(L, "")

        if f.get("changes"):
            _p(L, "**Что сделано при слиянии**", "",
               "| операция | слайд | откуда | что |", "|---|---|---|---|")
            for c in f["changes"]:
                op = OP.get(c["op"], c["op"])
                at = c.get("at") or "вся дека"
                src = f"{c['from']} #{c['src_slide']}" if c.get("from") else "—"
                what = c.get("title") or c.get("shape") or ""
                note = _wrap(c.get("note", ""))
                cell = f"{what} — {note}" if what and note else (what or note)
                _p(L, f"| {op} | {at} | {src} | {cell} |")
            _p(L, "")

        if f.get("not_taken"):
            _p(L, "**Что НЕ перенесено** — «не перенесено» здесь значит решено, а не забыто.",
               "", "| слайд донора | что | почему |", "|---|---|---|")
            for c in f["not_taken"]:
                why = REASON.get(c["reason"], c["reason"])
                if c.get("of"):
                    why += f" слайда {c['of']}"
                if c.get("note"):
                    why += f" ({_wrap(c['note'])})"
                _p(L, f"| {c['src_slide']} | {c['title']} | {why} |")
            _p(L, "")

        if f.get("media"):
            m = f["media"]
            dropped = ", ".join(m.get("dropped", [])) or "—"
            _p(L, f"**Медиа:** было {m['before']}, стало {m['after']}, "
                  f"новых частей {m['added']}, ушло: {dropped}. {_wrap(m.get('note', ''))}", "")

        if f.get("verified"):
            _p(L, "**Проверено**", "")
            for k, val in f["verified"].items():
                if isinstance(val, bool):
                    val = "да" if val else "НЕТ"
                elif isinstance(val, dict):
                    val = " · ".join(f"{kk} {vv}" for kk, vv in val.items())
                _p(L, f"- {VERIFIED.get(k, k)}: {val}")
            _p(L, "")

        closed = [i for i in (f.get("issues") or []) if i.get("status") == "closed"]
        opened = [i for i in (f.get("issues") or []) if i.get("status") != "closed"]
        if opened or closed:
            _p(L, "**Замечания**", "")
            for i in opened + closed:
                mark = "✅" if i.get("status") == "closed" else "⚠️"
                where = f" (слайд {i['slide']})" if i.get("slide") else ""
                _p(L, f"- {mark} **{i['id']}**{where} — {_wrap(i['symptom'])}")
                for key, label in (("cause", "причина"), ("inherited_from", "пришло из"),
                                   ("fix", "лечение"), ("note", "детали"), ("owner", "чья зона")):
                    if i.get(key):
                        _p(L, f"  - {label}: {_wrap(i[key])}")
            _p(L, "")

    _p(L, "## Где искали форки и не нашли", "",
       "Чтобы следующий проход не искал заново.", "")
    for s in pr["searched_and_empty"]:
        _p(L, f"- {s['where']} — {_wrap(s['result'])}")
    _p(L, "")

    return "\n".join(L).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="не писать, а проверить, что settings/files.md совпадает с YAML")
    args = ap.parse_args(argv)

    text = render(yaml.safe_load(SRC.read_text()))
    if args.check:
        current = OUT.read_text() if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)} отстал от {SRC.relative_to(ROOT)} — "
                  f"перегенерируйте: just -f .tmp/Justfile files-md", file=sys.stderr)
            return 1
        print(f"{OUT.relative_to(ROOT)}: совпадает с YAML")
        return 0
    OUT.write_text(text)
    print(f"{OUT.relative_to(ROOT)}: {len(text.splitlines())} строк")
    return 0


if __name__ == "__main__":
    sys.exit(main())
