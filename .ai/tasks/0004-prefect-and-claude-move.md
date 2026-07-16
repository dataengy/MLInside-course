# 0004 · Prefect-flow + перенос `.claude`→`.ai/.claude` (оставшийся тулкит)

**Приоритет:** p2 · **Область:** src/prefect, .ai

## Prefect-оркестрация (`src/prefect/flow.py`)
- Flow: `load_content → render_pptx / render_html (параллельно) → publish` (publish-таск шеллит
  `~/.ai/scripts/publish/publish-deck.sh` или пропускается флагом).
- Net-new (в webinar-maker Prefect нет — там ThreadPoolExecutor + TG-бот). Зависимость `prefect` — в extras.
- Дать recipe `just flow`.

## Перенос `.claude`→`.ai/.claude` (осторожно!)
- Claude Code читает настройки только из `<root>/.claude/` (наш Stop-хук авто-публикации тоже).
- План: `mkdir .ai/.claude && mv .claude/* .ai/.claude/ && rmdir .claude && ln -s .ai/.claude .claude`,
  затем **проверить**, что Claude Code видит настройки/хук; **если сломалось — вернуть в корень**.
- Делать в отдельной сессии/шаге (риск сломать текущую конфигурацию).
- Предложенный хелпер `claude-to-ai` (script+skill) автоматизирует перенос+симлинк+проверку+fallback.
- Также: `.ai/{AGENTS,CLAUDE}.md` (RU, слоями поверх README) + корневой `README.md`/`README-ru.md` с картой agentic-файлов.
