# Публикация дек: Telegram + GDrive (вечный URL) + колонки листа

Спека ленты `src/publisher/` (задача
[#6 — Deck publish pipeline: Telegram + GDrive (persistent URL) + GSheet columns](https://github.com/dataengy/MLInside-course/issues/6)).
Сиблинг [`schedule-gsheet-lane.md`](schedule-gsheet-lane.md) (чтение листа); эта лента —
обратное направление: запись в лист + доставка артефактов.

## Зачем

`data/generated/` и `~/Downloads` — локальные (gitignored): собранная дека без публикации
не существует нигде, кроме ноутбука автора. По новой версии деки лента доставляет её в три
канала: **TG** (текст-нотификация + сам pptx в топик курса), **GDrive** (один стабильный
файл на предмет — URL не меняется между версиями) и **курсовой лист** (колонки
«pptx (GDrive)» / «версия» / «слайдов» в строке лекции).

## Триггер — только явный

Билдер (`preza_gen`) мятит **новую minor-версию на каждом билде** (`_resolve_naming`
сканирует `data/generated/`), поэтому автопубликация на каждый ребилд заспамила бы чат и
Drive. Публикация — явная идемпотентная команда; SessionStart-хук
`scripts/hooks/deck-publish-status.sh` (fail-open, без сети) напоминает о двух разных
состояниях, не смешивая их:

| строка хука | что значит | что делать |
|---|---|---|
| ⚠ собрано новее опубликованного | версия в `data/generated/` выше записанной | `just publish-new` |
| ⓘ версии актуальны, не завершены леги … | версия та же, но лег не дошёл до `ok`/`skipped` | `just publish-new --only <лег>` (хук печатает готовую команду) |

## Команды

```bash
just publish-new-dry            # что будет сделано (без сети и записей)
just publish-new                # опубликовать всё новое (только не-ok леги)
just publish-new --deck content/preza-dbt-v3-content.yml   # одна дека (или out_name)
just publish-new --only tg      # один лег: tg | drive | sheet (повторяемый флаг)
just publish-new --force        # перегнать даже ok-леги текущей версии
just publish-status             # курсор vs свежесобранное, по декам
just publish-init-drive         # один раз: создать папку Drive, id → settings/publish.yml
just publish                    # dbt: build --all + open + publish-new --deck dbt
```

## Механика

- **Версия** — из имени файла `data/generated/{out_name}_v{major}.{minor}.pptx`
  (`publisher/detect.py`; регэксп заякорен на `.pptx`, стем сверяется точно). Кол-во
  слайдов — из самого pptx (`python-pptx`), не из контент-YAML.
- **Порядок легов: drive → tg → sheet.** TG-текст и строка листа несут Drive-URL, поэтому
  Drive первый. Sheet-лег требует `drive: ok` для текущей версии (строка описывает один
  консистентный артефакт), иначе `skipped`. Леги изолированы: падение одного не роняет ни
  соседние леги, ни остальные деки; exit 1 — если хоть один attempted-лег упал.
- **Drive**: файл `{out_name}.pptx` (без версии!) в папке `drive.folder_id`; новая версия =
  `files().update` того же fileId → **webViewLink вечный**. Потеря курсора не плодит
  дубликаты: сначала update по записанному id, при 404 — поиск по имени в папке (adopt),
  только потом create. Версия — в `description` файла. Шаринг `anyone_reader`
  обеспечивается идемпотентно на каждом аплоаде (permissions.list → create).
- **Sheet**: таб резолвится **живьём** (`spreadsheets().get`; кэшированный
  `settings/schedule.yml` однажды приезжал не через API — ему не верим; после первого
  живого прогона пиньте реальное имя в `settings/gsheet.yml → mapping.tab`). Колонка темы —
  по кандидат-карте ридера (`mapper.resolve_columns`), строка — по `mapper.normalize`
  (ё≠е и пунктуация уже учтены). Три колонки дозаводятся идемпотентно: известный индекс из
  курсора → текстовый поиск по хедеру → append справа; хедер-ячейки и данные пишутся
  **одним** `values().batchUpdate` (USER_ENTERED, диапазон на ячейку). Нет строки
  (OGIP, Prefect — их нет в расписании) → лег `skipped`, дека всё равно считается
  обслуженной.
- **TG**: текст через `tg-project-inform.sh --slug mlinside_course` (роутинг по слагу →
  чат/топик из `~/.ai/skills/_settings/telegram.yml`), файл через
  `preza_gen.publish.publish_deck` (→ `publish-deck.sh` → `tg-send-file.sh`, топик 118).
  Пре-флайт гард 49MB (жёсткий кап Bot API — 50MB; деки сейчас ~35MB). Глобальный
  Stop-хук `deck-watch.sh` остаётся в `on_complete: "open"` — TG-отправкой владеет эта
  лента, дублей нет.
- **Записи**: локальный курсор `data/.state/deck-publish-state.json` (gitignored,
  атомарная запись после каждой деки) + git-tracked блок `published:` в
  `content/presentations.yml` (переживает `just presentations-plan` — upsert не трогает
  незнакомые ключи). На свежем клоне курсор **сидируется** из `published:` — повторных
  отправок в TG не будет. Ретрай перегоняет только не-ok леги: TG никогда не шлётся дважды
  за одну версию.
- Правило порядка (без локов, один оператор): `just presentations-plan` и
  `just publish-new` не запускать одновременно — оба пишут `presentations.yml`.
- **Транзиентные отказы ретраятся** (`publisher/gapi.py`, `api.retries` в publish.yml):
  Google время от времени отвечает 503/500/429 на здоровый запрос. Без ретрая такой чих
  неотличим от настоящего отказа — лег пишется `error` в git-tracked `published:`, а прогон
  выходит с ненулевым кодом из-за икоты датацентра. Ретраятся ТОЛЬКО транзиентные коды;
  403 (квота/права) и 404 — работа для человека, повтор её лишь оттягивает. Все вызовы
  идут через `gapi.run` / `gapi.call`, чтобы ни одна точка не забыла.
- **Отказы переводятся в действие** (`publisher/errors.py`): все реальные падения этой
  ленты были политикой в одежде API-ошибки — переполненный диск приходит как
  `storageQuotaExceeded`, read-only-шаринг как голый 403, мёртвый консент как
  `invalid_grant`. К тексту ошибки спереди подставляется, что должен сделать человек;
  оригинал сохраняется целиком (он же уезжает в `published.legs`).
- **Проверка ворот перед прогоном** — `.tmp/probe_google_access.py` (только чтение):
  чей Drive и сколько места, читается ли лист, есть ли `canEdit`, и репетиция записи —
  таб, колонка темы, куда встанут новые колонки, какая дека в какую строку.

## Транспорт (Google write-лента)

**Одного кредла на обе записи не существует** — экран согласия gcloud пропускает только
не-чувствительные скоупы. Отсюда две ленты, выбираются по API (`PublishConfig.lane`,
`auth.get_service`):

| Лег | Кредл | Скоуп | Что нужно человеку |
|---|---|---|---|
| **Drive** | user-ADC `hnkovr@gmail.com` (`~/.config/gcloud/application_default_credentials.json`) | `drive.file` | консент `adc-login` (сделан 2026-08-20) + место на диске аккаунта |
| **Sheet** | сервис-аккаунт `gsheets-reader@for-prodamus-1-494316.iam.gserviceaccount.com` (`~/.secrets/google-sa-…json`) | `spreadsheets` | расшарить лист этому адресу как **Редактор** (сейчас Viewer) |

Что перепробовано и почему отвергнуто (не возвращать):

- **`.../auth/drive`** (полный) — restricted-скоуп, консент отвечает «Приложение
  заблокировано». Работает `drive.file`: он покрывает всё, что лента сама создала — свою
  папку и по одному файлу на предмет.
- **`spreadsheets` в ADC** — *sensitive*-скоуп, тот же экран блокировки (2026-08-20).
  Тот же логин **без** него проходит. Поэтому лист пишет SA, а не ADC. Важно: список
  `auth.scopes` обязан совпадать с реально выданным — google-auth роняет `RefreshError`,
  если запрошенный скоуп не был выдан.
- **SA для Drive** — у сервис-аккаунта нет storage-квоты на личном Drive, а Shared Drives
  требуют Workspace. SA обслуживает только лист.
- **Свой OAuth-клиент (AGD-gen)** — умер `invalid_grant`: у клиента в Testing-статусе
  refresh-токены живут 7 дней. У gcloud-клиента refresh-токен долгоживущий.

**Quota-project.** Drive API отказывает user-ADC без quota-проекта, а у ADC-файла свой
(`stambul-tts`) с выключенным Drive API. Проект задан в `auth.quota_project` и вешается
**на кредл** (`with_quota_project`), а не на ADC-файл — машинный ADC используют другие
проекты, его настройку не трогаем. В проекте не лежат данные, он только учитывает вызовы;
единственное требование — включённый `drive.googleapis.com`.

Логин (когда токен умрёт): `just -f ~/.ai/scripts/gcloud/Justfile adc-login account=hnkovr@gmail.com`.
Попутно починен корневой баг этой ленты — `just` не имеет именованных аргументов, и
`adc-login account=X` кормил gcloud `--account="account=X"`
([hnkovr/.ai#8](https://github.com/hnkovr/.ai/issues/8)). `publisher/auth.py`
принципиально **не умеет** интерактивный флоу (google_auth_oauthlib не импортируется):
мёртвый токен = громкий RuntimeError с командой починки.

## Чек-лист первого живого прогона

Пройдено 2026-08-20: ① консент `drive.file` ✅ · ② Drive-папка создана
(`drive.folder_id` в `settings/publish.yml`) ✅ · ③ TG-лег отработал на всех шести деках ✅.
Осталось два внешних условия:

1. **Место на Drive** `hnkovr@gmail.com` — сейчас 98.69 GiB при лимите 15 GiB (сам Drive
   занимает 0.07 GiB, переполнены Gmail/Photos), аплоад отвечает `storageQuotaExceeded`.
   После расширения квоты: `just publish-new --only drive`.
2. **Права на лист** — выдать `gsheets-reader@for-prodamus-1-494316.iam.gserviceaccount.com`
   роль **Редактор** на таблице расписания. После этого: `just publish-new --only sheet`.

Затем полный прогон `just publish-new` и проверка: стабильность URL на ребилде (та же
ссылка), идемпотентность повторного прогона («already ok»), три колонки в листе без дублей.

## Известные ограничения

- Переименование `out_name` осиротит старый Drive-файл (новый создастся под новым именем) —
  ручная уборка в Drive.
- Ревизии Drive копятся при каждом update (обрезаются гуглом ~30 дней / 100 ревизий для
  бинарников) — не блокер.
- `anyone_reader` — ссылка открываема всем, у кого она есть (снимается
  `drive.share: none`).
- Лист должен давать **Editor** сервис-аккаунту лист-ленты, иначе sheet-лег ловит 403
  (TG/Drive при этом работают — изоляция легов).
- Drive-лег упирается в квоту аккаунта-владельца папки: `storageQuotaExceeded` — это про
  место, а не про права.
