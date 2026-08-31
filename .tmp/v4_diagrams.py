# -*- coding: utf-8 -*-
"""Канонические ASCII-схемы деки v4 (`code_lang: diagram`) — источник истины для рамок.

Зачем генератор, а не рисование руками в YAML: рамка из box-drawing глифов держится только
на том, что все её строки РОВНО одной длины. При ручной правке это разъезжается мгновенно и
незаметно в исходнике — видно уже на собранном слайде. Здесь длины совпадают по построению:
box() сам добивает содержимое до ширины рамки.

Второе правило: из стрелок используем только ←↑→↓ (U+2190..2193) и глифы U+2500..257F —
они есть в Consolas. ▶▼◀▲ (U+25B6 и соседи) в Consolas отсутствуют, подставляются другим
шрифтом другой ширины и ломают моноширинность.

Влить схемы обратно в контент:

    from v4_diagrams import D
    from patch_slide_code import patch
    for sid, code in D.items():
        patch("content/preza-dbt-v4-content.yml", sid, code)

Написан при сборке v4 деки; в Justfile намеренно не заведён.
"""


def box(lines, width=None, top_mark=None, bottom_mark=None, title=None):
    """Рамка из box-drawing глифов. top_mark/bottom_mark — символ входа/выхода
    (↓/┬/┴) в середине верхней/нижней границы."""
    body = list(lines)
    if title:
        body = [title.center(width or max(map(len, body))), ""] + body
    w = width or max(len(l) for l in body)
    def edge(l, r, mark):
        bar = list("─" * w)
        if mark:
            bar[w // 2] = mark
        return l + "".join(bar) + r
    out = [edge("┌", "┐", top_mark)]
    out += ["│" + l.ljust(w) + "│" for l in body]
    out += [edge("└", "┘", bottom_mark)]
    return out


def stack(col, *rows):
    """Вертикальная цепочка «текст → │ → ↓ → текст» с общей колонкой стрелок."""
    out = []
    for i, r in enumerate(rows):
        if i:
            out += [" " * col + "│", " " * col + "↓"]
        out.append(r)
    return out


def indent(lines, n):
    return [" " * n + l for l in lines]


D = {}

# ─────────────────────────────────────────────────────────────────────────────
D["005-full-stack-data-specialist"] = "\n".join([
    "                      FULL-STACK DATA SPECIALIST",
    "",
    "    Infra              Data              Analytics             ML",
    "      │                 │                    │                  │",
    "      ↓                 ↓                    ↓                  ↓",
    "   DevOps  ──→   DE   ──→   AE   ──→   DA / BIE   ──→   MLE / MLOps",
    "",
    "   source → ingestion → storage → transformations → quality → analytics",
    "          → features → training → orchestration → deployment → monitoring",
    "",
    "                                 ↑",
    "                      AI / LLM / AGENTS",
    "            снижают стоимость переключения между слоями стека",
])

ZONE_W = 80
ZONE_COL = 1 + ZONE_W // 2          # колонка ↓/┬ на границах рамки DBT ZONE


ZONE_W = 80
ZONE_COL = 1 + ZONE_W // 2          # колонка ↓/┬ на границах рамки DBT ZONE

D["012-skvoznaya-arhitektura"] = "\n".join(
    ["  RAW   olist_raw:  orders · order_items · sellers · customers · products",
     " " * ZONE_COL + "│"]
    + box([
        "  sources    ──→   staging    ──→   intermediate   ──→   feature marts",
        "  olist_raw        stg_orders       int_order_level      mart_delivery_features",
        "                   stg_order_items",
        "                   stg_sellers",
    ], width=ZONE_W, top_mark="↓", bottom_mark="┬", title="D B T   Z O N E")
    + [" " * ZONE_COL + "│",
       " " * ZONE_COL + "↓",
       "      training dataset ──→ train model ──→ model registry ──→ inference"]
)

FRESH_W = 46
FRESH_INDENT = ZONE_COL - 1 - FRESH_W // 2

D["035-arhitektura-plus-testy-docs"] = "\n".join(
    ["  RAW   olist_raw:  orders · order_items · sellers · customers · products",
     " " * ZONE_COL + "│"]
    + indent(box(["  source freshness  ──  данные вообще доехали?"], width=FRESH_W,
                 top_mark="↓", bottom_mark="┬"), FRESH_INDENT)
    + [" " * ZONE_COL + "│",
       " " * ZONE_COL + "↓"]
    + box([
        "  sources    ──→   staging    ──→   intermediate   ──→   feature marts",
        "",
        "  tests    not_null · unique · accepted_values · relationships · ranges",
        "  docs     описание модели и колонки, owner, consumers",
        "  lineage  граф ref() — от source до витрины признаков",
    ], width=ZONE_W, top_mark="↓", bottom_mark="┬", title="D B T   Z O N E")
    + [" " * ZONE_COL + "│   tests passed ?",
       " " * ZONE_COL + "↓",
       "      training dataset ──→ train model ──→ model registry ──→ inference"]
)

PAIR_W, PAIR_GAP, PAIR_L = 34, 3, 2
_left = PAIR_L + 1 + PAIR_W // 2
_right = PAIR_L + PAIR_W + 2 + PAIR_GAP + 1 + PAIR_W // 2


def _pair_edge(mark_l, mark_r, l="┌", r="┐"):
    def one(m):
        bar = list("─" * PAIR_W)
        bar[PAIR_W // 2] = m if m else "─"
        return l + "".join(bar) + r
    return " " * PAIR_L + one(mark_l) + " " * PAIR_GAP + one(mark_r)


D["043-dbt-ne-ml-pipeline"] = "\n".join(
    [_pair_edge(None, None)]
    + [" " * PAIR_L + "│" + a.center(PAIR_W) + "│" + " " * PAIR_GAP + "│" + b.center(PAIR_W) + "│"
       for a, b in [("D B T  —  Э Т О", "З А   П Р Е Д Е Л А М И"), ("", "")]]
    + [" " * PAIR_L + "│" + a.ljust(PAIR_W) + "│" + " " * PAIR_GAP + "│" + b.ljust(PAIR_W) + "│"
       for a, b in [
           ("  sources", "  model training"),
           ("  staging", "  experiment tracking"),
           ("  intermediate", "  model registry"),
           ("  feature marts", "  serving / inference"),
           ("  tests · docs · lineage", "  model monitoring, drift"),
           ("  incremental materialization", "  retraining policy"),
       ]]
    + [_pair_edge("┬", "┬", l="└", r="┘"),
       " " * _left + "│" + " " * (_right - _left - 1) + "↑",
       " " * _left + "└" + "  training dataset  ".center(_right - _left - 1, "─") + "┘"]
)

COS_W, COS_L = 62, 2
COS_COL = COS_L + 1 + COS_W // 2

D["055-olist-pipeline-airflow-cosmos"] = "\n".join(
    ["   wait_for_olist_raw                    # сенсор: сырьё доехало",
     " " * COS_COL + "│",
     " " * COS_COL + "↓"]
    + indent(box([
        "  stg_orders     stg_order_items     stg_sellers",
        "          └───────────┬───────────────────┘",
        "                      ↓",
        "             int_order_level",
        "                      ↓",
        "          int_seller_delay_history     # point-in-time",
        "                      ↓",
        "           mart_delivery_features",
        "                      ↓",
        "                 dbt tests             # quality gate",
    ], width=COS_W, bottom_mark="┬", title="Cosmos  DbtTaskGroup"), COS_L)
    + [" " * COS_COL + "↓",
       " " * (COS_COL - 11) + "build_training_dataset",
       " " * COS_COL + "↓",
       " " * (COS_COL - 10) + "train_delivery_model",
       " " * COS_COL + "↓",
       " " * (COS_COL - 7) + "evaluate_model  ──→  метрика хуже baseline → STOP",
       " " * COS_COL + "↓",
       " " * (COS_COL - 7) + "register_model  ──→  deploy / notify"]
)

D["062-finalnyj-vizual"] = "\n".join([
    "              FULL-STACK DATA SPECIALIST   +   AI / AGENTS",
    "",
    "                              RAW DATA",
    "                                 │",
    "                                 ↓",
    "                   DBT DATA / FEATURE LAYER",
    "         versioned · modular · tested · documented ·",
    "            incremental · observable · orchestrated",
    "                                 │",
    "                                 ↓",
    "                            ML PIPELINE",
    "         training ─ evaluation ─ registry ─ serving",
    "                                 │",
    "                                 ↓",
    "                            PRODUCTION",
])

D["034-quality-gate-pered-obucheniem"] = "\n".join([
    "                          dbt build",
    "                              │        # модели собраны, тесты прогнаны",
    "                              ↓",
    "                       tests passed ?",
    "                              │",
    "              ┌───────────────┴───────────────┐",
    "              │                               │",
    "             NO                              YES",
    "              │                               │",
    "              ↓                               ↓",
    "    STOP + алерт                     build_training_dataset",
    "    training НЕ запускается                   │",
    "    в проде остаётся                          ↓",
    "    предыдущая модель                    train_model",
])

D["038-lovushka-max-event-time"] = "\n".join(
    ["   max(ts) в витрине = 10 марта",
     " " * 14 + "│",
     " " * 14 + "↓"]
    + indent(box([
        " прогон 11 марта",
        " ",
        " заказ от 12 марта    ──→  ✓  попадёт",
        " заказ от 08 марта    ──→  ✗  НЕ попадёт  (опоздал)",
        " правка заказа от 05  ──→  ✗  НЕ попадёт  (правка задним числом)",
    ], width=64), 3)
    + ["",
       "   # тесты при этом зелёные: того, чего в таблице нет,",
       "   # проверить нельзя"]
)

D["049-zachem-airflow-esli-est-dag"] = "\n".join(
    ["  ingestion",
     " " * 9 + "│",
     " " * 9 + "↓"]
    + indent(box(["  dbt граф   ←── dbt знает только это"], width=38), 2)
    + [" " * 9 + "│",
       " " * 9 + "↓"]
    + stack(9, "  validation", "  training", "  evaluation", "  registry", "  deploy / notify")
)

D["059-izmenenie-sql-fichi-eto-izmenenie-ml-sistemy"] = "\n".join(
    stack(10, "   изменение SQL-признака",
              "   Git PR",
              "   dbt parse / compile          # шаблон вообще рендерится?",
              "   dbt build --select state:modified+   # изменённое и всё ниже",
              "   code review",
              "   merge",
              "   production dbt build",
              "   training pipeline")
)

D["006-pochemu-voznik-analytics-engineering"] = "\n".join([
    "ETL       source ──→ Python / Spark / ETL-движок ──→ warehouse",
    "                     # логика живёт вне хранилища, compute отдельный",
    "",
    "ELT       source ──→ warehouse ──→ SQL-трансформации",
    "                     # облачные DWH дёшевы: считаем рядом с данными",
    "",
    "ANALYTICS ELT  +  software engineering practices",
    "ENGINEERING",
    "          git · модульность · тесты · документация · CI · lineage · ownership",
])

D["013-mlops-smysl-konceptov-dbt"] = "\n".join([
    "source()        ──→  откуда пришли данные для признака",
    "ref()           ──→  граф зависимостей и lineage признака",
    "test            ──→  не запускаем training на сломанной feature-таблице",
    "docs            ──→  определение признака, владелец, семантика",
    "incremental     ──→  не пересчитываем всю историю признаков",
    "CI              ──→  изменение SQL-признака проходит review + автотесты",
    "orchestrator    ──→  dbt build завершился успешно → запускаем training",
])

D["016-olist-ot-raw-k-feature-martu"] = "\n".join([
    "  orders      order_items      sellers      customers    products   geolocation",
    "    │              │              │             │            │           │",
    "    └──────────────┴──────┬───────┴─────────────┴────────────┴───────────┘",
    "                          ↓",
    "  sources        source('olist_raw', ...)          # контракт входа + freshness",
    "                          ↓",
    "  staging        stg_orders   stg_order_items   stg_sellers   stg_customers",
    "                 типы · флаги · части даты · без джойнов",
    "                          ↓",
    "  intermediate   int_order_level                  # РОВНО одна строка на заказ",
    "                 позиции свёрнуты до заказа, расстояние клиент↔продавец",
    "                          ↓",
    "  marts          mart_delivery_features           # витрина признаков",
    "                 item_count · total_price · freight_share · distance_km ·",
    "                 seller_avg_delay_90d · order_hour · target is_late_delivery",
])
