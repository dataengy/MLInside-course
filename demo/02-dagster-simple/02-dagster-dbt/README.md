# Демо 2 · Dagster + dbt — уровни 0 → 1 → 2 → 3

Слайды **18–27** упрощённой деки «Оркестрация ML-пайплайнов на Dagster», около 10 минут.
Демо ровно по уровням интеграции со слайда 19: `dbt` из чёрного ящика становится
частью сквозного графа от загрузки до обученной модели.

Данные — [jaffle shop](https://github.com/dbt-labs/jaffle_shop_duckdb), склад — один файл
DuckDB. dbt-проект рядом: [`analytics_dbt/`](analytics_dbt/README.md).

```
raw_customers ─→ stg_customers ─┐
raw_orders    ─→ stg_orders    ─┼→ customers ─┐
raw_payments  ─→ stg_payments  ─┴→ orders ────┴→ feature_mart ─→ training_dataset ─→ trained_model
   ассеты          dbt-модели                       СТЫК            (sklearn, проверка net_propuskov)
  загрузки                                     dbt → ML
```

## Перед записью

```bash
just setup    # uv sync + состояние «до демо»
just smoke    # весь сценарий без браузера; должен закончиться «SMOKE OK»
```

`just smoke` сам возвращает состояние «до демо» и прогоняет pytest. Ставить заранее
ничего не нужно, сеть на показе не нужна.

Состояние «до демо»: в `defs/` только `resources.py` и `raw.py` — в графе **три ассета
загрузки и больше ничего**. dbt-проект существует на диске, но Dagster про него не знает.
Это и есть картинка с левой половины слайда 18: dbt живёт сам по себе.

## Сценарий

| # | Слайд | Здесь | Что видит зритель |
|---|---|---|---|
| 1 | 18 · тезис | `just dev` | граф из трёх узлов загрузки на http://localhost:3000; dbt не видно |
| 2 | 20 · Level 0 | `just level-0`, Reload | **один** узел `dbt_project_build` за которым весь проект; `just materialize` — зелёный, но внутри ничего не разглядеть |
| 3 | 21–23 · Level 1 | `just level-1`, Reload | чёрный ящик распался на **6 моделей**; на карточках сразу появились **26 dbt-тестов** как проверки; источники `jaffle_raw/raw_*` висят **без родителей** |
| 4 | 25 · Level 2, сшивка | `just stitch`, Reload | добавили `meta.dagster.asset_key` — узлы источников исчезли, появились рёбра `raw_orders → stg_orders`; граф стал **связным** |
| 5 | 25 · Level 2, низ | `just level-2-ml`, Reload | ниже `feature_mart` встали `training_dataset` и `trained_model`; граф идёт от CSV до модели |
|   | 26–27 · Level 3 | `just materialize` | `roc_auc 0.6049`, `rows 35`, `features 6`; 27 проверок зелёные |
|   | частичный пересчёт | `just downstream` | `key:feature_mart+` — dbt пересобирает только витрину, дальше идёт обучение; загрузка не трогается |

Шаг 4 — центральный. До него полезно вслух спросить: «что здесь не так?» — и показать,
что в графе **два куска**, потому что Dagster не знает, кто делает `raw.raw_orders`.

`just graph` печатает рёбра и проверки в терминале: то же, что видно в UI, но без браузера.
`just status` — что устарело и какие метаданные.

## Где код расходится со слайдами

Проверено на Dagster 1.13.22, dagster-dbt 0.29.22, dbt-core 1.12.4, dbt-duckdb 1.11.0.
Отличия помечены в коде комментарием `≠ слайд`.

- **`project_dir` считается от папки демо, а не от `ml-platform`.** На слайде 21
  `project_dir=ROOT / "analytics_dbt"` — проект dbt лежал бы ВНУТРИ проекта Dagster.
  Здесь они рядом, как в коде слайда 20 (`project_dir="../analytics_dbt"`).
- **Имена источника и таблицы другие.** На слайде 25 — `olist_raw` / `orders`,
  здесь — `jaffle_raw` / `raw_orders`. Ключ ассета в обоих случаях `raw_orders`:
  сшивка идёт **по ключу**, имя таблицы в складе к ней отношения не имеет.
- **`key=` и `name=` вместе Dagster не принимает.** Ключ ассета загрузки задаёт только
  `key=dg.AssetKey([...])`, как на слайде; имя Dagster выводит из ключа сам.
- **Уровень 3 приезжает вместе с уровнем 1.** Слайд 26 подан отдельным шагом, но
  dbt-тесты становятся asset checks в тот момент, когда `@dbt_assets` разворачивает
  манифест, — потому что `dbt.cli(["build"])`, а не `run`. Отдельного действия нет.
- **Манифест обязателен ДО импорта.** `prepare_if_dev()` работает только под `dg dev`;
  для `dg launch` и pytest манифест собирает `just _parse` (`dbt parse`). Это ровно то
  правило со слайда 21: манифест — артефакт сборки.

## Две ловушки, на которых демо падало

**1. DuckDB пускает в файл только одного писателя.** Исполнитель Dagster по умолчанию
многопроцессный, три ассета загрузки независимы — значит идут параллельно и ловят

```
IO Error: Could not set lock on file ... Conflicting lock is held ... (PID ...)
```

Лечится объявлением пула: `pool="duckdb"` у всех, кто трогает файл, и лимит в
`.dagster_home/dagster.yaml`. **Гранулярность обязана быть `op`:**

```yaml
concurrency:
  pools:
    granularity: op      # ← НЕ run
    default_limit: 1
```

`granularity: run` читается как «по одному за раз», но ограничивает число
**одновременных запусков** на пул: внутри одного запуска шаги по-прежнему идут
параллельно, и блокировка возвращается. На нормальном складе (Postgres, Snowflake)
пул не нужен — это цена DuckDB.

**2. Типы сырья — ответственность загрузчика.** В оригинальном jaffle shop `raw_orders`
был seed, и тип даты выводил dbt. Здесь таблицу пишем мы, а CSV типов не несёт: без
явного разбора `order_date` ложится в склад строкой, и падает не загрузка, а модель
тремя уровнями ниже:

```
Binder Error: Cannot compare values of type VARCHAR and type DATE
  LINE 45: where order_date < date '2018-03-01'
```

Обе ловушки закрыты тестами (`tests/test_pool.py`, `tests/test_raw_load.py`) — чтобы
следующая правка не вернула их молча.

Ещё мелочь: dbt на каждой команде проверяет свою версию на pypi. Без сети соединение
отбивается сразу, демо это не замедляет; анонимную телеметрию мы выключили в
`dbt_project.yml` (`flags.send_anonymous_usage_stats: false`).

## Тесты

```bash
just test          # 37 тестов
just test -q -k stitch
```

| Файл | Что держит |
|---|---|
| `test_raw_load.py` | строки и **типы** сырья; регрессия на `order_date` строкой |
| `test_sources_stitch.py` | ключи в `_sources.yml` и в `defs/raw.py` **совпадают**; сшивка меняет только `meta` |
| `test_dbt_project.py` | 6 моделей, 26 тестов, родители `feature_mart`, раскладка по папкам, `cutoff_date` |
| `test_feature_mart.py` | одна строка на клиента, домены `target`/`split`, **нет утечки будущего**, и кросс-тест с демо 1 |
| `test_ml_assets.py` | `deps=[AssetKey("feature_mart")]`, числа `35 / 0.6049 / 6`, `customer_id` не признак |
| `test_pool.py` | пул `duckdb` объявлен везде, гранулярность `op` |
| `test_files_registry.py` | сырьё и `status.py` одинаковы во всех демо (`../files.yml`) |

Самый полезный из них — `test_klyuchi_sshivki_sovpadayut_s_assetami_zagruzki`: переименуют
ассет загрузки — граф не упадёт и dbt не пожалуется, источник просто молча повиснет
отдельным узлом, и демо покажет ровно то, что собиралось опровергнуть.

Второй по полезности — `test_vitrina_dbt_sovpadaet_s_vitrinoj_pandas`: витрина признаков
считается дважды, на SQL в демо 2 и на pandas в демо 1, и результаты обязаны совпасть.
Поэтому оба демо показывают одинаковые `rows 35`, `roc_auc 0.6049`, `features 6`.

Тесты работают в своём временном файле DuckDB и проверяют **канон из `stash/`**:
состояние демо и рабочие копии в `defs/` они не задевают.

## Если демо сорвалось

- `dg dev` не поднялся или порт занят — `PORT=3001 just dev`.
- Граф не изменился после Reload — повторить шаг и проверить вывод `dg list defs`;
  после `just stitch` манифест пересобирается сам (`just _parse` внутри рецепта).
- `@dbt_assets` не импортируется («manifest not found») — `just _parse`.
- Блокировка DuckDB — проверить, что не висит `dg dev` из другой сессии, и что
  `.dagster_home/dagster.yaml` содержит `granularity: op`.
- Всё сломалось — `just reset`, и сценарий с шага 2. Правленые вживую файлы шагов
  не теряются: `reset` откладывает их в `.reset-backup/`.

## Что где лежит

```
data/raw_*.csv              сырьё jaffle shop — канон общий с демо 1 (хардлинки, ../files.yml)
scripts/status.py           stale и метаданные в терминале (хардлинк, общий с демо 1)
scripts/graph.py            рёбра графа и проверки — чем сшито, что висит без родителя
analytics_dbt/              dbt-проект: 6 моделей, 26 тестов, feature_mart (свой README)
stash/level0.py             уровень 0: весь dbt одним ассетом
stash/analytics_dbt.py      уровень 1: @dbt_assets поверх манифеста
stash/ml.py                 уровень 2, низ: training_dataset + trained_model + проверка
stash/_sources.plain.yml    источники ДО сшивки — из него `just reset` возвращает канон
stash/_sources.stitched.yml источники ПОСЛЕ сшивки: отличие ровно в meta.dagster.asset_key
ml-platform/                проект от create-dagster; project.py + defs/{resources,raw}.py под гитом
Justfile                    шаги сценария, smoke и тесты
```
