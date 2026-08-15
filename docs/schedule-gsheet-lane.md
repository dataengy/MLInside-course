# Лента «GSheet-расписание → accents → preza-review»

Как тезисы лекций из курсового Google-листа становятся рубрикой (`accents:`), по которой
`/preza-review` оценивает каждую деку. Одна команда после настройки: `just presentations-plan`.

## Схема

```
GSheet (лист расписания)                 id: 1cxYGtU36nbmO5DhjtNkm_HMESiNPwoWdd6QY8yb2JaU
  │  колонки: старая запись | название | тезисы | лектор
  ▼  just gsheet-dump                    (сырой дамп → settings/schedule.yml)
settings/gsheet.yml                      (таб, header_row, карта колонок, сплит тезисов)
  ▼  just presentations-plan             (upsert по normalized topic)
content/presentations.yml → accents:    (рубрика; курируемые поля не трогаются)
  ▼  just preza-review-all
docs/reviews/<out_name>.{md,findings.yml}
```

## Предусловие: Google ADC (user-lane)

Читалка (`integrations/google/sheets/`) использует Application Default Credentials
аккаунта `hnkovr@gmail.com` (readonly-скоупы sheets+drive):

```bash
just -f ~/.ai/scripts/gcloud/Justfile adc-status
just -f ~/.ai/scripts/gcloud/Justfile adc-login account=hnkovr@gmail.com  # браузерный консент ОБЯЗАН завершиться
just gsheet-tabs                                                          # smoke + имена табов
```

Прерванный логин = нет ADC-файла — это и была причина исходного блокера
(см. скилл `/reset-google-account-creds`, там этот репозиторий в `known_usages`).

## settings/gsheet.yml — грабли

1. **`mapping.columns` замещает дефолт целиком** (`src/schedule/settings.py::load()` не
   мержит по-полевому). Карту колонок всегда повторять полностью.
2. **«тезисы» нет в DEFAULT_MAPPING** — без `settings/gsheet.yml` синк молча даст ноль
   акцентов у всех лекций.
3. **«старая запись» не мапить в `n`** — это свободный текст; численный ключ сломал бы
   topic-матчинг upsert-а.
4. **Тезисы-ячейка — один абзац «1. … 2. … 3. …»** без переводов строк. Включён
   `accents_split_numbering: true` → `mapper._NUMBERED_ITEM` режет по номерным границам
   (идемпотентно и при настоящих `\n`; десятичные дроби не трогает).

## Семантика upsert (src/schedule/mapper.py)

- Матчинг существующей записи — по `n:`, иначе по **normalized topic** (регистр, пунктуация
  и ё/е не важны). Поэтому topic dbt-деки переименован (2026-08-13) в точное «название»
  листа: «Трансформация данных и витрины (dbt)».
- Из листа перезаписываются только `SHEET_FIELDS` = n/date/topic/owner/status/accents/notes.
  Курируемое (`content`, `out_name`, `slides`, `visuals`, `generated`, `homework`, что угодно
  рукописное) — переживает синк. Записи, ушедшие с листа, помечаются stale, не удаляются.
- Строки листа без записи в плане (лекции других лекторов) добавляются «голыми»
  (`content: null`) — безвредно: review/build фильтруют по непустому `content`.

## Акцентная ось /preza-review

- Рубрика = `accents:` записи плана; матчер стеммит термины (первые 5 символов) и ищет
  ≥`hit_ratio` (0.75) терминов на ОДНОМ слайде. Настройки:
  `~/.ai/skills/_catalog/docs/pptx/preza-review/settings/review.yml`.
- Русский стемминг груб: в слайдах повторяем **лексику акцента буквально**
  (напр. «изоляция», а не «изолируют»; «е» вместо «ё» в спорных местах — «расчетов»).
- Ложный partial → чинить keywords/stopwords/hit_ratio; **`severity.accent_missing`
  не понижать** (это смысл гейта; см. закрытую задачу .ai/tasks/0006).

## Hook

`scripts/hooks/preza-accents-status.sh` (SessionStart, `.claude/settings.json`):
предупреждает, если лента не настроена/не запускалась или sheet-matched дека осталась
без акцентов. Fail-open, без сети.

## Хронология

- 2026-07-27 — план засеян руками, `accents: []`; читалка + `/preza-review` готовы.
- 2026-08-11..13 — ADC-блокер разобран (`/reset-google-account-creds`); карта колонок под
  живой лист; сплит нумерованных тезисов; первый живой прогон акцентной оси; целевые
  правки трёх дек (dbt 52, Dagster 51, CI/CD+Obs 42 слайдов) под 12 акцентов листа.
