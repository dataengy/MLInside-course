Доработай текущую презентацию. Контекст проекта и исходная презентация уже находятся в активной сессии — не пересоздавай презентацию с нуля и не проси меня повторно присылать материалы.
+ в том числе
  * код по возможности перепиши для OLIST (если это не портит пример – иначе оставь)
  * попробуй внедрить подсветку синтаксиса
  * если лимита слайдов недостаточно, то можешь добавлять слайды сверх него – лимит не приоритет, приоритет – полное покрытие материалы и не перегруженные слайды
  * если где-то уместно добавить картинки/схемы/скриншоты, то добавь ссылку для поиска такой картинки на слайд в колонтитулы, подсветив жёлтым эту ссылку

ЦЕЛЬ

Перефокусируй лекцию с «обзора возможностей dbt» на:

«dbt как ключевой инструмент full-stack data specialist: как превратить слой подготовки данных и ML-признаков из набора ad-hoc Python/pandas-скриптов в production-grade, тестируемую, документированную и оркестрируемую часть data/ML platform».

Аудитория по-прежнему — ML Engineers / MLOps engineers, но главный framing теперь шире: full-stack data specialist.

Целевая продолжительность лекции: 1:30–1:45.
Ориентир по объёму: примерно 55–60 слайдов. Не надо искусственно держаться за 50–55, если это ухудшает повествование.

ДЗ И OLIST

1. Полностью убери из презентации домашнее задание:
   - формулировку ДЗ;
   - требования к сдаче;
   - чек-листы ДЗ;
   - всё, что выглядит как assignment/homework.

2. Olist НЕ убирай.
   Преврати Olist из домашнего задания в сквозной production ML example.

Используй примерно такую цепочку:

raw:
- orders
- order_items
- sellers
- при необходимости customers/products/geolocation

→ sources

→ stg_orders
→ stg_order_items
→ stg_sellers
→ ...

→ int_order_level

→ mart_delivery_features

→ training dataset

→ train model

→ model registry

→ inference

Целевая ML-задача может остаться связанной с delivery time / delayed delivery prediction.

==================================================
1. НОВЫЙ FRAMING: FULL-STACK DATA SPECIALIST
==================================================

В начале лекции добавь/переделай несколько слайдов, объясняющих изменение роли современного data/ML специалиста.

Нужно донести:

- Исторически обязанности разделились между:
  DevOps / Platform Engineer
  Data Engineer
  Analytics Engineer
  Data Analyst / BI Engineer
  ML Engineer
  MLOps Engineer

- Это разделение по-прежнему необходимо в крупных и сложных системах.

- Но LLM-assisted и agentic-driven development резко снижают стоимость работы специалиста через несколько слоёв стека.

- Поэтому возрастает ценность full-stack data specialist, который понимает весь путь:

  source
  → ingestion
  → storage
  → transformations
  → quality
  → analytics
  → features
  → training
  → orchestration
  → deployment
  → monitoring

- В некоторых небольших/средних проектах один сильный специалист с AI-assisted tooling сможет закрывать значительную часть функций, которые раньше требовали нескольких отдельных специалистов:
  DevOps + DE + AE + DA/BIE + MLE.

ВАЖНО:
не утверждай, что LLM «отменят» эти профессии или что один человек всегда заменит команду.

Правильный тезис:
LLM/agents уменьшают стоимость переключения между слоями и повышают leverage сильного generalist/full-stack специалиста; на масштабе и для сложных систем глубокие специализации сохраняют ценность.

Свяжи это с dbt:

dbt — один из инструментов, позволяющих одному специалисту управлять data transformation layer инженерным способом:
- version control;
- modularity;
- testing;
- documentation;
- lineage;
- incremental processing;
- CI;
- orchestration integration.

Добавь визуальный слайд примерно:

            FULL-STACK DATA SPECIALIST

 Infra       Data         Analytics       ML
   ↓           ↓              ↓            ↓

DevOps → DE → AE → DA/BIE → MLE/MLOps

               ↑
         AI / LLM / Agents
   снижают стоимость переключения
        между слоями стека

Не перегружай его текстом.

==================================================
2. ANALYTICS ENGINEERING: ПОЧЕМУ ОНО ПОЯВИЛОСЬ
==================================================

Усиль историю возникновения Analytics Engineering.

Нужно объяснить не столько историю компании dbt Labs, сколько инженерную причину появления специализации:

- ELT + cloud DWH;
- compute переместился ближе к warehouse;
- аналитики стали писать всё больше production SQL;
- Data Engineers не должны становиться bottleneck для каждой новой витрины;
- возникла необходимость применять software engineering practices к SQL transformations;
- Git;
- modular models;
- testing;
- documentation;
- CI;
- lineage;
- ownership.

Покажи эволюцию:

ETL:
source → Python/Spark/ETL engine → warehouse

ELT:
source → warehouse → SQL transformations

Analytics Engineering:
ELT + software engineering practices.

После этого свяжи с современной full-stack ролью:
MLE сегодня сталкивается с очень похожей проблемой при подготовке training datasets/features.

==================================================
3. PYTHON VS SQL — ГЛАВНЫЙ ИНЖЕНЕРНЫЙ ПРИНЦИП
==================================================

Очень явно сформулируй:

«Табличные, детерминированные и массовые преобразования данных, которые естественно выполняются рядом с данными, выносим из ad-hoc pandas/Python-кода в версионируемые SQL-модели dbt.

Python остаётся там, где он действительно нужен:
- training;
- ML libraries;
- специальные алгоритмы;
- transformations, плохо выражаемые SQL;
- внешние API / сложная procedural logic».

Добавь comparison slide:

ad-hoc Python/pandas
vs
dbt SQL model

Сравни:
- reproducibility;
- execution near data;
- code review;
- lineage;
- tests;
- docs;
- incremental processing;
- orchestration;
- observability/debuggability.

Не утверждай «SQL всегда лучше Python».

==================================================
4. СКВОЗНАЯ АРХИТЕКТУРНАЯ КАРТИНКА
==================================================

Сделай одну качественную архитектурную диаграмму и возвращайся к ней 3–4 раза по ходу лекции.

Базовая схема:

raw
 ↓
dbt sources
 ↓
staging
 ↓
intermediate
 ↓
feature marts
 ↓
training dataset
 ↓
train model
 ↓
model registry
 ↓
inference

Визуально выдели рамкой:

┌──────────── DBT ZONE ────────────┐
sources → staging → intermediate → marts
└──────────────────────────────────┘

Позже на эту же картинку добавляй:
- tests;
- docs;
- lineage;
- incremental;
- CI;
- Airflow;
- training trigger.

Не рисуй каждый раз принципиально новую архитектуру.
Используй одну визуальную метафору, постепенно обогащая её.

==================================================
5. MLOPS-СМЫСЛ ОСНОВНЫХ КОНЦЕПЦИЙ DBT
==================================================

Добавь отдельный компактный слайд:

source()
→ откуда пришли данные для признака

ref()
→ dependency graph / lineage признака

test
→ не запускаем training на сломанной feature table

docs
→ определение признака, owner, semantics

incremental
→ не пересчитываем всю историю признаков

CI
→ изменение SQL-feature проходит review + automated tests

orchestrator
→ dbt build успешно завершился → запускаем training

Это один из ключевых слайдов лекции.

==================================================
6. СЛОИ DBT-ПРОЕКТА
==================================================

Сохрани и усили:

sources
→ staging
→ intermediate
→ marts

Покажи их одновременно:
1. абстрактно;
2. через Olist.

Например:

source('olist', 'orders')
        ↓
stg_orders
        ↓
int_order_level
        ↓
mart_delivery_features

Объясни responsibility каждого слоя.

Marts в этой лекции должны включать feature marts, а не только BI marts.

==================================================
7. JINJA И MACROS — ОСТАВИТЬ
==================================================

Верни/оставь Jinja и macros.

Но framing:

не «ещё одна возможность dbt»,

а:

«Как full-stack специалист перестаёт копипастить SQL и начинает строить reusable transformation platform».

Покажи:
- {{ ref() }}
- {{ source() }}
- var()
- env_var() при необходимости;
- простой for loop;
- простой macro.

Не уходи глубоко в metaprogramming.

adapter.dispatch и low-level adapter internals перенеси во вторую часть / appendix.

Добавь хороший MLE-oriented macro example.

Например:
- safe_divide;
- feature normalization SQL helper;
- repeated feature aggregation;
- generate surrogate key;
- reusable date/window logic.

Покажи также опасность:
Jinja/macros могут сделать SQL слишком магическим.

Правило:
prefer readable SQL; abstract repeated infrastructure patterns, not every three lines of SQL.

==================================================
8. DBT PACKAGES — ОСТАВИТЬ, НО ОТФИЛЬТРОВАТЬ
==================================================

Оставь packages, полезные full-stack data specialist / MLE.

Не делай огромный каталог.

Сгруппируй примерно:

MODELING / UTILITIES
- dbt-utils
- dbt-date, если уместно
- audit-helper, если актуально

QUALITY / VALIDATION
- dbt-expectations или актуальный поддерживаемый эквивалент;
- другие действительно актуальные quality packages, если нужны.

OBSERVABILITY
- dbt-artifacts / elementary-related integration, если актуально;
- только если проект/пакет реально поддерживается сейчас.

ML / FEATURE ENGINEERING
- только реальные и актуальные проекты/packages;
- не придумывай ML packages ради заполнения слайда.

Перед использованием проверь актуальное состояние проектов.
Deprecated/unmaintained package не преподноси как default recommendation.

Для каждого package:
- 1 строка «зачем MLE»;
- без подробного API.

==================================================
9. TESTS + DOCS + LINEAGE
==================================================

Сохрани сильный существующий блок.

Обязательно:
- not_null;
- unique;
- accepted_values;
- relationships;
- singular tests;
- unit tests — кратко;
- docs;
- lineage.

Свяжи с feature engineering.

Пример:

mart_delivery_features:
- order_id unique + not_null;
- feature columns not_null там, где это contract;
- accepted range;
- relationships;
- custom business/data sanity test.

Подчеркни:

dbt tests обычно являются data assertions/checks,
а не обязательно физическими DB constraints.

Добавь quality gate:

dbt build
   ↓
tests passed?
 ├─ NO → STOP
 └─ YES → train model

==================================================
10. INCREMENTAL + CLICKHOUSE
==================================================

Сохрани и усили этот блок.

Обязательно:
- full refresh vs incremental;
- is_incremental();
- {{ this }};
- watermark;
- ClickHouse specifics;
- late-arriving data;
- lookback;
- idempotency;
- partition/update strategy;
- стоимость полного пересчёта.

Очень явно покажи опасность:

WHERE event_time > max(event_time)

— это учебный пример, но не универсальный production pattern.

Объясни:
- late arrivals;
- corrections;
- mutable source data.

Покажи safer strategy:
watermark + lookback / partitions / idempotent recomputation.

Свяжи с feature marts:
«мы хотим дёшево обновлять features, но не терять исправленные/опоздавшие события».

==================================================
11. ТРИ MLOPS-НЮАНСА
==================================================

Сделай 1–2 отдельных слайда.

A. dbt ≠ ML pipeline

dbt отвечает за data/feature transformation layer.

За пределами dbt:
- model training;
- experiment tracking;
- registry;
- serving;
- model monitoring.

B. Offline feature table ≠ online Feature Store

mart_delivery_features в ClickHouse может быть отличным:
- offline feature layer;
- training dataset source.

Но это ещё не автоматически:
- online feature store;
- low-latency feature serving;
- Feast/Tecton-like architecture.

C. DATA LEAKAGE / POINT-IN-TIME CORRECTNESS

Это особенно важно.

Покажи простой пример.

Prediction time:
2025-03-01 10:00

Feature:
seller_avg_delivery_delay

НЕЛЬЗЯ использовать заказы seller-а,
которые завершились после prediction time.

Объясни:
для ML недостаточно «правильно посчитать SQL aggregate».
Нужно гарантировать:

feature_timestamp <= prediction_timestamp

или эквивалентную point-in-time semantics.

Это один из главных ML-specific моментов лекции.

==================================================
12. PYTHON В DBT + OPENDBT
==================================================

Оставь/добавь отдельный блок.

Ответь:

«Можно ли использовать Python внутри dbt?»

Покажи:
- Python models там, где они поддерживаются;
- ограничения adapter/backend;
- SQL remains default for relational transformations;
- Python — escape hatch, а не замена SQL.

Добавь короткий пример Python model.

Отдельно расскажи про OpenDBT и релевантные Python/extensions capabilities.

ВАЖНО:
проверь текущую документацию/актуальное состояние OpenDBT перед редактированием.
Не делай утверждений по памяти, если API/возможности могли измениться.

Сделай слайд:

WHEN SQL
WHEN PYTHON
WHEN NOT DBT

Это должно помогать выбирать инструмент.

==================================================
13. AIRFLOW + DBT: ОТ ПРОСТОГО К ЗРЕЛОМУ
==================================================

Сделай полноценный блок orchestration.

Начни с вопроса:

«dbt умеет построить transformation DAG.
Зачем тогда Airflow?»

Ответ:
dbt знает зависимости transformations,
но production pipeline шире:

ingestion
→ dbt
→ validation
→ training
→ evaluation
→ registry
→ deployment / notification

Покажи варианты интеграции от простого к зрелому:

1. BashOperator / shell command

   dbt build

Плюсы:
- просто;
- прозрачно;
- хороший старт.

Минусы:
- весь dbt graph часто выглядит как одна Airflow task;
- слабая granular observability.

2. Dedicated dbt operators / wrappers

Кратко.
Укажи, что экосистема таких библиотек менялась и часть старых проектов может быть deprecated.

3. dbt Cloud/API — кратко, если релевантно.

4. dmp-af

5. Cosmos

Не перегружай первыми тремя.
Основной акцент блока — Cosmos и dmp-af.

==================================================
14. DMP-AF — ОТДЕЛЬНЫЙ СЛАЙД
==================================================

Создай отдельный слайд:

«dmp-af: dbt-first orchestration on Airflow»

Используй актуальный проект:

https://github.com/dmp-labs/dmp-af

НЕ преподноси старый Toloka/dbt-af как текущий проект.
Можно в notes кратко сказать, что старый проект deprecated и active development переехал в dmp-labs/dmp-af.

Объясни design philosophy:

- dbt-first;
- domain-driven;
- генерация Airflow DAGs из dbt project/manifest;
- dbt models становятся отдельными Airflow tasks;
- scheduling ближе к dbt configuration;
- разные domains можно разделять по DAG;
- date interval из Airflow можно использовать внутри dbt transformations;
- интересен для больших dbt projects.

Особенно отметь use case:
large/domain-oriented dbt installations.

Добавь ссылку на GitHub прямо на слайд/в resources.

Проверь README текущего dmp-labs/dmp-af и используй актуальные названия API.

==================================================
15. COSMOS — ОТДЕЛЬНЫЙ СЛАЙД
==================================================

Создай отдельный слайд:

«Cosmos: Airflow-native orchestration of dbt»

Объясни:
- open-source Astronomer project;
- dbt project → Airflow DAG / TaskGroup;
- dbt nodes могут отображаться как Airflow tasks;
- retries;
- scheduling;
- Airflow observability;
- connections;
- execution modes;
- integration into larger Airflow pipelines.

Cosmos — основной рекомендуемый вариант для примера этой лекции.

Добавь ссылки:

OFFICIAL GUIDE:
https://www.astronomer.io/docs/learn/airflow-dbt

BOOK / EBOOK:
https://www.astronomer.io/ebooks/orchestrating-dbt-with-airflow-using-cosmos/

Также можно добавить:
https://www.astronomer.io/ebooks/airflow-and-dbt-using-cosmos-13-practical-dag-code-examples/

Добавь 1–2 актуальных YouTube/video resources по Cosmos.
Предпочитай официальные материалы Astronomer.

Проверь URL перед добавлением.
Не придумывай ссылки.

==================================================
16. COSMOS VS DMP-AF — ОТДЕЛЬНЫЙ СЛАЙД
==================================================

Добавь comparison slide.

Не делай вывод «один объективно лучше».

Сравни:

                     COSMOS              DMP-AF

Philosophy           Airflow-centric     dbt-first /
                                         domain-driven

Unit of execution    dbt nodes/tasks     dbt nodes/tasks

Integration          DAG / TaskGroup     generated DAGs /
                                         domains

Sweet spot           general Airflow +   large/domain-
                     dbt integration     oriented dbt setups

Airflow ownership    stronger            more hidden from
                                         dbt author

Scheduling           Airflow-oriented    stronger dbt-side
                                         scheduling concepts

Date interval        supported through   explicit important
integration          Airflow patterns    design concept

Learning curve       familiar for        attractive when
                     Airflow users       team thinks dbt-first

Для курса:
Cosmos = основной production example.
dmp-af = важная альтернативная архитектура.

Обязательно сверяй сравнение с актуальной документацией обоих проектов.

==================================================
17. ПРИМЕР PIPELINE — ТОЛЬКО AIRFLOW + COSMOS
==================================================

Перепиши существующий «пример пайплайна».

Он должен быть именно Airflow + Cosmos.

Архитектура:

raw_data_ready
      ↓
DbtTaskGroup / Cosmos
      ↓
dbt models + tests
      ↓
quality gate
      ↓
build_training_dataset
      ↓
train_model
      ↓
evaluate_model
      ↓
register_model
      ↓
(optional) deploy / notify

Используй Olist.

Например:

wait_for_olist_raw
       ↓
┌─────────────────────────┐
│ Cosmos DbtTaskGroup     │
│                         │
│ stg_orders              │
│      ↓                  │
│ int_order_level         │
│      ↓                  │
│ mart_delivery_features  │
│      ↓                  │
│ tests                   │
└─────────────────────────┘
       ↓
train_delivery_model
       ↓
evaluate
       ↓
register

Добавь небольшой реальный code example Cosmos.

Не делай код слишком длинным.
Главное — показать архитектурную идею.

==================================================
18. DAGSTER — ОТДЕЛЬНЫЙ СЛАЙД
==================================================

Cosmos и Dagster НЕ объединять на одном слайде.

Создай отдельный короткий слайд:

«А если мы используем Dagster?»

Покажи:
- asset-centric model;
- dbt assets;
- lineage;
- natural representation of data assets;
- orchestration dbt + downstream ML assets.

Но не уходи глубоко.

Большой callout:

«Dagster подробно разбираем в отдельной лекции курса».

Цель слайда:
дать студенту mental map, а не обучить Dagster.

==================================================
19. CI/CD ДЛЯ DBT + ML
==================================================

Сохрани/усиль.

Покажи путь:

SQL feature change
      ↓
Git PR
      ↓
dbt parse / compile
      ↓
dbt tests / build
      ↓
review
      ↓
merge
      ↓
production dbt build
      ↓
training pipeline

Объясни:
изменение SQL feature — это изменение ML system.

Поэтому transformation code должен иметь тот же engineering discipline, что Python model code.

==================================================
20. OLIST END-TO-END CASE
==================================================

Вместо большого количества обзорных dbt-слайдов сделай компактный, но реальный end-to-end case.

Покажи:

orders
order_items
sellers
customers
products
geolocation
        ↓
sources
        ↓
staging
        ↓
int_order_level
        ↓
mart_delivery_features

Примеры features:
- item_count;
- total_price;
- freight_value;
- seller/customer distance;
- product weight;
- seller historical delivery statistics;
- order time features;
- другие разумные признаки.

Затем:

mart_delivery_features
        ↓
point-in-time selection
        ↓
training dataset
        ↓
Python / ML training

Добавь SQL fragments из этого кейса на протяжении лекции.

Не создавай отдельные toy examples, если тот же concept можно показать на Olist.

==================================================
21. ЧТО ПЕРЕНЕСТИ В PART 2 / APPENDIX
==================================================

Убери из основного narrative или перенеси во вторую часть:

- подробная история dbt как компании/продукта;
- глубокое Core vs Cloud comparison;
- Fusion internals;
- IDE comparison;
- adapter.dispatch;
- low-level adapter internals;
- глубокий Data Vault;
- Anchor modeling;
- grants/access-control details;
- package management internals;
- exhaustive package catalog;
- глубокий Data Catalog;
- exhaustive adapter/database comparison;
- AI features самого dbt;
- подробные тренды dbt;
- enterprise-only details, не нужные для mental model MLE.

Не обязательно физически удалять материал:
можно перенести после основного conclusion в:

PART 2 / ADVANCED / APPENDIX.

==================================================
22. PRESENTER NOTES — СУЩЕСТВЕННО РАСШИРИТЬ
==================================================

Это обязательная часть задачи.

Перепиши presenter notes так, чтобы презентация фактически содержала сценарий лектора на 90–105 минут.

Не дублируй текст слайда.

Для каждого содержательного слайда notes должны по возможности включать:

1. MAIN MESSAGE
   Что студент должен вынести.

2. TALK TRACK
   Что именно преподаватель рассказывает устно.

3. MLE / FULL-STACK ANGLE
   Почему это важно ML Engineer / full-stack data specialist.

4. EXAMPLE
   Желательно Olist или production scenario.

5. CAVEAT / COMMON MISTAKE
   Что студенты обычно понимают неправильно.

6. TRANSITION
   Как перейти к следующему слайду.

Для code slides:
добавь WALKTHROUGH:
- какие 2–4 строки показать;
- что не нужно разбирать;
- какой conceptual takeaway.

Не превращай notes в эссе на несколько страниц для каждого слайда.
Они должны быть удобны во время реальной лекции.

Добавь ориентировочный timing.

Например:

[Timing: ~2 min]

Распредели материал так, чтобы суммарно было примерно 90–105 минут.

Примерный бюджет:

Full-stack framing + AE history:
10–12 min

dbt mental model + SQL/Python + layers:
15–18 min

Jinja/macros/packages:
10–12 min

tests/docs/lineage:
10–12 min

incremental + ClickHouse + PIT:
12–15 min

Airflow orchestration:
18–22 min

Olist end-to-end + CI/ML:
10–12 min

conclusion:
3–5 min

Не нужно механически соблюдать эти цифры, но итоговая длительность должна быть реалистичной.

==================================================
23. REFERENCES / LINKS
==================================================

Добавь полезные ссылки прямо в notes или на resource slides.

Для Cosmos обязательно:
- official Astronomer guide;
- Astronomer Cosmos ebook;
- practical DAG examples ebook;
- 1–2 официальных video/YouTube resources.

Для dmp-af:
- https://github.com/dmp-labs/dmp-af
- documentation/README;
- YouTube/video материалы, если найдёшь достоверные релевантные материалы.

ВАЖНО:
если нормального официального/качественного YouTube-видео про dmp-af нет, НЕ выдумывай URL.
Вместо этого оставь GitHub/docs и при необходимости напиши в notes:
«На момент подготовки лекции отдельный качественный официальный YouTube tutorial не найден».

Проверь все внешние ссылки перед финализацией.

==================================================
24. ВИЗУАЛЬНЫЙ СТИЛЬ
==================================================

Сохрани общий визуальный язык текущей презентации.

Но:
- меньше стен текста;
- больше архитектурных схем;
- больше progression diagrams;
- code snippets короткие;
- одинаковая визуальная семантика dbt zone на всех схемах;
- Olist entities/models обозначай одинаково по всей лекции;
- Python / dbt / Airflow / ML layers визуально различай последовательно.

На сквозной схеме DBT ZONE должен визуально узнаваться каждый раз.

Используй build-up:
одна и та же схема постепенно обогащается tests/docs/incremental/orchestration/ML.

==================================================
25. ФИНАЛЬНЫЙ NARRATIVE
==================================================

В конце студент должен уметь ответить на вопросы:

1. Зачем ML Engineer вообще dbt?
2. Почему возник Analytics Engineering?
3. Какие transformations оставить SQL/dbt, а какие Python?
4. Как организовать sources → staging → intermediate → feature marts?
5. Как tests/docs/lineage делают feature layer надёжным?
6. Как делать incremental feature computation в ClickHouse?
7. Почему point-in-time correctness критична для ML?
8. Как встроить dbt в Airflow?
9. Чем conceptually отличаются Cosmos и dmp-af?
10. Где заканчивается dbt и начинается ML pipeline?
11. Почему эти навыки важны full-stack data specialist в эпоху LLM/agents?

Финальный тезис лекции:

«dbt — не инструмент “для аналитиков” и не замена ML pipeline.

Для full-stack data specialist это способ превратить transformation/feature layer в software-engineered компонент production data/ML system:

versioned
+ modular
+ tested
+ documented
+ incremental
+ observable
+ orchestrated.»

Последний визуальный слайд:

RAW DATA
   ↓
DBT DATA / FEATURE LAYER
   ↓
ML PIPELINE
   ↓
P[tasks](tasks)RODUCTION

и сверху/вокруг:

FULL-STACK DATA SPECIALIST
          +
     AI / AGENTS

==================================================
26. ПОСЛЕ РЕДАКТИРОВАНИЯ
==================================================

После внесения изменений:

1. Проверь всю презентацию на логическую последовательность.
2. Удали дубли, появившиеся после перестановки слайдов.
3. Проверь, что нет ссылок на удалённое ДЗ.
4. Проверь numbering/section headers.
5. Проверь code snippets на синтаксическую корректность.
6. Проверь актуальность dbt/OpenDBT/Cosmos/dmp-af APIs.
7. Проверь все URL.
8. Проверь, что Cosmos, dmp-af и Dagster имеют отдельные слайды.
9. Проверь, что основной pipeline example использует Airflow + Cosmos.
10. Проверь, что Olist используется как сквозной пример.
11. Проверь presenter notes на всех содержательных слайдах.
12. Посчитай суммарный estimated lecture timing из notes:
    target = 90–105 minutes.
13. Сделай визуальный QA всех слайдов:
    overflow, слишком мелкий текст, broken diagrams, inconsistent alignment.
14. Если после изменений получилось >60 основных слайдов, сначала попробуй объединить/сжать второстепенные слайды, а не выкидывать ключевой MLOps/full-stack материал.
15. Advanced/Part 2/Appendix не учитывай в основной хронометраж лекции.

В самом конце выдай краткий changelog:
- итоговое число основных слайдов;
- число appendix/part 2 slides;
- estimated lecture duration;
- какие новые слайды добавлены;
- какие старые блоки перенесены в Part 2;
- какие слайды существенно переработаны;
- какие внешние источники были добавлены.