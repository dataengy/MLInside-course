---
name: recyclebin-instead-of-delete
description: "Убирая файлы — переносить в ../.recyclebin, удалять только точный дубль по sha256, историю удалений вести всегда"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c54a29a2-df84-435d-b63a-c8cc7c3c341d
  modified: 2026-09-01T18:22:45.862Z
---

Решение владельца от 2026-09-01: убирая файлы, не удалять их, а переносить в
`../.recyclebin` — каталог рядом с репозиториями (`/Users/user/gi/@dataengy/.recyclebin`).
Исключение одно: файл, чьё содержимое побайтово совпадает с уже сохранённой копией, —
такой можно удалить, но запись обязана попасть в журнал `.recyclebin/.history.csv`
(колонки `ts_utc,action,path_from,repo,sha256,size_bytes,kept_at,reason,actor`).

**Why:** «восстановимо из git» верно только пока цел коммит. За один день 2026-09-01
ветка `worktree-preza-dbt-v4-0-2` была создана, слита, удалена, пересоздана и удалена
снова; под `git-lfs` указатель в истории остаётся, а объект уезжает в GC вместе с
последним ref. Отдельно опасны заигнорированные каталоги (`.tmp/build/`,
`data/generated/`): их не видит ни `git status`, ни проверки `worktree_land.sh`, и
оттуда файл исчезает молча — там час ручной правки деки прожил вне git и уцелел
случайно.

**How to apply:** перед любым `rm`, `git rm`, `git worktree remove`, `git clean` —
`just recycle <путь>` (или `scripts/recycle.sh`). Для дубля `just recycle --dup-of
<сохранённая копия> <путь>`: скрипт сам сверит sha256 и откажет, если они разошлись.
Скрипт также отказывается трогать файл, открытый другим процессом (`lsof`) — 2026-09-01
`git rm` снёс .pptx, открытый в PowerPoint, пришлось восстанавливать. Если файл надо
убрать ИЗ ВЕТКИ, но оставить на диске — это `git rm --cached`, а в журнал пишется
`untracked-duplicate`. Правило целиком — [[deck-versioning-semver]] соседствует в том же
репозитории; спека в скилле `recyclebin`, настройки в `settings/config.yml` → `recyclebin`.
