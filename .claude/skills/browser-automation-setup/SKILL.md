---
name: browser-automation-setup
description: 'Выбрать и поднять рабочий движок браузерной автоматизации, когда расширение Claude in Chrome не подключено или отвалилось. Даёт лестницу отказа claude-in-chrome MCP → Playwright → headless Chrome, команды установки через uv без засорения проекта, и правила ожидания тяжёлых SPA (Dagster, MLflow, Airflow, Superset). Триггеры: "Browser extension is not connected", "tabs_context_mcp вернул ошибку", "нечем открыть страницу", "сними страницу браузером", "нужен headless-браузер", "MCP claude-in-chrome отвалился".'
---

Поднять браузер, когда штатный путь не работает. Не про то, ЧТО делать на странице, — про то,
ЧЕМ её открыть. Съёмку экранов для деки см. `ui-screenshots-for-decks`.

## Лестница отказа

Идти строго сверху вниз, не перепрыгивая: каждый следующий шаг дороже предыдущего.

| # | Движок | Когда | Цена |
|---|---|---|---|
| 1 | `mcp__claude-in-chrome__*` | расширение подключено | 0 — уже стоит |
| 2 | Playwright (chromium) | расширение молчит, нужен контроль ожиданий | ~95 МБ, разовая загрузка |
| 3 | headless Chrome напрямую | Playwright не ставится | 0, если Chrome есть |

### Шаг 1 — проверить штатный путь

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp
```

затем `tabs_context_mcp{createIfEmpty:true}`. Признак отказа — дословно:

> Browser extension is not connected. Please ensure the Claude browser extension is installed…

**Не чинить расширение самому** и не просить пользователя его переустанавливать посреди
задачи: это его окружение и его решение. Сказать одной строкой, что переходишь на Playwright,
и перейти.

### Шаг 2 — Playwright

```bash
uv run --with playwright python -c "import playwright; print('ok')"
uv run --with playwright playwright install chromium      # ~95 МБ, только первый раз
```

`--with` не трогает зависимости проекта — в `pyproject.toml` ничего не добавляется.
Скрипт запускать тем же `uv run --with playwright python script.py`.

### Шаг 3 — headless Chrome

Когда нет ни расширения, ни возможности качать браузер:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --screenshot=out.png \
  --window-size=1680,1000 --virtual-time-budget=8000 http://localhost:3111
```

Годится для статики. Для SPA — ненадёжно: `--virtual-time-budget` угадывает время загрузки,
а не ждёт готовности.

## Ожидание тяжёлых SPA

Dagster, MLflow, Airflow и Superset рисуют содержимое после нескольких раундов запросов.
`networkidle` для них **недостаточен** — он срабатывает, когда граф ещё пустой.

```python
await pg.goto(url, wait_until="networkidle")
await pg.wait_for_selector("text=feature_table", timeout=30_000)   # ждать СОДЕРЖИМОЕ
await pg.wait_for_timeout(2000)                                     # добор на анимации
```

Правило: ждать **конкретный элемент, который должен появиться**, а не общее состояние сети.
Если элемента не знаешь — сними пробный кадр и посмотри на него, прежде чем писать сценарий.

## Разведка перед сценарием

Маршруты и вёрстка меняются от версии к версии. Сначала одна пробная страница:

```python
await pg.screenshot(path=f"{OUT}/probe.png")
print("URL:", pg.url, "| TITLE:", await pg.title())
print(await pg.eval_on_selector_all("a[href]",
      "els => [...new Set(els.map(e => e.getAttribute('href')))].slice(0, 40)"))
```

Прочитать кадр глазами (`Read` по файлу), потом писать съёмку. Угадывать селекторы по памяти
— главный источник пустых кадров.

## Чего не делать

- Не запускать `alert`/`confirm`/`prompt` и не кликать по кнопкам, которые их вызывают:
  модальное окно блокирует расширение целиком, и сессия перестаёт отвечать.
- Не ставить Playwright глобально (`pip install`) — только `uv run --with`.
- Не повторять один и тот же падающий вызов больше 2–3 раз. Не помогло — сказать
  пользователю, что пробовал и что сломалось, и спросить, как дальше.
- Не оставлять поднятые процессы (`dg dev`, `mlflow ui`) после работы: они держат файлы
  и мешают удалить каталог. Гасить явно.
