# HANDOFF — лента публикации дек + исключение чужой деки (2026-08-26)

Снимок keep-листа перед компакцией. Заменяет `.claude/KEEP-2026-08-22.md` (удалён,
содержимое устарело; версия остаётся в истории git). Сессия работала в worktree
`airflow-editing-skip` и пушила в `main` через `push origin HEAD:main` — общий checkout
всё это время держала чужая сессия на `feat/preza-merge`, его не трогали.

## Открытые задачи

| # | Состояние | Чего ждёт |
|---|---|---|
| [#6](https://github.com/dataengy/MLInside-course/issues/6) Drive-лег | код готов, папка создана | **места на диске** `hnkovr@gmail.com` |
| [#6](https://github.com/dataengy/MLInside-course/issues/6) Sheet-лег | код + SA-лента прописаны, репетиция сошлась | роли **Редактор** для SA на листе |

Трекер репо — GitHub Issues; Jira запрещена. Коммиты привязываются `(#N)`.

## Сделано (коммиты в `main`)

- `db8fc69` — хук `deck-publish-status.sh`: раздельно «⚠ собрано новее» и «ⓘ леги не
  завершены» (раньше печатал самопротиворечивое «не опубликованы свежие версии …
  (издано: та же версия)»).
- `b0cac14` — **две ленты кредлов**: Drive ← user-ADC `hnkovr@gmail.com` (`drive.file`),
  лист ← SA `gsheets-reader@for-prodamus-1-494316…` (`spreadsheets`); quota-проект
  вешается на кредл (`with_quota_project`), машинный ADC-файл не трогаем. Папка Drive
  `1L-Jau_Xl78f_dXA611grdsKnxLUKU5Tp`.
- `602953b` — честная запись `published.legs.drive: error` после отказа по квоте.
- `978f677` — `publisher/errors.py` (отказ → действие) + `.tmp/probe_google_access.py`
  переписан в проверку ворот с репетицией записи листа.
- `3bf9ad9` — `publisher/gapi.py`: транзиентные 5xx/429 ретраятся, политика (403/404) — нет.
- `d21d32c` — **дека Airflow выведена из-под наших правок** (`#7`): ключ
  `settings/config.yml → deck_generation.editing_excluded`, запрет на единственной точке
  записи `scripts/preza/edit_slides.py::_write`, инвариант 10 у `preza-accents-keeper`,
  раздел «Кто есть кто» в `docs/course-rules.md`, тесты `src/tests/test_editing_excluded.py`.

Тесты: `just test` — **285 passed, 4 skipped**. Ruff: мои файлы чисты (в
`edit_slides.py` остался ОДИН пре-существующий B904 — он был там и до правок).

## Что НЕ сделано и почему (саммари теряет это первым)

1. **Drive-загрузка** — не права, а **место**: `hnkovr@gmail.com` занимает 98.70 GiB при
   лимите 15 (сам Drive — 0.07, переполнены Gmail/Photos), аплоад отвечает
   `storageQuotaExceeded`. Владелец **решил остаться на этом аккаунте и расширить квоту**
   («Use hnkovr, space is not a problem (I'll increase it)») — не предлагать смену
   аккаунта заново. После расширения: `just publish-new --only drive`.
2. **Колонки листа** — нужна роль **Редактор** для
   `gsheets-reader@for-prodamus-1-494316.iam.gserviceaccount.com` (сейчас Viewer,
   `canEdit=false`). Ключ уже прописан в `settings/publish.yml#auth.sheet`.
   После выдачи: `just publish-new --only sheet`.
3. Репетиция записи листа по живым данным сошлась: таб `Sheet1`, тема в колонке **B**
   («название»), три колонки встанут в **E/F/G**, деки — в строки 5/6/7/9; Prefect и OGIP
   законно без строки (`skipped`).

## Решения, которые НЕ пересматривать

- **Две ленты кредлов.** Экран согласия gcloud блокирует и restricted `drive`, и
  **sensitive `spreadsheets`** («This app is blocked»); тот же логин без `spreadsheets`
  проходит. Не возвращать ни один из двух скоупов в ADC-ленту.
- `auth.scopes` обязан совпадать с реально выданным — google-auth роняет `RefreshError`
  на невыданный скоуп.
- Ретраятся ТОЛЬКО транзиентные коды; 403/404 — работа человека, повтор её оттягивает.
- Дека Apache Airflow — предмет Влада Бояджи: читаем, не правим (см. `d21d32c`).
- dbt-дека рукописная — провенанс-штамп ей не ставить никогда.
- Правки — в worktree; в общем checkout никаких `git reset`/`checkout`/`stash`.

## Файлы, которые должны существовать после компакции

- `src/publisher/**` (+ `gapi.py`, `errors.py` и их тесты)
- `settings/publish.yml` (две ленты, `drive.folder_id`, `api.retries`),
  `settings/config.yml` (`deck_generation.editing_excluded`)
- `scripts/preza/edit_slides.py` (запрет правки), `src/tests/test_editing_excluded.py`
- `docs/deck-publish-pipeline.md`, `docs/course-rules.md`, `docs/CHANGELOG.md`
- `.tmp/probe_google_access.py` (проверка ворот + репетиция записи листа)
