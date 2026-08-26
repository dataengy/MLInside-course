# HANDOFF 2026-08-26 — ветка preza-merge завершена, но не влита

Снимок KEEP-списка перед компакцией (второй за день; первый —
[`HANDOFF-2026-08-26-preza-dbt-jinja.md`](HANDOFF-2026-08-26-preza-dbt-jinja.md), там
состояние dbt-деки и задача про SWOT Jinja). Инструкция компакции сохраняет упоминания
файлов, но не их содержимое, поэтому существенное продублировано здесь.

## Resume

```bash
cd ~/github/@dataengy/MLInside-course && claude --resume d925286e-901d-4bad-912b-2ae4885126da
```

## Открытые задачи

| Ключ | Что | Статус |
|---|---|---|
| [#4 — /preza-review + foreign-deck import (Airflow lecture-5 deck)](https://github.com/dataengy/MLInside-course/issues/4) | ревьюер + импорт чужой .pptx | открыт с 2026-08-15 |
| [#6 — Deck publish pipeline: Telegram + GDrive (persistent URL) + GSheet columns](https://github.com/dataengy/MLInside-course/issues/6) | TG-лег работает; drive/sheet ждут внешних условий | открыт |
| [#7 — Правила продакшена курса и Q&A с менеджером](https://github.com/dataengy/MLInside-course/issues/7) | блоки записи ≤25 мин, хук, агент | открыт |
| [#9 — Перенести дизайн-правки менеджера в Dagster-деку](https://github.com/dataengy/MLInside-course/issues/9) | форк v1.4 ещё не скачан | открыт |
| [#10 — Запись лекций до 2026-08-31](https://github.com/dataengy/MLInside-course/issues/10) | тест-клип, dbt (лекция 4), Dagster (лекция 6) | **дедлайн через 5 дней** |
| [#11 — CI/CD-дека (лекция 8, с Владом)](https://github.com/dataengy/MLInside-course/issues/11) | план блоков + черновик менеджеру | открыт |
| [#12 — dbt-дека: скрины/код Airflow и Dagster на слайдах 036/037](https://github.com/dataengy/MLInside-course/issues/12) | решить и добавить | открыт |
| [#13 — ДЗ: балльная система](https://github.com/dataengy/MLInside-course/issues/13) | слайды 050/049 + HW1/HW2 | открыт, `question` |
| [#14 — Изоляция параллельных сессий](https://github.com/dataengy/MLInside-course/issues/14) | worktree по умолчанию, shared-tree-guard | открыт |

## Сделано (подтверждается коммитами)

| Коммит | Что |
|---|---|
| [`362d210`](https://github.com/dataengy/MLInside-course/commit/362d210) | KEEP-снимок по dbt-деке (предыдущая компакция) |
| [`eb5f66b`](https://github.com/dataengy/MLInside-course/commit/eb5f66b) | preza-merge: пересборка verify с профилем предложения, честный R1, измеренные допуски |
| [`ec94087`](https://github.com/dataengy/MLInside-course/commit/ec94087) | Jinja вглубь: циклы/условия, контекст и отладка, диспетчеризация макросов |
| [`230f95b`](https://github.com/dataengy/MLInside-course/commit/230f95b) | курсор публикации: dbt v3.20 (73 слайда) в TG |

Ход реализации preza-merge целиком — в [`.tmp/preza-merge-sdd-ledger.md`](../../.tmp/preza-merge-sdd-ledger.md)
(312 строк, заканчивается `BRANCH COMPLETE.`). До этой компакции файл был **не в git** —
единственный артефакт под риском; закоммичен вместе с этим снимком.

## Не сделано и почему

- **`feat/preza-merge` на 29 коммитов впереди `main`, PR не заведён — при том что
  [#8](https://github.com/dataengy/MLInside-course/issues/8) уже ЗАКРЫТ.** Задача закрыта по
  факту готовности работы, но в `main` её нет. Расхождение трекера и `main` — решение владельца
  (влить, оставить веткой или переоткрыть #8).
- **`width: 5.5` в допусках verify — «отключённая проверка в виде числа».** Ревьюер прав:
  left/top/height получили обоснованную границу 0.45", а width подогнан под наблюдаемый максимум
  (5.40) и на слайде 13.3" съедает ~90% диапазона R4, то есть перестаёт быть регрессионным
  гейтом. На выданную деку не влияет (сейчас 0 расхождений), цена — будущая: форк, где менеджер
  СУЖАЕТ колонку, пройдёт молча. Честная форма — явное исключение «width не структурная проверка
  под R4», а не подогнанное число. Не чинилось: второй волны правок не было, это выбор владельца.
- **Публикация: drive/sheet ждут по всем декам**, у OGIP `drive=error` (не pending — ошибка).
  `just publish-status` — источник правды.
- **PreCompact-хук в этом репозитории не установлен.** `just -f .tmp/Justfile
  precompact-keeplist-hook` не существует, поэтому шаг 1 `/compact-safely` каждый раз делается
  руками. Обнаружено дважды с интервалом в месяц (2026-07-28 и сегодня) — ставится через
  `/add-session-hook`.
- **10 файлов в `.tmp` не разобраны** (`/audit-tmp-untriaged`). Все 9 скриптов **уже в git** и
  под них есть рецепты `.tmp/Justfile`, так что компакции они не боятся; это бэклог продвижения
  в канон, а не риск потери. Исключение — `lint_content_scalars.py`: от него зависит корневой
  рецепт `just preza-lint`, то есть корневой Justfile завязан на `.tmp`.
- **`GITLAB_TOKEN` истекает 2026-08-29** (SessionStart-хук), плюс 13 ключей без значений.

## Принятые решения (не переспрашивать)

- **Трекер здесь — только GitHub Issues.** «JT» в этом проекте = GH Issue, Jira запрещена;
  политика в `~/.ai/skills/settings/tracker_binding.yml → projects.MLInside-course`.
  Коммиты биндятся как `(#N)`.
- **Параллельные сессии делят чекаут** — правки через `EnterWorktree`, в общем корне только
  чтение; `git reset`/`checkout`/`stash` в общем корне запрещены (инцидент #14). Локи
  совещательные. Для preza-merge осознанно выбрана ветка вместо worktree: 6 сабмодулей + LFS,
  параллельных исполнителей не было — обоснование в шапке леджера.
- **`data/` ведёт librarian** (plan→apply→catalog), руками файлы не двигать.
- **Дека, которую этот репозиторий не генерировал, получает `generated: false`** — фабриковать
  штамп `— Сгенерировано:` нельзя.
