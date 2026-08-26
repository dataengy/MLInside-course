# CLAUDE-curr-status — MLInside-course

## Session 2026-08-26 — репозиторий подготовлен к переезду на MacBook M1

**Что сделано** ([#1](https://github.com/dataengy/MLInside-course/issues/1), скилл
`prepare-repo-for-new-workstation`): инвентаризация всех копий (1 клон, 2 воркtree, 1 стэш,
6 сабмодулей) → всё сведено. `main` подтянут до `origin/main` (`git fetch origin main:main`,
без checkout — дерево общее с параллельной сессией), `feat/preza-merge` получила upstream,
machine-local стэш (`.superpowers/` в `.gitignore`) стал коммитом, ветка воркtree
`worktree-course-rules-session` целиком содержится в `origin/main` — терять нечего.
Все 6 сабмодулей чисты и запушены.

**Три дефекта переезда, найденные и закрытые:**
1. `secrets-doctor` отчитывался «зелено» при полностью отсутствующей Google-авторизации:
   кредлы publish-ленты названы в `settings/publish.yml`, а не в `.env.secrets` (там
   соответствующие переменные пустые), и проверка file-typed секретов их пропускала.
   Теперь доктор читает пути из `publish.yml` и падает с готовой командой `bw-pull-file`.
2. Рунбук бутстрапа клонировал репозиторий **до** `brew install git-lfs` — 72 LFS-объекта
   (~1.2 ГБ дек) приезжали заглушками. Порядок исправлен, добавлены `git lfs pull`,
   `just sync` и гейт.
3. Дрейф `settings/.env.secrets` ↔ шаблона (`GOOGLE_OAUTH_TOKEN_CACHE`) — закрыт, блоб
   git-secret перешифрован и проверен на round-trip (16 имён, все значения пустые).

Добавлен снимок станции `.ai/workstations/macCoreI9.yml` (+ индекс): ветка/HEAD, воркtree'ы,
id незакрытых сессий под `claude --resume`, наличие файлов секретов без значений.

**Осталось — нужно от человека:** (1) **Bitwarden-хранилище заперто** — эскроу не выполнен;
`export BW_SESSION=$(bw unlock --raw)` → `just secrets-push`, и главное — два реальных
кредла вне репозитория (`~/.config/gcloud/application_default_credentials.json`,
`~/.secrets/google-sa-for-prodamus-1-494316.json`) через `bw-push-file`: без них новая машина
получит зелёный доктор и мёртвую ленту публикации (команды — `docs/secrets-sync.md`).
(2) `uv.lock` в `.gitignore` → версии не запинены. (3) `just test` берёт `python3` с `PATH`,
а не `.venv`; `uv run python -m pytest` зелёный и собирает больше тестов — смена точки входа
меняет состав гейта, решение владельца.


## Session 2026-08-26 — preza_merge: dbt-дека слита с форком ревьюера → v3.19.1+alina-fmt

**Что сделано** ([#8](https://github.com/dataengy/MLInside-course/issues/8), Task 15 — финальная в плане `2026-08-26-preza-merge`):
проставлены решения по предложению `docs/reviews/merge/*.proposal.yml` (`accept`: R1, R2, R3,
R4, R6, R11; `reject`: R7 — капслок титула, вкус, не запрошен); `undecided: []`, `accepted_keys`
проверены. Предложение изначально несло `profile: merged` (расхождение с уже
закоммиченным профилем-заготовкой `alina-2026-08` и с пин-тестом `test_deck_selects_its_profile`,
который допускает только `{classic, alina-2026-08}`) — исправлено на `profile: alina-2026-08`
перед `apply`. `just preza-merge-apply` собрал `data/generated/MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx`
(70 слайдов); `content/preza-dbt-v3-content.yml` тронут РОВНО одной строкой (`format:`);
`alina-2026-08` в `settings/formats.yml` уточнён по факту измерений (`visual_bottom` 7.0→7.01,
`table_top` 2.45→2.47), `classic` не изменился по значениям (только YAML-форматирование).
Независимая проверка собранного файла подтвердила: 70 слайдов, обводка `2419FF` отсутствует
(только тёмная `1A1A1A`), нижние кромки визуала на 7.01″, верх таблиц на 2.47″, явный кегль
тела — 0 (весь оставшийся явный кегль — в код-панелях/текстбоксах, вне R1).
`just preza-merge-verify --contact-sheet` **завершился с кодом ≠0**: перестроенная база против
форка показывает остаточные расхождения геометрии сверх допуска ±0.4″ на части слайдов
(адаптивная ширина колонки и высота код-панелей воспроизводят решение правила приближённо, не
точную ручную подгонку каждого слайда) — ожидаемо для R2/R4 (доля < 1.0); допуски и профиль
под верификацию не подгонялись, расхождения перечислены в отчёте и в `docs/CHANGELOG.md`.
Пин `test_dbt_deck_uses_the_merged_format_profile` добавлен в `src/tests/test_content.py`,
`just test` зелёный (370 passed, 4 skipped). `just check` (ruff+ty) падает на
**предсуществующем** долге вне зоны этой задачи (лишний `zip()` без `strict=` и неиспользуемая
переменная в `src/preza_merge/{align,diff,rules,verify}.py`, unresolved-import в `src/schedule`
и `src/tests/test_schedule.py`) — не трогалось, вне scope Task 15. Открытый вопрос «Перенос
дизайн-правок менеджера в генератор» закрыт в `docs/course-qa.md` (перенесён в «Отвеченные»).

**Осталось:** форк Dagster v1.4 ([#9](https://github.com/dataengy/MLInside-course/issues/9)) —
файл менеджера ещё не скачан из чата; та же лента (`preza-merge-{propose,apply,verify}`), когда
появится. Пред-существующий lint/typecheck-долг в `src/preza_merge/*` и `src/schedule/*`
(см. выше) не устранён — не входил в scope этой задачи.

## Session 2026-08-26 — правила продакшена курса от менеджера → код, доки, хук, агент

**Что сделано** ([#7](https://github.com/dataengy/MLInside-course/issues/7)): чат с менеджером курса (Алина Веденская, @alina_3V) разобран в
правила и Q&A. SSoT скаляров — `settings/config.yml → course_production`; нарратив —
`docs/course-rules.md`; журнал — `docs/course-qa.md` (16 отвеченных, **5 открытых**
чекбоксами). План блоков записи (`recording.blocks`, id слайдов; монтаж режет уроки ≤25 мин)
для dbt (6 блоков, 70 сл. ≈ 91 мин) и Dagster (4, 49 ≈ 63.7). `src/course` +
`just preza-blocks{,-all}`, `just course-status`, SessionStart-хук
`course-production-status.sh`, сабагент `course-production-keeper`, память
`mlinside_course_production_rules`, кандидат скилла `course-rules-upsert`. Тесты 280 passed.

**Последние 3 задачи:** (1) правила / Q&A / блоки записи — этот раздел; (2) моделирование,
MV/стриминг/права в dbt-деке 62→70 сл., `preza-lint` / `preza-slides` (2026-08-25);
(3) транзиентные ретраи Google в publisher (2026-08-25).

**Незакрытое (последние 2 рабочих дня + из чата) — нужно от человека:**
1. **Дедлайн менеджера: записать всё до 2026-08-31** (5 дней; [#10](https://github.com/dataengy/MLInside-course/issues/10)). Ни одна наша лекция не
   записана, пробный клип не сделан, ПО по инструкции не подтверждено.
2. Ответить Алине ([#13](https://github.com/dataengy/MLInside-course/issues/13), [#10](https://github.com/dataengy/MLInside-course/issues/10)): баллы ДЗ (наши слайды и `HW*.md` в баллах), тест-запись, ориентир даты
   записи dbt — черновики ответов под чекбоксами в `docs/course-qa.md`.
3. Дизайн-правки Алины ([#8](https://github.com/dataengy/MLInside-course/issues/8) dbt, [#9](https://github.com/dataengy/MLInside-course/issues/9) Dagster; шрифт / отступы / обводка код-блоков) живут только в её pptx
   v3.15 / v1.4 — перенести в `content/build_deck_v3-settings.yml`, иначе v3.19 их теряет;
   затем `just publish-new` (v3.19 собрана, не издана; drive/sheet-леги по-прежнему ждут
   квоты Drive и роли Редактор — см. сессию 2026-08-19..22).
4. CI/CD-дека ([#11](https://github.com/dataengy/MLInside-course/issues/11)) — без плана блоков (хук напоминает); черновик менеджеру не отправлялся.
5. Параллельная сессия в этом же дереве (#8, `docs/preza-merge-lane.md`) — её файлы не
   трогать; коммиты только path-scoped.

## Session 2026-08-19..22 — авторизация решена, публикация ждёт двух внешних условий

**Что оказалось правдой про блокировку консента**: gcloud-клиент режет не только restricted
`drive`, но и **sensitive `spreadsheets`** — тот же логин без него прошёл сразу. Отсюда
**две ленты кредлов** (`b0cac14`): Drive ← user-ADC hnkovr@gmail.com (`drive.file`,
quota-проект вешается на кредл, машинный ADC не трогаем), лист ← сервис-аккаунт
`gsheets-reader@for-prodamus-1-494316…`. Папка Drive создана
(`drive.folder_id` в `settings/publish.yml`), TG-лег отработал на всех шести деках.

**Осталось внешнее** (обе — действия человека, код готов):
1. место на Drive `hnkovr@gmail.com` — 98.70 GiB при лимите 15 → `storageQuotaExceeded`;
   владелец расширяет квоту, дальше `just publish-new --only drive`;
2. роль **Редактор** на листе для `gsheets-reader@…` (`canEdit=false`) →
   `just publish-new --only sheet`.

Репетиция листа по живым данным (`978f677`): таб `Sheet1`, тема в **B**, колонки встанут в
**E/F/G**, деки в строки 5/6/7/9 (Prefect и OGIP законно без строки). Отказы теперь
переводятся в действие (`publisher/errors.py`), ворота проверяются
`.tmp/probe_google_access.py`. Хук `deck-publish-status.sh` больше не противоречит себе
(`db8fc69`). Тесты: 248 passed, 4 skipped.

## Session 2026-08-16..18 — публикационная лента: TG + GDrive (вечный URL) + колонки листа

**Код-комплит, закоммичено** (`dcad8e6` → [#6](https://github.com/dataengy/MLInside-course/issues/6)):
`src/publisher/` + `just publish-new{,-dry}`/`publish-status`/`publish-init-drive` +
SessionStart-хук `deck-publish-status.sh` + 43 теста (suite 251 зелёный). Порядок легов
drive→tg→sheet, изоляция, ретрай только не-ok, курсор + git-tracked `published:`-блок.
Spec: [docs/deck-publish-pipeline.md](../docs/deck-publish-pipeline.md).
Попутно **починен корневой баг ADC-ленты** (`just` без именованных args → gcloud получал
`--account="account=X"`; [hnkovr/.ai#8](https://github.com/hnkovr/.ai/issues/8), ~/.ai
`de2c45b`), write-скоупы drive+spreadsheets в дефолтах `reset-google-account-creds`;
мёртвый AGD-gen OAuth-токен (invalid_grant) удалён из ~/.secrets.

**Ждёт ТОЛЬКО браузерного ADC-консента** (логин слушает :8085, вотчер на ADC-файл
взведён): смок → `publish-init-drive` (folder_id в settings/publish.yml) → dry →
первая публикация OGIP → все деки → пин имени таба. Чек-лист — в спеке.

## Session 2026-08-13..16 — акцентная ось ЖИВА: тезисы листа → accents → 12/12 hit

**Блокер акцентной оси (2026-07-27) РАЗРЕШЁН.** Полная лента поднята и прогнана:
`settings/gsheet.yml` (полная карта колонок, «тезисы»→accents) → `just presentations-plan`
(4 updated / 4 added-голых / 3 stale, dbt-topic переименован под «название» листа) →
`just preza-review-all`: **dbt, Dagster, CI/CD+Obs — 12/12 акцентов hit, 0 err/0 warn**;
`hit_ratio: 0.75` подгонки не потребовал. Закрыта
[.ai/tasks/.done/0006](../.ai/tasks/.done/0006-review-accents-axis.md). Spec ленты:
[docs/schedule-gsheet-lane.md](../docs/schedule-gsheet-lane.md).

**Оговорка по транспорту**: ADC-консент в браузере так и не был добит (3 дня, 4 попытки) —
первый дамп `settings/schedule.yml` получен через claude.ai Drive-коннектор в формате
`fetch_raw` (данные листа сверены дважды, 13.08 и 16.08 — идентичны); `plan`-шаг и всё
дальше — штатный код. Фоновый `adc-login` ещё слушает :8085; после консента пересинк —
`just gsheet-dump && just presentations-plan` (идемпотентно).

**Деки под 12 акцентов** (точечные правки, без реструктуризации): dbt 51→**52** слайда
(новый `052-sloi-dbt-proekta`; без штампа — рукописная), Dagster 50→**51** (новый
`051-ml-pajplajn-kak-cepochka-assetov`; штамп v1.1 model=claude-fable-5), CI/CD 40→**42**
(новые `051-sborka-docker-obraza-v-ci`, `052-fastapi-instrumentaciya-prometheus`; штамп
v1.1). `slides_max` 50→55. Сборка: dbt v3.14 / Dagster v1.3 / CICD v1.3 (pptx+html,
хардлинки в ~/Downloads). Тесты: 21 passed (счётчик dbt 52; +тест нумерованного сплита).

**Новая обвязка**: хук `scripts/hooks/preza-accents-status.sh` (SessionStart), суб-агент
`.claude/agents/preza-accents-keeper.md` (scope: project; зеркало в `~/.ai/agents/`
отложено — канонический репо грязный и не на main), память
`schedule_gsheet_accents_lane`, `~/.ai/projects/MLInside-course/README.md`, скилл
`preza-review` дополнен и заново захардлинкен (каталог=глобал=репо).

**Наш Airflow-дек: 3/4 акцентов** (partial по XCom-тезису) — лекция Влада, вне скоупа
этой сессии; чужой импортный Airflow-дек по-прежнему error (заглушки; открытый вопрос 0005).

## Session 2026-08-11 — workstation bootstrap: всё закоммичено и ЗАПУШЕНО

**Push-блокер РАЗРЕШЁН.** Причиной «Repository not found» была потеря collaborator-доступа
hnkovr к приватному `dataengy/MLInside-course` (репо цел, не удалён): re-invite от аккаунта
dataengy (второй в gh keyring) + accept → `main` запушен (`57460a4..442ff4a`, 21 коммит,
LFS ok). Все 6 сабмодулей и отдельный клон `~/github/@dataengy/mlinside-hw-olist`
сверены с live-remote (`ls-remote`) — в синхроне.

**Tracker включён**: репо теперь реально использует GH Issues —
[#1](https://github.com/dataengy/MLInside-course/issues/1) зонт этой сессии,
[#2](https://github.com/dataengy/MLInside-course/issues/2)–[#5](https://github.com/dataengy/MLInside-course/issues/5)
ретро-биндинг июльских коммитов (`git filter-branch --msg-filter` по unpushed-диапазону —
после пуша так уже нельзя). Гейт `sc-verify-tracker-binding` (SC_TRACKERS=github) зелёный.

**Secrets — два лейна** (`scripts/secrets-sync.sh`, `just secrets-*`, ранбук
`docs/secrets-sync.md`): Bitwarden secure notes (транспорт) + git-secret
(`settings/.env.secrets.secret` закоммичен; ключ `tg-eventer <hnkovr@gmail.com>`).
`settings/.env.secrets.template` = контракт имён; `just secrets-doctor` зелёный.
**⏳ PENDING (нужен мастер-пароль):** `export BW_SESSION=$(bw unlock --raw)` →
`just secrets-push` + `bash scripts/secrets-sync.sh bw-push-gpg`.

**Новое в .claude/**: агент `workstation-bootstrapper` (инвариант «committed/pushed/
reproducible»), SessionStart-хук `scripts/hooks/repo-sync-status.sh` (ahead/dirty/
submodule-drift/staleness `.secret`-блоба; сработает со следующей сессии).

**⚠️ ОТКРЫТО (не решено этой сессией):** конкурирующие семьи колод. Codex-драфты
`content/preza-{dagster,prefect,cicd-observability}-v1-content.yml` ЗАКОММИЧЕНЫ ради
сохранности (два из трёх ниже минимума 20 слайдов), но Justfile по-прежнему указывает
на длинноимённую семью — вопрос «какая семья каноническая» остаётся за пользователем
(см. блокер сессии 2026-07-27 ниже). Тесты: 201 passed (счётчики dbt-деки обновлены
под Olist-ДЗ: 51 слайд, 14 код-панелей).



**Shipped** (5 commits `547b499..7765d86` here + `a8ad588` in `~/.ai`):

- `integrations/google/sheets/` — first `integrations/` dir. `connector.py`/`utils.py`/`__init__.py`
  **hardlinked** from `~/pdp.deploy_dev/scripts/tools-utils/gsheets` (registry:
  `~/.ai/integrations/_relink-actualized.py`). Editing them changes pdp too — re-link with
  `ln -f` after any editor save. Project-owned `auth.py` = ADC-first branch.
- `src/schedule/` — `python -m schedule {tabs,dump,plan,show}`; `content/presentations.yml`
  seeded by hand with the 5 decks. `just gsheet-*` / `presentations-*` / `preza-review*`.
- `/preza-review` — catalog skill + `create-preza-about-de-tool/scripts/review_content.py`;
  tunables in `preza-review/settings/review.yml`. Reports → `docs/reviews/`.

**⚠️ BLOCKER — the accent axis is untested.** `just gsheet-tabs` needs Application Default
Credentials. Two `gcloud auth application-default login --account=hnkovr@gmail.com` runs were
started and both stopped before consent, so `~/.config/gcloud/application_default_credentials.json`
does not exist. gcloud **forces** `cloud-platform` into the scope list (a sheets-only list is
rejected), and `print-access-token --scopes=…sheets` cannot mint one non-interactively.
Alternative that needs no gcloud login: share the sheet with
`gsheets-reader@for-prodamus-1-494316.iam.gserviceaccount.com` and add this repo to that
account's `projects:` in `~/.ai/settings/gcloud.yml`.
Next: `just gsheet-tabs` → `gsheet-dump` → write `settings/gsheet.yml` with the real headers →
`just presentations-plan` → `just preza-review-all`.

**⚠️ PUSH BLOCKED — needs a decision.** 8 commits ahead on protected `main`:
- the tracker gate marks all 8 unbound (this repo has never used tracker refs);
- pushing carries the parallel session's 3 picstore commits along with mine.

**Parallel-session collision (resolved, worth knowing).** `ffab5c2` committed a `Justfile` newer
than the copy on disk; committing the working copy would have deleted three `picstore-*` recipes.
It also appended a **second** picstore block without removing the first → duplicate `_picstore`
variable + duplicate recipes → `just` refused to parse *anything*. `c1b267a` restores their
version, re-applies my recipes and removes the redundant block (all 10 unique picstore recipes
kept). **Lesson: re-read the Justfile from disk and run `just --list` before every commit here.**

**Known-red:** `just preza-review content/preza-dbt-v3-content.yml` exits 1 — that deck has no
provenance stamp in its first/last notes (pre-existing; it is the one deck excluded from
`preza-validate-all`). Fix with `just preza-stamp`.

**Left uncommitted on purpose:** `.ai/.codex/`, `.tmp/.last-review-nudge`, the three
`content/preza-*-v1-content.yml` Codex drafts, `src/preza_gen.egg-info/` (wants gitignoring),
`src/picstore` submodule pointer.

## Interrupted Task

> Interrupted: 2026-07-27 — resume with: `claude --resume 799821fd-9e53-4233-b48d-7962c4feaacb`

**Task:** три задачи по колодам (dbt / Dagster / Prefect / CI/CD+Observability / Airflow),
каждая с директивой «предложи скрипт/скилл + `/save-all-deterministic-for-skill-as-scripts` + code standards + хуки при необходимости»:

1. **Отправить последнюю версию каждой колоды в Telegram** (топик MLInside 118, `~/.ai/scripts/telegram/tg-send-file.sh`, чат `-1002281796095`).
2. **Заархивировать все НЕпоследние версии** в `.archive/` внутри их исходного пути (`data/generated/.archive/`).
3. **Убедиться, что весь сгенерированный контент в git через git-LFS.**

**Reached (обследование готово, ничего ещё не сделано):**
- `data/generated/` содержит 26 файлов, но **целиком в `.gitignore`** (строка 20) → ничего не трекается.
- `.gitattributes`: есть LFS-правила для pptx/pdf/mov/key/mp4/zip/docx/xlsx — **нет правила для `*.html`**.
- Последнее в TG (топик 118) уходило **v3.4** dbt; на диске **v3.13**.

**⚠️ БЛОКЕР — по каждому сюжету на диске ДВЕ конкурирующие семьи колод (мои vs Codex-сессии):**

| сюжет | Codex-билд | мой билд (совпадает с закоммиченными content/) |
|---|---|---|
| Dagster | `MLInside_Dagster_v1.4` | `MLInside_Современная-оркестрация-ML-пайплайнов-Dagster_v1.2` |
| Prefect | `MLInside_Prefect_v1.1` | `MLInside_Современная-оркестрация-ML-пайплайнов-Prefect_v1.2` |
| CI/CD | `MLInside_CICD_Observability_v1.1` | `MLInside_Автоматизация-и-мониторинг-CICD-Prometheus-Grafana_v1.2` |
| Airflow | — | `MLInside_Оркестрация-данных-Apache-Airflow_v1.1` |
| dbt | — | `MLInside_Введение-в-dbt_v3.13` |

Наивный «max version per name» отправит ОБЕ Dagster-колоды, и Codex-овская v1.4 > моей v1.2 (но это 31-слайдовый черновик). **Нужно решение пользователя, какая семья каноническая, ПЕРЕД отправкой/архивацией.**

**Remains:**
- Получить решение по конкурирующим семьям (это тот же незакрытый вопрос про `preza-*-v1-content.yml`).
- Реализовать 3 задачи скриптами (предложить: `deck-publish-latest.sh`, `deck-archive-old.sh`, git-LFS через существующий скилл `git-lfs-setup` + un-ignore `data/generated/` с LFS для html).
- ⚠️ **DISK-CRITICAL: 4Gi свободно** — писать осторожно, LFS-добавление больших файлов может упасть.

**Resume CLI:**
```bash
claude --resume 799821fd-9e53-4233-b48d-7962c4feaacb
```

---

> Автогенерируемая часть (git/submodule/env/deck) — `just ctx` (см. «Как обновлять»).
> Обновлено: 2026-07-19. Ведётся **несколькими агентами** (Claude Code + Codex) в одном рабочем дереве.

## Кто и где работает (важно!)

Задача велась **параллельно в Claude Code и Codex** в одном worktree. Отсюда:
- версии колоды скачут (каждый билд бампит `_v3.N` — автоинкремент), контент при этом может быть идентичным;
- правки одних и тех же файлов из двух агентов → **перед правкой всегда перечитывай файл с диска**, не доверяй контексту.

Свежие Codex-сессии: `~/.codex/sessions/2026/07/17/rollout-2026-07-17T01-45-*.jsonl`, `…T01-11-*.jsonl`.

## Последние 3 завершённые задачи

1. **`077da45`** (2026-07-19) — **Librarian-ингест**: iCloud `_2025-11-ВШЭ_ВНЕШНЕЕ_ОБУЧЕНИЕ` +
   dbt-материалы из `~/Downloads` + бывший `assets/` → `data/` (46 перемещений: 11 текущих дек +
   21 в `.history/`, 13 docs, 2 записи; sha256-дедуп, 16 точных дублей удалено из iCloud,
   маркер `_MOVED-TO-REPO.md`); `data/CATALOG.md` + `data/reviews.yml`; git LFS (~800MB).
2. **`2645a9a`** (2026-07-19) — сабмодуль **`hnkovr/librarian`** → `src/librarian`
   (dedupe/categorize/version-stack/catalog, 24 теста) + `just librarian-*` + `docs/data-structure.md`.
3. **`f3d8ca4`@preza_gen** — закоммичена и запушена вся WIP-работа Codex в сабмодуле
   (soffice-pdf, `_fit_code_box`, preza_refactoring) + пути `assets/` → `data/decks/`.

## Текущее состояние

**Новое (2026-07-20): генератор дек по DE-инструментам.**
Канонический скилл `create-preza-about-de-tool` (+ саб-скиллы `preza-de-outline`/`-stamp`/`-validate`)
в `~/.ai/skills/_catalog/docs/pptx/`; в репо проброшен **двумя способами** —
хардлинк `.claude/skills/<slug>/skill.md` и симлинк-директория `.claude/skills-canonical/<slug>`
(в каждом `NOTES.md` с объяснением). Детерминированные скрипты: `validate_content.py`,
`stamp_provenance.py`, `resolve_slug.py`, `build_deck.sh`, `port-skill-local.sh`.
Политика в `settings/config.yml → deck_generation` (20..50 слайдов, профиль `code-tables`,
штамп `model/harness/effort/version` в заметках первого и последнего слайда).
Новые деки: **Dagster — 50 слайдов** (25 код-панелей, 10 таблиц), **Prefect — 30**,
**CI/CD + Observability — 40**, **Apache Airflow — 40** (см. `docs/CHANGELOG.md`).
Гейт: `just preza-validate-all` (4 деки, все зелёные).

⚠️ **Требует решения:** на диске лежат незакоммиченные черновики прошлой Codex-сессии
`content/preza-{dagster,prefect,cicd-observability}-v1-content.yml` (31/17/17 слайдов).
Два из них **ниже минимума в 20 слайдов**. Justfile перенаправлен на новые файлы;
черновики **не тронуты** — нужно решить: оставить, слить или отправить в `.stash/`.

**Колода (dbt):** 48 слайдов · 13 код-слайдов · 16 картинок · 7 таблиц.
Сборка: `data/generated/MLInside_Введение-в-dbt_v3.N.{pptx,html,pdf}` → хардлинк в `~/Downloads`.
В TG (топик 118) последним уходил **v3.4** (43 слайда) — **новые 48-слайдовые версии ещё не отправлялись**.

**Окружение:** LibreOffice 26.2.4 (`soffice`) + poppler (`pdftoppm`) установлены → доступен
честный QA: `pptx → pdf → png` настоящими шрифтами (qlmanage даёт serif-фолбэк — **не баг колоды**).
Диск: ~3.4Gi свободно (79% занято) — **узкое место**, уже ловили `ENOSPC`.

## Незакрытое (последние 2 рабочих дня)

- ✅ **iCloud-ингест ЗАВЕРШЁН (2026-07-27)**: все evicted-файлы скачаны и перенесены
  (32 действия: Семинар12/14, Практикум-по-dbt 76MB, лекции/ДЗ/зипы, Dagster mp4);
  ДЗ-репо → приватные зеркала `hnkovr/hse-dz45-{dbt-project,clickhouse-hw}` + submodules
  `data/code/`. В iCloud остался только маркер + 2 tmp-мусора — папку можно удалять.
  (upload-квота iCloud всё ещё исчерпана — на нас не влияет.)
- ⚠️ `just typecheck` — 22 pre-existing диагностик в `preza_gen/preza_refactoring` (lint/тесты зелёные, 49 passed).
- ⚠️ v6-дека: метаданные автора не очищены; `dbt-final-verify` завязан на v4-снапшот (см. `data/reviews.yml`).
- 🐞 **Пофикшен overflow код-панелей** (в сабмодуле, тоже незакоммичено): `_fit_code_box` считал
  **логические** строки, а длинные строки **переносятся** → код вылезал за пределы панели
  (на «dbt_utils в деле» обрезался `{% endif %}`). Теперь: `_visual_lines`/`_code_height` учитывают
  перенос, `_fit_code_size` **уменьшает шрифт** (13 → до `min_size: 9`), пока обёрнутый текст не влезет.
  `_CHAR_W_EM = 0.72` — worst-case ширина моноширинного глифа (LibreOffice подставляет шрифт шире
  Consolas; замер по реальной панели). Тесты: `src/preza_gen/tests/test_layout.py` (+3 регрессии).
  Ужимаются 2 слайда: «Инкрементальная модель», «dbt_utils в деле» → 12.5pt.
- 🧹 Мусор: `content/preza-dbt-v3-content.yml.bak1`, `src/preza_gen.egg-info/`,
  `~$*.pptx` (lock-файлы открытого PowerPoint) в `data/generated/` и `assets/decks/`.
- ⛔ **Task #1** — GitHub projects/issues для MLInside-course & preza_gen: заблокировано gh-идентичностью,
  handoff-скрипт `.tmp/create-github-issues.sh` (запускает пользователь).
- 📋 Бэклог: `.ai/tasks/0001-pdf-weasyprint`, `0002-pdf-chromium` (**частично закрыты** soffice-путём),
  `0003-mle-content`, `0004-prefect-and-claude-move`.

## Полезные скрипты

| Скрипт | Что делает |
|---|---|
| `.tmp/render_pdf_pages.py` | pptx→pdf→png выбранных страниц (**честный** QA через LibreOffice+poppler) |
| `.tmp/audit_code_slides.py` | плотность код-слайдов и итоговая раскладка (side/full) |
| `.tmp/render_slides.py` | qlmanage-превью слайда (быстро, но **serif-фолбэк**) |
| `.tmp/verify_deck.py`, `extract_source.py` | проверка колоды / извлечение текста исходника |

## Следующие шаги

1. Починить iCloud (сеть/квота) → дозагрузить evicted-файлы (#8), затем ДЗ-репо → submodules (#5).
2. Честный QA (`.tmp/render_pdf_pages.py`) по 48-слайдовой колоде; TG-топик 118 (там всё ещё v3.4).
3. Очистка метаданных v6 + перевод `dbt-final-verify` на конфиг; типчек preza_refactoring.
4. Рассмотреть `docs/data-structure.md` (per-course nesting, link-stubs для >100MB записей).

## Как обновлять

Детерминированная часть — скриптом (см. `scripts/ctx-snapshot.*` / `just ctx`), а не руками:
git-лог, submodule-статус, факты колоды, версии инструментов, диск, следы Codex/Claude-сессий.
