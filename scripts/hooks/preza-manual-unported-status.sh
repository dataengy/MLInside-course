#!/usr/bin/env bash
# SessionStart hook: ручные правки деки, которые могли не доехать до контента.
# Fail-open, без сети и без python — хук на старте сессии обязан быть мгновенным.
#
# ЗАЧЕМ. Дека генерируется из content/*-content.yml, но человек правит готовый .pptx в
# PowerPoint. Такая правка не воспроизводится ничем и умирает на следующей сборке, если её
# не перенесли в контент. 2026-09-01/02 это случилось трижды подряд: v4.2.1-man сутки
# пролежала с непереносённым слайдом про Dagster, v4.4.1-man — с новым слайдом и
# перестановкой вступления, v4.7.0+man — с шестью правками. Каждый раз их находили случайно.
#
# ПРИЗНАК — ВРЕМЯ, а не содержимое. Ручная дека новее последней сборки почти наверняка несёт
# правку, которой в контенте нет: сборка перезаписывает только сгенерированное. Сравнение по
# содержимому (диф заголовков через python-pptx) честнее, но стоит секунды на каждой деке;
# дорогой хук перестают читать, а дешёвый работает. Разбор — за скиллом /preza-graft.
#
# Ложная тревога возможна: правку могли перенести и не тронуть файл. Поэтому формулировка
# «проверьте, перенесены ли», а не «потеряно».
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

MANUAL_DIR=data/source/manual
BUILT_DIR=data/generated
[ -d "$MANUAL_DIR" ] || exit 0

# Точка отсчёта — самая свежая сборка любой деки. Сборок нет вовсе — сравнивать не с чем.
newest_build=$(ls -t "$BUILT_DIR"/*.pptx 2>/dev/null | head -1)
[ -n "$newest_build" ] || exit 0

stale=""
for f in "$MANUAL_DIR"/*.pptx; do
  [ -e "$f" ] || continue
  [ "$f" -nt "$newest_build" ] && stale="$stale $(basename "$f")"
done

# ВТОРАЯ проверка, по КОММИТАМ, — закрывает ложный негатив первой. Сравнение со сборкой
# молчит, если деку пересобрали, а правку в контент так и не перенесли: свежая сборка
# делает ручной файл «старым». Между тем это и есть тот самый случай, ради которого хук
# заведён — пересборка правку уже затёрла. Здесь опорой служит не сборка (артефакт), а
# content-YAML: если ручной файл закоммичен ПОЗЖЕ последней правки контента, работа
# в контент не доехала.
#
# Без python и без YAML-парсера намеренно: хук на старте сессии обязан быть мгновенным,
# а системный python3 здесь без pyyaml — половина хуков репозитория из-за этого молча
# мертва. `out_name` берётся грепом; версия в нём отличает живую деку (v4) от архивной (v3).
unported=""
for f in "$MANUAL_DIR"/*.pptx; do
  [ -e "$f" ] || continue
  man_ct=$(git log -1 --format=%ct -- "$f" 2>/dev/null)
  [ -n "$man_ct" ] || continue                      # не в git — это забота другого хука
  stem=$(basename "$f" .pptx); stem=${stem%-man}; stem=${stem%+man}
  base=${stem%%_v[0-9]*}

  best_yml=""; best_ver=""
  for y in content/*-content.yml; do
    [ -e "$y" ] || continue
    out=$(grep -m1 '^  out_name:' "$y" 2>/dev/null | sed 's/^  out_name: *//; s/ *#.*//')
    [ "${out%%_v[0-9]*}" = "$base" ] || continue
    ver=$(printf '%s' "$out" | sed -n 's/.*_v\([0-9.]*\).*/\1/p')
    if [ -z "$best_yml" ] || [ "$(printf '%s\n%s\n' "$best_ver" "$ver" | sort -V | tail -1)" = "$ver" ]; then
      best_yml=$y; best_ver=$ver
    fi
  done
  [ -n "$best_yml" ] || continue

  yml_ct=$(git log -1 --format=%ct -- "$best_yml" 2>/dev/null)
  [ -n "$yml_ct" ] || continue
  [ "$man_ct" -gt "$yml_ct" ] && unported="$unported $(basename "$f") → $best_yml;"
done

[ -n "$stale$unported" ] || exit 0
[ -n "$stale" ] && printf '[preza-manual] ⚠ ручная дека новее последней сборки — проверьте, перенесены ли правки:%s\n' "$stale"
[ -n "$unported" ] && printf '[preza-manual] ⚠ ручная дека закоммичена позже своего контента — правка в контент не доехала:%s\n' "$unported"
printf '[preza-manual]   разбор двух линий: /preza-graft · перенос в контент: /deck-manual-pass\n'
exit 0
