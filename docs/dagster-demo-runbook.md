# Живые демо лекции про Dagster — где что лежит

Практика лекции вынесена в отдельный репозиторий и подключена сюда сабмодулем:

| Что | Где |
|---|---|
| Демо-проект (код, dbt, данные) | `data/code/dagster_demo/` → [dataengy/mlinside-dagster-demo](https://github.com/dataengy/mlinside-dagster-demo) |
| **Сценарий показа (runbook)** | `data/code/dagster_demo/docs/RUNBOOK.md` |
| Домашнее задание | `homework/mlinside-hw-olist/` → [hnkovr/mlinside-hw-olist](https://github.com/hnkovr/mlinside-hw-olist), спека `docs/HW2-dagster.md` |
| Дека | `content/preza-dagster-v2-content.yml`, демо-слайды `017`, `026`, `042` |

Этот файл — только указатель. **Сценарий не дублируется**: он живёт рядом с кодом, который
описывает, иначе разъедется при первой же правке проекта.

## Быстрый старт

```bash
git submodule update --init data/code/dagster_demo
cd data/code/dagster_demo
uv sync
just reset      # состояние «до демо»: данные на месте, ничего не материализовано
just smoke      # прогон всего графа — обязан закончиться RUN_SUCCESS
just reset      # smoke оставляет граф материализованным, сбрасываем обратно
just dev        # → http://localhost:3111
```

## Что показывают три демо

```
DEMO 1 (слайд 017, ~6 мин)    feature_table → training_dataset_qs → trained_model_qs
DEMO 2 (слайд 026, ~9 мин)    raw_orders/raw_items → stg_* → int_order_features
                              → feature_mart          ← главное демо лекции
DEMO 3 (слайд 042, ~6.5 мин)  feature_mart → training_dataset → trained_model
                              → evaluation → registered_model
```

Принцип: **не демонстрировать набор текста — демонстрировать изменение состояния системы
и семантику графа.** Весь код написан заранее.

## Если демо сорвалось

В деке есть screenshot fallback — приложение **A14** (DEMO 1), **A15** (DEMO 2),
**A16** (DEMO 3). Уходить туда сразу, не чинить на камере. Кадры A14 сняты с этого же
проекта и лежат в `data/source/media/pic-dagster-*.png`.

Ещё не сняты (слоты `wanted` в `content/preza-dagster-v2-images.yml`): сквозной dbt-граф
(927), dbt-тесты как asset checks (929), MLflow в метаданных (931) и триптих
Airflow 2 / Airflow 3 / Dagster (049).
