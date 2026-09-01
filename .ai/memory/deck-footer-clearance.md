---
name: deck-footer-clearance
description: Прижатые к низу код-панели и схемы обязаны оставлять зазор до подвала — логотипа И строки «Материалы»
metadata: 
  node_type: memory
  type: project
  originSessionId: e0aa7f92-2441-4fb0-aee1-0219c36ca720
  modified: 2026-08-31T15:36:48.384Z
---

В шаблоне MLInside подвал — это ДВА элемента: логотип «MLINSIDE» на 6.954–7.144 in
от верха слайда (x 0.60–1.85) и строка «📚 Материалы», textbox которой начинается
на 6.98 in (`_add_materials` в рендерере). Профиль `alina-2026-08` в
`settings/formats.yml` прижимает визуал к `visual_bottom`.

**Why:** дефект незаметен в контент-YAML и в оценках рендерера — виден только на
собранном слайде, поэтому регулярно доезжал до ревьюера. Формально панель может
не пересекаться с подвалом и всё равно читаться как упирающаяся: LibreOffice
дорисовывает обводку скруглённого прямоугольника примерно на 0.08 in ниже его
геометрии.

**How to apply:** 2026-08-31 значение прошло два шага — 7.01 → 6.71 (панель резала
логотип) → **6.51** (при 6.71 зазор до подвала был всего 0.16 in и лектор видел
наезд). Держать зазор ≥ 0.35 in до 6.98. Проверки: тест
`test_bottom_anchored_visual_clears_the_footer_logo` в
`src/preza_gen/tests/test_format_render.py`, правило профиля в `.tmp/fit_check.py`
(до сборки) и правило `ЗАЗОР` в `.tmp/pdf_overflow_check.py` (по PDF от LibreOffice).
Помнить: `settings/formats.yml` перезаписывается целиком через
`just preza-merge-apply` — после каждого прогона значение надо проверять заново.
См. [[deck-versioning-semver]], [[deck-slide-with-picture-and-scheme]].
