# MLInside-course · AI-воркспейс (`.ai/`)

Дополнительное пространство для agentic-работы (не заменяет корневой `.claude/`).

> **Важно:** `.claude/` живёт в **корне** репозитория — Claude Code читает настройки только оттуда
> (там же Stop-хук авто-публикации колод). Перенос `.claude`→`.ai/.claude` — отдельная задача
> [`tasks/0004`](tasks/0004-prefect-and-claude-move.md) (с проверкой и откатом).

## Что где
- `tasks/` — бэклог задач (PDF-движки, MLE-контент, Prefect, перенос `.claude`).
- `memory/` — версионируемая копия памяти Claude Code (живёт в `~/.claude/projects/<slug>/memory/`,
  вне git): `just memory-check|push|pull`, [README](memory/README.md).
- `.codex/`, `skills/{local,global/{symlinks,hardlinks}}` — под будущую AI-оснастку проекта.

## Генератор презентаций `preza_gen` (v3)
- Код: `../src/preza_gen/` — `utils.py` (логгер/хелперы), `settings.py` (`Config`/`Content`),
  `build_deck_v3.py` (CLI), `build_deck_v3.yml` (настройки+контент), `renderers/{pptx,html,pdf}.py`.
- Один content-model → 3 рендерера. Внешние входы (шаблон, исходная колода) **хардлинкнуты** в
  `../data/source/`, манифест — `../settings/files.yml`. Вывод — `../data/generated/` + hardlink в
  `~/Downloads/MLInside_*.pptx` (для publish-хука).
- Сборка/отправка:
  ```
  just build         # pptx + html
  just build-all     # + pdf (LibreOffice/soffice; tasks/0001-0002 закрыты → tasks/.done/)
  just send          # → Telegram-топик 118
  just test          # pytest src/tests
  ```
- Авторство в колоде убрано; титул/финал подогнаны под референсные MLInside-колоды.
