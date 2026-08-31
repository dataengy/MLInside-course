#!/usr/bin/env python3
"""Хронометраж и структура подстрочников в контент-YAML деки — идемпотентно.

ЗАЧЕМ. Заметка докладчика несёт длительность слайда (``[~N мин]``), но не абсолютное время:
читая с экрана, лектор не видит, опаздывает он или нет. И разделы заметки («Главное»,
«Рассказ», «Осторожно»…) идут сплошным текстом. Скрипт делает обе правки:

    10:00-11:30 [~1.5 мин] **Главное:**
    - трансформации — это !!общий стык!!, а не чужая зона.

    **Переход:**
    - ~~«У аналитиков эта же боль случилась на десять лет раньше».~~

Вся логика — в ``preza_gen.notes``; тот же модуль вызывается на КАЖДОЙ сборке
(``pipeline._format_notes``), поэтому деку с часами можно получить и не трогая YAML.
Этот скрипт нужен, чтобы часы были видны в самом контенте — в ревью, в диффе, в редакторе.

ИДЕМПОТЕНТНОСТЬ. Повторный ``apply`` не наслаивает штампы и не дробит буллеты: перед
простановкой старые часы срезаются, а буллеты сворачиваются обратно в прозу и собираются
заново. Второй прогон подряд обязан показать «изменений 0» — это и есть проверка.

КОМАНДЫ

    python3 scripts/preza/notes_fix.py check CONTENT.yml          # exit 1, если разошлось
    python3 scripts/preza/notes_fix.py apply CONTENT.yml
    python3 scripts/preza/notes_fix.py apply CONTENT.yml --scope=all
    python3 scripts/preza/notes_fix.py apply CONTENT.yml --max-sentences=2 --max-chars=180

``--scope``: ``stamped`` (по умолчанию) — часы только слайдам с ``[~N мин]``; ``all`` — всем,
слайд без метки считается нулевым; ``per-part`` — как ``all``, но в каждой части (PART 2,
PART 3) часы идут с нуля. ``--no-clock`` оставляет только структуру разделов и СНИМАЕТ
ранее проставленные часы.

Запись — блочной хирургией: файл режется по ``- kind:``, правится только значение ключа
``notes:``, остальные слайды остаются байт-в-байт. Перед записью результат проверяется на
парсибельность YAML и на то, что заметки не изменились ни в чём, кроме форматирования.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from edit_slides import refuse_if_excluded, split_blocks  # noqa: E402
from preza_gen import notes as N  # noqa: E402

NOTES_KEY = "  notes:"
INDENT = "    "


def _notes_span(block: str) -> tuple[int, int] | None:
    """Границы значения ключа ``notes:`` в блоке слайда, в номерах строк [начало, конец)."""
    lines = block.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.startswith(NOTES_KEY)), None)
    if start is None:
        return None
    end = start + 1
    while end < len(lines):
        ln = lines[end]
        # Значение кончается на первой непустой строке с отступом ≤ 2 — это следующий ключ
        # слайда или начало следующего слайда. Пустые строки внутри блочного скаляра свои.
        if ln.strip() and len(ln) - len(ln.lstrip(" ")) <= 2:
            break
        end += 1
    return start, end


def _render_notes(text: str) -> str:
    """Значение ``notes:`` как канонический блочный скаляр.

    ``|2`` (явный индикатор отступа) обязателен: заметка может начинаться с пробела или
    содержать строку, начинающуюся глубже — без индикатора YAML определил бы отступ по
    первой строке и разобрал текст иначе.
    """
    body = text.rstrip("\n")
    out = [NOTES_KEY + " |2\n"]
    out += [(INDENT + ln + "\n") if ln.strip() else "\n" for ln in body.split("\n")]
    return "".join(out)


def _slide_notes(block: str) -> str:
    doc = yaml.safe_load("content:\n" + block)
    return (doc["content"][0].get("notes") or "") if doc.get("content") else ""


def _plain(text: str) -> str:
    """Текст без форматирования — часов, буллетов и пробелов.

    Сравнение по нему ловит настоящую потерю содержания и не срабатывает на переносах,
    которые скрипт и должен менять.
    """
    text = N.CLOCK_RE.sub("", text.strip())
    text = re.sub(r"^[ \t]*- ", "", text, flags=re.M)
    return re.sub(r"\s+", " ", text).strip()


def run(content_yml: Path, *, write: bool, scope: str, clock: bool,
        max_sentences: int, max_chars: int) -> int:
    head, blocks = split_blocks(content_yml.read_text(encoding="utf-8"))

    # Часы считаются по всей деке, поэтому сначала полный проход через preza_gen.notes —
    # тот же код, что и на сборке, чтобы результаты не могли разойтись.
    doc = yaml.safe_load(content_yml.read_text(encoding="utf-8"))
    specs = [type("S", (), dict(kind=s.get("kind", ""), id=s.get("id", ""),
                                notes=s.get("notes") or ""))() for s in doc["content"]]
    N.apply_deck(specs, clock=clock, scope=scope,
                 max_sentences=max_sentences, max_chars=max_chars)
    if len(specs) != len(blocks):
        raise SystemExit(f"{content_yml}: YAML видит {len(specs)} слайдов, "
                         f"блочная разбивка — {len(blocks)}; файл не тронут")

    changed, stamped, bulleted, no_duration, damaged = 0, 0, 0, [], []
    out_blocks: list[str] = []
    for block, spec in zip(blocks, specs):
        span = _notes_span(block)
        before = _slide_notes(block)
        after = spec.notes
        if span is None or not before.strip() or after == before:
            out_blocks.append(block)
        else:
            if _plain(before) != _plain(after):
                damaged.append(spec.id)
            lines = block.splitlines(keepends=True)
            out_blocks.append("".join(lines[:span[0]]) + _render_notes(after)
                              + "".join(lines[span[1]:]))
            changed += 1
        if N.CLOCK_RE.match(after):
            stamped += 1
        bulleted += sum(1 for ln in after.split("\n") if ln.startswith("- "))
        if N.duration(after) is None and after.strip():
            no_duration.append(spec.id)

    if damaged:
        raise SystemExit(f"{content_yml}: у {len(damaged)} слайдов изменился ТЕКСТ, а не "
                         f"только форматирование — файл не тронут: {', '.join(damaged[:5])}")

    text = head + "".join(out_blocks)
    try:
        reparsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SystemExit(f"{content_yml}: результат не парсится как YAML, файл не тронут: {exc}")
    for spec, got in zip(specs, reparsed["content"]):
        if (got.get("notes") or "").rstrip("\n") != spec.notes.rstrip("\n"):
            raise SystemExit(f"{content_yml}: заметка слайда {spec.id} после записи читается "
                             "иначе, чем записана — файл не тронут")

    if write and changed:
        refuse_if_excluded(content_yml)
        content_yml.write_text(text, encoding="utf-8")

    total = sum(1 for s in specs if s.notes.strip())
    print(f"{content_yml}: слайдов с заметками {total}, с часами {stamped}, "
          f"буллетов {bulleted}, изменено {changed}")
    if no_duration:
        print(f"  без метки [~N мин] ({len(no_duration)}): {', '.join(no_duration[:6])}"
              + (" …" if len(no_duration) > 6 else ""))
    if not write:
        print("  " + ("расходится — нужен apply" if changed else "совпадает"))
    return 1 if (changed and not write) else 0


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    opts = {a.split("=", 1)[0]: a.split("=", 1)[-1] for a in argv[1:] if a.startswith("--")}
    if len(args) != 2 or args[0] not in ("check", "apply"):
        print(__doc__)
        return 2
    return run(
        Path(args[1]),
        write=(args[0] == "apply"),
        scope=opts.get("--scope", "stamped"),
        clock="--no-clock" not in opts,
        max_sentences=int(opts.get("--max-sentences", 3)),
        max_chars=int(opts.get("--max-chars", 240)),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
