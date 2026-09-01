---
name: ui-screenshots-for-decks
description: 'Снять скриншоты живого интерфейса (Dagster, dbt docs, MLflow, Airflow, Superset) для слайдов деки MLInside и правильно завести их в репозиторий — кадрирование под макет, имена pic-<инструмент>-<что>.png, реестр content/<deck>-images.yml (wanted → placed с origin/note), проверка вёрстки. Триггеры: "сними скриншоты UI для деки", "нужны кадры для screenshot fallback", "слот wanted в реестре картинок", "поставь картинку на слайд приложения", "capture Dagster UI for the deck".'
---

Снять кадр живого интерфейса и довести его до слайда так, чтобы следующий проход расстановки
картинок не переиграл решение. Движок браузера поднимает `browser-automation-setup`.

## Порядок

1. **Поднять то, что снимаем** — локально, с данными и историей. Пустой интерфейс
   бесполезен: на кадре должны быть материализации, статусы, метрики.
2. **Разведка** — один пробный кадр, прочитать глазами, потом писать съёмку.
3. **Съёмка** — по кадру на слот.
4. **Кадрирование** — обрезать до содержательного прямоугольника.
5. **В репозиторий** — файл в `data/source/media/`, `image:` на слайд, реестр.
6. **Проверки** — вёрстка и сборка.

## Что снимать

Кадр отвечает на вопрос слайда, а не показывает «программу вообще». Хорошие кадры несут
**состояние**: зелёные узлы после материализации, `Unsynced` после правки upstream, метрику
в метаданных, проверку 1/1 Passed. Плохие — пустой граф и меню.

Готовить состояние заранее: несколько материализаций подряд (чтобы была история и график
метрики), правка `code_version` (чтобы получить устаревшие узлы), сломанные данные
(чтобы проверка покраснела).

## Съёмка

```python
pg = await b.new_page(viewport={"width": 1680, "height": 1000}, device_scale_factor=2)
```

`device_scale_factor=2` обязателен — иначе на проекторе текст в кадре мылится.

Кадрировать по элементу, а не по окну:

```python
el = await pg.query_selector("[data-testid='asset-graph']")
await el.screenshot(path=out)                      # только нужный прямоугольник
```

Если элемент не выделяется — снять область: `pg.screenshot(clip={"x":…, "y":…, "width":…, "height":…})`.

В кадре не должно быть: чужих вкладок, путей с именем пользователя, тулбаров браузера,
пустого места по краям.

## Имена

`pic-<инструмент>-<что-на-кадре>.png`, латиницей, через дефис:

```
pic-dagster-asset-graph.png       граф из трёх узлов со статусами
pic-dagster-run-log.png           страница запуска: сколько ассетов, проверок, секунд
pic-dagster-asset-metadata.png    метаданные материализации
pic-dagster-stale-graph.png       устаревшие узлы после правки upstream
pic-dagster-mlflow-link.png       связка метаданных Dagster и прогона MLflow
```

## Постановка на слайд

`image:` ставится **перед** `bullets:` в блоке слайда. Картинка идёт справа, схема/код —
слева, буллетов оставить 2–3 и укоротить: длинные буллеты налезают на картинку.

Убрать жёлтый 🔍-слот, который картинку заказывал, — иначе в подвале останется просьба
снять уже снятое:

```yaml
- kind: content
  id: 921-a14-shag-5-asset-graph
  title: 'Шаг 5: посмотреть asset graph'
  image: pic-dagster-asset-graph.png      # ← добавили
  bullets:
  - Граф — карта того, что существует, а не картинка запуска
  materials:                               # ← 🔍-элемент отсюда удалили
```

## Реестр — обязательный шаг

Без него следующий проход расстановки сочтёт файл неиспользованным и разложит картинки сам.

```bash
uv run python scripts/preza/images_manifest.py sync content/<deck>-content.yml
uv run python scripts/preza/images_manifest.py check content/<deck>-content.yml   # «совпадает»
```

`sync` переведёт слот `wanted` → `placed`. Дальше руками проставить происхождение:

```yaml
- file: pic-dagster-asset-graph.png
  origin:
    kind: local
    source: 'одноразовый проект Dagster (uvx create-dagster), снят Playwright с localhost'
    url: null
  note: 'снят с локального демо-проекта: три ассета материализованы, проверки 1/1'
```

**Значения с `: ` обязаны быть в кавычках** — двоеточие с пробелом ломает YAML. Та же
ловушка в `label:` у `materials`.

Состояния реестра: `placed` · `manual-removed` (снято руками — не возвращать) ·
`manual-moved` · `spare` (файл есть, на слайдах нет) · `wanted` (кадра ещё нет).

Кадр, чьё происхождение подтвердить не можешь (появился в дереве не от тебя), — сохранить
как `spare` и сказать пользователю. Не ставить на слайд молча.

## Проверки после

```bash
PYTHONPATH=src uv run python .tmp/fit_check.py content/<deck>-content.yml     # 0 замечаний
PYTHONPATH=src uv run python -m preza_gen.build_deck --pptx --html \
  --settings content/build_deck_v3-settings.yml --content content/<deck>-content.yml
soffice --headless --convert-to pdf --outdir /tmp/qa data/generated/<DECK>.pptx
uv run --with pymupdf python .tmp/pdf_overflow_check.py /tmp/qa/<DECK>.pdf     # 0 замечаний
```

И посмотреть глазами хотя бы одну готовую страницу — рендер в PNG через pymupdf
(`page.get_pixmap(dpi=110).save(...)`), затем `Read`. Автопроверки не ловят «картинка
не о том».

## Коммитить порциями

Скриншот — **не артефакт**: пересобрать его нечем, а до коммита он untracked и исчезает
без следа при `git worktree remove`. Коммитить по мере съёмки, а не пакетом в конце.
