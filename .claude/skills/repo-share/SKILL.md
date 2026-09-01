---
name: repo-share
description: 'Доступ к репозиториям курса MLInside: кто чем владеет, у кого какие права, что чинить после переноса или добавления сабмодуля. Оборачивает scripts/repo-share.sh (just repo-share-doctor / just repo-share) и хранит проектные факты — два аккаунта, восемь репозиториев, переезд под dataengy 2026-09-01. Триггеры: "не клонируется сабмодуль", "нет доступа к preza_gen/picstore", "выдай права на репозитории курса", "кто владеет репозиториями курса", "just repo-share".'
---

Курс живёт в восьми репозиториях и работается из **двух** аккаунтов GitHub. Какой из них
отдаст keychain конкретной машины — заранее неизвестно, поэтому оба держатся `admin`
везде. Общие механики GitHub API — в глобальном скилле `github-repo-ownership`;
здесь только проектное.

## Сначала — диагностика

```bash
just repo-share-doctor      # матрица доступа, ничего не меняет
just repo-share             # довести всех до admin, идемпотентно
```

`doctor` падает с кодом 1, если хоть у кого-то не `admin`. Список репозиториев берётся
из `.gitmodules` + `EXTRA_REPOS` в скрипте — новый сабмодуль попадает в проверку сам,
руками список править не надо.

## Устройство

| Репозиторий | Видимость | Что это |
|---|---|---|
| `dataengy/MLInside-course` | public | зонтичный репозиторий курса |
| `dataengy/preza_gen` | private | генератор дек (`src/preza_gen`) |
| `dataengy/picstore` | private | каталог картинок (`src/picstore`) |
| `dataengy/librarian` | public | `src/librarian` |
| `dataengy/mlinside-hw-olist` | public | ДЗ по dbt и Dagster (`homework/`) |
| `dataengy/mlinside-dagster-demo` | public | демо-проект лекции (`data/code/dagster_demo`) |
| `dataengy/hse-dz45-dbt-project` | private | архивное зеркало ВШЭ (`data/code/dbt_project`) |
| `dataengy/hse-dz45-clickhouse-hw` | private | архивное зеркало ВШЭ (`data/code/clickhouse_hw`) |

Аккаунты: `hnkovr` и `dataengy`. Оба должны быть залогинены — `gh auth login --user <acct>`;
скрипт берёт токены явно и **не** трогает активный аккаунт `gh`.

## 2026-09-01: переезд под dataengy

Все сабмодули раньше были под `hnkovr/*` и переехали под `dataengy`, чтобы у курса был
один владелец. Последствия, которые всплывают до сих пор:

- **В чужом чекауте после `git pull` обязательно:**
  ```bash
  git submodule sync && git submodule update --init --recursive
  ```
  Без этого он продолжает ходить по старым адресам через редирект GitHub. Редирект работает,
  но полагаться на него не стоит.
- Права `hnkovr` после переноса откатились на `write`: GitHub оставляет прежнего владельца
  коллаборатором, а `PUT collaborators/{user}` существующему коллаборатору **молча не
  повышает право**. Это закрыто в `grant()` — remove-then-invite. Если снова увидишь `write`
  там, где ждёшь `admin`, — причина почти всегда эта.

## Когда доступ всё равно не работает

1. `just repo-share-doctor` — увидеть, чего не хватает, и кому.
2. Если `none` у аккаунта, который точно залогинен, — протухший токен:
   `gh auth login --user <acct>`.
3. Если сабмодуль не клонируется, а доступ есть, — дело не в правах, а в том, какую
   личность отдаёт credential helper: см. заметку 2 в `scripts/repo-update.sh`.
4. Добавили сабмодуль — просто прогнать `just repo-share`, список подхватится сам.
