# Agentic backlog

Хвосты сессий, оформленные так, чтобы следующий агент взял задачу с холодного старта.
Пишется скиллом `to-agentic-backlog`. Закрытые записи **не удаляем** — зачёркиваем с датой.

---

## 2026-09-01 · дека Dagster v2.2.0, три live-demo, сабмодуль практики

### Снять триптих Airflow 2 / Airflow 3 / Dagster

- **Зачем:** слайд про сравнение трёх продуктов стоит без картинки, ради которой задуман;
  сейчас держится на диаграмме и подстрочнике. Это последний незакрытый слот деки.
- **Где:** слайд `049-odin-pajplajn-tri-interfeysa` в `content/preza-dagster-v2-content.yml`;
  слот `wanted` в `content/preza-dagster-v2-images.yml`; в подвале слайда висит жёлтая
  🔍-ссылка.
- **Контекст:** нужен **один склеенный кадр 3:1** из скриншотов **одного и того же
  логического пайплайна** (загрузка → преобразования → обучение → оценка → регистрация)
  в трёх интерфейсах. Dagster-половину снять несложно — рабочий проект лежит в сабмодуле
  `data/code/dagster_demo` (`just reset && just dev`). Airflow 2 и Airflow 3 требуют двух
  поднятых контуров; отсюда их поднять было нечем, поэтому слот и остался.
  Требования к кадрам — в `data/code/dagster_demo/docs/RUNBOOK.md`, раздел
  «Airflow: почему живого демо нет»: одинаковый масштаб, одинаковая ширина окна, подпись
  под каждым кадром, не подкрашивать левый в красный, а правый в зелёный.
- **Как проверить:**
  ```bash
  uv run python scripts/preza/images_manifest.py check content/preza-dagster-v2-content.yml
  PYTHONPATH=src uv run python .tmp/fit_check.py content/preza-dagster-v2-content.yml
  ```
- **Готово, когда:** в реестре нет записей `wanted`, `fit_check` даёт 0 замечаний,
  на собранном слайде 049 стоит триптих.
- **Блокирует:** ничего, но нужны два поднятых Airflow — вероятно, задача для машины
  с Docker, а не для этой.

### Решить, переносить ли mlinside-dagster-demo под hnkovr

- **Зачем:** остальные сабмодули курса лежат под `hnkovr`, а новый — под `dataengy`.
  Разнобой во владельце усложняет выдачу доступов студентам.
- **Где:** https://github.com/dataengy/mlinside-dagster-demo; запись в `.gitmodules`,
  секция `[submodule "data/code/dagster_demo"]`.
- **Контекст:** репозиторий создан под `dataengy`, потому что `gh` авторизован этим
  аккаунтом и на `hnkovr` выдаёт `GraphQL: dataengy cannot create a repository for hnkovr`.
  Репозиторий публичный, как и `hnkovr/mlinside-hw-olist`.
- **Как проверить:** после переноса `git submodule sync && git submodule update --init
  data/code/dagster_demo` отрабатывает без ошибок.
- **Готово, когда:** url в `.gitmodules` совпадает с фактическим владельцем.
- **Блокирует:** **человек** — перенос делается в Settings → Transfer ownership, агент
  этого сделать не может и не должен.

### Починить `just preza-validate`

- **Зачем:** гейт схемы деки не запускается вообще — валидация перед сборкой сейчас
  не выполняется ни для одной деки, ошибки в контент-YAML ловятся только на рендере.
- **Где:** `Justfile`, переменная `_preza_skill` →
  `~/.ai/skills/_catalog/docs/pptx/create-preza-about-de-tool/scripts`. Каталога нет.
  Тем же путём сломаны `preza-validate-all`, `preza-review`, `preza-review-all`,
  `preza-stamp`, `preza-slug`.
- **Контекст:** скрипты внешнего каталога скиллов не установлены на этой машине.
  Проверено: `ls` по пути даёт `No such file or directory`. Обойдено вручную —
  акценты сверялись грепом по тексту слайдов, провенанс правился руками.
  Варианта два: восстановить внешний каталог либо перенести скрипты в репозиторий
  (`scripts/preza/`), где живут остальные.
- **Как проверить:**
  ```bash
  just preza-validate content/preza-dagster-v2-content.yml
  just preza-review   content/preza-dagster-v2-content.yml
  ```
- **Готово, когда:** обе команды отрабатывают и `preza-review` подтверждает, что все
  четыре акцента лекции Dagster закрыты.
- **Блокирует:** ничего.

### Дописать ML-часть в ДЗ-2 или явно развести её с демо

- **Зачем:** дека обещает сквозной путь до `registered_model`, а ДЗ-2 доводит студента
  только до витрины: обучения, оценки и реестра моделей в нём нет. Студент не сможет
  повторить то, что видел в DEMO 3.
- **Где:** сабмодуль `homework/mlinside-hw-olist`, каталог
  `orchestration/src/olist_orchestration/assets/` — там только `dbt.py` и `raw.py`;
  спека `docs/HW2-dagster.md`.
- **Контекст:** эталон ML-части уже написан и работает в
  `data/code/dagster_demo/src/dagster_demo/defs/ml.py` (обучение → оценка → регистрация
  в MLflow на локальном SQLite, шлюз качества через `dg.Failure`). Колонки в демо
  специально названы как в Olist (`freight_ratio`, `distance_km`, `n_items`,
  `seller_delay_d`), так что перенос механический. Решение, делать ли это частью ДЗ,
  за автором курса: возможно, ML-часть намеренно оставлена лекции.
- **Как проверить:** в сабмодуле ДЗ `dagster asset list` показывает ассеты обучения
  и регистрации; спека `HW2-dagster.md` описывает критерии их приёмки.
- **Готово, когда:** либо ML-часть есть в ДЗ, либо в `HW2-dagster.md` написано явно,
  что она в задание не входит и почему.
- **Блокирует:** **человек** — это решение о содержании курса.

### Разобраться с `.tmp/render-pdf/`

- **Зачем:** единственное, что осталось untracked в рабочем дереве; мешает чистому сносу
  worktree, и никто из сессий не признал файлы своими.
- **Где:** `.tmp/render-pdf/` в корне репозитория, PNG-рендеры страниц от 00:36.
- **Контекст:** каталог был untracked ещё до начала этой сессии. Соседняя сессия сказала,
  что файлы её и что их можно терять, но подтверждения от человека не было.
  Сессия, готовящая снос, предлагала вынести их в `/Users/user/gi/@dataengy/.recyclebin/`
  вместо удаления.
- **Как проверить:** `git status --porcelain` в корне пуст.
- **Готово, когда:** каталог либо закоммичен, либо перенесён в `.recyclebin/`, либо удалён
  осознанно.
- **Блокирует:** **человек** — решение, нужны ли эти рендеры.

### Перепроверить кадр `pic-dagster-stale-graph.png`

- **Зачем:** кадр иллюстрирует «изменился ассет наверху — устарело всё, что ниже», но на нём
  `Unsynced` помечены **все три** узла, включая сам изменённый. Формально это верное
  поведение Dagster, но слайд про downstream, и кадр читается слабее, чем мог бы.
- **Где:** `data/source/media/pic-dagster-stale-graph.png`, слайд
  `923-a14-shag-7-selective-recomputation`.
- **Контекст:** кадр снят после смены `code_version` у `feature_table`, поэтому узел
  устарел и сам. Чтобы получить «свежий верх, устаревший низ», надо менять не код витрины,
  а код `training_dataset` — либо материализовать `feature_table` заново перед съёмкой.
  Проект для пересъёмки: `data/code/dagster_demo`, `just reset && just dev`.
- **Как проверить:** на новом кадре у верхнего узла нет плашки `Unsynced`, у двух нижних —
  есть.
- **Готово, когда:** кадр заменён, реестр пересинхронизирован, `fit_check` даёт 0 замечаний.
- **Блокирует:** ничего. Приоритет низкий — текущий кадр не врёт, просто менее нагляден.

## 2026-09-04 · дека Dagster -simple: 50 слайдов, код и схемы, только Airflow 3 + Cosmos

### Откалибровать модель вписывания код-панели в `preza_gen`

- **Зачем:** `_fit_code_size` считает, что строка в 79 символов влезает в правую колонку
  5.95in при 13pt; в LibreOffice и PowerPoint такая строка переносится уже с ~57–60
  символов. Генератор выбирает крупный кегль, панель рвётся, а проверка «overflow: нет»
  врёт. Обходится только руками — ≤48 символов в строке (так собрана дека -simple).
- **Где:** `src/preza_gen/renderers/pptx.py` — `_visual_lines`, `_code_height`,
  `_fit_code_size`. Это сабмодуль `src/preza_gen` (ветка `feat/image-full`), правка едет
  в его репозиторий.
- **Контекст:** замечено 2026-09-04 на `content/preza-dagster-simple-content.yml`: панели
  60–80 символов рвались на кадрах PDF при 13pt, после реформата до ≤48 — чисто. Причина не
  установлена: либо ширина символа в модели занижена, либо не вычитаются внутренние поля
  панели, либо Consolas на macOS подменяется более широким шрифтом (в PowerPoint с Consolas
  перенос наступит позже, но тоже раньше 79). Кадры снимать через pymupdf — Poppler на
  машине нет.
- **Как проверить:**
  ```bash
  PYTHONPATH=src .venv/bin/python -c "from preza_gen.renderers import pptx as R; \
    print(R._fit_code_size('x'*70, R.ImageBox(0, 0, 5.95, 4.8), {'size': 13, 'min_size': 9}))"
  # сейчас печатает 13.0; после калибровки — кегль, при котором кадр PDF не переносит строку
  ```
- **Готово, когда:** для строки в 70 символов модель даёт кегль без переноса на кадре PDF;
  деки v2 и -simple пересобираются без визуальных изменений.
- **Блокирует:** ничего.

### Решить, заводить ли деку -simple в `content/presentations.yml`

- **Зачем:** дека собрана как черновик под ручную вставку в целевую презентацию и намеренно
  не в плане: publish-хук её не видит, `preza-review-all` не проверяет. Если она станет
  самостоятельной лекцией, ей нужны запись в плане и акценты.
- **Где:** `content/presentations.yml`; дека `content/preza-dagster-simple-content.yml`,
  рецепт `just dagster-simple-build`.
- **Контекст:** сборка v1.0.0 лежит в `.tmp/build/` и `~/Downloads/_MLInside.2026-08/`;
  статус «в план не заводить» записан в шапке YAML.
- **Как проверить:** `grep -n dagster-simple content/presentations.yml`.
- **Готово, когда:** либо запись в плане есть и `just preza-review
  content/preza-dagster-simple-content.yml` проходит, либо решение «черновик» подтверждено
  и запись не нужна.
- **Блокирует:** **человек** — статус деки.

### Дать `.tmp/render_pdf_pages.py` запасной путь без Poppler

- **Зачем:** скрипт падает с `pdftoppm is required`, Poppler на машине нет; кадры для
  проверки вёрстки снимались одноразовым скриптом через `uv run --with pymupdf`.
- **Где:** `.tmp/render_pdf_pages.py`; рецепт `render-pdf` в `.tmp/Justfile` вызывает
  системный `python3`, у которого нет pyyaml, — тот же дефект, что у `lint-scalars`.
- **Контекст:** рабочая замена — `uv run --no-project --with pymupdf python`,
  `pymupdf.open(pdf)[n].get_pixmap(dpi=110).save(path)`.
- **Как проверить:** `just -f .tmp/Justfile render-pdf .tmp/build/<дека>.pdf 5` создаёт
  PNG на машине без `pdftoppm`.
- **Готово, когда:** команда выше отрабатывает без Poppler.
- **Блокирует:** ничего.

### Сверить слайды 039 и 042 деки -simple с актуальными Airflow и Cosmos перед записью

- **Зачем:** код `@asset` из `airflow.sdk` и `DbtDag` Cosmos сверены 2026-09-04 по пакетам
  apache-airflow-task-sdk 1.3.1 и astronomer-cosmos 1.15.1; обе библиотеки выпускают
  минорные версии раз в несколько месяцев, к записи сигнатуры могут уехать.
- **Где:** слайды `039-airflow-3-asset-i-planirovanie-po-assetam` и
  `042-cosmos-dbt-proekt-kak-dag-airflow` в `content/preza-dagster-simple-content.yml`.
- **Как проверить:**
  ```bash
  uv run --no-project --with apache-airflow-task-sdk python -c \
    "import inspect; from airflow.sdk import asset; print(inspect.signature(asset))"
  uv run --no-project --with astronomer-cosmos --with 'apache-airflow>=3' python -c \
    "import inspect; from cosmos import RenderConfig, ProjectConfig; \
     print(inspect.signature(RenderConfig)); print(inspect.signature(ProjectConfig))"
  ```
- **Готово, когда:** все параметры со слайдов есть в выводе обеих команд.
- **Блокирует:** ничего. Приоритет низкий — делать перед датой записи.
