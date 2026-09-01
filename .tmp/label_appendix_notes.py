#!/usr/bin/env python3
"""Расставить метки разделов в заметках PART 2, PART 3 и «Картинок».

ЗАЧЕМ. `notes_fix.py` нормализует только блоки С МЕТКОЙ (`**Рассказ:** …`). Заметки
основной части эту конвенцию используют, приложения — нет: там просто абзацы, поэтому
они остались прозой, когда основная часть уехала в списки.

Карта ниже — ручная, по одному ярлыку на абзац: содержание каждого слайда прочитано.
`None` означает «абзац продолжает предыдущий раздел» — его подхватит
`.tmp/fold_continuations.py`. Абзац, у которого метка уже есть, пропускается.

Ярлыки приложения отличаются от лекционных: «Переход» здесь бессмысленен (живого
рассказа нет), зато нужны «Что дальше» и «Как пользоваться» на разделителях частей.

    PYTHONPATH=src python3 .tmp/label_appendix_notes.py content/preza-dbt-v4-content.yml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preza_gen import notes as N  # noqa: E402

MARKER = "- kind:"

LABELS: dict[str, list[str | None]] = {
    # ── PART 2 · DS/MLE нюансы ────────────────────────────────────────────────
    "950-part-2-ds-mle-nyuansy":      ["Главное", "Что дальше", "Как пользоваться"],
    "951-training-serving-skew":      ["Главное", "Разбор", None, None, "Практический смысл"],
    "952-utechki-v-priznakah":        ["Главное", "Разбор", None, None, None, None, "Осторожно"],
    "953-kogda-nuzhen-feature-store": ["Главное", "Разбор", None, "Для MLE", "Пример", "Осторожно"],
    # ── PART 3 · Advanced / Appendix ──────────────────────────────────────────
    "900-part-2-advanced-appendix":   ["Главное", "Что дальше", "Что переехало", "Как пользоваться"],
    "901-dbt-core-vs-dbt-cloud":      ["Главное", "Практический смысл"],
    "902-gde-pisat-dbt":              ["Главное", "Разбор", None, None],
    "903-fusion-i-dbt-core-v2":       ["Главное", "Разбор", "Практический смысл"],
    "905-adaptery":                   ["Главное", "Разбор"],
    "906-makrosy-v-proekte":          ["Главное", "Разбор", "Осторожно"],
    "909-data-vault-i-automatedv":    ["Главное", "Разбор", "Осторожно"],
    "910-prava-dostupa-v-dbt":        ["Главное", "Осторожно", "Практический смысл"],
    "911-pakety-versii-i-riski":      ["Главное", "Осторожно", "Практический смысл"],
    "912-esche-pakety-pod-zadachu":   ["Главное", "Осторожно", None],
    "913-pakety-v-ci-i-prode":        ["Главное", "Осторожно", "Практический смысл"],
    "914-snapshots-i-docs-istoriya":  ["Главное", "Осторожно", "Разбор"],
    "915-materialized-views-clickhouse": ["Главное", "Разбор", "Практический смысл"],
    "916-mikrobatching":              ["Главное", "Разбор", "Практический смысл"],
    "917-dbt-i-potokovye-dannye":     ["Главное", "Разбор", "Практический смысл"],
    "918-semantic-layer-metricflow":  ["Главное", "Разбор", "Практический смысл"],
    "920-dbt-state-i-dbt-wizard":     ["Главное", "Разбор", "Практический смысл"],
    "921-jinja-swot":                 ["Главное", "Разбор", "Осторожно"],
    "922-pochemu-drugie-uhodyat-ot-shablonov": ["Главное", "Разбор", None, "Практический смысл"],
    "923-sqlmesh-i-dbt-swot":         ["Главное", "Осторожно", "Практический смысл"],
    "924-sqlmesh-poverh-dbt-proekta": ["Главное", "Разбор", "Осторожно"],
    "925-deklarativnye-transformacii": ["Главное", "Разбор", None],
    # ── Картинки ──────────────────────────────────────────────────────────────
    "990-kartinki":                   ["Главное", "Зачем это здесь", None, "Учёт картинок"],
    "991-kartinka-olist-db-schema":   ["Главное", None],
    "992-kartinka-olist-csv":         ["Главное", None],
    "993-kartinka-dag-bolshogo-proekta": ["Главное", None],
    "994-kartinka-jinja-ishodnik":    ["Главное", None],
    "995-kartinka-jinja-skompilirovano": ["Главное", None, None],
    "996-kartinka-stranica-paketa":   ["Главное", None],
    "997-ssylki-na-poisk-kartinok":   ["Главное", None, None, None],
}


def already_labelled(notes: str, plan: list[str | None]) -> bool:
    """Заметка уже размечена этой картой — значит миграция по ней прошла.

    Карта описывает состояние ДО разметки: по ярлыку на абзац, где ``None`` — абзац,
    продолжающий предыдущий раздел. После разметки такие абзацы сворачиваются в свой
    раздел (`fold_continuations.py`, а затем и `notes_fix.py`), и число абзацев падает
    ровно на число ``None``. Поэтому «абзацев меньше, чем ярлыков» — не рассогласование,
    а нормальный вид уже сделанной работы, и отличается он от настоящей поломки тем, что
    КАЖДЫЙ оставшийся абзац несёт метку.

    Без этой проверки скрипт падал на собственном результате: одноразовая миграция,
    выполненная однажды, при повторном запуске выглядела как сломанная карта.

    Признак — «у КАЖДОГО абзаца есть метка», а не совпадение числа абзацев с картой.
    Число сверять нельзя: после миграции заметки живут дальше и разделы в них дробятся
    (у `997-ssylki-na-poisk-kartinok` карта помнит один раздел, а в заметке их уже три).
    Ужесточение до равенства оставило бы скрипт падающим ровно на тех слайдах, которые
    успели развиться.

    >>> already_labelled("**Главное:** раз.\\n\\n**Разбор:** два.", ["Главное", "Разбор", None])
    True
    >>> already_labelled("**Главное:** раз.\\n\\n**Новый:** два.", ["Главное", None])
    True
    >>> already_labelled("раз.\\n\\nдва.", ["Главное", "Разбор", None])
    False
    >>> already_labelled("**Главное:** раз.\\n\\nбез метки.", ["Главное", "Разбор"])
    False
    """
    paras = re.split(r"\n\s*\n", notes.strip())
    return bool(paras) and all(N._LABEL_RE.match(p) for p in paras)


def label_notes(notes: str, plan: list[str | None]) -> str:
    paras = re.split(r"\n\s*\n", notes.strip())
    if len(paras) != len(plan):
        raise SystemExit(f"карта не совпала: абзацев {len(paras)}, ярлыков {len(plan)}")
    out = []
    for para, lab in zip(paras, plan):
        if lab and not N._LABEL_RE.match(para):
            para = f"**{lab}:** {para}"
        out.append(para)
    return "\n\n".join(out)


def main(path_str: str) -> int:
    path = Path(path_str)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(MARKER)]
    header = "".join(lines[: starts[0]])
    bounds = starts + [len(lines)]
    blocks = ["".join(lines[a:b]) for a, b in zip(bounds, bounds[1:])]

    done = skipped = 0
    for i, block in enumerate(blocks):
        sid = re.search(r"^  id:\s*(\S+)", block, re.M).group(1)
        plan = LABELS.get(sid)
        if plan is None:
            continue
        # Блочный скаляр в этом файле встречается в трёх видах: `|`, `|-` и `|2`.
        m = re.search(r"^  notes: (\|[-0-9]*)\n", block, re.M)
        if not m:
            raise SystemExit(f"{sid}: нет блока notes")
        head, sep, body = block.partition(m.group(0))
        ind = "    "
        notes = "".join(ln[len(ind):] if ln.startswith(ind) else ln
                        for ln in body.splitlines(keepends=True))
        if already_labelled(notes, plan):
            skipped += 1
            continue
        new = label_notes(notes, plan)
        # Правка обязана быть ровно «приписать ярлык в начало абзаца»: сверяем поабзацно,
        # что новый текст либо совпал со старым, либо отличается только этим префиксом.
        for before, after, lab in zip(re.split(r"\n\s*\n", notes.strip()),
                                      re.split(r"\n\s*\n", new.strip()), plan):
            if after != before and after != f"**{lab}:** {before}":
                raise SystemExit(f"{sid}: правка изменила текст, а не только метки")
        new_body = "".join(ind + ln + "\n" if ln else "\n" for ln in new.splitlines())
        if new_body != body:
            blocks[i] = head + sep + new_body
            done += 1

    out = header + "".join(blocks)
    import yaml
    yaml.safe_load(out)
    path.write_text(out, encoding="utf-8")
    print(f"{path}: метки расставлены на {done} слайдах, уже размечено {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
