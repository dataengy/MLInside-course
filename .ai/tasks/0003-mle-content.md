# 0003 · Авторинг MLE-контента (новая колода на том же пайплайне)

**Приоритет:** p1 · **Область:** preza_gen/content

v3-пайплайн обкатан на dbt-контенте. Теперь MLE-колода — переиспользуя генератор.

- Получить источник по MLE (pptx/PDF/конспект) — как был 84-слайдовый исходник для dbt.
- Создать `src/preza_gen/content/mle.yml` (та же схема: settings+content; kind title/agenda/section/content/table/closing).
- Медиа: если у источника есть свои картинки — прописать `source_deck` = MLE-исходник (медиа извлекаются автоматически).
- Сборка: `python -m preza_gen.build_deck_v3 --content src/preza_gen/content/mle.yml --all`.
- Проверить референс-стиль (титул без подзаголовка, финал `Section header`), без авторства.
