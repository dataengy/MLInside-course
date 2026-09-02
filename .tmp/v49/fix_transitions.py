#!/usr/bin/env python3
"""Переписать «Переход» у слайдов, которым перестановка сменила соседа.

Почему не `sub` в плане патчера: он ищет подстроку внутри ОДНОГО блока слайда, а две
одинаковые фразы «Переход» различаются только тем, какой слайд идёт следующим — то есть
строкой из соседнего блока. Здесь адресация по id, поэтому неоднозначности нет.

    python3 .tmp/v49/fix_transitions.py content/preza-dbt-v4-content.yml
"""
import re, sys, pathlib, yaml

# id слайда → новый текст перехода (без обрамления, оно достраивается)
NEW = {
    "012-skvoznaya-arhitektura":
        "«Дальше — как это работает изнутри: что dbt на самом деле делает с вашим SQL».",
    "014c-proekt-ne-okruzhenie":
        "«И главное про окружение: где живут значения, если в репозитории их нет».",
    "014c3-dbt-project-yml":
        "«Инструмент понятен. Теперь главный вопрос проектирования: как раскладывать сами данные».",
    "060-izmenenie-sql-fichi-eto-izmenenie-ml-sistemy":
        "«Прежде чем разбирать рубежи по одному — карта: где какую ошибку ловят».",
    "014d-shift-left":
        "«Первый рубеж подробно: что именно проверяется до коммита».",
    "062-priznaki-mart-delivery-features":
        "«Соберём все механизмы dbt в одну таблицу и переведём их на язык MLOps».",
    "013-mlops-smysl-konceptov-dbt":
        "«И финальная картинка: где вы теперь стоите».",
}

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
starts = [i for i, l in enumerate(lines) if l.startswith("- kind:")]
header = "".join(lines[: starts[0]])
bounds = starts + [len(lines)]
blocks = ["".join(lines[a:b]) for a, b in zip(bounds, bounds[1:])]

done = []
for i, b in enumerate(blocks):
    sid = re.search(r"^  id:\s*(\S+)", b, re.M).group(1)
    if sid not in NEW:
        continue
    # Курсив ~~…~~ встречается по всей заметке, поэтому якорь — метка раздела,
    # а меняется только буллет сразу под ней.
    pat = re.compile(r"(\*\*Переход:\*\*\n)    - .*", re.M)
    b2, n = pat.subn(lambda m: m.group(1) + "    - ~~" + NEW[sid] + "~~", b, count=1)
    if n != 1:
        raise SystemExit(f"{sid}: не нашёл ровно один «Переход»")
    blocks[i] = b2
    done.append(sid)

out = header + "".join(blocks)
yaml.safe_load(out)
path.write_text(out, encoding="utf-8")
print(f"{path}: переходы переписаны у {len(done)} слайдов")
missing = set(NEW) - set(done)
if missing:
    raise SystemExit(f"не найдены слайды: {sorted(missing)}")
