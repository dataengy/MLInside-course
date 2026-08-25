#!/usr/bin/env bash
# SessionStart hook: правила продакшена курса от менеджера. Fail-open, no network.
# Печатает дни до дедлайна записи всех лекций, деки лектора без плана блоков записи
# (content/presentations.yml → recording.blocks; монтаж режет уроки до 25 мин), блоки
# длиннее лимита и число открытых вопросов менеджеру (docs/course-qa.md, «Открытые вопросы»).
# Логика — src/course (та же, что `just course-status`); скаляры — settings/config.yml →
# course_production. Spec: docs/course-rules.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0
[ -f settings/config.yml ] || exit 0
[ -d src/course ] || exit 0

PYTHONPATH=src python3 -m course status --hook 2>/dev/null || true
exit 0
