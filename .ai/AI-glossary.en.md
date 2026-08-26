# AI glossary (EN)

> English & infra terms from work sessions on the MLInside 2026 course (course production
> rules, deck generation and publishing, parallel-session isolation, trackers). Each entry
> duplicates its description as a Russian translation and adds a real usage example.
> Russian-origin / russified slang lives in [AI-glossary.ru.md](AI-glossary.ru.md).
> Enrichment: skill-chain `add-terms-to-glossary` →
> `scan-session-for-new-glossary-terms-candidates` → `update-terms-glossaries`.
>
> **Marker legend** — every term is tagged:
> `[general]` = standard / transferable term, meaning holds outside this project;
> `[project]` = course/repo-specific, only makes sense with the context given here.
> Ordered simple → complex: base terms first, composites (built on them) later.
>
> **term-meta** — every entry carries a machine-readable line right after the heading:
> `<!-- term-meta {…} -->` (slug, word-form regex, translation, tag, date). Empty optional
> fields are not printed.
>
> Schema: `~/.ai/skills/.settings/docs/docs_glossarize.yml` → `docs_glossarize.term_meta`.
> Checks: `just -f ~/.ai/skills/_scripts/docs/glossary/Justfile terms-check` / `… terms-validate`.

## Quick index

| Term | Tag | Summary |
|---|---|---|
| [worktree](#worktree) | general | linked git checkout with its own HEAD/index — the only real isolation between parallel agent sessions |
| [agent-lock](#agent-lock) | general | advisory session lock over a repo — announces intent, cannot stop another session's git |
| [fail-open hook](#fail-open-hook) | general | session hook that only prints and always exits 0 — silence never means healthy |
| [fail-loud settings](#fail-loud-settings) | general | config read that raises on a missing key instead of substituting a default |
| [recording.blocks](#recordingblocks) | project | curated field in content/presentations.yml holding a deck's recording-block plan |
| [course_production](#course_production) | project | settings/config.yml section — SSoT of the course manager's production rules |
| [MAX_PROJECTS_LIMIT_REACHED](#max_projects_limit_reached) | project | Todoist free-plan 403 when active projects hit the cap (8, Inbox included) |

## worktree

<!-- term-meta {slug: worktree, match: "worktree", ru: Связанное рабочее дерево того же репозитория со своими HEAD/индексом/веткой, tag: general, added: 2026-08-26} -->

`[general]` A linked working tree of the same repository (`git worktree`, or `EnterWorktree` in Claude Code → `.claude/worktrees/<name>`). It has its own HEAD, index and branch, so another session's `git checkout` in the shared tree cannot move the branch your commit lands on.
> **RU:** Связанное рабочее дерево того же репозитория со своими HEAD/индексом/веткой — единственная настоящая изоляция между параллельными агентскими сессиями.
> **Пример:** Правки — в worktree; в main — git fetch && git rebase origin/main && git push origin HEAD:main.
> **См. также:** [общее дерево](AI-glossary.ru.md#общее-дерево), [agent-lock](#agent-lock)

## agent-lock

<!-- term-meta {slug: agent-lock, match: "agent\\-lock", ru: Совещательный лок сессии на репозиторий: заявляет намерение, но не мешает чужому git. Фолбэк, когда worktree невозможен., tag: general, added: 2026-08-26} -->

`[general]` Advisory lock a session takes on a repository (`agent-session-lock.sh acquire --repo …`), paired with `settle-check` before committing. Advisory means announced, not enforced: it does not block another session's `git checkout`, `reset` or commit.
> **RU:** Совещательный лок сессии на репозиторий: заявляет намерение, но не мешает чужому git. Фолбэк, когда worktree невозможен.
> **Пример:** Worktree невозможен → agent-lock acquire + settle-check + коммиты только `only <мои пути>`.
> **См. также:** [worktree](#worktree), [общее дерево](AI-glossary.ru.md#общее-дерево)

## fail-open hook

<!-- term-meta {slug: fail-open-hook, match: "fail\\-open\ hook", ru: Хук, который только печатает и всегда выходит 0; сломанный хук неотличим от «всё чисто», tag: general, added: 2026-08-26} -->

`[general]` A SessionStart-class hook that informs and never blocks: it swallows its own errors and exits 0. The trap is that a broken hook looks exactly like a clean repo, so every change to one must be pipe-tested (`echo '{}' | bash <hook>`).
> **RU:** Хук, который только печатает и всегда выходит 0; сломанный хук неотличим от «всё чисто» — после правок обязателен пайп-тест.
> **Пример:** scripts/hooks/course-production-status.sh — fail-open: без settings/config.yml просто молчит.
> **См. также:** [fail-loud settings](#fail-loud-settings)

## fail-loud settings

<!-- term-meta {slug: fail-loud-settings, match: "fail\\-loud\ settings", ru: Чтение настроек, при котором отсутствующий ключ роняет код, а не подменяется дефолтом., tag: general, added: 2026-08-26} -->

`[general]` Reading configuration so that a missing key raises (no inline default). A rule silently applied with an invented threshold is worse than a crash: it looks enforced and is not.
> **RU:** Чтение настроек, при котором отсутствующий ключ роняет код, а не подменяется дефолтом.
> **Пример:** course.settings.require(rules, 'lecture.block_max_min') → MissingSetting, а не 25 по умолчанию.
> **См. также:** [course_production](#course_production), [fail-open hook](#fail-open-hook)

## recording.blocks

<!-- term-meta {slug: recordingblocks, match: "recording\.blocks", ru: Курируемое поле плана презентаций с планом блоков записи по id слайдов.", tag: project, added: 2026-08-26} -->

`[project]` The hand-curated key in `content/presentations.yml` listing `{title, from, to}` per block, where `from`/`to` are slide **ids** (stable across reordering, unlike numbers). Checked by `just preza-blocks <content>`: full coverage, in order, no overlaps are errors; a block over the limit is a warning (`--strict` promotes it).
> **RU:** Курируемое поле плана презентаций с планом блоков записи по id слайдов.
> **Пример:** just preza-blocks content/preza-dagster-content.yml → 4 блока, 49 сл. ≈ 63.7 мин.
> **См. также:** [блок записи](AI-glossary.ru.md#блок-записи), [course_production](#course_production)

## course_production

<!-- term-meta {slug: course_production, match: "course_production", ru: Секция настроек проекта, tag: project, added: 2026-08-26} -->

`[project]` The `settings/config.yml` section holding every scalar of the course manager's rules: deadlines, lecture duration, block limit, minutes-per-slide, design decisions, recording rules, homework policy, pipeline. Read fail-loud by `src/course`; the narrative lives in `docs/course-rules.md`, the Q&A in `docs/course-qa.md`.
> **RU:** Секция настроек проекта — единственный источник скаляров правил продакшена курса.
> **Пример:** course_production.deadlines.record_all_by: 2026-08-31 — хук считает дни до дедлайна.
> **См. также:** [fail-loud settings](#fail-loud-settings), [дизайн-пасс](AI-glossary.ru.md#дизайн-пасс)

## MAX_PROJECTS_LIMIT_REACHED

<!-- term-meta {slug: max_projects_limit_reached, match: "MAX_PROJECTS_LIMIT_REACHED", ru: Отказ Todoist на создание проекта при исчерпанном лимите free-тарифа.", tag: project, added: 2026-08-26} -->

`[project]` The HTTP 403 Todoist returns on project creation once the free plan's active-project cap is reached. The API never exposes the limit, so it lives as an observed scalar in `projects_policy.yml#capacity.max_active_projects`; the fix is archiving an empty project or merging a small one into its family.
> **RU:** Отказ Todoist на создание проекта при исчерпанном лимите free-тарифа.
> **Пример:** 8/8 → слили tg_events_week_digest → tg-events-parser, слот освободился.
> **См. также:** [ключ напоминания](AI-glossary.ru.md#ключ-напоминания)
