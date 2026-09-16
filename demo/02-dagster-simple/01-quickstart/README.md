# Демо 1 · Quick Start — от пустой папки до графа

Слайд **17** упрощённой деки «Оркестрация ML-пайплайнов на Dagster», около 7 минут.
Демо ровно по семи шагам Quick Start (слайды 8–16): ничего нового, всё вместе и вживую.
Данные — [jaffle shop](https://github.com/dbt-labs/jaffle_shop_duckdb): из его сырья
собрана витрина признаков `features.parquet`, одна строка на клиента.

```
feature_table ──→ training_dataset ──→ trained_model
 (pandas, свежесть)   └─ проверка net_propuskov   (sklearn, метаданные)
```

## Перед записью

```bash
just setup    # uv sync + состояние «до демо»
just smoke    # весь сценарий без браузера; должен закончиться «SMOKE OK»
```

`just smoke` сам возвращает состояние «до демо»: `defs/` пустая, история запусков стёрта,
признаки собраны на срез 2018-03-01, и в конце прогоняет `just test`. Ставить заранее
ничего не нужно, сеть на показе не нужна.

## Сценарий

| # | Слайд | Здесь | Что видит зритель |
|---|---|---|---|
| 1 | `uvx create-dagster@latest project ml-platform` → `dg dev` | `just dev` | пустой граф на http://localhost:3000 |
| 2 | три ассета → `defs/ml.py`, Reload, `dg list defs` | `just add-assets`, в UI — Reload | граф из трёх узлов и проверка у `training_dataset` |
| 3 | `dg launch --assets '*'` | `just materialize` или Materialize all в UI | запуск с логом по шагам; на `trained_model` метаданные `roc_auc 0.6049`, `rows 35`, `features 6` |
| 4 | правим `feature_table` → ниже stale | `just new-data` | признаки пересобраны на срез 2018-03-15, пересчитан только `feature_table`; у `training_dataset` пометка устаревшего |
|   | `dg launch --assets 'feature_table+'` | `just downstream` | пересчитано всё ниже; у модели `rows 40`, `roc_auc 0.6225`, на графике метаданных две точки |
| 5 | карточка `training_dataset` → Checks | в UI | проверка `net_propuskov` зелёная, метаданные `propuski 0`, история |

Шаг 1 можно показать вживую: `uvx create-dagster@latest project ml-platform` во временной
папке — ответить `y` на вопрос про `uv sync`. Это минута-две и нужна сеть. Дальше
переходить в готовый `ml-platform/` этой папки: он создан той же командой
(create-dagster 1.13.22), в нём уже стоят pandas, scikit-learn и joblib.

Свежесть (шаг 7 Quick Start) видна на карточке `feature_table`: политика 12 ч → WARN,
24 ч → FAIL. Сразу после материализации она зелёная; дожидаться провала на записи не нужно.

`just status` печатает в терминале то же, что карточки в UI: что устарело, почему,
какие метаданные.

## Где код расходится со слайдами

Проверено на Dagster 1.13.22. Отличия помечены в коде комментарием `≠ слайд`.

- **`feature_table+` — одна ступень, а не «всё ниже».** Голое имя с плюсом Dagster 1.13
  разбирает старым синтаксисом выборки, где `+` — один слой: пересчитаются `feature_table`
  и `training_dataset`, а `trained_model` останется устаревшим. «Всё ниже» в новом
  синтаксисе — `key:feature_table+`, так и сделано в `just downstream`. Так же: `+key:X` —
  всё выше, `key:X+2` — две ступени.
- **Stale ставится только прямому потомку.** После пересчёта `feature_table` устаревшим
  помечен `training_dataset`; `trained_model` получит пометку, когда пересчитается его
  родитель. Фраза «всё ниже помечено устаревшим» для 1.13 неточна.
- **`training_dataset` выбрасывает колонку `split`.** Иначе строка `"train"` попадает в
  признаки, и `LogisticRegression` падает на `could not convert string to float`.
- **`trained_model` создаёт папку `models/`** перед `joblib.dump`.
- **`compute_kind` работает, но это старая форма.** Бейдж в UI рисуется, а селектор
  `kind:pandas` ничего не находит: он смотрит на `kinds={"pandas"}`.

## Тесты

```bash
just test          # 14 тестов
just test -q -k propuski
```

| Файл | Что держит |
|---|---|
| `test_make_features.py` | витрина признаков: колонки, домены `target`/`split`, **нет утечки будущего**, срез реально меняет выборку |
| `test_assets.py` | три ассета и ребро между ними, политика свежести 12/24 ч, проверка `net_propuskov` (зелёная и красная), числа `35 / 0.6049 / 6` |

`just smoke` проверяет ДЕМО — порядок шагов, stale, историю запусков; pytest проверяет КОД
ассетов. Отдельно зафиксированы все расхождения со слайдами из раздела ниже: если Dagster
однажды их устранит, тест упадёт — и поправить надо будет README, а не тест.

Тесты читают канон `stash/ml.py`, а не рабочую копию `defs/ml.py`, и работают во временной
папке: состояние демо они не задевают.

Витрина признаков демо 1 (pandas) и витрина демо 2 (dbt) сверяются между собой — этим
занят `test_vitrina_dbt_sovpadaet_s_vitrinoj_pandas` в демо 2. Поэтому оба демо показывают
одинаковые `rows 35`, `roc_auc 0.6049`, `features 6`.

## Если демо сорвалось

- `dg dev` не поднялся или порт занят — `PORT=3001 just dev`.
- Граф не появился после Reload — `just add-assets` ещё раз и проверить вывод `dg list defs`.
- Всё сломалось — `just reset`, и сценарий с шага 2. Правленый вживую `defs/ml.py` не
  теряется: `reset` откладывает его в `.reset-backup/`.

## Что где лежит

```
data/raw_*.csv          сырьё jaffle shop — канон для всех трёх демо (хардлинки, ../files.yml)
scripts/make_features.py  сырьё → ml-platform/features.parquet (логика как у dbt feature_mart)
scripts/status.py         stale и метаданные в терминале (хардлинк, общий для трёх демо)
stash/ml.py               готовый defs/ml.py: слайды 10–16 одним файлом
ml-platform/              проект от create-dagster: pyproject.toml, uv.lock, src/ml_platform/defs/
ml-platform/tests/        pytest: витрина признаков, ассеты, проверка, расхождения со слайдами
Justfile                  шаги сценария, smoke и тесты
```
