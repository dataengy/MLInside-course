#!/usr/bin/env python3
"""Свернуть абзацы-продолжения в их раздел — чтобы булитировались и они тоже.

ЗАЧЕМ. `notes_fix.py` нормализует только блоки С МЕТКОЙ (`**Рассказ:** …`). Абзац, который
автор написал следующим за меткой, — отдельный блок без метки, он «проходит насквозь» и
остаётся прозой даже со снятым порогом булитирования. Именно в таких абзацах и живут
оставшиеся полотна текста. Скрипт приклеивает их к предыдущему разделу, после чего
обычный `notes_fix.py apply` режет всё на предложения единым правилом.

НЕ ТРОГАЕТ: блок без предшествующей метки (штамп «ВНЕ ХРОНОМЕТРАЖА», преамбулы) и строку
происхождения «— Сгенерировано: …» — она служебная и в подстрочник докладчика не входит.

Разовый скрипт: после него правку держит сам контент, повторный прогон ничего не находит.

    PYTHONPATH=src python3 .tmp/fold_continuations.py content/preza-dbt-v4-content.yml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preza_gen import notes as N  # noqa: E402

KEEP_APART = ("— Сгенерировано:",)
MARKER = "- kind:"


def _flat(text: str) -> list[str]:
    """Слова заметки без разметки списка — инвариант, который правка менять не имеет права."""
    return re.sub(r"^\s*-\s+", " ", text, flags=re.M).split()


def fold(notes: str) -> str:
    secs = N.split_sections(notes)
    out: list[N.Section] = []
    for sec in secs:
        if (
            sec.label is None
            and out
            and any(s.label for s in out)
            and not sec.body.startswith(KEEP_APART)
        ):
            # Продолжение может само быть списком (рукописные буллеты автора) — сворачиваем
            # его в прозу тем же _unbullet, что применяется к разделам с меткой, иначе
            # дефис уедет в середину предложения.
            body = N._unbullet(sec.body)
            out[-1] = N.Section(out[-1].label, f"{out[-1].body} {body}".strip(), out[-1].prefix)
        else:
            out.append(sec)
    return N.render_sections(out, max_sentences=999, max_chars=99999)


def main(path_str: str) -> int:
    path = Path(path_str)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(MARKER)]
    header = "".join(lines[: starts[0]])
    bounds = starts + [len(lines)]
    blocks = ["".join(lines[a:b]) for a, b in zip(bounds, bounds[1:])]

    changed = 0
    for i, block in enumerate(blocks):
        # Блочный скаляр в контенте встречается в трёх видах: `|`, `|-` и `|2`. Зашитый
        # `|2` молча пропускал заметки приложения — они как раз написаны первыми двумя.
        m = re.search(r"^  notes: (\|[-0-9]*)\n", block, re.M)
        if not m:
            continue
        head, sep, body = block.partition(m.group(0))
        indent = "    "
        notes = "".join(ln[len(indent):] if ln.startswith(indent) else ln for ln in body.splitlines(keepends=True))
        folded = fold(notes)
        if _flat(folded) != _flat(notes):
            raise SystemExit(f"{block[:40]!r}: свёртка изменила текст, а не только разметку")
        new_body = "".join(indent + ln + "\n" if ln else "\n" for ln in folded.splitlines())
        if new_body != body:
            blocks[i] = head + sep + new_body
            changed += 1

    out = header + "".join(blocks)
    import yaml
    yaml.safe_load(out)  # fail-loud до записи
    path.write_text(out, encoding="utf-8")
    print(f"{path}: свёрнуто продолжений на {changed} слайдах")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
