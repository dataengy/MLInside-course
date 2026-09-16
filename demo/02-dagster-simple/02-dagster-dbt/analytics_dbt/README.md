# analytics_dbt — jaffle shop под демо Dagster

Классический jaffle shop на DuckDB — [dbt-labs/jaffle_shop_duckdb](https://github.com/dbt-labs/jaffle_shop_duckdb),
ветка `duckdb`, коммит `36bde6c` (2026-03-02), лицензия Apache-2.0 (`LICENSE` рядом).
Папка названа `analytics_dbt`, как на слайдах лекции; имя dbt-проекта осталось `jaffle_shop`.

Один и тот же проект используют демо 2 и демо 3. Почти все файлы — **хардлинки**,
реестр — `../../files.yml`. Правка в одной папке сразу видна в другой.

## Что изменено относительно оригинала

| Что | Было | Стало | Зачем |
|---|---|---|---|
| Сырьё | seeds `raw_*` | источник `jaffle_raw` (схема `raw`) | таблицы грузит Dagster: ассетами (демо 2) или через dlt (демо 3) |
| staging | `ref('raw_*')` | `source('jaffle_raw', 'raw_*')` | чтобы у источника был ключ ассета загрузки |
| Витрины | `models/*.sql` | `models/marts/*.sql` | выборка `fqn:marts.*` со слайдов |
| Новая модель | — | `marts/feature_mart.sql` | витрина признаков — стык dbt и ML |
| `profiles.yml` | `path: jaffle_shop.duckdb` | `DUCKDB_PATH` из окружения | один файл DuckDB на демо, путь задаёт Dagster |
| Тесты | `schema.yml` ×2 | `_staging.yml`, `_marts.yml` | содержимое то же, плюс тесты `feature_mart` |

SQL моделей `customers`, `orders` и staging-моделей в остальном дословный.

## Граф

```
raw_customers → stg_customers ─┐
raw_orders    → stg_orders    ─┼→ customers ─┐
raw_payments  → stg_payments  ─┴→ orders ────┴→ feature_mart
```

`customers` читает все три staging-модели, `orders` — `stg_orders` и `stg_payments`.

`feature_mart`: одна строка на клиента. Признаки считаются по заказам до даты среза
`var('cutoff_date')` (по умолчанию `2018-03-01`), цель `target` — был ли заказ после неё.
Каждый пятый клиент уходит в тест (`split`). Задача игрушечная, но утечки будущего в ней нет.

## Руками, без Dagster

```bash
# из этой папки; сырьё должно уже лежать в raw.* (его грузят ассеты Dagster)
DUCKDB_PATH=../jaffle_shop.duckdb dbt build --profiles-dir .
```
