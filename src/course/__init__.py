"""course — правила продакшена курса MLInside как код.

Источник правил — чат с менеджером курса (docs/course-rules.md, Q&A — docs/course-qa.md);
скаляры — ``settings/config.yml → course_production`` (читаются fail-loud, без дефолтов).

* ``course.blocks`` — план блоков записи лекции (монтаж режет уроки до N минут → паузы
  между блоками): ``content/presentations.yml → recording.blocks`` против порядка слайдов.
* ``course.status`` — что печатает SessionStart-хук ``scripts/hooks/course-production-status.sh``:
  дедлайн записи, деки лектора без плана блоков, блоки длиннее лимита, открытые вопросы.

CLI: ``python -m course blocks [CONTENT…] [--strict] [--md]`` · ``python -m course status [--hook]``
(``just preza-blocks``, ``just preza-blocks-all``, ``just course-status``).
"""
