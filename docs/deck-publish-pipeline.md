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
`scripts/hooks/deck-publish-status.sh` (fail-open, без сети) напоминает, когда собранное
новее опубликованного.

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

## Транспорт (Google write-лента)

**Состояние на 2026-08-19.** ЧТЕНИЕ листа работает без браузера — через сервис-аккаунт
(`just gsheet-tabs` → `Sheet1`). ЗАПИСЬ пока нет: у обоих SA `canEdit=false` (проверено
Drive-capabilities), а ADC-консент не завершён. Два пути открыть запись:

| Путь | Что сделать | Что заработает |
|---|---|---|
| **ADC-консент** (полный) | добить браузерный логин (скоупы `spreadsheets` + `drive.file`) | всё: Drive-загрузка **и** колонки листа |
| **Шаринг на SA** (без браузера) | расшарить лист на `service-account-1@for-prodamus-1.iam.gserviceaccount.com` как **Редактор**, затем прописать ключ в `auth.service_account_file` | только колонки листа; Drive-лег упадёт изолированно (у SA нет storage-квоты) |

Полный скоуп `.../auth/drive` использовать **нельзя**: он restricted, экран согласия gcloud
отвечает «Приложение заблокировано». Рабочий вариант — `drive.file`.

User-ADC **hnkovr@gmail.com** с write-скоупами `drive` + `spreadsheets`
(`settings/publish.yml → auth`; токен-кэш — сам ADC-файл
`~/.config/gcloud/application_default_credentials.json`, override —
`$GOOGLE_OAUTH_TOKEN_CACHE`). Логин:

```bash
just -f ~/.ai/scripts/gcloud/Justfile adc-login account=hnkovr@gmail.com   # браузер ДОБИТЬ
```

История выбора: OAuth-токен AGD-gen умер (`invalid_grant` — 7-дневная смерть
refresh-токенов у клиента в Testing-статусе), у сервис-аккаунтов нет storage-квоты на
Drive (а на личном аккаунте нет Shared Drives), у gcloud-клиента refresh-токен
долгоживущий. Попутно починен корневой баг ADC-ленты — `just` не имеет именованных
аргументов, `adc-login account=X` кормил gcloud `--account="account=X"`
([hnkovr/.ai#8](https://github.com/hnkovr/.ai/issues/8)); write-скоупы закреплены в
дефолтах `reset-google-account-creds`. `publisher/auth.py` принципиально **не умеет**
интерактивный флоу (google_auth_oauthlib не импортируется): мёртвый токен = громкий
RuntimeError с командой починки.

## Чек-лист первого живого прогона

1. Добить браузерный консент (`adc-login` выше) — появится ADC-файл.
2. Смок: `python -m publisher status` (или scratchpad-смок) — refresh, Drive list,
   canEdit листа.
3. `just publish-init-drive` → вставить id в `settings/publish.yml → drive.folder_id`.
4. `just publish-new-dry` → глазами; затем первый прогон на неучебной деке:
   `just publish-new --deck MLInside_OGIP-Open-Games-Intelligence-Platform`.
5. Все деки: `just publish-new`. Проверить: стабильность URL на ребилде (та же ссылка),
   идемпотентность повторного прогона («nothing to do»), 3 колонки в листе без дублей.
6. Запинить реальное имя таба в `settings/gsheet.yml → mapping.tab`.

## Известные ограничения

- Переименование `out_name` осиротит старый Drive-файл (новый создастся под новым именем) —
  ручная уборка в Drive.
- Ревизии Drive копятся при каждом update (обрезаются гуглом ~30 дней / 100 ревизий для
  бинарников) — не блокер.
- `anyone_reader` — ссылка открываема всем, у кого она есть (снимается
  `drive.share: none`).
- Лист должен быть расшарен hnkovr@gmail.com как **Editor**, иначе sheet-лег ловит 403
  (TG/Drive при этом работают — изоляция легов).
