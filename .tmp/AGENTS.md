# AGENTS — `.tmp/` (dev/QA helpers)

Заметки для агентов (и людей), работающих с генератором презентаций.

## Что это
Одноразовые, но переиспользуемые скрипты для **проверки** и **отладки** колод `preza_gen`
(см. `README.md`). Не часть пакета `src/preza_gen/`; можно удалять/переписывать свободно.

## Правила
- Запуск — из **корня репозитория** через `just -f .tmp/Justfile <recipe>`.
- Скрипты не мутируют исходники и не трогают `data/source/` — только читают и рендерят во `.tmp/`.
- Генерируемые артефакты (`.tmp/render/`, `.tmp/render-pdf/`, `.tmp/media/`, `*.png`, `*.pptx`) —
  git-ignored; в git идут только `*.py`, `*.md`, `Justfile`.
- Для визуальной проверки предпочитайте `render-pdf`: он рендерит PDF, экспортированный
  LibreOffice, и не подменяет Corbel/Consolas шрифтами Quick Look.
- Правки контента по id слайда — `just preza-slides <content> …` (`scripts/preza/edit_slides.py`,
  мутирующий, поэтому живёт в `scripts/`, а не здесь).
- Напоминания в Todoist — `just course-reminders[-apply]` (`scripts/todoist/upsert_reminders.py`,
  пишет во внешний сервис → тоже `scripts/`; чистая логика плана — `src/course/reminders.py`).
- Продовый генератор — сабмодуль `src/preza_gen/`; курсной контент и настройки —
  `content/{preza-dbt-v3-content,build_deck_v3-settings}.yml`. Эти скрипты — вокруг пайплайна
  (QA), не вместо него.

## Быстрая проверка новой версии
```
just -f .tmp/Justfile lint-scalars  # ДО билда: скалярные поля контент-YAML
just build                       # собрать (корневой Justfile)
just -f .tmp/Justfile verify     # counts + emphasis + author
just -f .tmp/Justfile audit-code # длина/раскладка code-слайдов
just -f .tmp/Justfile render-pdf data/generated/MLInside_Введение-в-dbt_v3.9.pdf 13 16
                                  # визуально глянуть истинный LibreOffice-рендер
```

## Связанное
- Генератор/контент: `../src/preza_gen/`, `../.ai/README.md`.
- Публикация: корневой `just send` → Telegram-топик 118.
