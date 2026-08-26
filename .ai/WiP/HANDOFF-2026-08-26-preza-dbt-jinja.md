# HANDOFF 2026-08-26 — dbt-дека: Jinja вглубь, SWOT-задача впереди

Снимок KEEP-списка перед компакцией. Полное состояние — на диске и в git; саммари
сохраняет только упоминания файлов, поэтому всё существенное продублировано здесь.

## Resume

```bash
claude --resume f04f1053-0db7-4db1-bd55-1aee4e815db8
```

## Открытые задачи

| Ключ | Что | Статус |
|---|---|---|
| [#6](https://github.com/dataengy/MLInside-course/issues/6) | Deck publish pipeline: TG + GDrive + колонки листа | открыт; TG-лег работает, drive/sheet ждут внешних условий |
| [#8](https://github.com/dataengy/MLInside-course/issues/8) | preza-merge: форк ревьюера → формат-профиль | ветка `feat/preza-merge`, 27 коммитов впереди `main`, PR не заведён |

**Следующая задача (промпт пользователя, дословно):**

> add
> - SWOT jinja with other approaches
> - why ather projects (SQLMesh, Bruin, Spark SDP?) try to avoid it
>
> make more accent on the following (from gsheer about this subject 4 prezentaion & lecture):
> "Подход Analytics Engineering: Перенос логики трансформации данных из Python-скрипов на уровень SQL.
> Структурирование dbt-проекта: Источники (sources), промежуточные модели (staging) и финальные витрины признаков (marts).
> Качество данных: Автоматическое тестирование ограничений (уникальность, null, связи) и генерация документации.
> Инкрементальные модели: Оптимизация расчетов через обновление только новых данных в ClickHouse."

Просил выполнять на `/model fable` + `/effort max` (переключает сам).

## Сделано (подтверждается коммитами)

| Коммит | Что |
|---|---|
| `d497351` | моделирование (ER, medallion/EDW, DV+AutomateDV), MV в ClickHouse, микробатчинг, стриминг, права доступа |
| `4a8f7f5` | `.tmp/lint_content_scalars.py` (`just preza-lint`) + `scripts/preza/edit_slides.py` (`just preza-slides`) |
| `a0e50ac` | scalar-gate описан в скилле `preza-de-validate`; инварианты 6–8 у сабагента `preza-accents-keeper` |
| `ec94087` | Jinja вглубь: циклы/условия (`074`), контекст и отладка через compile (`075`), диспетчеризация макросов (`076`) |
| `230f95b` | курсор публикации: dbt `v3.20` (73 слайда) отправлена в TG, топик 118 |

Актуальная сборка: `data/generated/MLInside_Введение-в-dbt_v3.20.pptx` — 73 слайда,
формат-профиль `alina-2026-08` (`deck.format` в контент-YAML, профиль в `settings/formats.yml`).

## Не сделано и почему

- **PR из `feat/preza-merge` в `main` не заведён** — ветку переключила параллельная сессия
  под #8; мои коммиты легли туда же. Отправка в TG от ветки не зависит, но в `main`
  изменений нет. Решение за владельцем.
- **`~/.ai` не закоммичен** — scalar-gate в
  `skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts/validate_content.py` и его
  описание в `preza-de-validate/SKILL.md` живут на диске, но это отдельный репозиторий со
  своей привязкой коммитов к issues `hnkovr/.ai`, и подходящий номер задачи неизвестен.
  Правки рабочие: скиллы читаются с диска.
- **Остальные пять дек формат-профиль не получили** — `deck.format` стоит только у dbt-деки,
  их последние сборки уже `tg=ok`, новых версий нет. Раздать профиль — отдельная работа.
- **Drive- и sheet-леги публикации** — `pending` у всех дек: квота Drive у `hnkovr@gmail.com`
  и роль Редактор для сервис-аккаунта на листе (см. `docs/deck-publish-pipeline.md`).

## Принятые решения (не перерешивать)

1. **Правки деки — только `just preza-slides <content> <cmd>`** (splice по id слайда).
   Никакого round-trip через `yaml.safe_dump`: он переформатирует весь файл.
2. **`just preza-lint` перед каждым билдом.** Буллет или ячейка вида `- текст: продолжение`
   без кавычек — это YAML-**мапа**; билд падает поздно с `TypeError: … got 'dict'`.
   Гейт теперь есть и в каноническом `validate_content.py`.
3. **Рост деки** = поднять `deck_generation.slides_max` в `settings/config.yml` датированным
   комментарием НАД предыдущим + обновить пины в `src/tests/test_content.py`
   (число слайдов и число code-слайдов) тем же изменением. Сейчас: max 76, пины 73 / 29.
4. **Провенанс-штамп dbt-деке не ставим** — она рукописная (`generated: false`); валидатор
   ругается, `preza-review` понижает это до info. Это ожидаемое состояние, не дефект.
5. **Публикация — явная**: `just publish-new --only tg`. Одна версия в TG уходит один раз;
   повтор только через `--force`.
6. **ЛИМИТ ЗАПИСИ (важно для следующей задачи).** `just preza-blocks content/preza-dbt-v3-content.yml`:
   блок 3 «dbt Core: компиляция, Jinja, материализации, сущности» — **24.7 мин при лимите 25**.
   Ещё один слайд в этот блок его ломает. Вся дека ≈95 мин против ориентира 50–90 мин.
   Новые Jinja-слайды либо ставить вне блока 3, либо делить блок надвое
   (`recording.blocks` в `content/presentations.yml`, правила — `docs/course-rules.md`).
   Дедлайн записи всех лекций — 2026-08-31.

## Где что лежит

- Контент деки: `content/preza-dbt-v3-content.yml` (73 слайда, id-шники стабильны).
- **Четыре акцента лекции — уже на диске**: `content/presentations.yml` → запись с
  `out_name: MLInside_Введение-в-dbt` → `accents:` (Analytics Engineering, слои
  sources/staging/marts, качество данных, инкрементальные модели в ClickHouse).
  Проверка покрытия: `just preza-review content/preza-dbt-v3-content.yml` (сейчас 4/4).
- Ленты и их спеки: `docs/deck-publish-pipeline.md`, `docs/schedule-gsheet-lane.md`,
  `docs/preza-merge-lane.md`, `docs/course-rules.md`.
- Инварианты правок: `.claude/agents/preza-accents-keeper.md` (пункты 6–8).
