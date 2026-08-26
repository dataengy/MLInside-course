# HANDOFF 2026-08-26 — course-rules-session (снимок keep-листа перед компакцией)

Снимок обязателен: компакция сохраняет *упоминания* файлов, не содержимое. Всё ниже
лежит на диске и запушено в `main` (`origin/main` = `5e8558b`), кроме отмеченного.

Resume: `cd /Users/nk.myg/github/@dataengy/MLInside-course/.claude/worktrees/course-rules-session && claude --resume 890cc998-1985-4946-b5a2-735b52bd316a`
(сессия живёт в нативном worktree `worktree-course-rules-session`; в общем checkout — параллельная
сессия на `feat/preza-merge`, её файлы не трогать).

## Открытые задачи (GitHub Issues — Jira здесь запрещена)

| Issue | Статус |
|---|---|
| [#7 — Правила продакшена курса и Q&A с менеджером: docs, settings, блоки записи ≤25 мин, хук и агент](https://github.com/dataengy/MLInside-course/issues/7) | сделано, тело дополнено статусом + follow-ups; можно закрывать после ревью |
| [#14 — Изоляция параллельных сессий: worktree по умолчанию, shared-tree-guard, session-lock-hooks](https://github.com/dataengy/MLInside-course/issues/14) | сделано (`5e8558b`); можно закрывать |
| [#10 — Запись лекций до 2026-08-31: тест-клип, dbt (лекция 4), Dagster (лекция 6)](https://github.com/dataengy/MLInside-course/issues/10) | открыто — работа человека; дедлайн менеджера |
| [#13 — ДЗ: балльная система — решение и переписать критерии (слайды 050/049 + HW1/HW2)](https://github.com/dataengy/MLInside-course/issues/13) | ждёт решения Николая; черновик ответа в `docs/course-qa.md` |
| [#11 — CI/CD-дека (лекция 8, с Владом): план блоков записи + черновик менеджеру](https://github.com/dataengy/MLInside-course/issues/11) | открыто; хук `course-production-status` напоминает |
| [#12 — dbt-дека: скрины/код Airflow и Dagster на слайдах 036/037](https://github.com/dataengy/MLInside-course/issues/12) | открыто |
| [#8](https://github.com/dataengy/MLInside-course/issues/8) / [#9](https://github.com/dataengy/MLInside-course/issues/9) — перенос дизайн-правок Алины (dbt / Dagster) | параллельная сессия (лента `preza-merge`, агент `preza-merge-keeper`) |
| hnkovr/.ai [#19](https://github.com/hnkovr/.ai/issues/19) `pre-commit-check.sh` обрывается на WARN github.com · [#20](https://github.com/hnkovr/.ai/issues/20) todoist `upsert.py` / `create-project` | открыты, найдены здесь |

## Сделано (коммиты `main`)

- `64ea85e` feat(course) — `settings/config.yml → course_production` + `participants`; `content/presentations.yml → recording.blocks` (dbt 6 блоков / Dagster 4); `src/course` (`blocks`, `status`, `cli`); `just preza-blocks{,-all}`, `just course-status`
- `19904fe` test(course) — `src/tests/test_course_blocks.py` (280 passed, 4 skipped)
- `c6568cc` chore(hooks) — `scripts/hooks/course-production-status.sh` + регистрация
- `426f8c1` docs(course) — `docs/course-rules.md`, `docs/course-qa.md`, README, CHANGELOG
- `42f39ab` chore(ai) — агент `.claude/agents/course-production-keeper.md`, инвариант 9 у `preza-accents-keeper`
- `c279719` (cherry-pick `ac7062c`) docs — ссылки на issues в open-вопросах и статусе
- `01412b5` chore(ai) — статус/лог: follow-ups #10–#13, Todoist, инцидент
- `5e8558b` chore(session) — `scripts/hooks/shared-tree-guard.sh`, session-lock хуки в `.claude/settings.json`, `.gitignore` (`.claude/worktrees/`, `.ai/.locks/`), README «Parallel sessions»
- `~/.ai`: `ff28fc0` кандидат `course-rules-upsert`; `b0efbe0` `projects_capacity.py` + `projects_policy.yml` + рецепты + кандидаты `session-isolate-worktree-or-lock`, `todoist-projects-capacity` (запушено)
- Память: `mlinside_course_production_rules`, `session_isolation_worktree`, обновлён `project_mlinside_course` (Алина, Todoist project id)
- Todoist: проект «MLInside» `6hMWcRPhHrC8Jqhx`; напоминание `6hMVWW78RWgM8w2F` (p1, 2026-08-26 10:00); слиты `tg_events_week_digest`→`tg-events-parser`, `pdp-personal`→`PDP` (владелец применил сам); 7/8 проектов
- TG-информ smart-commit отправлен; комменты прогресса в #7, #8, #14

## НЕ сделано и почему (саммари теряет это первым)

1. **Ответы Алине** (баллы ДЗ, тест-запись, дата записи dbt) — решения человека; черновики под чекбоксами `docs/course-qa.md`, напоминание в Todoist.
2. **Перенос дизайн-правок Алины из pptx v3.15/v1.4 в генератор** — ведёт параллельная сессия (#8/#9); v3.19 dbt-деки собрана, не издана — публиковать после переноса.
3. **`~/.claude/settings.json`** (строка хука `projects_capacity.py --hook`) — правка на месте, файл gitignored в `~/.claude` по дизайну — коммита не будет.
4. **Скилл `course-rules-upsert` и два глобальных кандидата** — не промоутированы в каталог (политика: только через `/create-skill`, отдельным решением).
5. **`ac7062c` остался в `feat/preza-merge`** (ветка параллельной сессии; тот же дифф, что `c279719`) — не переписывал чужую ветку; смержится чисто.
6. **Хук `course-production-status` в общем checkout** появится там только после merge `main` в их ветку / переключения на `main`.
7. `pre-commit-check.sh` не чинил (hnkovr/.ai#19) — эквивалент проверок гонял вручную.

## Второй проход (после первого снимка) — глоссарий, напоминания, закрытые issues

- Закрыты: [#7](https://github.com/dataengy/MLInside-course/issues/7) (правила продакшена) и [#14](https://github.com/dataengy/MLInside-course/issues/14) (изоляция сессий) — весь скоуп в `main`.
- Открыт [#16](https://github.com/dataengy/MLInside-course/issues/16) — глоссарий + лента напоминаний; сделано в нём же:
  - `.ai/AI-glossary.{ru,en}.md` — 15 терминов сессии (порядок простые → составные, якоря OK);
  - `settings/reminders.yml` + `src/course/reminders.py` + `scripts/todoist/upsert_reminders.py`
    + `just course-reminders[-apply]` — 9 напоминаний, идемпотентно по `key:` в описании задачи;
  - `src/tests/test_course_reminders.py` (+14 → **294 passed, 4 skipped**);
  - доки: «Напоминания» и «Термины» в `docs/course-rules.md`, README, `.tmp/AGENTS.md`, CHANGELOG;
  - агент `course-production-keeper` — инварианты 9 (зеркалить сроки в напоминания) и 10 (глоссарий).
- Todoist: проект «MLInside» `6hMWcRPhHrC8Jqhx`; 9 напоминаний применены, повторный прогон — `0/0/9`.
  Владелец слил `tg_events_week_digest`→`tg-events-parser` и `pdp-personal`→`PDP` (7/8 проектов).

### Не сделано во втором проходе
1. `just lint` красный на `src/orchestration/*` (I001, 2 ошибки, коммит `7089812`) — файлы чужой
   ленты, не трогал; чинится `ruff check --fix src/orchestration`.
2. Кандидаты скиллов в `~/.ai` (`session-isolate-worktree-or-lock`, `todoist-projects-capacity`,
   `course-rules-upsert`) не промоутированы в каталог — только через `/create-skill`, отдельным решением.
3. Компакция контекста в этой сессии так и не запускается: `/compact` из терминала приходит
   обычным сообщением (5 попыток, одно- и многострочные). Заведён драфт фидбека.

## Согласованные решения (не переспрашивать)

- Трекер репо — только GitHub Issues; коммиты `(#N)`; «JT» здесь = GH Issue.
- Правки — только в нативном worktree; в `main` — `git fetch && git rebase origin/main && git push origin HEAD:main`; в общем checkout ничего не коммитить/не переключать.
- Хуки репо живут в `scripts/hooks/` + `.claude/settings.json` (не `scripts/session-hooks/` + `settings.local.json`).
- Todoist: лимит 8 активных проектов (free) — скаляр в `~/.ai/skills/_settings/tasks/todoist/projects_policy.yml`; архив/слияние только по явному «ок» владельца (он уже применил два слияния).
- `recording.blocks` — id слайдов, покрытие полное; блок > 25 мин — предупреждение, `--strict` — ошибка; `min_per_slide: 1.3` — эвристика.
- Дедлайн записи 2026-08-31 — скаляр `course_production.deadlines.record_all_by`; хук считает дни.
- Правила менеджера не смягчать; неназванное — открытый вопрос, не правило.
