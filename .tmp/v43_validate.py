#!/usr/bin/env python3
"""Проверки §10 брифа v4.4: хронометраж, наличие и качество подстрочников.

Основная часть — от первого слайда до `Спасибо за внимание!` включительно; всё после
неё (PART 2, PART 3, «Картинки») в хронометраж не входит и обязано быть без часов.

    python3 .tmp/v43_validate.py content/preza-dbt-v4-content.yml
"""
from __future__ import annotations
import re, sys, yaml

# Шапка `[MM:SS–MM:SS · ~N мин]`. Прежний голый формат (`MM:SS-MM:SS`) тоже принимается:
# проверка должна работать и на деке, ещё не прогнанной через новый `preza-notes apply`.
STAMP = re.compile(r"^\[?(\d{2,3}):(\d{2})[–-](\d{2,3}):(\d{2})")
PARTS = STAMP
CLOSING_KIND = "closing"


def main(path: str) -> int:
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    slides = doc["content"]
    end = next(i for i, s in enumerate(slides) if s["kind"] == CLOSING_KIND)
    main_part, tail = slides[: end + 1], slides[end + 1 :]
    bad: list[str] = []

    prev = None
    for s in main_part:
        n = (s.get("notes") or "").lstrip()
        if not n:
            bad.append(f"{s['id']}: нет заметок"); continue
        if not STAMP.match(n):
            bad.append(f"{s['id']}: заметки не начинаются с MM:SS-MM:SS"); continue
        a, b, c, d = PARTS.match(n).groups()
        st, en = int(a) * 60 + int(b), int(c) * 60 + int(d)
        if prev is None and st != 0:
            bad.append(f"{s['id']}: первый слайд стартует не с 00:00")
        if prev is not None and st != prev:
            bad.append(f"{s['id']}: разрыв — предыдущий кончился на {prev // 60:02d}:{prev % 60:02d}")
        if en <= st:
            bad.append(f"{s['id']}: интервал не растёт")
        prev = en
        # заметка не должна дословно повторять текст слайда
        for b_ in s.get("bullets") or []:
            if b_.strip() and b_.strip() in n:
                bad.append(f"{s['id']}: заметка дословно повторяет буллет «{b_[:40]}…»")

    for s in tail:
        n = (s.get("notes") or "").lstrip()
        if STAMP.match(n):
            bad.append(f"{s['id']}: часы после «Спасибо за внимание!»")

    print(f"основная часть: {len(main_part)} слайдов, финиш "
          f"{prev // 60:02d}:{prev % 60:02d} ({prev / 60:.1f} мин); вне хронометража {len(tail)}")
    for b in bad:
        print("  ✗", b)
    print(f"нарушений: {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
