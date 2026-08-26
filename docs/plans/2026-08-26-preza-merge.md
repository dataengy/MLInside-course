# preza_merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Слить форк ревьюера (`MLInside_Введение-в-dbt_v3.15 (1).pptx`) со своей веткой `v3.19`, перенеся правки форматирования в генератор как именованный профиль, и оставить после себя многоразовую ленту `preza_merge` с обвязкой.

**Architecture:** Правки ревьюера выражаются правилами, поэтому они переносятся **в генератор** (профиль в `settings/formats.yml`, исполняемый `renderers/pptx.py`), а не в один `.pptx` — иначе следующий `just build` их затрёт. Новый пакет `src/preza_merge/` нормализует деки в сравнимую модель, диффит три стороны (base / ours / theirs), выводит правила с доказательствами, применяет их и верифицирует результат пересборкой base-контента новым профилем против форка.

**Tech Stack:** Python 3.11+, python-pptx 1.0, click, pyyaml, loguru, pytest, ruff, ty; `just` как канонический вход; LibreOffice (опционально, для contact-sheet).

**Spec:** [docs/preza-merge-lane.md](../preza-merge-lane.md) — читать вместе с планом; план аргументирует из спеки.

**Tracker:** [#8 — preza_merge: слияние версий и форков презентаций](https://github.com/dataengy/MLInside-course/issues/8). Каждый коммит несёт `(#8)`.

## Global Constraints

- **Fail-loud**: все скаляры приходят из YAML, никаких инлайновых дефолтов в коде; отсутствующий ключ, неизвестное имя профиля, неразобранная версия → исключение с текстом, что делать (`~/.ai/skills/.settings/code_specs/script_standards.yml`).
- **Единственный мягкий модуль** — SessionStart-хук: fail-open (`set -u`, `|| true`, `exit 0` при отсутствии данных), как соседние хуки в `scripts/hooks/`.
- **`just check` (ruff + ty + pytest) обязан остаться зелёным** после каждой задачи. Базовая линия на старте: 261 passed, 4 skipped.
- **Профиль `classic` рендерит байт-в-байт как сегодня** — это пиновый тест, а не пожелание.
- **Язык**: docstrings и комментарии в коде — английские (как весь `src/`); `docs/*.md`, отчёты и сообщения коммитов — русские.
- **Скилл создаётся ТОЛЬКО через `/create-skill`** — прямая запись в `~/.claude/skills/**` или `~/.ai/skills/_catalog/**` запрещена политикой (`~/.ai/skills/.settings/skill_create.yml`).
- **Версии**: `descr` в имени версии обязан матчиться `^[a-z0-9][a-z0-9._-]*$`.
- **Допуск верификации**: `0.4` дюйма по `left/top/width/height`.
- **Порог правила**: `min_share = 0.8`.
- **Целевой артефакт кейса**: `MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx`.
- **Правила менеджера — вход для детекторов наравне с диффом**: `settings/config.yml →
  course_production.design` + [docs/course-rules.md](../course-rules.md). Так найдено R11
  (снятая обводка код-панелей), которое первый дифф пропустил, потому что модель не читала
  обводку фигур. Лента закрывает открытый вопрос «Перенос дизайн-правок менеджера в генератор»
  в [docs/course-qa.md](../course-qa.md) ([#7](https://github.com/dataengy/MLInside-course/issues/7)).
- **Пины кейса** (проверены на диске, использовать как ожидаемые значения в тестах и отчётах): base-контент = коммит `6752d35` (57 слайдов), ours = `HEAD` (70 слайдов), theirs = `/Users/nk.myg/Downloads/MLInside_Введение-в-dbt_v3.15 (1).pptx` (57 слайдов); в форке 59 гиперссылок, 30 футеров «📚 Материалы», 114 notes-частей.

## File Structure

| Файл | Ответственность |
|------|-----------------|
| `src/preza_gen/utils.py` (изм.) | разбор/форматирование версии `x.y.z[+descr]`, `resolve_out_name` с патч-режимом |
| `src/preza_gen/settings.py` (изм.) | датакласс `Format`, загрузка профиля из `formats_file`, `Config.fmt` |
| `src/preza_gen/renderers/pptx.py` (изм.) | исполнение профиля: R1/R3/R6/R7, затем R2/R4 |
| `src/preza_gen/build_deck.py` (изм.) | флаги `--patch` / `--descr` |
| `src/preza_gen/pipeline.py` (изм.) | проброс патч-режима в `_resolve_naming` |
| `src/publisher/detect.py` (изм.) | распознавание патч-версий, порядок по `(major, minor, patch)` |
| `settings/formats.yml` (нов.) | именованные профили (генерируется `apply`) |
| `settings/merge.yml` (нов.) | SSoT ленты: пороги, допуски, пути, маска форк-кандидатов |
| `src/preza_merge/model.py` (нов.) | нормализованная модель деки |
| `src/preza_merge/diff.py` (нов.) | попарный дифф двух моделей → `DiffReport` |
| `src/preza_merge/align.py` (нов.) | 3-way выравнивание слайдов по заголовкам |
| `src/preza_merge/rules.py` (нов.) | детекторы R1–R4/R6/R7 + регрессии R8–R10 |
| `src/preza_merge/report.py` (нов.) | `*.md` + `*.proposal.yml` |
| `src/preza_merge/apply.py` (нов.) | запись профиля, `deck.format`, патч-сборка |
| `src/preza_merge/verify.py` (нов.) | структурный + инвариантный контроль, contact-sheet |
| `src/preza_merge/cli.py` (нов.) | `propose / apply / verify / run` |
| `src/preza_merge/tests/` (нов.) | тесты пакета |
| `scripts/hooks/preza-merge-status.sh` (нов.) | SessionStart-хук ленты |
| `.claude/agents/preza-merge-keeper.md` (нов.) | суб-агент ленты |
| `Justfile` (изм.) | рецепты `preza-merge-*` |

---

### Task 1: Нотация версии `x.y.z[+descr]` в генераторе

**Files:**
- Modify: `src/preza_gen/utils.py:135-181` (блок `_VER_RE` / `next_minor` / `resolve_out_name`)
- Test: `src/preza_gen/tests/test_version.py` (создать)

**Interfaces:**
- Consumes: ничего (первая задача)
- Produces: `preza_gen.utils.parse_version(name: str) -> tuple[int, int, int, str] | None`, `format_version(major: int, minor: int, patch: int = 0, descr: str = "") -> str`, `next_minor(names: list[str], base: str, major: int) -> int` (сигнатура прежняя), `next_patch(names: list[str], base: str, major: int, minor: int) -> int`, `resolve_out_name(base, mode, existing, *, major=None, ts=None, patch_of=None, descr="") -> str`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_gen/tests/test_version.py`:

```python
"""Version notation x.y.z[+descr] — parsing, ordering, and name resolution."""

import pytest

from preza_gen.utils import (
    format_version,
    next_minor,
    next_patch,
    parse_version,
    resolve_out_name,
)


def test_parse_plain_and_patch_versions():
    assert parse_version("X_v3.19.pptx") == (3, 19, 0, "")
    assert parse_version("X_v3.19.1.pptx") == (3, 19, 1, "")
    assert parse_version("X_v3.19.1+alina-fmt.pptx") == (3, 19, 1, "alina-fmt")
    assert parse_version("X_v3.19.1+alina-fmt") == (3, 19, 1, "alina-fmt")


def test_parse_rejects_unversioned_names():
    assert parse_version("X_v3.pptx") is None       # no minor → not a version
    assert parse_version("X.pptx") is None


def test_descr_never_swallows_the_extension():
    """Regression: a greedy descr pattern ate '.pptx' and produced 'alina-fmt.pptx'."""
    assert parse_version("X_v3.19.1+alina-fmt.pptx")[3] == "alina-fmt"


def test_format_version_omits_empty_parts():
    assert format_version(3, 19) == "3.19"
    assert format_version(3, 19, 1) == "3.19.1"
    assert format_version(3, 19, 1, "alina-fmt") == "3.19.1+alina-fmt"


def test_ordering_is_by_numeric_triple_only():
    names = ["X_v3.20.pptx", "X_v3.19.1+alina-fmt.pptx", "X_v3.19.pptx"]
    assert sorted(names, key=lambda n: parse_version(n)[:3]) == [
        "X_v3.19.pptx",
        "X_v3.19.1+alina-fmt.pptx",
        "X_v3.20.pptx",
    ]


def test_next_minor_ignores_patch_suffixes():
    """A patch build must not push the next ordinary build onto a patch branch."""
    assert next_minor(["X_v3.19.pptx", "X_v3.19.1+alina-fmt.pptx"], "X", 3) == 20


def test_next_patch_counts_within_one_minor():
    names = ["X_v3.19.pptx", "X_v3.19.1+alina-fmt.pptx", "X_v3.18.4.pptx"]
    assert next_patch(names, "X", 3, 19) == 2
    assert next_patch(names, "X", 3, 18) == 5
    assert next_patch([], "X", 3, 19) == 1


def test_resolve_out_name_patch_mode():
    existing = ["X_v3.19.pptx"]
    assert resolve_out_name(
        "X", "increment", existing, major=3, patch_of="3.19", descr="alina-fmt"
    ) == "X_v3.19.1+alina-fmt"


def test_resolve_out_name_rejects_bad_descr():
    with pytest.raises(ValueError, match="descr"):
        resolve_out_name("X", "increment", [], major=3, patch_of="3.19", descr="Alina Fmt!")


def test_resolve_out_name_rejects_unparsable_patch_of():
    with pytest.raises(ValueError, match="patch_of"):
        resolve_out_name("X", "increment", [], major=3, patch_of="v3", descr="x")
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd /Users/nk.myg/github/@dataengy/MLInside-course && python3 -m pytest src/preza_gen/tests/test_version.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_version'`

- [ ] **Step 3: Реализация**

В `src/preza_gen/utils.py` заменить блок от комментария `# Output naming (auto-versioning).` до конца `resolve_out_name` на:

```python
# Output naming (auto-versioning). A build resolves a versioned stem from a base name:
#   increment → {base}_v{major}.{n}  (n = max existing minor for that major + 1)
#   timestamp → {base}_{ts}
#   fixed     → {base}   (back-compat: put the full versioned name in the base)
# A merge/patch build adds a third number and an optional build tag:
#   {base}_v{major}.{minor}.{patch}+{descr}   e.g. MLInside_Введение-в-dbt_v3.19.1+alina-fmt
# Ordering is the numeric triple only — `descr` labels a build, it never ranks one.
_EXTS = (".pptx", ".html", ".pdf")
# Anchored at the END of the stem: an unanchored descr pattern happily ate ".pptx".
_VER_RE = _re.compile(r"_v(\d+)\.(\d+)(?:\.(\d+))?(?:\+([a-z0-9][a-z0-9._-]*))?$")
_DESCR_RE = _re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _stem(name: str) -> str:
    """Drop a known deck extension so the version regex can anchor at the end.

    >>> _stem("X_v3.19.1.pptx")
    'X_v3.19.1'
    >>> _stem("X_v3.19.1")
    'X_v3.19.1'
    """
    for ext in _EXTS:
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


def parse_version(name: str) -> tuple[int, int, int, str] | None:
    """``(major, minor, patch, descr)`` of a versioned deck name, or None.

    >>> parse_version("X_v3.19.pptx")
    (3, 19, 0, '')
    >>> parse_version("X_v3.19.1+alina-fmt.pptx")
    (3, 19, 1, 'alina-fmt')
    >>> parse_version("X_v3.pptx") is None      # no minor → not a version
    True
    """
    m = _VER_RE.search(_stem(name))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), m.group(4) or ""


def format_version(major: int, minor: int, patch: int = 0, descr: str = "") -> str:
    """Render a version triple + optional build tag.

    >>> format_version(3, 19)
    '3.19'
    >>> format_version(3, 19, 1, "alina-fmt")
    '3.19.1+alina-fmt'
    """
    core = f"{major}.{minor}" + (f".{patch}" if patch else "")
    return core + (f"+{descr}" if descr else "")


def next_minor(names: list[str], base: str, major: int) -> int:
    """Return the next minor for '{base}_v{major}.<n>' seen among ``names`` (1 if none).

    Patch suffixes are ignored on purpose: after a 3.19.1 merge build the next ordinary
    build must be 3.20, not another patch.

    >>> next_minor(["X_v3.1.pptx", "X_v3.2.html", "X_v2.9.pptx"], "X", 3)
    3
    >>> next_minor(["X_v3.19.pptx", "X_v3.19.1+alina-fmt.pptx"], "X", 3)
    20
    >>> next_minor(["X_v3.pptx"], "X", 3)   # no minor → ignored
    1
    >>> next_minor([], "X", 3)
    1
    """
    minors = [
        v[1]
        for n in names
        if n.startswith(f"{base}_v{major}.")
        for v in [parse_version(n)]
        if v and v[0] == major
    ]
    return (max(minors) + 1) if minors else 1


def next_patch(names: list[str], base: str, major: int, minor: int) -> int:
    """Return the next patch for '{base}_v{major}.{minor}.<n>' among ``names`` (1 if none).

    >>> next_patch(["X_v3.19.pptx", "X_v3.19.1+alina-fmt.pptx"], "X", 3, 19)
    2
    >>> next_patch([], "X", 3, 19)
    1
    """
    patches = [
        v[2]
        for n in names
        if n.startswith(f"{base}_v{major}.{minor}")
        for v in [parse_version(n)]
        if v and (v[0], v[1]) == (major, minor)
    ]
    return (max(patches) + 1) if patches else 1


def resolve_out_name(
    base: str,
    mode: str,
    existing: list[str],
    *,
    major: int | None = None,
    ts: str | None = None,
    patch_of: str | None = None,
    descr: str = "",
) -> str:
    """Resolve a versioned output stem. ``mode`` ∈ {fixed, increment, timestamp}; fail-loud.

    ``patch_of`` ("3.19") overrides ``mode`` and resolves the next patch of that version —
    this is how a merge build lands beside its parent instead of consuming a new minor.

    >>> resolve_out_name("Deck", "fixed", [])
    'Deck'
    >>> resolve_out_name("Deck", "increment", ["Deck_v3.1.pptx"], major=3)
    'Deck_v3.2'
    >>> resolve_out_name("Deck", "timestamp", [], ts="20260716-2230")
    'Deck_20260716-2230'
    >>> resolve_out_name("Deck", "increment", ["Deck_v3.19.pptx"], major=3,
    ...                  patch_of="3.19", descr="alina-fmt")
    'Deck_v3.19.1+alina-fmt'
    """
    if patch_of is not None:
        if descr and not _DESCR_RE.match(descr):
            raise ValueError(
                f"descr must match {_DESCR_RE.pattern!r} (lowercase, no spaces): {descr!r}"
            )
        parsed = parse_version(f"X_v{patch_of}")
        if not parsed:
            raise ValueError(f"patch_of must be 'major.minor' (e.g. '3.19'), got {patch_of!r}")
        pmajor, pminor = parsed[0], parsed[1]
        patch = next_patch(existing, base, pmajor, pminor)
        return f"{base}_v{format_version(pmajor, pminor, patch, descr)}"
    if mode == "fixed":
        return base
    if mode == "increment":
        if major is None:
            raise ValueError("increment naming needs version_major")
        return f"{base}_v{major}.{next_minor(existing, base, major)}"
    if mode == "timestamp":
        if not ts:
            raise ValueError("timestamp naming needs a ts value")
        return f"{base}_{ts}"
    raise ValueError(f"unknown naming mode: {mode!r}")
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_gen/tests/test_version.py src/preza_gen -q`
Expected: PASS (включая доктесты — `pytest` собирает их через `--doctest-modules`)

- [ ] **Step 5: Коммит**

```bash
git add src/preza_gen/utils.py src/preza_gen/tests/test_version.py
git commit -m "feat(preza-gen): нотация версии x.y.z[+descr] — патч-сборки поверх версии (#8)"
```

---

### Task 2: Патч-версии в генераторе и CLI

**Files:**
- Modify: `src/preza_gen/pipeline.py:32-40` (`_resolve_naming`) и `build_deck()`
- Modify: `src/preza_gen/build_deck.py:24-75` (опции CLI)
- Test: `src/preza_gen/tests/test_version.py` (дополнить)

**Interfaces:**
- Consumes: `utils.resolve_out_name(..., patch_of=, descr=)` из Task 1
- Produces: `pipeline.build_deck(settings_yml, content_yml, *, pptx=False, html=False, pdf=False, patch_of: str | None = None, descr: str = "") -> BuildResult`; CLI-флаги `--patch <major.minor>` и `--descr <slug>`

- [ ] **Step 1: Написать падающий тест**

Дописать в `src/preza_gen/tests/test_version.py`:

```python
def test_resolve_naming_threads_patch_mode(tmp_path):
    """A patch build names itself from patch_of, not from the deck's naming mode."""
    from preza_gen import pipeline
    from preza_gen.settings import Config, Generation, ImageBox, Layouts, Theme

    out_dir = tmp_path / "generated"
    out_dir.mkdir()
    (out_dir / "Deck_v3.19.pptx").write_bytes(b"")
    cfg = Config(
        template=tmp_path / "t.pptx",
        source_deck=tmp_path / "s.pptx",
        media_dir=None,
        out_dir=out_dir,
        out_name="Deck",
        downloads_dir=None,
        downloads_link=None,
        theme=Theme("2419FF", "FFFFFF", "1A1A1A", "F2F2F7", "Corbel"),
        layouts=Layouts("a", "b", "c", "d", "e", "f"),
        image_box=ImageBox(0, 0, 1, 1),
        code_style={"font": "Consolas", "size": 13, "min_size": 9, "fg": "E6EDF3", "bg": "0D1117"},
        code_box=ImageBox(0, 0, 1, 1),
        code_box_full=ImageBox(0, 0, 1, 1),
        notes_emphasis={},
        generation=Generation(parallel=False),
        naming="increment",
        version_major=3,
        fmt=None,
        format_name="classic",
    )

    pipeline._resolve_naming(cfg, patch_of="3.19", descr="alina-fmt")
    assert cfg.out_name == "Deck_v3.19.1+alina-fmt"
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_gen/tests/test_version.py::test_resolve_naming_threads_patch_mode -v`
Expected: FAIL — `_resolve_naming() got an unexpected keyword argument 'patch_of'` (либо `TypeError` по `fmt`/`format_name`, если Task 3 ещё не сделан — тогда порядок задач нарушен, вернуться к Task 3)

> **Порядок:** этот тест конструирует `Config` с полями `fmt` и `format_name` из Task 3. Выполнять Task 2 **после** Task 3, либо временно убрать эти два поля из фикстуры и вернуть их в Task 3.

- [ ] **Step 3: Реализация**

В `src/preza_gen/pipeline.py` заменить `_resolve_naming` и сигнатуру `build_deck`:

```python
def _resolve_naming(cfg: S.Config, *, patch_of: str | None = None, descr: str = "") -> None:
    """Resolve cfg.out_name (versioned stem) + cfg.downloads_link in place. Fail-loud."""
    existing = [p.name for p in cfg.out_dir.glob("*")] if cfg.out_dir.is_dir() else []
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    cfg.out_name = resolve_out_name(
        cfg.out_name,
        cfg.naming,
        existing,
        major=cfg.version_major,
        ts=ts,
        patch_of=patch_of,
        descr=descr,
    )
    if cfg.downloads_dir:
        cfg.downloads_link = expand_path(cfg.downloads_dir) / f"{cfg.out_name}.pptx"
```

И в `build_deck()` добавить параметры и проброс:

```python
def build_deck(
    settings_yml: str | Path,
    content_yml: str | Path,
    *,
    pptx: bool = False,
    html: bool = False,
    pdf: bool = False,
    patch_of: str | None = None,
    descr: str = "",
) -> BuildResult:
    """Load settings+content, resolve the versioned name, render the requested formats."""
    cfg, content = S.load(settings_yml, content_yml)
    _resolve_naming(cfg, patch_of=patch_of, descr=descr)
```

(остальное тело `build_deck` без изменений)

В `src/preza_gen/build_deck.py` добавить две опции перед `def main(`:

```python
@click.option(
    "--patch",
    "patch_of",
    default=None,
    help="build a patch of this version (e.g. 3.19) → _v3.19.<n>[+descr] instead of a new minor",
)
@click.option(
    "--descr",
    default="",
    help="build tag appended after '+' (lowercase slug); only meaningful with --patch",
)
```

и провести их через сигнатуру `main(...)` в вызов:

```python
    res = pipeline.build_deck(
        settings_yml,
        content_yml,
        pptx=do_pptx,
        html=do_html,
        pdf=do_pdf,
        patch_of=patch_of,
        descr=descr,
    )
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_gen -q && python3 -m preza_gen.build_deck --help | grep -E "patch|descr"`
Expected: PASS; в справке видны `--patch` и `--descr`

- [ ] **Step 5: Коммит**

```bash
git add src/preza_gen/pipeline.py src/preza_gen/build_deck.py src/preza_gen/tests/test_version.py
git commit -m "feat(preza-gen): --patch/--descr — сборка патч-версии поверх существующей (#8)"
```

---

### Task 3: Профили форматирования в настройках

**Files:**
- Modify: `src/preza_gen/settings.py:76-146` (датаклассы + `load`)
- Create: `settings/formats.yml`
- Modify: `content/build_deck_v3-settings.yml` (ключ `formats_file`, перенос `body_font`)
- Modify: `content/preza-dbt-v3-content.yml` (ключ `deck.format`)
- Test: `src/preza_gen/tests/test_format_profile.py` (создать)

**Interfaces:**
- Consumes: ничего из предыдущих задач
- Produces: `preza_gen.settings.Format` (датакласс с полями `body_font, visual_anchor, visual_bottom, visual_top_min, table_top, bullets_width, bullets_width_full, bullets_width_narrow, bullets_gap, drop_empty_placeholders, title_slide_uppercase`), `Config.fmt: Format`, `Config.format_name: str`, `settings.load_format(formats_path: Path, name: str) -> Format`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_gen/tests/test_format_profile.py`:

```python
"""Named formatting profiles: loading, defaults, and fail-loud behaviour."""

from pathlib import Path

import pytest
import yaml

from preza_gen import settings

_REPO = Path(__file__).resolve().parents[3]
FORMATS_YML = _REPO / "settings" / "formats.yml"
SETTINGS_YML = _REPO / "content" / "build_deck_v3-settings.yml"
CONTENT_YML = _REPO / "content" / "preza-dbt-v3-content.yml"


def test_classic_profile_pins_todays_behaviour():
    """`classic` must keep the values the renderer hard-coded before profiles existed."""
    fmt = settings.load_format(FORMATS_YML, "classic")
    assert fmt.body_font == {
        "bullets_only": {0: 26, 1: 21, 2: 18},
        "with_image": {0: 20, 1: 17, 2: 15},
    }
    assert fmt.visual_anchor == "box"
    assert fmt.table_top == 1.5
    assert fmt.bullets_width == "fixed"
    assert fmt.bullets_width_narrow == 6.2
    assert fmt.drop_empty_placeholders is False
    assert fmt.title_slide_uppercase is False
    assert fmt.code_border == "accent"


def test_unknown_profile_fails_loud():
    with pytest.raises(KeyError, match="no-such-profile"):
        settings.load_format(FORMATS_YML, "no-such-profile")


def test_unknown_key_inside_profile_fails_loud(tmp_path):
    p = tmp_path / "formats.yml"
    p.write_text(
        yaml.safe_dump({"formats": {"x": {"body_font": "inherit", "nonsense": 1}}}),
        encoding="utf-8",
    )
    with pytest.raises(TypeError):
        settings.load_format(p, "x")


def test_deck_selects_its_profile():
    cfg, _ = settings.load(SETTINGS_YML, CONTENT_YML)
    assert cfg.format_name in {"classic", "alina-2026-08"}
    assert cfg.fmt.bullets_width_narrow == 6.2
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_gen/tests/test_format_profile.py -v`
Expected: FAIL — `AttributeError: module 'preza_gen.settings' has no attribute 'load_format'`

- [ ] **Step 3: Реализация**

Создать `settings/formats.yml`:

```yaml
# formats.yml — named FORMATTING profiles for preza_gen. Referenced from a deck settings
# yaml via `settings.formats_file`; a deck picks one with `deck.format`.
#
# GENERATED-AND-EDITED: `just preza-merge-apply` rewrites this whole file, so keep prose
# out of it — durable explanation lives in docs/preza-merge-lane.md.
#
# classic — the behaviour hard-coded in the renderer before profiles existed. Pinned by
# src/preza_gen/tests/test_format_profile.py; do not "improve" it, add a new profile.
formats:
  classic:
    body_font: {bullets_only: {0: 26, 1: 21, 2: 18}, with_image: {0: 20, 1: 17, 2: 15}}
    visual_anchor: box
    visual_bottom: 7.0
    visual_top_min: 1.7
    table_top: 1.5
    bullets_width: fixed
    bullets_width_full: 12.3
    bullets_width_narrow: 6.2
    bullets_gap: 0.25
    drop_empty_placeholders: false
    title_slide_uppercase: false
    code_border: accent
```

В `content/build_deck_v3-settings.yml`: удалить блок `body_font:` (он переехал в профиль `classic`) и добавить рядом с `out_dir`:

```yaml
  formats_file: settings/formats.yml
```

В `content/preza-dbt-v3-content.yml` добавить в блок `deck:` строку `format: classic` (после `version_major: 3`) — переключение на новый профиль сделает Task 11.

В `src/preza_gen/settings.py` добавить датакласс перед `Config`:

```python
@dataclass
class Format:
    """One named FORMATTING profile — WHERE things sit, not WHAT the deck says.

    `body_font` is either a {bullets_only|with_image: {level: pt}} map or the literal
    "inherit", which leaves the size to the template master.
    """

    body_font: dict | str
    visual_anchor: str  # box → centre in image_box/code_box | bottom → pin to visual_bottom
    visual_bottom: float  # inches from the top edge; used when visual_anchor == "bottom"
    visual_top_min: float  # highest a bottom-anchored visual may climb (clear of the title)
    table_top: float
    bullets_width: str  # fixed → always bullets_width_narrow beside a visual | adaptive
    bullets_width_full: float
    bullets_width_narrow: float
    bullets_gap: float  # min vertical clearance between the bullet block and the visual
    drop_empty_placeholders: bool
    title_slide_uppercase: bool
    code_border: str  # accent | dark | white | none — outline of the dark code panel
```

В `Config` заменить строку `body_font: dict  # ...` на:

```python
    fmt: Format  # named formatting profile (settings/formats.yml → deck.format)
    format_name: str  # which profile the deck asked for — carried for reports/provenance
```

и добавить загрузчик:

```python
def load_format(formats_path: str | Path, name: str) -> Format:
    """Load one named profile from a formats yaml. Fail-loud on file/name/key.

    The `Format` dataclass rejects unknown keys, so a typo in a profile is a build-time
    error rather than a silently ignored setting.
    """
    path = expand_path(formats_path)
    if not path.is_file():
        raise FileNotFoundError(f"formats_file not found: {path}")
    profiles = load_yaml(path)["formats"]
    if name not in profiles:
        raise KeyError(f"unknown format profile {name!r} in {path} (have: {sorted(profiles)})")
    return Format(**profiles[name])
```

В `load()` — собрать профиль и передать в `Config` (заменив `body_font=s["body_font"]`):

```python
    format_name = d.get("format", "classic")
    fmt = load_format(s["formats_file"], format_name)
```

```python
        fmt=fmt,
        format_name=format_name,
```

В `renderers/pptx.py:319` временно заменить `cfg.body_font[...]` на `cfg.fmt.body_font[...]`, чтобы сборка не сломалась до Task 4.

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_gen src/tests -q && just build && python3 -c "
from pptx import Presentation; import glob
p = sorted(glob.glob('data/generated/MLInside_Введение-в-dbt_v3.*.pptx'))[-1]
print(p, len(Presentation(p).slides))"`
Expected: PASS; сборка проходит, свежая версия — 70 слайдов

- [ ] **Step 5: Коммит**

```bash
git add settings/formats.yml src/preza_gen/settings.py src/preza_gen/renderers/pptx.py \
        src/preza_gen/tests/test_format_profile.py content/build_deck_v3-settings.yml \
        content/preza-dbt-v3-content.yml
git commit -m "feat(preza-gen): именованные профили форматирования, classic закреплён тестом (#8)"
```

---

### Task 4: Рендерер исполняет простые правила профиля (R1, R3, R6, R7, R11)

**Files:**
- Modify: `src/preza_gen/renderers/pptx.py` — `_set_body`, `_add_table`, `render`
- Test: `src/preza_gen/tests/test_format_render.py` (создать)

**Interfaces:**
- Consumes: `settings.Format` из Task 3
- Produces: `_add_table(slide, table: dict, theme: dict, *, top: float) -> None`; поведение `render()`, зависящее от `cfg.fmt`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_gen/tests/test_format_render.py`:

```python
"""The renderer must obey the active formatting profile (simple rules: R1, R3, R6, R7)."""

from pathlib import Path

import pytest
import yaml
from pptx import Presentation
from pptx.util import Inches

from preza_gen import pipeline, settings

_REPO = Path(__file__).resolve().parents[3]
SETTINGS_YML = _REPO / "content" / "build_deck_v3-settings.yml"


def _mini_content(tmp_path: Path, fmt_name: str) -> Path:
    """A 3-slide deck: title, a table slide, a section slide with no bullets."""
    doc = {
        "deck": {
            "out_name": "Mini",
            "naming": "fixed",
            "version_major": 3,
            "format": fmt_name,
            "source_deck": str(_REPO / "data" / "source" / "MLinside-шаблон-презентаций.pptx"),
            "downloads_dir": None,
        },
        "content": [
            {"kind": "title", "title": "Введение в dbt", "subtitle": ""},
            {
                "kind": "table",
                "title": "Таблица",
                "table": {"headers": ["a", "b"], "rows": [["1", "2"]]},
            },
            {"kind": "content", "title": "Только буллеты", "bullets": ["раз", "два"]},
            {
                "kind": "content",
                "title": "Код",
                "bullets": ["раз"],
                "code": "select 1\nfrom t",
            },
        ],
    }
    p = tmp_path / "mini.yml"
    p.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return p


def _build(tmp_path: Path, fmt_name: str) -> Presentation:
    content = _mini_content(tmp_path, fmt_name)
    out = tmp_path / f"out-{fmt_name}"
    out.mkdir(exist_ok=True)
    s = yaml.safe_load(SETTINGS_YML.read_text(encoding="utf-8"))
    s["settings"]["out_dir"] = str(out)
    s["settings"]["formats_file"] = str(_REPO / "settings" / "formats.yml")
    s["settings"]["template"] = str(_REPO / s["settings"]["template"])
    sett = tmp_path / "settings.yml"
    sett.write_text(yaml.safe_dump(s, allow_unicode=True), encoding="utf-8")
    res = pipeline.build_deck(sett, content, pptx=True)
    return Presentation(str(res.out_path))


pytestmark = pytest.mark.skipif(
    not (_REPO / "data" / "source" / "MLinside-шаблон-презентаций.pptx").is_file(),
    reason="deck template not materialized (git-lfs)",
)


def test_classic_keeps_explicit_bullet_sizes_and_table_top(tmp_path):
    prs = _build(tmp_path, "classic")
    table = next(sh for sh in prs.slides[1].shapes if sh.has_table)
    assert abs(table.top - Inches(1.5)) < Inches(0.02)
    body = prs.slides[2].placeholders[1]
    sizes = {r.font.size for p in body.text_frame.paragraphs for r in p.runs}
    assert sizes == {Inches(26 / 72)}  # 26 pt, explicit


def test_profile_inherits_bullet_size_and_lowers_tables(tmp_path):
    """R1 + R3: no explicit run size, table pushed under the title."""
    fmt = settings.load_format(_REPO / "settings" / "formats.yml", "alina-2026-08")
    assert fmt.body_font == "inherit"
    prs = _build(tmp_path, "alina-2026-08")
    table = next(sh for sh in prs.slides[1].shapes if sh.has_table)
    assert abs(table.top - Inches(fmt.table_top)) < Inches(0.02)
    body = prs.slides[2].placeholders[1]
    assert all(r.font.size is None for p in body.text_frame.paragraphs for r in p.runs)


def test_code_panel_border_follows_the_profile(tmp_path):
    """R11: the manager removed the blue outline — the profile decides, not the renderer."""
    from pptx.dml.color import RGBColor

    classic = _build(tmp_path, "classic")
    panel = next(sh for sh in classic.slides[3].shapes if sh.name.startswith("Rounded"))
    assert panel.line.color.rgb == RGBColor.from_string("2419FF")

    merged = _build(tmp_path, "alina-2026-08")
    panel = next(sh for sh in merged.slides[3].shapes if sh.name.startswith("Rounded"))
    assert panel.line.color.rgb == RGBColor.from_string("1A1A1A")  # theme dark, not accent


def test_profile_drops_empty_placeholders_and_upcases_the_title(tmp_path):
    """R6 + R7 — checked on a profile that switches them on."""
    formats = yaml.safe_load((_REPO / "settings" / "formats.yml").read_text(encoding="utf-8"))
    prof = dict(formats["formats"]["alina-2026-08"])
    prof["title_slide_uppercase"] = True
    formats["formats"]["_t"] = prof
    ff = tmp_path / "formats.yml"
    ff.write_text(yaml.safe_dump(formats, allow_unicode=True), encoding="utf-8")

    content = _mini_content(tmp_path, "_t")
    out = tmp_path / "out2"
    out.mkdir()
    s = yaml.safe_load(SETTINGS_YML.read_text(encoding="utf-8"))
    s["settings"].update(
        out_dir=str(out),
        formats_file=str(ff),
        template=str(_REPO / s["settings"]["template"]),
    )
    sett = tmp_path / "settings2.yml"
    sett.write_text(yaml.safe_dump(s, allow_unicode=True), encoding="utf-8")
    prs = Presentation(str(pipeline.build_deck(sett, content, pptx=True).out_path))

    assert prs.slides[0].shapes.title.text == "ВВЕДЕНИЕ В DBT"
    # the table slide's layout placeholder carries no text → dropped
    empty = [
        sh
        for sh in prs.slides[1].shapes
        if sh.is_placeholder and sh.has_text_frame and not sh.text_frame.text.strip()
    ]
    assert empty == []
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_gen/tests/test_format_render.py -v`
Expected: FAIL — профиля `alina-2026-08` ещё нет в `settings/formats.yml` (`KeyError`)

- [ ] **Step 3: Реализация**

Добавить профиль в `settings/formats.yml` (под `classic`):

```yaml
  # alina-2026-08 — derived from the reviewer's fork of v3.15 (docs/preza-merge-lane.md).
  alina-2026-08:
    body_font: inherit
    visual_anchor: bottom
    visual_bottom: 7.0
    visual_top_min: 1.7
    table_top: 2.45
    bullets_width: adaptive
    bullets_width_full: 12.3
    bullets_width_narrow: 6.2
    bullets_gap: 0.25
    drop_empty_placeholders: true
    title_slide_uppercase: false
    code_border: dark
```

В `src/preza_gen/renderers/pptx.py`:

`_set_body` уже принимает `sizes: dict | None` и пропускает установку размера при `None` — менять нечего.

`_add_code` — обводка панели из профиля (R11). Расширить сигнатуру и заменить установку цвета:

```python
def _add_code(
    slide, code: str, caption: str, theme: dict, box: ImageBox, style: dict, size: float,
    *, border: str = "accent"
) -> None:
```

```python
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(style["bg"])
    if border == "none":
        shp.line.fill.background()
    else:
        shp.line.color.rgb = theme[border]
        shp.line.width = Pt(1)
```

(старые строки `shp.line.color.rgb = theme["accent"]` и `shp.line.width = Pt(1)` удалить — они
переехали в `else`)

`_add_table` — параметризовать верх:

```python
def _add_table(slide, table: dict, theme: dict, *, top: float) -> None:
    headers, rows = table["headers"], table["rows"]
    ratios = table.get("col_ratios")
    left, top_emu, width = Inches(0.45), Inches(top), Inches(12.43)
    tbl = slide.shapes.add_table(
        len(rows) + 1, len(headers), left, top_emu, width, Inches(0.45 + 0.4 * len(rows))
    ).table
```

(остальное тело без изменений)

Добавить хелпер рядом с `_set_notes`:

```python
def _drop_empty_placeholders(slide) -> None:
    """Remove layout placeholders left without text (R6) — invisible in show, noisy in XML.

    Identity is compared on the XML element: python-pptx builds a NEW proxy object on every
    ``shapes.title`` access, so ``shape == slide.shapes.title`` cannot be trusted.
    """
    title = slide.shapes.title
    title_el = title._element if title is not None else None
    for shape in list(slide.shapes):
        if not shape.is_placeholder or not shape.has_text_frame:
            continue
        if shape._element is title_el:
            continue
        if not shape.text_frame.text.strip():
            shape._element.getparent().remove(shape._element)
```

В `render()` заменить тело цикла по слайдам:

```python
    for spec in content.slides:
        fmt = cfg.fmt
        s = prs.slides.add_slide(layouts[cfg.layouts[spec.kind]])
        title = spec.title.upper() if (spec.kind == "title" and fmt.title_slide_uppercase) else spec.title
        s.shapes.title.text = title
        if spec.kind == "title" and spec.subtitle:
            with contextlib.suppress(Exception):
                s.placeholders[1].text = spec.subtitle
        elif spec.kind == "table" and spec.table:
            _add_table(s, spec.table, theme, top=fmt.table_top)
        elif spec.kind in ("agenda", "content"):
            side = bool(spec.image or (spec.code and spec.bullets))
            if side:
                ph = s.placeholders[1]
                l0, t0, h0 = ph.left, ph.top, ph.height
                ph.left, ph.top, ph.height, ph.width = l0, t0, h0, Inches(fmt.bullets_width_narrow)
            if spec.bullets:
                sizes = (
                    None
                    if fmt.body_font == "inherit"
                    else fmt.body_font["with_image" if side else "bullets_only"]
                )
                _set_body(s, spec.bullets, sizes)
            else:
                s.placeholders[1].text_frame.clear()
            if spec.image:
                _add_pic(s, str(media / spec.image), cfg.image_box)
            elif spec.code:
                side_code = bool(spec.bullets)
                safe = cfg.code_box if side_code else cfg.code_box_full
                box = _fit_code_box(
                    spec.code,
                    safe,
                    cfg.code_style,
                    min_height=2.0 if side_code else 2.6,
                )
                size = _fit_code_size(spec.code, safe, cfg.code_style)
                _add_code(
                    s, spec.code, spec.code_caption, theme, box, cfg.code_style, size,
                    border=fmt.code_border,
                )
        _add_materials(s, spec.materials, theme)
        if spec.notes:
            _set_notes(s, spec.notes)
        if fmt.drop_empty_placeholders:
            _drop_empty_placeholders(s)
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_gen src/tests -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add settings/formats.yml src/preza_gen/renderers/pptx.py src/preza_gen/tests/test_format_render.py
git commit -m "feat(preza-gen): профиль исполняет R1/R3/R6/R7/R11 — кегль мастера, низ таблиц, обводка код-панели (#8)"
```

---

### Task 5: Рендерер исполняет R2 (визуал к низу) и R4 (адаптивная колонка)

**Files:**
- Modify: `src/preza_gen/renderers/pptx.py` — `_visual_lines`, `_add_pic`, `render`
- Test: `src/preza_gen/tests/test_format_render.py` (дополнить), `src/preza_gen/tests/test_layout.py` (дополнить)

**Interfaces:**
- Consumes: `settings.Format` (Task 3), `_fit_code_box` / `_fit_code_size` (существующие)
- Produces: `_visual_lines(code: str, width_in: float, size: float, char_w_em: float = _CHAR_W_EM) -> int`, `_master_body_sizes(prs) -> dict[int, float]`, `_bullets_height(bullets: list, width_in: float, sizes: dict[int, float]) -> float`, `_anchor_bottom(box: ImageBox, bottom: float, top_min: float) -> ImageBox`, `_add_pic(slide, path, box, *, anchor_bottom: float | None = None)`

- [ ] **Step 1: Написать падающий тест**

Дописать в `src/preza_gen/tests/test_layout.py`:

```python
def test_anchor_bottom_pins_the_lower_edge():
    from preza_gen.renderers.pptx import _anchor_bottom

    box = ImageBox(left=6.95, top=1.7, width=5.95, height=3.0)
    pinned = _anchor_bottom(box, bottom=7.0, top_min=1.7)
    assert abs(pinned.top + pinned.height - 7.0) < 1e-9
    assert pinned.height == box.height


def test_anchor_bottom_clamps_at_top_min():
    """A panel taller than the safe area must not climb into the title."""
    from preza_gen.renderers.pptx import _anchor_bottom

    box = ImageBox(left=6.95, top=1.7, width=5.95, height=6.0)
    pinned = _anchor_bottom(box, bottom=7.0, top_min=1.7)
    assert pinned.top == 1.7
    assert abs(pinned.height - 5.3) < 1e-9


def test_bullets_height_grows_with_text():
    from preza_gen.renderers.pptx import _bullets_height

    sizes = {0: 18.0, 1: 16.0, 2: 14.0}
    short = _bullets_height(["раз", "два"], 12.3, sizes)
    long = _bullets_height(["раз" * 60, "два" * 60, "три" * 60], 12.3, sizes)
    assert long > short > 0


def test_body_text_wraps_wider_than_monospace():
    """Proportional body text fits more characters per inch than the code metric assumes."""
    from preza_gen.renderers.pptx import _BODY_CHAR_W_EM, _visual_lines

    text = "и" * 200
    assert _visual_lines(text, 6.2, 18, _BODY_CHAR_W_EM) < _visual_lines(text, 6.2, 18)
```

Дописать в `src/preza_gen/tests/test_format_render.py`:

```python
def _code_content(tmp_path: Path, fmt_name: str, bullets: list, code: str) -> Path:
    doc = {
        "deck": {
            "out_name": "MiniCode",
            "naming": "fixed",
            "version_major": 3,
            "format": fmt_name,
            "source_deck": str(_REPO / "data" / "source" / "MLinside-шаблон-презентаций.pptx"),
            "downloads_dir": None,
        },
        "content": [{"kind": "content", "title": "Код", "bullets": bullets, "code": code}],
    }
    p = tmp_path / f"mini-code-{fmt_name}.yml"
    p.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return p


def _build_content(tmp_path: Path, content: Path, tag: str) -> Presentation:
    out = tmp_path / f"out-{tag}"
    out.mkdir(exist_ok=True)
    s = yaml.safe_load(SETTINGS_YML.read_text(encoding="utf-8"))
    s["settings"].update(
        out_dir=str(out),
        formats_file=str(_REPO / "settings" / "formats.yml"),
        template=str(_REPO / s["settings"]["template"]),
    )
    sett = tmp_path / f"settings-{tag}.yml"
    sett.write_text(yaml.safe_dump(s, allow_unicode=True), encoding="utf-8")
    return Presentation(str(pipeline.build_deck(sett, content, pptx=True).out_path))


def test_code_panel_is_pinned_to_the_bottom(tmp_path):
    """R2: whatever the snippet's height, the panel's lower edge sits at visual_bottom."""
    content = _code_content(tmp_path, "alina-2026-08", ["раз", "два"], "select 1\nfrom t")
    prs = _build_content(tmp_path, content, "code")
    panel = next(
        sh for sh in prs.slides[0].shapes if sh.shape_type is not None and sh.name.startswith("Rounded")
    )
    bottom_in = (panel.top + panel.height) / 914400
    assert abs(bottom_in - 7.0) < 0.02


def test_short_bullets_take_the_full_width_over_the_panel(tmp_path):
    """R4: two short bullets end well above the panel → full width; a long list stays narrow."""
    short = _build_content(
        tmp_path, _code_content(tmp_path, "alina-2026-08", ["раз", "два"], "select 1"), "short"
    )
    long_bullets = ["очень длинный пункт про трансформацию данных " * 3] * 6
    long = _build_content(
        tmp_path,
        _code_content(tmp_path, "alina-2026-08", long_bullets, "select 1\n" * 20),
        "long",
    )
    w_short = short.slides[0].placeholders[1].width / 914400
    w_long = long.slides[0].placeholders[1].width / 914400
    assert w_short > 10.0
    assert abs(w_long - 6.2) < 0.02
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `python3 -m pytest src/preza_gen/tests/test_layout.py src/preza_gen/tests/test_format_render.py -v`
Expected: FAIL — `ImportError: cannot import name '_anchor_bottom'`

- [ ] **Step 3: Реализация**

В `src/preza_gen/renderers/pptx.py` — обобщить метрику и добавить хелперы (рядом с `_visual_lines`):

```python
_CHAR_W_EM = 0.72
# Proportional body text (Corbel and its substitutes) packs more characters per em than the
# worst-case monospace advance above. Used only to ESTIMATE whether a bullet block clears a
# bottom-anchored visual — never to place text.
_BODY_CHAR_W_EM = 0.5
_LINE_H_EM = 1.3
_PAD_IN = 0.28
_MARGIN_IN = 0.28


def _visual_lines(code: str, width_in: float, size: float, char_w_em: float = _CHAR_W_EM) -> int:
    """Count RENDERED lines — long lines wrap inside the panel and each wrap costs height.

    >>> _visual_lines("ab\\ncd", 10.0, 13)          # short lines never wrap
    2
    >>> _visual_lines("x" * 400, 2.0, 13) > 4       # one long line wraps many times
    True
    """
    usable = max(0.5, width_in - _MARGIN_IN)
    cpl = max(8, int(usable / (size / 72 * char_w_em)))
    lines = code.rstrip("\n").splitlines() or [""]
    return sum(max(1, math.ceil(len(ln) / cpl)) for ln in lines)
```

```python
def _master_body_sizes(prs) -> dict[int, float]:
    """Body text sizes (pt) the template master defines per indent level.

    With `body_font: inherit` the renderer sets no size, so this is the only way to know
    how tall a bullet block will be. Levels the master omits fall back to the last one.
    """
    sizes: dict[int, float] = {}
    for master in prs.slide_masters:
        styles = master._element.find(qn("p:txStyles"))
        if styles is None:
            continue
        body = styles.find(qn("p:bodyStyle"))
        if body is None:
            continue
        for lvl, node in enumerate(body):
            props = node.find(qn("a:defRPr"))
            if props is not None and props.get("sz"):
                sizes[lvl] = int(props.get("sz")) / 100
        if sizes:
            break
    if not sizes:
        raise ValueError("template master defines no body text sizes — cannot use body_font: inherit")
    return sizes


def _bullets_height(bullets: list, width_in: float, sizes: dict[int, float]) -> float:
    """Estimated height (inches) of a bullet block at ``width_in``."""
    total = _PAD_IN
    for item in bullets:
        text, lvl = (item[0], item[1]) if isinstance(item, (list, tuple)) else (item, 0)
        size = sizes.get(lvl, sizes[max(sizes)])
        total += _visual_lines(text, width_in, size, _BODY_CHAR_W_EM) * (size / 72 * _LINE_H_EM)
    return total


def _anchor_bottom(box: ImageBox, bottom: float, top_min: float) -> ImageBox:
    """Pin a box's LOWER edge to ``bottom``, never letting its top climb above ``top_min``.

    >>> _anchor_bottom(ImageBox(1.0, 1.7, 5.0, 3.0), bottom=7.0, top_min=1.7).top
    4.0
    """
    top = bottom - box.height
    if top < top_min:
        return ImageBox(left=box.left, top=top_min, width=box.width, height=bottom - top_min)
    return ImageBox(left=box.left, top=top, width=box.width, height=box.height)
```

`_add_pic` — принять якорь:

```python
def _add_pic(slide, path: str, box: ImageBox, *, anchor_bottom: float | None = None) -> tuple[float, float]:
    """Place a picture fitted into ``box``; return its (top, height) in inches.

    With ``anchor_bottom`` the fitted image's LOWER edge is pinned there instead of the
    image being centred in the box (R2).
    """
    bl = Inches(box.left)
    bw, bh = int(Inches(box.width)), int(Inches(box.height))
    iw, ih = Image.open(path).size
    w, h = fit_image_box(iw, ih, bw, bh)
    h_in = h / 914400
    if anchor_bottom is None:
        top_emu = Inches(box.top) + (bh - h) // 2
    else:
        top_emu = Inches(anchor_bottom - h_in)
    slide.shapes.add_picture(path, bl + (bw - w) // 2, int(top_emu), width=w, height=h)
    return int(top_emu) / 914400, h_in
```

В `render()` — переставить порядок: сначала геометрия визуала, затем ширина буллетов. Заменить ветку `elif spec.kind in ("agenda", "content"):` целиком на:

```python
        elif spec.kind in ("agenda", "content"):
            side = bool(spec.image or (spec.code and spec.bullets))
            # The visual's box is resolved FIRST: with bullets_width: adaptive the bullet
            # column's width depends on where the visual's top edge lands.
            visual_top: float | None = None
            code_box: ImageBox | None = None
            code_size: float | None = None
            if spec.code:
                side_code = bool(spec.bullets)
                safe = cfg.code_box if side_code else cfg.code_box_full
                if fmt.visual_anchor == "bottom":
                    safe = ImageBox(
                        left=safe.left,
                        top=fmt.visual_top_min,
                        width=safe.width,
                        height=fmt.visual_bottom - fmt.visual_top_min,
                    )
                code_box = _fit_code_box(
                    spec.code, safe, cfg.code_style, min_height=2.0 if side_code else 2.6
                )
                code_size = _fit_code_size(spec.code, safe, cfg.code_style)
                if fmt.visual_anchor == "bottom":
                    code_box = _anchor_bottom(code_box, fmt.visual_bottom, fmt.visual_top_min)
                visual_top = code_box.top

            if side:
                ph = s.placeholders[1]
                l0, t0, h0 = ph.left, ph.top, ph.height
                width_in = fmt.bullets_width_narrow
                if fmt.bullets_width == "adaptive" and spec.bullets:
                    sizes_est = (
                        _master_body_sizes(prs)
                        if fmt.body_font == "inherit"
                        else {k: float(v) for k, v in fmt.body_font["with_image"].items()}
                    )
                    top_in = t0 / 914400
                    ceiling = (visual_top if visual_top is not None else fmt.visual_bottom - 5.0)
                    if (
                        top_in + _bullets_height(spec.bullets, fmt.bullets_width_full, sizes_est)
                        <= ceiling - fmt.bullets_gap
                    ):
                        width_in = fmt.bullets_width_full
                ph.left, ph.top, ph.height, ph.width = l0, t0, h0, Inches(width_in)
            if spec.bullets:
                sizes = (
                    None
                    if fmt.body_font == "inherit"
                    else fmt.body_font["with_image" if side else "bullets_only"]
                )
                _set_body(s, spec.bullets, sizes)
            else:
                s.placeholders[1].text_frame.clear()

            if spec.image:
                _add_pic(
                    s,
                    str(media / spec.image),
                    cfg.image_box,
                    anchor_bottom=(fmt.visual_bottom if fmt.visual_anchor == "bottom" else None),
                )
            elif spec.code and code_box is not None and code_size is not None:
                _add_code(
                    s, spec.code, spec.code_caption, theme, code_box, cfg.code_style, code_size,
                    border=fmt.code_border,
                )
```

> **Замечание для реализатора:** при `bullets_width: adaptive` и картинке `visual_top` неизвестен до вставки (высота зависит от пропорций файла). Используется консервативный потолок `fmt.visual_bottom - 5.0` (полная высота `image_box`) — колонка расширяется только там, где текст заведомо короткий. Это осознанный компромисс, а не недосмотр: ошибиться в сторону узкой колонки безопасно, в сторону широкой — наложение текста на картинку.

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_gen src/tests -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add src/preza_gen/renderers/pptx.py src/preza_gen/tests/test_layout.py src/preza_gen/tests/test_format_render.py
git commit -m "feat(preza-gen): профиль исполняет R2/R4 — визуал к нижней кромке, адаптивная колонка буллетов (#8)"
```

---

### Task 6: Патч-версии в паблишере

**Files:**
- Modify: `src/publisher/detect.py:15-59`
- Test: `src/publisher/tests/test_detect_patch.py` (создать)

**Interfaces:**
- Consumes: ничего (регекс намеренно свой, см. docstring `detect.py`)
- Produces: `BuiltDeck(out_name, path, major, minor, patch, descr, sig)` с `version` = `"3.19.1+alina-fmt"` и порядком по `(major, minor, patch)`

- [ ] **Step 1: Написать падающий тест**

Создать `src/publisher/tests/test_detect_patch.py`:

```python
"""The publisher must see a patch build as a newer version than its parent."""

from publisher import detect


def _touch(d, name):
    p = d / name
    p.write_bytes(b"x")
    return p


def test_patch_version_is_newer_than_its_parent(tmp_path):
    _touch(tmp_path, "Deck_v3.19.pptx")
    _touch(tmp_path, "Deck_v3.19.1+alina-fmt.pptx")

    newest = detect.newest(tmp_path, "Deck")
    assert newest is not None
    assert (newest.major, newest.minor, newest.patch) == (3, 19, 1)
    assert newest.descr == "alina-fmt"
    assert newest.version == "3.19.1+alina-fmt"


def test_plain_versions_keep_their_shape(tmp_path):
    _touch(tmp_path, "Deck_v3.19.pptx")
    newest = detect.newest(tmp_path, "Deck")
    assert newest.version == "3.19"
    assert newest.patch == 0


def test_exact_stem_still_required(tmp_path):
    _touch(tmp_path, "Deck-old_v9.9.pptx")
    _touch(tmp_path, "Deck_v3.19.1+x.pptx")
    assert detect.newest(tmp_path, "Deck").version == "3.19.1+x"


def test_ordering_ignores_the_build_tag(tmp_path):
    _touch(tmp_path, "Deck_v3.19.1+aaa.pptx")
    _touch(tmp_path, "Deck_v3.20.pptx")
    assert detect.newest(tmp_path, "Deck").version == "3.20"
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/publisher/tests/test_detect_patch.py -v`
Expected: FAIL — `TypeError`/`AttributeError`: у `BuiltDeck` нет `patch`

- [ ] **Step 3: Реализация**

В `src/publisher/detect.py` заменить регекс, датакласс и `find_versions`:

```python
# Anchored to the .pptx suffix and paired with an exact-stem check. Patch and build tag are
# optional: "_v3.19.pptx", "_v3.19.1.pptx", "_v3.19.1+alina-fmt.pptx" all parse.
_VER_RE = re.compile(r"_v(\d+)\.(\d+)(?:\.(\d+))?(?:\+([a-z0-9][a-z0-9._-]*))?\.pptx$")


@dataclass(frozen=True)
class BuiltDeck:
    """One built pptx artifact of one deck."""

    out_name: str
    path: Path
    major: int
    minor: int
    patch: int
    descr: str
    sig: str  # "<int mtime>:<size>"

    @property
    def version(self) -> str:
        """
        >>> BuiltDeck("X", Path("X_v3.14.pptx"), 3, 14, 0, "", "0:0").version
        '3.14'
        >>> BuiltDeck("X", Path("X_v3.19.1+alina-fmt.pptx"), 3, 19, 1, "alina-fmt", "0:0").version
        '3.19.1+alina-fmt'
        """
        core = f"{self.major}.{self.minor}" + (f".{self.patch}" if self.patch else "")
        return core + (f"+{self.descr}" if self.descr else "")
```

```python
def find_versions(out_dir: Path, out_name: str) -> list[BuiltDeck]:
    """Every built version of one deck, version-ascending.

    The stem must match ``out_name`` exactly: ``MLInside_Dagster`` must not pick up
    ``MLInside_Dagster-old_v1.1.pptx`` (glob prefix alone would). Ordering is the numeric
    triple — the build tag labels a build, it never ranks one.
    """
    found: list[BuiltDeck] = []
    if not out_dir.is_dir():
        return found
    for p in out_dir.glob(f"{out_name}_v*.pptx"):
        m = _VER_RE.search(p.name)
        if not m or p.name[: -len(m.group(0))] != out_name:
            continue
        found.append(
            BuiltDeck(
                out_name,
                p,
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3) or 0),
                m.group(4) or "",
                sig(p),
            )
        )
    return sorted(found, key=lambda d: (d.major, d.minor, d.patch))
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/publisher -q && just publish-status`
Expected: PASS; `publish-status` печатает статус без ошибок

- [ ] **Step 5: Коммит**

```bash
git add src/publisher/detect.py src/publisher/tests/test_detect_patch.py
git commit -m "feat(publisher): патч-версии видны ленте публикации как новые (#8)"
```

---

### Task 7: `preza_merge.model` — нормализованная модель деки

**Files:**
- Create: `src/preza_merge/__init__.py`, `src/preza_merge/model.py`, `src/preza_merge/tests/__init__.py`, `src/preza_merge/tests/conftest.py`, `src/preza_merge/tests/test_model.py`
- Modify: `pyproject.toml` (не требуется — `packages.find` уже смотрит в `src`)

**Interfaces:**
- Consumes: ничего
- Produces: `preza_merge.model.load(path: str | Path) -> Deck`; датаклассы `Deck(slides: list[Slide], theme_fonts: dict[str, str], master_body_sizes: dict[int, float])`, `Slide(n: int, layout: str, title: str, notes: str, shapes: list[Shape])`, `Shape(name, kind, left, top, width, height, placeholder, body_pr: dict, paras: list[Para], table: list[list[str]] | None, hyperlinks: list[str], line_color: str | None, line_width: int | None)`, `Para(level: int, props: dict, end_size: int | None, runs: list[Run])`, `Run(text, size: int | None, bold, italic, underline, font, color)`; хелперы `Shape.text() -> list[str]` (склеенные абзацы с нормализацией пробелов), `Shape.bottom -> float`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/conftest.py`:

```python
"""Synthetic decks for merge-lane tests — built on python-pptx's own template.

Deliberately independent of the course template (data/ is git-lfs): the merge lane must be
testable on any checkout.
"""

from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Inches, Pt


def _add(prs, title, bullets, *, sizes=None, body_width=None, body_top=None):
    slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title and Content
    slide.shapes.title.text = title
    body = slide.placeholders[1]
    if body_width is not None:
        body.width = Inches(body_width)
    if body_top is not None:
        body.top = Inches(body_top)
    tf = body.text_frame
    tf.clear()
    for i, text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        if sizes is not None:
            for r in p.runs:
                r.font.size = Pt(sizes)
    return slide


@pytest.fixture
def make_deck(tmp_path):
    """make_deck("name", [(title, [bullets]), ...], sizes=20) -> Path to a .pptx"""

    def _make(name: str, slides, *, sizes=None, body_width=None, body_top=None) -> Path:
        prs = Presentation()
        for title, bullets in slides:
            _add(prs, title, bullets, sizes=sizes, body_width=body_width, body_top=body_top)
        out = tmp_path / f"{name}.pptx"
        prs.save(str(out))
        return out

    return _make
```

Создать `src/preza_merge/tests/test_model.py`:

```python
"""The normalized deck model — what the differ is allowed to see."""

from preza_merge import model


def test_model_captures_titles_bullets_and_geometry(make_deck):
    path = make_deck("a", [("Заголовок", ["раз", "два"])], sizes=20)
    deck = model.load(path)

    assert len(deck.slides) == 1
    slide = deck.slides[0]
    assert slide.title == "Заголовок"
    body = next(sh for sh in slide.shapes if sh.paras and sh.name != slide.shapes_title_name)
    assert body.text() == ["раз", "два"]
    assert body.width > 0
    assert {r.size for p in body.paras for r in p.runs} == {2000}


def test_text_joins_runs_and_normalizes_whitespace(make_deck):
    """A PowerPoint round-trip splits one bullet into many runs — the model must rejoin."""
    from pptx import Presentation

    path = make_deck("b", [("T", ["one"])])
    prs = Presentation(str(path))
    para = prs.slides[0].placeholders[1].text_frame.paragraphs[0]
    para.runs[0].text = "od"
    extra = para.add_run()
    extra.text = "in  \n one"
    prs.save(str(path))

    deck = model.load(path)
    body = next(sh for sh in deck.slides[0].shapes if sh.paras and sh.paras[0].runs)
    assert body.text() == ["odin one"]


def test_bottom_edge_is_derived(make_deck):
    path = make_deck("c", [("T", ["x"])])
    shape = next(sh for sh in model.load(path).slides[0].shapes if sh.height)
    assert abs(shape.bottom - (shape.top + shape.height)) < 1e-9


def test_shape_outline_is_captured(make_deck):
    """R11 lives here: a diff blind to outlines cannot notice a removed border."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    path = make_deck("e", [("T", ["x"])])
    prs = Presentation(str(path))
    shape = prs.slides[0].shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(1), Inches(2), Inches(1)
    )
    shape.line.color.rgb = RGBColor.from_string("2419FF")
    shape.line.width = Pt(1)
    prs.save(str(path))

    found = next(sh for sh in model.load(path).slides[0].shapes if sh.name.startswith("Rounded"))
    assert found.line_color == "2419FF"
    assert found.line_width == 12700


def test_master_body_sizes_are_read(make_deck):
    path = make_deck("d", [("T", ["x"])])
    sizes = model.load(path).master_body_sizes
    assert sizes and all(v > 0 for v in sizes.values())
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_merge -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge'`

- [ ] **Step 3: Реализация**

Создать `src/preza_merge/__init__.py`:

```python
"""preza_merge — merge a reviewer's .pptx fork back into the deck GENERATOR.

The lane normalizes decks into a comparable model, diffs the three sides (base / ours /
theirs), derives formatting RULES with evidence, writes them into a named profile that
preza_gen executes, and verifies the result by rebuilding the base content with the new
profile against the fork. Spec: docs/preza-merge-lane.md.
"""
```

Создать `src/preza_merge/model.py`:

```python
"""preza_merge.model — a normalized, comparable model of a .pptx.

Only what the differ and the rule detectors are allowed to reason about: geometry in
inches, paragraph/run properties as raw OOXML attribute values, joined text, notes, theme
fonts and the master's body sizes. Picture bytes, animations and layout internals are out
of scope by design — the lane never rewrites a deck's content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Emu

_EMU_IN = 914400
_WS = re.compile(r"\s+")
# Paragraph/run/body attributes worth comparing — everything else is round-trip noise.
_BODY_KEYS = ("lIns", "tIns", "rIns", "bIns", "anchor", "wrap", "vert")
_PARA_KEYS = ("marL", "indent", "algn")
_RUN_KEYS = ("sz", "b", "i", "u")


@dataclass(frozen=True)
class Run:
    text: str
    size: int | None  # OOXML sz — hundredths of a point (2000 == 20 pt)
    bold: str | None
    italic: str | None
    underline: str | None
    font: str | None
    color: str | None


@dataclass(frozen=True)
class Para:
    level: int
    props: dict
    end_size: int | None  # endParaRPr@sz — survives when every run's size is cleared
    runs: list[Run]

    def text(self) -> str:
        """Runs joined, whitespace normalized — one paragraph, one string."""
        return _WS.sub(" ", "".join(r.text for r in self.runs)).strip()


@dataclass(frozen=True)
class Shape:
    name: str
    kind: str
    left: float
    top: float
    width: float
    height: float
    placeholder: str | None
    body_pr: dict
    paras: list[Para] = field(default_factory=list)
    table: list[list[str]] | None = None
    hyperlinks: list[str] = field(default_factory=list)
    line_color: str | None = None  # outline: hex, a theme role ("tx1"), or None when absent
    line_width: int | None = None  # EMU

    @property
    def bottom(self) -> float:
        return self.top + self.height

    def text(self) -> list[str]:
        """Non-empty paragraph texts, in order."""
        return [t for t in (p.text() for p in self.paras) if t]


@dataclass(frozen=True)
class Slide:
    n: int  # 1-based
    layout: str
    title: str
    notes: str
    shapes: list[Shape]
    shapes_title_name: str | None

    def by_name(self) -> dict[str, Shape]:
        return {s.name: s for s in self.shapes}


@dataclass(frozen=True)
class Deck:
    path: Path
    slides: list[Slide]
    theme_fonts: dict[str, str]
    master_body_sizes: dict[int, float]

    def titles(self) -> list[str]:
        return [s.title for s in self.slides]


def _in(value) -> float:
    return 0.0 if value is None else round(Emu(int(value)).inches, 3)


def _body_pr(text_frame) -> dict:
    node = text_frame._txBody.find(qn("a:bodyPr"))
    if node is None:
        return {}
    out = {k: node.get(k) for k in _BODY_KEYS if node.get(k) is not None}
    for child in node:
        tag = child.tag.split("}")[1]
        if tag in ("normAutofit", "spAutoFit", "noAutofit"):
            out["autofit"] = tag
    return out


def _para(paragraph) -> Para:
    props: dict = {}
    node = paragraph._p.find(qn("a:pPr"))
    end_size = None
    if node is not None:
        props = {k: node.get(k) for k in _PARA_KEYS if node.get(k) is not None}
        for tag in ("lnSpc", "spcBef", "spcAft"):
            el = node.find(qn(f"a:{tag}"))
            if el is not None and len(el):
                props[tag] = el[0].get("val")
        for tag in ("buNone", "buChar", "buAutoNum"):
            if node.find(qn(f"a:{tag}")) is not None:
                props[tag] = True
    end = paragraph._p.find(qn("a:endParaRPr"))
    if end is not None and end.get("sz"):
        end_size = int(end.get("sz"))
    return Para(
        level=paragraph.level,
        props=props,
        end_size=end_size,
        runs=[_run(r) for r in paragraph.runs],
    )


def _run(run) -> Run:
    node = run._r.find(qn("a:rPr"))
    size = font = color = bold = italic = underline = None
    if node is not None:
        size = int(node.get("sz")) if node.get("sz") else None
        bold, italic, underline = node.get("b"), node.get("i"), node.get("u")
        latin = node.find(qn("a:latin"))
        font = latin.get("typeface") if latin is not None else None
        fill = node.find(qn("a:solidFill"))
        if fill is not None and len(fill):
            color = fill[0].get("val") or fill[0].get("lastClr")
    return Run(run.text, size, bold, italic, underline, font, color)


def _hyperlinks(shape) -> list[str]:
    """External link targets inside a shape, in document order."""
    if not shape.has_text_frame:
        return []
    out = []
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            address = run.hyperlink.address
            if address:
                out.append(address)
    return out


def _line(shape) -> tuple[str | None, int | None]:
    """Outline colour + width of a shape, or (None, None) when it defines no line.

    The colour is returned RAW — a hex value or a theme role like "tx1" — because that is
    exactly what tells an accent border apart from the theme-text one the manager switched to.
    """
    props = shape._element.find(qn("p:spPr"))
    line = props.find(qn("a:ln")) if props is not None else None
    if line is None:
        return None, None
    fill = line.find(qn("a:solidFill"))
    color = None
    if fill is not None and len(fill):
        color = fill[0].get("val") or fill[0].get("lastClr")
    width = int(line.get("w")) if line.get("w") else None
    return color, width


def _shape(shape) -> Shape:
    paras: list[Para] = []
    body_pr: dict = {}
    if shape.has_text_frame:
        body_pr = _body_pr(shape.text_frame)
        paras = [_para(p) for p in shape.text_frame.paragraphs]
    table = None
    if getattr(shape, "has_table", False) and shape.has_table:
        table = [[c.text for c in row.cells] for row in shape.table.rows]
    placeholder = None
    if shape.is_placeholder:
        placeholder = f"{shape.placeholder_format.type}/{shape.placeholder_format.idx}"
    line_color, line_width = _line(shape)
    return Shape(
        name=shape.name,
        kind=str(shape.shape_type),
        left=_in(shape.left),
        top=_in(shape.top),
        width=_in(shape.width),
        height=_in(shape.height),
        placeholder=placeholder,
        body_pr=body_pr,
        paras=paras,
        table=table,
        hyperlinks=_hyperlinks(shape),
        line_color=line_color,
        line_width=line_width,
    )


def _theme_fonts(prs) -> dict[str, str]:
    for part in prs.part.package.iter_parts():
        if "theme" not in str(part.partname):
            continue
        xml = part.blob.decode("utf-8", "ignore")
        found = re.findall(r'<a:(major|minor)Font>\s*<a:latin typeface="([^"]*)"', xml)
        if found:
            return {k: v for k, v in found}
    return {}


def _master_body_sizes(prs) -> dict[int, float]:
    sizes: dict[int, float] = {}
    for master in prs.slide_masters:
        styles = master._element.find(qn("p:txStyles"))
        if styles is None:
            continue
        body = styles.find(qn("p:bodyStyle"))
        if body is None:
            continue
        for lvl, node in enumerate(body):
            props = node.find(qn("a:defRPr"))
            if props is not None and props.get("sz"):
                sizes[lvl] = int(props.get("sz")) / 100
        if sizes:
            break
    return sizes


def load(path: str | Path) -> Deck:
    """Normalize a .pptx into the comparable model."""
    p = Path(path).expanduser()
    prs = Presentation(str(p))
    slides = []
    for i, s in enumerate(prs.slides, 1):
        title_shape = s.shapes.title
        slides.append(
            Slide(
                n=i,
                layout=s.slide_layout.name,
                title=(title_shape.text if title_shape is not None else ""),
                notes=(s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""),
                shapes=[_shape(sh) for sh in s.shapes],
                shapes_title_name=(title_shape.name if title_shape is not None else None),
            )
        )
    return Deck(
        path=p,
        slides=slides,
        theme_fonts=_theme_fonts(prs),
        master_body_sizes=_master_body_sizes(prs),
    )
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add src/preza_merge/
git commit -m "feat(preza-merge): нормализованная модель деки — основа диффа (#8)"
```

---

### Task 8: `preza_merge.diff` — попарный дифф

**Files:**
- Create: `src/preza_merge/diff.py`, `src/preza_merge/tests/test_diff.py`

**Interfaces:**
- Consumes: `preza_merge.model.Deck` (Task 7)
- Produces: `preza_merge.diff.compare(a: Deck, b: Deck) -> DiffReport`; `DiffReport(slide_count: tuple[int, int], theme_fonts: tuple[dict, dict], slides: list[SlideDiff], counts: dict[str, int])`; `SlideDiff(n: int, title: str, classes: set[str], shapes_added: list[str], shapes_removed: list[str], geometry: list[GeomChange], runs_size_cleared: int, runs_size_changed: list[tuple[int, int]], paras_before: int, paras_after: int, notes_lost: bool, text_changed: list[str])`; `GeomChange(shape: str, attr: str, before: float, after: float)`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/test_diff.py`:

```python
"""Pairwise diff — what counts as a real change and what is round-trip noise."""

from preza_merge import diff, model


def test_identical_decks_report_nothing(make_deck):
    a = make_deck("a", [("T", ["раз", "два"])], sizes=20)
    b = make_deck("b", [("T", ["раз", "два"])], sizes=20)
    rep = diff.compare(model.load(a), model.load(b))
    assert rep.counts["text"] == 0
    assert rep.counts["geometry"] == 0
    assert rep.counts["font"] == 0


def test_run_splitting_is_not_a_text_change(make_deck):
    """Regression: a Google Slides round-trip split runs and looked like 34 text edits."""
    from pptx import Presentation

    a = make_deck("a", [("T", ["раз два"])])
    b = make_deck("b", [("T", ["раз два"])])
    prs = Presentation(str(b))
    para = prs.slides[0].placeholders[1].text_frame.paragraphs[0]
    para.runs[0].text = "раз"
    para.add_run().text = " два"
    prs.save(str(b))

    rep = diff.compare(model.load(a), model.load(b))
    assert rep.counts["text"] == 0


def test_cleared_run_sizes_are_counted(make_deck):
    a = make_deck("a", [("T", ["раз", "два"])], sizes=20)
    b = make_deck("b", [("T", ["раз", "два"])])
    rep = diff.compare(model.load(a), model.load(b))
    assert rep.slides[0].runs_size_cleared == 2
    assert rep.counts["font"] >= 1


def test_geometry_changes_are_listed_per_shape(make_deck):
    a = make_deck("a", [("T", ["раз"])], body_width=6.2)
    b = make_deck("b", [("T", ["раз"])], body_width=10.0)
    rep = diff.compare(model.load(a), model.load(b))
    changes = [c for c in rep.slides[0].geometry if c.attr == "width"]
    assert changes and abs(changes[0].after - 10.0) < 0.02


def test_lost_notes_and_merged_paragraphs_are_flagged(make_deck):
    from pptx import Presentation

    a = make_deck("a", [("T", ["раз", "два"])])
    prs = Presentation(str(a))
    prs.slides[0].notes_slide.notes_text_frame.text = "заметка"
    prs.save(str(a))

    b = make_deck("b", [("T", ["раз два"])])
    rep = diff.compare(model.load(a), model.load(b))
    assert rep.slides[0].notes_lost is True
    assert rep.slides[0].paras_before > rep.slides[0].paras_after


def test_slide_count_mismatch_compares_the_common_prefix(make_deck):
    a = make_deck("a", [("T1", ["x"]), ("T2", ["y"])])
    b = make_deck("b", [("T1", ["x"])])
    rep = diff.compare(model.load(a), model.load(b))
    assert rep.slide_count == (2, 1)
    assert len(rep.slides) == 1
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_merge/tests/test_diff.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge.diff'`

- [ ] **Step 3: Реализация**

Создать `src/preza_merge/diff.py`:

```python
"""preza_merge.diff — pairwise comparison of two normalized decks.

Compares slide-by-slide over the common prefix and shape-by-shape by NAME within a slide.
Text is compared as joined, whitespace-normalized paragraphs: a PowerPoint/Google round-trip
shatters one bullet into many runs, and a run-level comparison would report every such
slide as edited when nothing was said differently.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .model import Deck, Shape

_GEOM_ATTRS = ("left", "top", "width", "height")
_GEOM_EPS = 0.01  # inches — below this a difference is float/round-trip noise


@dataclass(frozen=True)
class GeomChange:
    shape: str
    attr: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return round(self.after - self.before, 3)


@dataclass
class SlideDiff:
    n: int
    title: str
    classes: set[str] = field(default_factory=set)
    shapes_added: list[str] = field(default_factory=list)
    shapes_removed: list[str] = field(default_factory=list)
    geometry: list[GeomChange] = field(default_factory=list)
    runs_size_cleared: int = 0
    runs_size_changed: list[tuple[int, int]] = field(default_factory=list)
    paras_before: int = 0
    paras_after: int = 0
    notes_lost: bool = False
    text_changed: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.classes)


@dataclass
class DiffReport:
    slide_count: tuple[int, int]
    theme_fonts: tuple[dict, dict]
    slides: list[SlideDiff]
    counts: Counter

    @property
    def theme_changed(self) -> bool:
        return self.theme_fonts[0] != self.theme_fonts[1]


def _compare_shape(name: str, a: Shape, b: Shape, sd: SlideDiff) -> None:
    for attr in _GEOM_ATTRS:
        before, after = getattr(a, attr), getattr(b, attr)
        if abs(after - before) > _GEOM_EPS:
            sd.geometry.append(GeomChange(name, attr, before, after))
            sd.classes.add("geometry")

    if a.text() != b.text():
        sd.text_changed.append(name)
        sd.classes.add("text")

    sd.paras_before += len([p for p in a.paras if p.runs])
    sd.paras_after += len([p for p in b.paras if p.runs])

    for pa, pb in zip(a.paras, b.paras):
        for ra, rb in zip(pa.runs, pb.runs):
            if ra.size is not None and rb.size is None:
                sd.runs_size_cleared += 1
                sd.classes.add("font")
            elif ra.size is not None and rb.size is not None and ra.size != rb.size:
                sd.runs_size_changed.append((ra.size, rb.size))
                sd.classes.add("font")
        if pa.props != pb.props or pa.level != pb.level:
            sd.classes.add("paragraph")


def compare(a: Deck, b: Deck) -> DiffReport:
    """Diff two decks over their common slide prefix."""
    slides: list[SlideDiff] = []
    counts: Counter = Counter()

    for sa, sb in zip(a.slides, b.slides):
        sd = SlideDiff(n=sa.n, title=sa.title)
        na, nb = sa.by_name(), sb.by_name()
        sd.shapes_added = sorted(set(nb) - set(na))
        sd.shapes_removed = sorted(set(na) - set(nb))
        if sd.shapes_added or sd.shapes_removed:
            sd.classes.add("shapes")
        for name in sorted(set(na) & set(nb)):
            _compare_shape(name, na[name], nb[name], sd)
        if sa.notes.strip() and not sb.notes.strip():
            sd.notes_lost = True
            sd.classes.add("notes")
        if sd.paras_before != sd.paras_after:
            sd.classes.add("paragraph")
        for cls in sd.classes:
            counts[cls] += 1
        slides.append(sd)

    for cls in ("text", "geometry", "font", "paragraph", "shapes", "notes"):
        counts.setdefault(cls, 0)
    if a.theme_fonts != b.theme_fonts:
        counts["theme"] = 1
    else:
        counts.setdefault("theme", 0)

    return DiffReport(
        slide_count=(len(a.slides), len(b.slides)),
        theme_fonts=(a.theme_fonts, b.theme_fonts),
        slides=slides,
        counts=counts,
    )
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add src/preza_merge/diff.py src/preza_merge/tests/test_diff.py
git commit -m "feat(preza-merge): попарный дифф — склейка прогонов гасит шум пересохранения (#8)"
```

---

### Task 9: `preza_merge.align` — 3-way выравнивание слайдов

**Files:**
- Create: `src/preza_merge/align.py`, `src/preza_merge/tests/test_align.py`

**Interfaces:**
- Consumes: `preza_merge.model.Deck` (Task 7)
- Produces: `preza_merge.align.align3(base: Deck, ours: Deck, theirs: Deck) -> Alignment`; `Alignment(rows: list[Row], unaligned: list[str])`; `Row(title: str, base: int | None, ours: int | None, theirs: int | None, status: str)` где `status ∈ {"unchanged", "ours-only", "theirs-only", "both", "dropped"}`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/test_align.py`:

```python
"""Three-way slide alignment by title sequence."""

from preza_merge import align, model


def _deck(make_deck, name, titles):
    return model.load(make_deck(name, [(t, ["x"]) for t in titles]))


def test_new_slides_on_our_side_are_ours_only(make_deck):
    base = _deck(make_deck, "b", ["A", "B"])
    ours = _deck(make_deck, "o", ["A", "NEW", "B"])
    theirs = _deck(make_deck, "t", ["A", "B"])

    res = align.align3(base, ours, theirs)
    new = next(r for r in res.rows if r.title == "NEW")
    assert new.status == "ours-only"
    assert new.base is None and new.ours == 2 and new.theirs is None


def test_slides_present_everywhere_are_unchanged(make_deck):
    base = _deck(make_deck, "b", ["A", "B"])
    res = align.align3(base, _deck(make_deck, "o", ["A", "B"]), _deck(make_deck, "t", ["A", "B"]))
    assert {r.status for r in res.rows} == {"unchanged"}


def test_reviewer_only_slide_is_theirs_only(make_deck):
    base = _deck(make_deck, "b", ["A"])
    ours = _deck(make_deck, "o", ["A"])
    theirs = _deck(make_deck, "t", ["A", "THEIRS"])
    res = align.align3(base, ours, theirs)
    assert next(r for r in res.rows if r.title == "THEIRS").status == "theirs-only"


def test_slide_dropped_on_our_side(make_deck):
    base = _deck(make_deck, "b", ["A", "GONE"])
    ours = _deck(make_deck, "o", ["A"])
    theirs = _deck(make_deck, "t", ["A", "GONE"])
    res = align.align3(base, ours, theirs)
    assert next(r for r in res.rows if r.title == "GONE").status == "dropped"


def test_duplicate_titles_are_reported_not_guessed(make_deck):
    base = _deck(make_deck, "b", ["DUP", "DUP"])
    ours = _deck(make_deck, "o", ["DUP", "DUP"])
    theirs = _deck(make_deck, "t", ["DUP", "DUP"])
    res = align.align3(base, ours, theirs)
    assert "DUP" in res.unaligned
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_merge/tests/test_align.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge.align'`

- [ ] **Step 3: Реализация**

Создать `src/preza_merge/align.py`:

```python
"""preza_merge.align — line up base / ours / theirs slides by title sequence.

Titles are the only stable identity across a fork: the reviewer's file has no slide ids and
its shape names are rewritten by the exporting tool. Ambiguity (a title appearing more than
once) is REPORTED, never guessed — a wrong alignment silently merges the wrong slide.
"""

from __future__ import annotations

import difflib
from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Row:
    """One logical slide across the three sides. Indices are 1-based, None = absent."""

    title: str
    base: int | None
    ours: int | None
    theirs: int | None
    status: str  # unchanged | ours-only | theirs-only | both | dropped


@dataclass
class Alignment:
    rows: list[Row] = field(default_factory=list)
    unaligned: list[str] = field(default_factory=list)

    def by_status(self, status: str) -> list[Row]:
        return [r for r in self.rows if r.status == status]


def _pairs(base_titles: list[str], other_titles: list[str]) -> dict[int, int]:
    """base index → other index (both 0-based) for slides the matcher considers equal."""
    matcher = difflib.SequenceMatcher(a=base_titles, b=other_titles, autojunk=False)
    out: dict[int, int] = {}
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op != "equal":
            continue
        for offset in range(i2 - i1):
            out[i1 + offset] = j1 + offset
    return out


def _status(in_ours: bool, in_theirs: bool, in_base: bool) -> str:
    if in_base and in_ours and in_theirs:
        return "unchanged"
    if in_base and not in_ours and in_theirs:
        return "dropped"
    if not in_base and in_ours and not in_theirs:
        return "ours-only"
    if not in_base and not in_ours and in_theirs:
        return "theirs-only"
    return "both"


def align3(base, ours, theirs) -> Alignment:
    """Align three decks by title sequence; ambiguous titles land in ``unaligned``."""
    bt, ot, tt = base.titles(), ours.titles(), theirs.titles()
    res = Alignment()

    dupes = {t for side in (bt, ot, tt) for t, n in Counter(side).items() if n > 1 and t}
    res.unaligned = sorted(dupes)

    b2o, b2t = _pairs(bt, ot), _pairs(bt, tt)
    matched_o, matched_t = set(b2o.values()), set(b2t.values())

    for i, title in enumerate(bt):
        o, t = b2o.get(i), b2t.get(i)
        res.rows.append(
            Row(
                title=title,
                base=i + 1,
                ours=(o + 1) if o is not None else None,
                theirs=(t + 1) if t is not None else None,
                status=_status(o is not None, t is not None, True),
            )
        )
    for j, title in enumerate(ot):
        if j not in matched_o:
            res.rows.append(Row(title, None, j + 1, None, "ours-only"))
    for k, title in enumerate(tt):
        if k not in matched_t:
            res.rows.append(Row(title, None, None, k + 1, "theirs-only"))

    res.rows.sort(key=lambda r: (r.ours or 10_000, r.base or 10_000, r.theirs or 10_000))
    return res
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add src/preza_merge/align.py src/preza_merge/tests/test_align.py
git commit -m "feat(preza-merge): 3-way выравнивание слайдов, неоднозначность не угадывается (#8)"
```

---

### Task 10: `preza_merge.rules` — детекторы правил и регрессий

**Files:**
- Create: `src/preza_merge/rules.py`, `settings/merge.yml`, `src/preza_merge/tests/test_rules.py`

**Interfaces:**
- Consumes: `diff.DiffReport` (Task 8), `model.Deck` (Task 7)
- Produces: `preza_merge.rules.MergeConfig` (загружается `MergeConfig.load(path)`), `Finding(rule: str, kind: str, key: str | None, value, share: float, evidence: str, slides: list[int])`, `detect(base: Deck, theirs: Deck, rep: DiffReport, cfg: MergeConfig) -> list[Finding]`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/test_rules.py`:

```python
"""Rule detectors: a systematic change becomes a profile key, a one-off does not."""

from pathlib import Path

import pytest
from pptx import Presentation

from preza_merge import diff, model, rules

_REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def cfg():
    return rules.MergeConfig.load(_REPO / "settings" / "merge.yml")


def _found(findings, rule):
    return next((f for f in findings if f.rule == rule), None)


def test_r1_fires_when_explicit_sizes_are_cleared(make_deck, cfg):
    base = model.load(make_deck("b", [("A", ["раз", "два"]), ("B", ["три"])], sizes=20))
    theirs = model.load(make_deck("t", [("A", ["раз", "два"]), ("B", ["три"])]))
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R1")
    assert found is not None
    assert found.key == "body_font" and found.value == "inherit"
    assert "3" in found.evidence  # three runs lost their explicit size


def test_r1_stays_silent_below_the_share_threshold(make_deck, cfg):
    """One slide out of five is a one-off, not a rule."""
    from pptx.util import Pt

    slides = [(f"S{i}", ["раз"]) for i in range(5)]
    base = model.load(make_deck("b", slides, sizes=20))
    path = make_deck("t", slides, sizes=20)
    prs = Presentation(str(path))
    for run in prs.slides[0].placeholders[1].text_frame.paragraphs[0].runs:
        run.font.size = None
    prs.save(str(path))
    theirs = model.load(path)
    assert _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R1") is None


def test_r4_fires_when_the_bullet_column_widens(make_deck, cfg):
    base = model.load(make_deck("b", [("A", ["x"]), ("B", ["y"])], body_width=6.2))
    theirs = model.load(make_deck("t", [("A", ["x"]), ("B", ["y"])], body_width=10.0))
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R4")
    assert found is not None and found.key == "bullets_width" and found.value == "adaptive"


def test_r11_fires_when_the_panel_border_goes_dark(make_deck, cfg):
    """The manager removed the blue outline on every code panel."""
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    def _with_panels(name, color):
        path = make_deck(name, [("A", ["x"]), ("B", ["y"])])
        prs = Presentation(str(path))
        for slide in prs.slides:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1), Inches(1), Inches(2), Inches(1)
            )
            shape.line.color.rgb = RGBColor.from_string(color)
        prs.save(str(path))
        return model.load(path)

    base = _with_panels("b", "2419FF")
    theirs = _with_panels("t", "1A1A1A")
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R11")
    assert found is not None
    assert found.key == "code_border" and found.value == "dark"


def test_r8_regression_on_theme_font_swap(make_deck, cfg):
    """A theme-font swap is an export artefact — reported, never merged."""
    base = model.load(make_deck("b", [("A", ["x"])]))
    loaded = model.load(make_deck("t", [("A", ["x"])]))
    theirs = model.Deck(
        path=loaded.path,
        slides=loaded.slides,
        theme_fonts={"major": "Calibri Light", "minor": "Calibri"},
        master_body_sizes=loaded.master_body_sizes,
    )
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R8")
    assert found is not None and found.kind == "regression" and found.key is None


def test_r10_regression_when_notes_are_lost(make_deck, cfg):
    base_path = make_deck("b", [("A", ["x"])])
    prs = Presentation(str(base_path))
    prs.slides[0].notes_slide.notes_text_frame.text = "заметка"
    prs.save(str(base_path))
    base = model.load(base_path)
    theirs = model.load(make_deck("t", [("A", ["x"])]))
    found = _found(rules.detect(base, theirs, diff.compare(base, theirs), cfg), "R10")
    assert found is not None and found.kind == "regression"


def test_config_loads_thresholds_from_yaml(cfg):
    assert cfg.min_share == 0.8
    assert cfg.tolerances["left"] == 0.4
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_merge/tests/test_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge.rules'`

- [ ] **Step 3: Реализация**

Создать `settings/merge.yml`:

```yaml
# merge.yml — SSoT of the deck merge lane (preza_merge). Spec: docs/preza-merge-lane.md.
merge:
  # A change becomes a profile RULE only when it is systematic: at least this share of the
  # slides that could carry it actually does. Below the threshold it stays a per-slide note.
  min_share: 0.8
  # Rebuilt-with-the-profile vs the fork: how far a box may sit from where the reviewer put
  # it by hand before verification calls it a mismatch (inches).
  tolerances: {left: 0.4, top: 0.4, width: 0.4, height: 0.4}
  # Where reports and proposals land.
  report_dir: docs/reviews/merge
  # SessionStart hook: a fork candidate is a deck-named .pptx carrying one of these markers.
  fork_markers: [" (1)", " (2)", " копия", "-copy", " copy"]
  fork_search_dir: ~/Downloads
  # Profile written by `apply` when the proposal does not name one.
  default_profile: merged
  # Rendering profile every deck starts from.
  base_profile: classic
```

Создать `src/preza_merge/rules.py`:

```python
"""preza_merge.rules — turn a diff into profile keys, with the evidence that justified them.

A rule fires only when the change is SYSTEMATIC (share of eligible slides >= min_share);
anything rarer stays a per-slide note, because writing a one-off into a profile would apply
it to slides the reviewer never touched. Changes that must NOT be carried over (export
artefacts, lost content) are emitted as `regression` findings so "not merged" never reads
as "overlooked".
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .diff import DiffReport
from .model import Deck

# Shape-name prefixes the generator produces. The reviewer's tool renames shapes it creates,
# but keeps the names of shapes it merely moves — which is exactly what this lane inspects.
_CODE_PANEL = "Rounded Rectangle"
_PICTURE = "Picture"
_TABLE = "Table"
_BODY = "Text Placeholder"
# Theme roles / hex values that read as "the dark theme text colour" rather than the accent.
_DARK_BORDERS = {"tx1", "1A1A1A", "000000"}


@dataclass(frozen=True)
class Finding:
    """One conclusion about the fork. ``kind`` ∈ {format, regression}."""

    rule: str
    kind: str
    key: str | None  # profile key for kind=format; None for regressions
    value: object
    share: float
    evidence: str
    slides: list[int] = field(default_factory=list)


@dataclass
class MergeConfig:
    min_share: float
    tolerances: dict
    report_dir: Path
    fork_markers: list[str]
    fork_search_dir: Path
    default_profile: str
    base_profile: str

    @classmethod
    def load(cls, path: str | Path) -> MergeConfig:
        """Load settings/merge.yml. Fail-loud on a missing file or key."""
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"merge settings not found: {p}")
        m = yaml.safe_load(p.read_text(encoding="utf-8"))["merge"]
        return cls(
            min_share=float(m["min_share"]),
            tolerances=m["tolerances"],
            report_dir=Path(m["report_dir"]),
            fork_markers=list(m["fork_markers"]),
            fork_search_dir=Path(m["fork_search_dir"]).expanduser(),
            default_profile=m["default_profile"],
            base_profile=m["base_profile"],
        )


def _shapes_named(deck: Deck, prefix: str):
    """(slide_number, shape) for every shape whose name starts with ``prefix``."""
    for slide in deck.slides:
        for shape in slide.shapes:
            if shape.name.startswith(prefix):
                yield slide.n, shape


def _r1(rep: DiffReport, cfg: MergeConfig) -> Finding | None:
    cleared = sum(s.runs_size_cleared for s in rep.slides)
    if not cleared:
        return None
    eligible = [s for s in rep.slides if s.paras_before]
    hit = [s.n for s in rep.slides if s.runs_size_cleared]
    share = len(hit) / len(eligible) if eligible else 0.0
    if share < cfg.min_share:
        return None
    return Finding(
        "R1",
        "format",
        "body_font",
        "inherit",
        share,
        f"сняты явные размеры у {cleared} прогонов на {len(hit)} слайдах — "
        f"кегль наследуется от мастера",
        hit,
    )


def _bottoms(deck: Deck, prefix: str) -> list[tuple[int, float]]:
    return [(n, sh.bottom) for n, sh in _shapes_named(deck, prefix) if sh.height]


def _r2(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    pairs = _bottoms(theirs, _CODE_PANEL) + _bottoms(theirs, _PICTURE)
    if len(pairs) < 2:
        return None
    values = [b for _, b in pairs]
    median = round(st.median(values), 2)
    hit = [n for n, b in pairs if abs(b - median) <= 0.35]
    share = len(hit) / len(pairs)
    if share < cfg.min_share:
        return None
    base_pairs = _bottoms(base, _CODE_PANEL) + _bottoms(base, _PICTURE)
    if base_pairs and abs(st.median([b for _, b in base_pairs]) - median) < 0.2:
        return None  # nothing moved
    return Finding(
        "R2",
        "format",
        "visual_anchor",
        {"visual_anchor": "bottom", "visual_bottom": median},
        share,
        f"нижняя кромка визуала у {len(hit)}/{len(pairs)} элементов ≈ {median}″ "
        f"(разброс {min(values):.2f}–{max(values):.2f})",
        sorted(hit),
    )


def _r3(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    tops = [(n, sh.top) for n, sh in _shapes_named(theirs, _TABLE)]
    if not tops:
        return None
    values = [t for _, t in tops]
    median = round(st.median(values), 2)
    hit = [n for n, t in tops if abs(t - median) <= 0.15]
    share = len(hit) / len(tops)
    base_tops = [t for _, t in ((n, sh.top) for n, sh in _shapes_named(base, _TABLE))]
    if share < cfg.min_share or (base_tops and abs(st.median(base_tops) - median) < 0.2):
        return None
    return Finding(
        "R3",
        "format",
        "table_top",
        median,
        share,
        f"верх таблиц {st.median(base_tops):.2f}″ → {median}″ на {len(hit)}/{len(tops)} слайдах",
        sorted(hit),
    )


def _r4(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    widened, total = [], 0
    base_by_slide = {n: sh for n, sh in _shapes_named(base, _BODY)}
    for n, shape in _shapes_named(theirs, _BODY):
        before = base_by_slide.get(n)
        if before is None or not before.width:
            continue
        total += 1
        if shape.width - before.width > 0.3:
            widened.append(n)
    if not total:
        return None
    share = len(widened) / total
    if share < cfg.min_share:
        return None
    return Finding(
        "R4",
        "format",
        "bullets_width",
        "adaptive",
        share,
        f"колонка буллетов расширена на {len(widened)}/{total} слайдах",
        sorted(widened),
    )


def _r6(base: Deck, theirs: Deck, rep: DiffReport, cfg: MergeConfig) -> Finding | None:
    eligible, hit = 0, []
    for sb, sd in zip(base.slides, rep.slides):
        empty = [
            sh.name
            for sh in sb.shapes
            if sh.placeholder and sh.paras and not sh.text() and sh.name != sb.shapes_title_name
        ]
        if not empty:
            continue
        eligible += 1
        if set(empty) & set(sd.shapes_removed):
            hit.append(sb.n)
    if not eligible:
        return None
    share = len(hit) / eligible
    if share < cfg.min_share:
        return None
    return Finding(
        "R6",
        "format",
        "drop_empty_placeholders",
        True,
        share,
        f"пустые плейсхолдеры сняты на {len(hit)}/{eligible} слайдах",
        hit,
    )


def _r7(base: Deck, theirs: Deck) -> Finding | None:
    if not base.slides or not theirs.slides:
        return None
    b, t = base.slides[0].title, theirs.slides[0].title
    if b and t and t == b.upper() and t != b:
        return Finding(
            "R7", "format", "title_slide_uppercase", True, 1.0, f"титул: {b!r} → {t!r}", [1]
        )
    return None


def _r11(base: Deck, theirs: Deck, cfg: MergeConfig) -> Finding | None:
    """Code-panel outline (R11).

    Found via the manager's stated rule, not via the geometry diff — see the plan's Global
    Constraints. Only the two unambiguous outcomes are proposed (dark / none); any other
    colour is left to the human rather than guessed into a profile.
    """
    before = {n: sh.line_color for n, sh in _shapes_named(base, _CODE_PANEL)}
    after = {n: sh.line_color for n, sh in _shapes_named(theirs, _CODE_PANEL)}
    common = sorted(set(before) & set(after))
    if not common:
        return None
    changed = [n for n in common if before[n] != after[n]]
    share = len(changed) / len(common)
    if share < cfg.min_share:
        return None
    values = {after[n] for n in changed}
    if values <= _DARK_BORDERS:
        value = "dark"
    elif values == {None}:
        value = "none"
    else:
        return None
    sample = before[changed[0]]
    return Finding(
        "R11",
        "format",
        "code_border",
        value,
        share,
        f"обводка код-панелей {sample} → {sorted(str(v) for v in values)} "
        f"на {len(changed)}/{len(common)} панелях",
        changed,
    )


def _regressions(base: Deck, theirs: Deck, rep: DiffReport) -> list[Finding]:
    out: list[Finding] = []
    if rep.theme_changed:
        out.append(
            Finding(
                "R8",
                "regression",
                None,
                rep.theme_fonts[1],
                1.0,
                f"шрифты темы {rep.theme_fonts[0]} → {rep.theme_fonts[1]} — артефакт экспорта",
                [],
            )
        )
    merged = [s.n for s in rep.slides if s.paras_after < s.paras_before]
    if merged:
        out.append(
            Finding(
                "R9",
                "regression",
                None,
                merged,
                len(merged) / max(1, len(rep.slides)),
                f"склеены абзацы на слайдах {merged} — потеря структуры буллетов",
                merged,
            )
        )
    lost = [s.n for s in rep.slides if s.notes_lost]
    if lost:
        out.append(
            Finding(
                "R10",
                "regression",
                None,
                lost,
                len(lost) / max(1, len(rep.slides)),
                f"потеряны заметки спикера на слайдах {lost}",
                lost,
            )
        )
    return out


def detect(base: Deck, theirs: Deck, rep: DiffReport, cfg: MergeConfig) -> list[Finding]:
    """All findings about the fork: profile rules first, then regressions."""
    found = [
        _r1(rep, cfg),
        _r2(base, theirs, cfg),
        _r3(base, theirs, cfg),
        _r4(base, theirs, cfg),
        _r6(base, theirs, rep, cfg),
        _r7(base, theirs),
        _r11(base, theirs, cfg),
    ]
    return [f for f in found if f is not None] + _regressions(base, theirs, rep)
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add settings/merge.yml src/preza_merge/rules.py src/preza_merge/tests/test_rules.py
git commit -m "feat(preza-merge): детекторы правил и регрессий + settings/merge.yml (#8)"
```

---

### Task 11: Отчёт, предложение и CLI `propose`

**Files:**
- Create: `src/preza_merge/report.py`, `src/preza_merge/cli.py`, `src/preza_merge/__main__.py`, `src/preza_merge/tests/test_report.py`
- Modify: `Justfile` (рецепты `preza-merge-*`)

**Interfaces:**
- Consumes: `rules.Finding`, `rules.MergeConfig` (Task 10), `align.Alignment` (Task 9), `diff.DiffReport` (Task 8)
- Produces: `preza_merge.report.write(out_stem: Path, ctx: ProposalContext) -> tuple[Path, Path]` (пишет `.md` и `.proposal.yml`), `ProposalContext(deck, base_pptx, ours_pptx, theirs_pptx, base_content_rev, profile_name, findings, alignment, diffs)`, `report.load_proposal(path) -> dict`; CLI `python -m preza_merge propose|apply|verify|run`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/test_report.py`:

```python
"""The proposal is the human's decision surface — it must be complete and machine-readable."""

from pathlib import Path

import yaml

from preza_merge import report, rules

_REPO = Path(__file__).resolve().parents[3]


def _ctx(tmp_path):
    findings = [
        rules.Finding("R1", "format", "body_font", "inherit", 1.0, "сняты явные размеры", [1, 2]),
        rules.Finding("R8", "regression", None, {"minor": "Calibri"}, 1.0, "шрифты темы", []),
    ]
    return report.ProposalContext(
        deck="content/x.yml",
        base_pptx=tmp_path / "b.pptx",
        ours_pptx=tmp_path / "o.pptx",
        theirs_pptx=tmp_path / "t.pptx",
        base_content_rev="abc1234",
        profile_name="merged",
        findings=findings,
        alignment=None,
        diffs={},
    )


def test_proposal_carries_a_decision_slot_per_format_rule(tmp_path):
    _, prop = report.write(tmp_path / "case", _ctx(tmp_path))
    data = yaml.safe_load(prop.read_text(encoding="utf-8"))

    rules_block = data["proposal"]["rules"]
    assert rules_block[0]["rule"] == "R1"
    assert rules_block[0]["decision"] is None  # awaits the human
    assert rules_block[0]["key"] == "body_font"
    assert "regressions" in data["proposal"]
    assert data["proposal"]["regressions"][0]["rule"] == "R8"
    assert "decision" not in data["proposal"]["regressions"][0]


def test_markdown_report_states_the_evidence(tmp_path):
    md, _ = report.write(tmp_path / "case", _ctx(tmp_path))
    text = md.read_text(encoding="utf-8")
    assert "R1" in text and "сняты явные размеры" in text
    assert "R8" in text and "шрифты темы" in text


def test_undecided_rules_are_detectable(tmp_path):
    _, prop = report.write(tmp_path / "case", _ctx(tmp_path))
    assert report.undecided(report.load_proposal(prop)) == ["R1"]


def test_accepted_rules_become_profile_keys(tmp_path):
    _, prop = report.write(tmp_path / "case", _ctx(tmp_path))
    data = report.load_proposal(prop)
    data["proposal"]["rules"][0]["decision"] = "accept"
    assert report.accepted_keys(data) == {"body_font": "inherit"}
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_merge/tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge.report'`

- [ ] **Step 3: Реализация**

Создать `src/preza_merge/report.py`:

```python
"""preza_merge.report — the human's decision surface: a markdown story + a YAML proposal.

The markdown explains WHY each rule fired (the evidence); the YAML is what `apply` reads.
Every format rule carries `decision: null` until a human writes accept/reject — apply
refuses to run while any decision is missing, so a rule can never slip in unread.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .rules import Finding


@dataclass
class ProposalContext:
    deck: str
    base_pptx: Path
    ours_pptx: Path
    theirs_pptx: Path
    base_content_rev: str
    profile_name: str
    findings: list[Finding]
    alignment: Any
    diffs: dict


def _rule_row(f: Finding) -> dict:
    return {
        "rule": f.rule,
        "key": f.key,
        "value": f.value,
        "share": round(f.share, 3),
        "evidence": f.evidence,
        "slides": f.slides,
        "decision": None,  # accept | reject — filled in by the human
    }


def _regression_row(f: Finding) -> dict:
    return {"rule": f.rule, "evidence": f.evidence, "slides": f.slides, "value": f.value}


def _md(ctx: ProposalContext) -> str:
    fmt = [f for f in ctx.findings if f.kind == "format"]
    reg = [f for f in ctx.findings if f.kind == "regression"]
    lines = [
        f"# Слияние деки — {ctx.deck}",
        "",
        f"- base: `{ctx.base_pptx.name}` (контент: `{ctx.base_content_rev}`)",
        f"- ours: `{ctx.ours_pptx.name}`",
        f"- theirs: `{ctx.theirs_pptx.name}`",
        f"- профиль: `{ctx.profile_name}`",
        "",
        "## Правила форматирования",
        "",
    ]
    if fmt:
        lines += ["| # | ключ | значение | доля | доказательство |", "|---|---|---|---|---|"]
        lines += [
            f"| {f.rule} | `{f.key}` | `{f.value}` | {f.share:.0%} | {f.evidence} |" for f in fmt
        ]
    else:
        lines.append("Системных правил не найдено.")
    lines += ["", "## Регрессии форка — не переносятся", ""]
    if reg:
        lines += ["| # | что | почему в отчёте |", "|---|---|---|"]
        lines += [
            f"| {f.rule} | {f.evidence} | перенос испортил бы деку |" for f in reg
        ]
    else:
        lines.append("Регрессий не обнаружено.")
    if ctx.alignment is not None:
        rows = ctx.alignment.rows
        lines += [
            "",
            "## Выравнивание слайдов",
            "",
            f"- всего строк: {len(rows)}",
            f"- только у нас: {len(ctx.alignment.by_status('ours-only'))}",
            f"- только у ревьюера: {len(ctx.alignment.by_status('theirs-only'))}",
            f"- неоднозначные заголовки: {ctx.alignment.unaligned or '—'}",
        ]
    lines += [
        "",
        "## Что дальше",
        "",
        "1. Проставить `decision:` (accept | reject) у каждого правила в `*.proposal.yml`.",
        "2. `just preza-merge-apply --proposal <файл>`",
        "3. `just preza-merge-verify --proposal <файл>`",
        "",
        "Спека ленты: [docs/preza-merge-lane.md](../../preza-merge-lane.md)",
        "",
    ]
    return "\n".join(lines)


def write(out_stem: Path, ctx: ProposalContext) -> tuple[Path, Path]:
    """Write ``<stem>.md`` + ``<stem>.proposal.yml``; return both paths."""
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    md_path = out_stem.with_suffix(".md")
    yml_path = out_stem.with_suffix(".proposal.yml")
    md_path.write_text(_md(ctx), encoding="utf-8")
    doc = {
        "proposal": {
            "deck": ctx.deck,
            "base_pptx": str(ctx.base_pptx),
            "ours_pptx": str(ctx.ours_pptx),
            "theirs_pptx": str(ctx.theirs_pptx),
            "base_content_rev": ctx.base_content_rev,
            "profile": ctx.profile_name,
            "rules": [_rule_row(f) for f in ctx.findings if f.kind == "format"],
            "regressions": [_regression_row(f) for f in ctx.findings if f.kind == "regression"],
        }
    }
    yml_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8"
    )
    return md_path, yml_path


def load_proposal(path: str | Path) -> dict:
    """Read a proposal yaml. Fail-loud when it is missing or malformed."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"proposal not found: {p}")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "proposal" not in doc:
        raise ValueError(f"not a merge proposal: {p}")
    return doc


def undecided(doc: dict) -> list[str]:
    """Rules still awaiting a human decision."""
    return [r["rule"] for r in doc["proposal"]["rules"] if r.get("decision") is None]


def accepted_keys(doc: dict) -> dict:
    """Profile keys implied by the accepted rules.

    A rule whose `value` is a mapping contributes ALL of its keys (R2 sets both the anchor
    and the edge); otherwise the rule's own `key` takes its `value`.
    """
    out: dict = {}
    for row in doc["proposal"]["rules"]:
        if row.get("decision") != "accept":
            continue
        value = row["value"]
        if isinstance(value, dict):
            out.update(value)
        else:
            out[row["key"]] = value
    return out
```

Создать `src/preza_merge/cli.py` (команда `propose`; `apply`/`verify` добавят Task 12–13):

```python
"""preza_merge.cli — propose / apply / verify / run. Canonical entry: just preza-merge-*."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from . import align, diff, model, report, rules
from .rules import MergeConfig

_SETTINGS = Path("settings/merge.yml")


def _content_at_rev(rev: str, path: str, dest: Path) -> Path:
    """Materialize `path` as of `rev` into `dest`. Fail-loud — verification depends on it."""
    out = subprocess.run(
        ["git", "show", f"{rev}:{path}"], capture_output=True, check=False
    )
    if out.returncode != 0:
        raise SystemExit(
            f"cannot read {path} at {rev}: {out.stderr.decode('utf-8', 'ignore').strip()}"
        )
    dest.write_bytes(out.stdout)
    return dest


@click.group()
def main() -> None:
    """Merge a reviewer's .pptx fork back into the deck generator."""


@main.command()
@click.option("--deck", required=True, help="content yaml of the deck being merged")
@click.option("--base", "base_pptx", required=True, help="the .pptx that went out for review")
@click.option("--ours", "ours_pptx", required=True, help="our newest built .pptx")
@click.option("--theirs", "theirs_pptx", required=True, help="the reviewer's fork")
@click.option("--base-content-rev", required=True, help="git rev whose content built --base")
@click.option("--profile", default=None, help="profile name to write (default: merge.yml)")
@click.option("--settings", "settings_path", default=str(_SETTINGS), show_default=True)
def propose(deck, base_pptx, ours_pptx, theirs_pptx, base_content_rev, profile, settings_path):
    """Diff the three sides, derive rules, write the report + proposal."""
    cfg = MergeConfig.load(settings_path)
    base = model.load(base_pptx)
    ours = model.load(ours_pptx)
    theirs = model.load(theirs_pptx)

    fork_diff = diff.compare(base, theirs)
    ours_diff = diff.compare(base, ours)
    alignment = align.align3(base, ours, theirs)
    findings = rules.detect(base, theirs, fork_diff, cfg)

    stem_name = f"{Path(ours_pptx).stem}_x_{Path(theirs_pptx).stem}".replace(" ", "_")
    stem = cfg.report_dir / stem_name
    md, prop = report.write(
        stem,
        report.ProposalContext(
            deck=deck,
            base_pptx=Path(base_pptx),
            ours_pptx=Path(ours_pptx),
            theirs_pptx=Path(theirs_pptx),
            base_content_rev=base_content_rev,
            profile_name=profile or cfg.default_profile,
            findings=findings,
            alignment=alignment,
            diffs={"fork": fork_diff.counts, "ours": ours_diff.counts},
        ),
    )
    click.echo(f"отчёт:      {md}")
    click.echo(f"предложение: {prop}")
    click.echo(f"правил: {sum(1 for f in findings if f.kind == 'format')} · "
               f"регрессий: {sum(1 for f in findings if f.kind == 'regression')}")
    if alignment.unaligned:
        click.echo(f"⚠ неоднозначные заголовки: {alignment.unaligned}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Создать `src/preza_merge/__main__.py`:

```python
from .cli import main

main()
```

В `Justfile` добавить блок после рецептов `preza-*`:

```just
# ── слияние версий и форков дек (preza_merge) — docs/preza-merge-lane.md ──
# Разобрать форк ревьюера против своей ветки: отчёт + предложение с решениями человека.
preza-merge-propose *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge propose {{ARGS}}

# Применить решения: профиль в settings/formats.yml, deck.format, сборка патч-версии.
preza-merge-apply *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge apply {{ARGS}}

# Проверить результат: base-контент новым профилем ↔ форк + инвариант мержа.
preza-merge-verify *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge verify {{ARGS}}

# propose → (решения) → apply → verify одной командой.
preza-merge-run *ARGS:
    cd {{_dir}} && PYTHONPATH=src python3 -m preza_merge run {{ARGS}}
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q && PYTHONPATH=src python3 -m preza_merge propose --help`
Expected: PASS; справка команды печатается

- [ ] **Step 5: Коммит**

```bash
git add src/preza_merge/report.py src/preza_merge/cli.py src/preza_merge/__main__.py \
        src/preza_merge/tests/test_report.py Justfile
git commit -m "feat(preza-merge): отчёт, предложение с решениями человека и команда propose (#8)"
```

---

### Task 12: `apply` — профиль, `deck.format`, патч-сборка

**Files:**
- Create: `src/preza_merge/apply.py`, `src/preza_merge/tests/test_apply.py`
- Modify: `src/preza_merge/cli.py` (команда `apply`)

**Interfaces:**
- Consumes: `report.load_proposal/undecided/accepted_keys` (Task 11), `rules.MergeConfig` (Task 10), `pipeline.build_deck(..., patch_of=, descr=)` (Task 2)
- Produces: `preza_merge.apply.write_profile(formats_path: Path, name: str, base_profile: str, keys: dict) -> None`, `apply.set_deck_format(content_path: Path, profile: str) -> bool`, `apply.run(proposal: dict, cfg: MergeConfig, *, settings_yml: Path, formats_path: Path, patch_of: str, descr: str, backend: str = "settings") -> Path`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/test_apply.py`:

```python
"""Applying a proposal: profile written, deck switched, patch built — and refusals."""

from pathlib import Path

import pytest
import yaml

from preza_merge import apply, rules

_REPO = Path(__file__).resolve().parents[3]


def _formats(tmp_path) -> Path:
    src = yaml.safe_load((_REPO / "settings" / "formats.yml").read_text(encoding="utf-8"))
    p = tmp_path / "formats.yml"
    p.write_text(yaml.safe_dump(src, allow_unicode=True), encoding="utf-8")
    return p


def test_profile_inherits_the_base_and_overrides_accepted_keys(tmp_path):
    path = _formats(tmp_path)
    apply.write_profile(path, "merged", "classic", {"body_font": "inherit", "table_top": 2.45})

    data = yaml.safe_load(path.read_text(encoding="utf-8"))["formats"]["merged"]
    assert data["body_font"] == "inherit"
    assert data["table_top"] == 2.45
    assert data["bullets_width_narrow"] == 6.2  # inherited from classic
    assert set(data) == set(yaml.safe_load(path.read_text(encoding="utf-8"))["formats"]["classic"])


def test_existing_profiles_survive_a_rewrite(tmp_path):
    path = _formats(tmp_path)
    apply.write_profile(path, "merged", "classic", {"table_top": 2.45})
    apply.write_profile(path, "other", "classic", {"table_top": 3.0})
    formats = yaml.safe_load(path.read_text(encoding="utf-8"))["formats"]
    assert {"classic", "merged", "other"} <= set(formats)
    assert formats["merged"]["table_top"] == 2.45


def test_deck_format_is_set_surgically(tmp_path):
    content = tmp_path / "deck.yml"
    content.write_text(
        "deck:\n  out_name: X   # keep me\n  naming: increment\n  version_major: 3\n"
        "content:\n- kind: title\n  title: T\n",
        encoding="utf-8",
    )
    assert apply.set_deck_format(content, "merged") is True
    text = content.read_text(encoding="utf-8")
    assert "format: merged" in text
    assert "# keep me" in text  # the surgical edit must not reformat the file
    assert yaml.safe_load(text)["deck"]["format"] == "merged"


def test_deck_format_replaces_an_existing_value(tmp_path):
    content = tmp_path / "deck.yml"
    content.write_text(
        "deck:\n  out_name: X\n  format: classic\ncontent: []\n", encoding="utf-8"
    )
    apply.set_deck_format(content, "merged")
    assert yaml.safe_load(content.read_text(encoding="utf-8"))["deck"]["format"] == "merged"


def test_apply_refuses_while_a_decision_is_missing(tmp_path):
    doc = {
        "proposal": {
            "deck": "content/x.yml",
            "base_pptx": "b.pptx",
            "ours_pptx": "o.pptx",
            "theirs_pptx": "t.pptx",
            "base_content_rev": "abc",
            "profile": "merged",
            "rules": [{"rule": "R1", "key": "body_font", "value": "inherit", "decision": None}],
            "regressions": [],
        }
    }
    cfg = rules.MergeConfig.load(_REPO / "settings" / "merge.yml")
    with pytest.raises(SystemExit, match="R1"):
        apply.run(
            doc,
            cfg,
            settings_yml=_REPO / "content" / "build_deck_v3-settings.yml",
            formats_path=_formats(tmp_path),
            patch_of="3.19",
            descr="x",
        )


def test_graft_backend_is_not_implemented(tmp_path):
    cfg = rules.MergeConfig.load(_REPO / "settings" / "merge.yml")
    with pytest.raises(NotImplementedError, match="graft"):
        apply.run(
            {"proposal": {"rules": [], "regressions": [], "profile": "merged",
                          "deck": "content/x.yml"}},
            cfg,
            settings_yml=_REPO / "content" / "build_deck_v3-settings.yml",
            formats_path=_formats(tmp_path),
            patch_of="3.19",
            descr="x",
            backend="graft",
        )
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `python3 -m pytest src/preza_merge/tests/test_apply.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge.apply'`

- [ ] **Step 3: Реализация**

Создать `src/preza_merge/apply.py`:

```python
"""preza_merge.apply — turn accepted decisions into a profile, a deck switch and a build.

Two writes, both deliberately narrow:
  * settings/formats.yml is REWRITTEN wholesale — it is a generated file with no prose to
    lose, which is exactly why profiles do not live in the comment-rich deck settings;
  * the deck's content yaml gets a SURGICAL one-line edit, because it is hand-authored and
    a yaml round-trip would strip its comments and reflow every block scalar.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .report import accepted_keys, undecided
from .rules import MergeConfig

_HEADER = """# formats.yml — named FORMATTING profiles for preza_gen. Referenced from a deck settings
# yaml via `settings.formats_file`; a deck picks one with `deck.format`.
#
# GENERATED-AND-EDITED: `just preza-merge-apply` rewrites this whole file, so keep prose
# out of it — durable explanation lives in docs/preza-merge-lane.md.
"""


def write_profile(formats_path: Path, name: str, base_profile: str, keys: dict) -> None:
    """Upsert profile ``name`` = ``base_profile`` + ``keys``. Other profiles survive."""
    path = Path(formats_path)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    profiles = doc["formats"]
    if base_profile not in profiles:
        raise KeyError(f"base profile {base_profile!r} not in {path}")
    merged = dict(profiles[base_profile])
    unknown = set(keys) - set(merged)
    if unknown:
        raise KeyError(f"unknown profile keys {sorted(unknown)} — not in {base_profile!r}")
    merged.update(keys)
    profiles[name] = merged
    path.write_text(
        _HEADER + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def set_deck_format(content_path: Path, profile: str) -> bool:
    """Point a deck's content yaml at ``profile``. Returns True when the file changed.

    Surgical on purpose: the content yaml is hand-authored (comments, folded notes), so it
    is edited as TEXT rather than round-tripped through a yaml dump.
    """
    path = Path(content_path)
    text = path.read_text(encoding="utf-8")
    existing = re.search(r"^(\s+)format:\s*\S.*$", text, flags=re.M)
    if existing:
        new = re.sub(r"^(\s+)format:\s*\S.*$", rf"\1format: {profile}", text, count=1, flags=re.M)
    else:
        anchor = re.search(r"^(\s+)out_name:.*$", text, flags=re.M)
        if not anchor:
            raise ValueError(f"cannot locate deck.out_name in {path}")
        indent = anchor.group(1)
        new = text[: anchor.end()] + f"\n{indent}format: {profile}" + text[anchor.end() :]
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def run(
    proposal: dict,
    cfg: MergeConfig,
    *,
    settings_yml: Path,
    formats_path: Path,
    patch_of: str,
    descr: str,
    backend: str = "settings",
) -> Path:
    """Apply a decided proposal and build the patch version. Returns the built .pptx path."""
    if backend == "graft":
        raise NotImplementedError(
            "backend 'graft' (copying slides between .pptx files) is iteration 2 — "
            "see docs/preza-merge-lane.md § Границы"
        )
    if backend != "settings":
        raise ValueError(f"unknown backend: {backend!r}")

    pending = undecided(proposal)
    if pending:
        raise SystemExit(
            f"нерешённые правила: {', '.join(pending)} — проставьте decision: accept|reject"
        )

    p = proposal["proposal"]
    profile = p["profile"]
    keys = accepted_keys(proposal)
    write_profile(Path(formats_path), profile, cfg.base_profile, keys)
    set_deck_format(Path(p["deck"]), profile)

    from preza_gen import pipeline  # deferred: keeps the merge lane importable without a build

    res = pipeline.build_deck(
        settings_yml, p["deck"], pptx=True, html=True, patch_of=patch_of, descr=descr
    )
    if res.out_path is None:
        raise SystemExit("сборка не дала .pptx — смотрите вывод build_deck")
    return res.out_path
```

В `src/preza_merge/cli.py` добавить команду:

```python
@main.command("apply")
@click.option("--proposal", "proposal_path", required=True, help="decided *.proposal.yml")
@click.option("--patch-of", required=True, help="version being patched, e.g. 3.19")
@click.option("--descr", required=True, help="build tag, e.g. alina-fmt")
@click.option("--settings", "settings_path", default=str(_SETTINGS), show_default=True)
@click.option(
    "--deck-settings",
    default="content/build_deck_v3-settings.yml",
    show_default=True,
    help="settings yaml the deck renders with",
)
@click.option("--formats", "formats_path", default="settings/formats.yml", show_default=True)
@click.option("--backend", default="settings", show_default=True, help="settings | graft")
def apply_cmd(proposal_path, patch_of, descr, settings_path, deck_settings, formats_path, backend):
    """Write the profile, switch the deck, build the patch version."""
    from . import apply as apply_mod

    cfg = MergeConfig.load(settings_path)
    doc = report.load_proposal(proposal_path)
    out = apply_mod.run(
        doc,
        cfg,
        settings_yml=Path(deck_settings),
        formats_path=Path(formats_path),
        patch_of=patch_of,
        descr=descr,
        backend=backend,
    )
    click.echo(f"собрано: {out}")
```

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add src/preza_merge/apply.py src/preza_merge/cli.py src/preza_merge/tests/test_apply.py
git commit -m "feat(preza-merge): apply — профиль, переключение деки, патч-сборка; graft явно отложен (#8)"
```

---

### Task 13: `verify` — структурный и инвариантный контроль

**Files:**
- Create: `src/preza_merge/verify.py`, `src/preza_merge/tests/test_verify.py`
- Modify: `src/preza_merge/cli.py` (команды `verify` и `run`)

**Interfaces:**
- Consumes: `model.load` (Task 7), `diff.compare` (Task 8), `rules.MergeConfig` (Task 10), `pipeline.build_deck` (Task 2)
- Produces: `preza_merge.verify.structural(rebuilt: Deck, theirs: Deck, cfg: MergeConfig) -> VerifyResult`, `verify.invariants(ours: Deck, merged: Deck) -> VerifyResult`, `VerifyResult(ok: bool, lines: list[str], mismatches: list[str])`, `verify.contact_sheet(pptx: Path, out_dir: Path) -> Path | None`

- [ ] **Step 1: Написать падающий тест**

Создать `src/preza_merge/tests/test_verify.py`:

```python
"""Verification: residual geometry within tolerance, content invariants exact."""

from pathlib import Path

import pytest

from preza_merge import model, rules, verify

_REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def cfg():
    return rules.MergeConfig.load(_REPO / "settings" / "merge.yml")


def test_small_residuals_pass(make_deck, cfg):
    a = model.load(make_deck("a", [("T", ["раз"])], body_width=6.2))
    b = model.load(make_deck("b", [("T", ["раз"])], body_width=6.4))  # 0.2" < 0.4" tolerance
    res = verify.structural(a, b, cfg)
    assert res.ok


def test_large_residuals_fail_with_a_slide_reference(make_deck, cfg):
    a = model.load(make_deck("a", [("T", ["раз"])], body_width=6.2))
    b = model.load(make_deck("b", [("T", ["раз"])], body_width=11.0))
    res = verify.structural(a, b, cfg)
    assert not res.ok
    assert any("1" in m for m in res.mismatches)


def test_invariants_catch_content_drift(make_deck):
    ours = model.load(make_deck("o", [("T", ["раз", "два"])]))
    merged_same = model.load(make_deck("m", [("T", ["раз", "два"])]))
    merged_drift = model.load(make_deck("d", [("T", ["раз", "ТРИ"])]))

    assert verify.invariants(ours, merged_same).ok
    bad = verify.invariants(ours, merged_drift)
    assert not bad.ok
    assert any("буллет" in m or "текст" in m for m in bad.mismatches)


def test_invariants_catch_a_lost_slide(make_deck):
    ours = model.load(make_deck("o", [("A", ["x"]), ("B", ["y"])]))
    merged = model.load(make_deck("m", [("A", ["x"])]))
    res = verify.invariants(ours, merged)
    assert not res.ok
    assert any("слайд" in m for m in res.mismatches)


def test_invariants_catch_lost_notes_and_links(make_deck):
    from pptx import Presentation

    ours_path = make_deck("o", [("A", ["x"])])
    prs = Presentation(str(ours_path))
    prs.slides[0].notes_slide.notes_text_frame.text = "заметка"
    run = prs.slides[0].placeholders[1].text_frame.paragraphs[0].runs[0]
    run.hyperlink.address = "https://example.com"
    prs.save(str(ours_path))

    ours = model.load(ours_path)
    merged = model.load(make_deck("m", [("A", ["x"])]))
    res = verify.invariants(ours, merged)
    assert not res.ok
    assert any("ссыл" in m for m in res.mismatches)
    assert any("заметк" in m for m in res.mismatches)
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `python3 -m pytest src/preza_merge/tests/test_verify.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'preza_merge.verify'`

- [ ] **Step 3: Реализация**

Создать `src/preza_merge/verify.py`:

```python
"""preza_merge.verify — did the profile actually reproduce the reviewer's deck, and did the
merge keep our content intact?

Two independent questions, deliberately not merged into one score:
  * STRUCTURAL — rebuild the base content with the new profile and compare against the fork.
    A rule approximates hand-placed boxes, so residuals within `merge.tolerances` are
    expected; anything larger is printed per slide and fails.
  * INVARIANT — compare the merged build against OUR newest build. A formatting profile may
    not change what the deck says: slide count, titles, bullet text, notes, hyperlink and
    materials-footer counts must match exactly.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .diff import compare
from .model import Deck
from .rules import MergeConfig

_MATERIALS_MARK = "📚"


@dataclass
class VerifyResult:
    ok: bool
    lines: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)

    def merge(self, other: VerifyResult) -> VerifyResult:
        return VerifyResult(
            ok=self.ok and other.ok,
            lines=self.lines + other.lines,
            mismatches=self.mismatches + other.mismatches,
        )


def structural(rebuilt: Deck, theirs: Deck, cfg: MergeConfig) -> VerifyResult:
    """Rebuilt-with-profile vs the fork: residual geometry must fit the tolerances."""
    rep = compare(rebuilt, theirs)
    res = VerifyResult(ok=True)
    res.lines.append(
        f"слайдов: {rep.slide_count[0]} ↔ {rep.slide_count[1]}; "
        f"расхождений по классам: {dict(rep.counts)}"
    )
    for sd in rep.slides:
        for change in sd.geometry:
            tol = cfg.tolerances.get(change.attr)
            if tol is None:
                continue
            if abs(change.delta) > tol:
                res.ok = False
                res.mismatches.append(
                    f"слайд {sd.n} «{sd.title[:40]}»: {change.shape}.{change.attr} "
                    f"{change.before}″ → {change.after}″ (Δ{change.delta:+.2f}″ > {tol}″)"
                )
    if rep.counts.get("font"):
        res.ok = False
        res.mismatches.append(
            f"размеры шрифта разошлись на {rep.counts['font']} слайдах — правило R1 не отработало"
        )
    return res


def _links(deck: Deck) -> int:
    return sum(len(sh.hyperlinks) for s in deck.slides for sh in s.shapes)


def _materials(deck: Deck) -> int:
    return sum(
        1
        for s in deck.slides
        for sh in s.shapes
        if any(_MATERIALS_MARK in t for t in sh.text())
    )


def _notes(deck: Deck) -> int:
    return sum(1 for s in deck.slides if s.notes.strip())


def invariants(ours: Deck, merged: Deck) -> VerifyResult:
    """A formatting profile must not change what the deck says."""
    res = VerifyResult(ok=True)
    if len(ours.slides) != len(merged.slides):
        res.ok = False
        res.mismatches.append(f"слайдов: {len(ours.slides)} → {len(merged.slides)}")
    for a, b in zip(ours.slides, merged.slides):
        if a.title.upper() != b.title.upper():  # R7 may upcase the title slide
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: заголовок {a.title!r} → {b.title!r}")
        ta = [t for sh in a.shapes for t in sh.text()]
        tb = [t for sh in b.shapes for t in sh.text()]
        if ta != tb:
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: изменился текст буллетов/панелей")
        if a.notes.strip() != b.notes.strip():
            res.ok = False
            res.mismatches.append(f"слайд {a.n}: изменились заметки спикера")
    for label, fn in (("ссылок", _links), ("футеров материалов", _materials), ("заметок", _notes)):
        x, y = fn(ours), fn(merged)
        res.lines.append(f"{label}: {x} ↔ {y}")
        if x != y:
            res.ok = False
            res.mismatches.append(f"{label}: {x} → {y}")
    return res


def contact_sheet(pptx: Path, out_dir: Path) -> Path | None:
    """Render a deck to per-slide PNGs via LibreOffice. Returns the dir, or None if absent."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)],
        check=False,
        capture_output=True,
    )
    pdf = out_dir / f"{pptx.stem}.pdf"
    if not pdf.is_file():
        return None
    subprocess.run(
        ["pdftoppm", "-png", "-r", "70", str(pdf), str(out_dir / pptx.stem)],
        check=False,
        capture_output=True,
    )
    return out_dir
```

В `src/preza_merge/cli.py` добавить команды `verify` и `run`:

```python
@main.command("verify")
@click.option("--proposal", "proposal_path", required=True)
@click.option("--merged", "merged_pptx", required=True, help="the built patch version")
@click.option("--settings", "settings_path", default=str(_SETTINGS), show_default=True)
@click.option(
    "--deck-settings", default="content/build_deck_v3-settings.yml", show_default=True
)
@click.option("--contact-sheet", "want_sheet", is_flag=True, help="also render PNG pages")
def verify_cmd(proposal_path, merged_pptx, settings_path, deck_settings, want_sheet):
    """Rebuild the base content with the profile and check it against the fork."""
    import tempfile

    from preza_gen import pipeline

    from . import verify as verify_mod

    cfg = MergeConfig.load(settings_path)
    doc = report.load_proposal(proposal_path)["proposal"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        base_content = _content_at_rev(doc["base_content_rev"], doc["deck"], tmp_path / "base.yml")
        # The verification build is scratch: redirect out_dir (and drop the ~/Downloads
        # hardlink) so it never lands beside the real versions the publisher scans.
        scratch_settings = _scratch_settings(Path(deck_settings), tmp_path)
        _drop_downloads_dir(base_content)
        res = pipeline.build_deck(scratch_settings, base_content, pptx=True)
        rebuilt = model.load(res.out_path)
        theirs = model.load(doc["theirs_pptx"])
        ours = model.load(doc["ours_pptx"])
        merged = model.load(merged_pptx)

        out = verify_mod.structural(rebuilt, theirs, cfg).merge(
            verify_mod.invariants(ours, merged)
        )
        if want_sheet:
            sheet = verify_mod.contact_sheet(Path(merged_pptx), cfg.report_dir / "contact")
            click.echo(f"contact-sheet: {sheet or 'LibreOffice не найден — пропущено'}")

    for line in out.lines:
        click.echo(line)
    for bad in out.mismatches:
        click.echo(f"✗ {bad}", err=True)
    if not out.ok:
        sys.exit(1)
    click.echo("✓ верификация пройдена")


@main.command()
@click.pass_context
@click.option("--deck", required=True)
@click.option("--base", "base_pptx", required=True)
@click.option("--ours", "ours_pptx", required=True)
@click.option("--theirs", "theirs_pptx", required=True)
@click.option("--base-content-rev", required=True)
@click.option("--profile", default=None)
def run(ctx, deck, base_pptx, ours_pptx, theirs_pptx, base_content_rev, profile):
    """propose, then stop at the decisions — apply/verify are deliberate follow-ups."""
    ctx.invoke(
        propose,
        deck=deck,
        base_pptx=base_pptx,
        ours_pptx=ours_pptx,
        theirs_pptx=theirs_pptx,
        base_content_rev=base_content_rev,
        profile=profile,
        settings_path=str(_SETTINGS),
    )
    click.echo("\nдальше: проставьте decision: в *.proposal.yml → just preza-merge-apply …")
```

И два хелпера рядом с `_content_at_rev` в `cli.py` — без них сборка верификации попала бы в
`data/generated/` и паблишер увидел бы черновик как настоящую версию:

```python
def _scratch_settings(deck_settings: Path, tmp_path: Path) -> Path:
    """Copy a deck settings yaml with out_dir redirected into a scratch dir."""
    doc = yaml.safe_load(deck_settings.read_text(encoding="utf-8"))
    doc["settings"]["out_dir"] = str(tmp_path / "generated")
    out = tmp_path / "settings.yml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return out


def _drop_downloads_dir(content_path: Path) -> None:
    """Blank a scratch content's downloads_dir so the build cannot hardlink into ~/Downloads."""
    doc = yaml.safe_load(content_path.read_text(encoding="utf-8"))
    doc["deck"]["downloads_dir"] = None
    content_path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
```

(добавить `import yaml` в шапку `cli.py`)

- [ ] **Step 4: Прогнать тесты**

Run: `python3 -m pytest src/preza_merge -q && PYTHONPATH=src python3 -m preza_merge verify --help`
Expected: PASS; справка печатается

- [ ] **Step 5: Коммит**

```bash
git add src/preza_merge/verify.py src/preza_merge/cli.py src/preza_merge/tests/test_verify.py
git commit -m "feat(preza-merge): верификация — остатки в допуске и неизменность содержания (#8)"
```

---

### Task 14: Обвязка — хук, агент, скилл

**Files:**
- Create: `scripts/hooks/preza-merge-status.sh`, `.claude/agents/preza-merge-keeper.md`
- Modify: `.claude/settings.json` (регистрация хука)
- Skill: `/create-skill preza-merge` (интерактивно; вручную файлы скилла не писать)

**Interfaces:**
- Consumes: `settings/merge.yml` (Task 10), `data/generated/` + `content/presentations.yml`
- Produces: SessionStart-строки вида `[preza-merge] ⚠ форк-кандидат: <файл> → just preza-merge-propose …`

- [ ] **Step 1: Написать хук**

Создать `scripts/hooks/preza-merge-status.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook: reviewer forks waiting to be merged. Fail-open, no network.
# Two states, never conflated:
#   ⚠ форк-кандидат — a deck-named .pptx with a copy marker in the fork search dir;
#   ⓘ нерешённое предложение — a *.proposal.yml still carrying `decision: null`.
# Spec: docs/preza-merge-lane.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

[ -f settings/merge.yml ] || exit 0
[ -f content/presentations.yml ] || exit 0

python3 - 2>/dev/null <<'EOF' || true
from pathlib import Path

import yaml

merge = yaml.safe_load(Path("settings/merge.yml").read_text(encoding="utf-8"))["merge"]
plan = yaml.safe_load(Path("content/presentations.yml").read_text(encoding="utf-8")) or {}
decks = [e for e in plan.get("presentations", []) if e.get("out_name") and e.get("content")]

search = Path(merge["fork_search_dir"]).expanduser()
markers = merge["fork_markers"]
generated = Path("data/generated")

candidates = []
if search.is_dir():
    for deck in decks:
        name = deck["out_name"]
        for path in search.glob(f"{name}_v*.pptx"):
            if not any(m in path.name for m in markers):
                continue
            newest = max(
                (p.stat().st_mtime for p in generated.glob(f"{name}_v*.pptx")), default=0
            )
            if path.stat().st_mtime > newest - 86400:
                candidates.append((deck["content"], path))

for content, path in candidates[:5]:
    print(f"[preza-merge] ⚠ форк-кандидат: {path.name}")
    print(f"[preza-merge]   just preza-merge-propose --deck {content} --theirs {path!s:.120}")

report_dir = Path(merge["report_dir"])
pending = []
if report_dir.is_dir():
    for prop in report_dir.glob("*.proposal.yml"):
        doc = yaml.safe_load(prop.read_text(encoding="utf-8")) or {}
        rules = (doc.get("proposal") or {}).get("rules") or []
        undecided = [r["rule"] for r in rules if r.get("decision") is None]
        if undecided:
            pending.append((prop, undecided))

for prop, undecided in pending[:5]:
    print(f"[preza-merge] ⓘ нерешённые правила {','.join(undecided)} → {prop}")
EOF
```

- [ ] **Step 2: Проверить хук вручную (fail-open)**

Run:
```bash
chmod +x scripts/hooks/preza-merge-status.sh
bash scripts/hooks/preza-merge-status.sh; echo "exit=$?"
cd /tmp && bash /Users/nk.myg/github/@dataengy/MLInside-course/scripts/hooks/preza-merge-status.sh; echo "exit=$?"
```
Expected: в репозитории — строка про форк-кандидат `MLInside_Введение-в-dbt_v3.15 (1).pptx`; вне репозитория — пустой вывод и `exit=0` (fail-open)

- [ ] **Step 3: Зарегистрировать хук и написать агента**

В `.claude/settings.json` добавить в массив `SessionStart[0].hooks` (после `deck-publish-status.sh`):

```json
    {
      "type": "command",
      "command": "bash scripts/hooks/preza-merge-status.sh",
      "timeout": 10,
      "statusMessage": "Checking reviewer deck forks"
    }
```

Создать `.claude/agents/preza-merge-keeper.md`:

```markdown
---
name: preza-merge-keeper
description: >-
  Owns the "reviewer's .pptx fork → formatting profile → patch version" lane for
  MLInside-course. Use for: a reviewer returned an edited deck, "what did they actually
  change", deriving/validating a formatting profile (settings/formats.yml), running
  `just preza-merge-{propose,apply,verify}`, and diagnosing why a rule did not fire
  (min_share threshold in settings/merge.yml) or why verification exceeded its tolerance.
  Reads docs/preza-merge-lane.md as its spec. For BUILDING decks use the preza-* just
  recipes; for accents/review use preza-accents-keeper; for PUBLISHING use
  `just publish-new` (deck-publish-pipeline.md); for whole-repo commit/push invariants use
  workstation-bootstrapper. Never copies slides between .pptx files — the graft backend is
  deliberately unimplemented (see the spec's «Границы»).
tools: All tools
---

# preza-merge-keeper

Спека ленты: [docs/preza-merge-lane.md](../../docs/preza-merge-lane.md). SSoT настроек:
`settings/merge.yml`; профили: `settings/formats.yml`.

## Инварианты

1. **Правки ревьюера едут в генератор, не в файл.** Мерж, записанный только в `.pptx`,
   умрёт при следующем `just build`. Если правку нельзя выразить правилом — это находка
   для отчёта, а не повод редактировать собранную деку.
2. **`base` обязателен.** Без версии, ушедшей на ревью, правка ревьюера неотличима от
   собственной правки автора. `base_content_rev` — коммит, чей контент дал `base`.
3. **Регрессии называются вслух.** Экспорт через Google Slides ломает шрифты темы, теряет
   заметки и склеивает абзацы. Эти изменения не переносятся, но обязаны попасть в отчёт —
   «не перенесли» не должно читаться как «пропустили».
4. **Решения принимает человек.** `apply` отказывается работать, пока у правила
   `decision: null`.
5. **Профиль `classic` неприкосновенен** — он закрепляет доprofile-поведение рендерера.

## Частые вопросы

- *Правило не сработало.* Доля затронутых слайдов ниже `merge.min_share` (0.8) — правка
  одиночная. Смотреть `per-slide` в отчёте.
- *Верификация упала на геометрии.* Ревьюер подбирал боксы вручную, правило даёт
  приближение. Если Δ систематически больше `merge.tolerances`, правило сформулировано
  неверно — не поднимать допуск, а править правило.
- *Нужно перенести один слайд побайтно.* Это бэкенд `graft`, он не реализован намеренно;
  оценка объёма — в конце спеки.
```

- [ ] **Step 4: Проверить регистрацию хука и создать скилл**

Run:
```bash
python3 -c "import json; d=json.load(open('.claude/settings.json')); print([h['command'] for h in d['hooks']['SessionStart'][0]['hooks']])"
python3 -m pytest -q
```
Expected: в списке присутствует `bash scripts/hooks/preza-merge-status.sh`; тесты зелёные

Затем создать скилл — **только** через слэш-команду, вручную файлы не писать:

```
/create-skill preza-merge — слияние форка ревьюера с веткой автора через профиль форматирования генератора; propose/apply/verify, settings/merge.yml, spec docs/preza-merge-lane.md
```

- [ ] **Step 5: Коммит**

```bash
git add scripts/hooks/preza-merge-status.sh .claude/agents/preza-merge-keeper.md .claude/settings.json
git commit -m "feat(tooling): хук форк-кандидатов, агент preza-merge-keeper, регистрация в SessionStart (#8)"
```

---

### Task 15: Провести слияние кейса и закрыть ленту документами

**Files:**
- Create: `docs/reviews/merge/MLInside_Введение-в-dbt_v3.19_x_MLInside_Введение-в-dbt_v3.15_(1).{md,proposal.yml}` (генерируются)
- Modify: `settings/formats.yml`, `content/preza-dbt-v3-content.yml`, `docs/CHANGELOG.md`, `.claude/CLAUDE-curr-status.md`, `.claude/.PROMPTS-LOG.md` (+ `-ru`), `src/tests/test_content.py`
- Memory: `~/.claude/projects/-Users-nk-myg-github--dataengy-MLInside-course/memory/`

**Interfaces:**
- Consumes: всё предыдущее
- Produces: `data/generated/MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx` + отчёт верификации

- [ ] **Step 1: Разобрать форк**

Run:
```bash
just preza-merge-propose \
  --deck content/preza-dbt-v3-content.yml \
  --base "data/generated/MLInside_Введение-в-dbt_v3.15.pptx" \
  --ours "data/generated/MLInside_Введение-в-dbt_v3.19.pptx" \
  --theirs "/Users/nk.myg/Downloads/MLInside_Введение-в-dbt_v3.15 (1).pptx" \
  --base-content-rev 6752d35 \
  --profile alina-2026-08
```
Expected: отчёт и предложение записаны; правил ≥ 4 (R1, R2, R3, R4; R6 при срабатывании порога), регрессий 3 (R8, R9, R10)

**Сверка с разведкой** (если расходится — детектор врёт, чинить его, а не подгонять):
- R1: сняты явные размеры примерно у 203 прогонов;
- R2: `visual_bottom` ≈ 7.0 (медиана нижних кромок 6.98–7.02);
- R3: `table_top` ≈ 2.45–2.47 на 9 таблицах;
- R4: расширение колонки на 15 из 18 слайдов с код-панелью;
- R11: обводка `2419FF` → `tx1` на 18 из 18 панелей.

Если R11 не сработало — детектор не читает обводку; это ровно тот класс правил, который дифф
пропускает (см. Global Constraints).

- [ ] **Step 2: Проставить решения**

Отредактировать `*.proposal.yml`: `decision: accept` у R1, R2, R3, R4, R6, R11; `decision: reject` у R7 (капс титула — решение вкуса, по умолчанию нет). Проверить:

```bash
python3 -c "
import sys; sys.path.insert(0,'src')
from preza_merge import report
d = report.load_proposal(sys.argv[1])
print('нерешённых:', report.undecided(d))
print('ключи профиля:', report.accepted_keys(d))
" docs/reviews/merge/*.proposal.yml
```
Expected: `нерешённых: []`, ключи включают `body_font: inherit`, `visual_anchor: bottom`, `visual_bottom`, `table_top`, `bullets_width: adaptive`, `code_border: dark`

Дополнительно убедиться, что синей обводки в собранном мерже не осталось:

```bash
python3 -c "
from pptx import Presentation
from pptx.oxml.ns import qn
from collections import Counter
prs = Presentation('data/generated/MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx')
c = Counter()
for s in prs.slides:
    for sh in s.shapes:
        if sh.name.startswith('Rounded'):
            sp = sh._element.find(qn('p:spPr')); ln = sp.find(qn('a:ln'))
            f = ln.find(qn('a:solidFill')) if ln is not None else None
            c[(f[0].get('val') or f[0].get('lastClr')) if (f is not None and len(f)) else 'none'] += 1
print(c)"
```
Expected: `2419FF` отсутствует (после Step 3, когда сборка уже сделана)

- [ ] **Step 3: Применить и собрать**

Run:
```bash
just preza-merge-apply --proposal docs/reviews/merge/*.proposal.yml --patch-of 3.19 --descr alina-fmt
ls -la "data/generated/MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx"
python3 -c "
from pptx import Presentation
p = Presentation('data/generated/MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx')
print('слайдов:', len(p.slides))"
```
Expected: файл существует, 70 слайдов

- [ ] **Step 4: Верифицировать и закрепить тестом**

Run:
```bash
just preza-merge-verify \
  --proposal docs/reviews/merge/*.proposal.yml \
  --merged "data/generated/MLInside_Введение-в-dbt_v3.19.1+alina-fmt.pptx" \
  --contact-sheet
just publish-status
```
Expected: `✓ верификация пройдена`; `publish-status` показывает `3.19.1+alina-fmt` как новейшую версию dbt-деки

Дописать пин в `src/tests/test_content.py`:

```python
def test_dbt_deck_uses_the_merged_format_profile():
    """The dbt deck ships with the reviewer-derived profile (docs/preza-merge-lane.md)."""
    cfg, _ = load()
    assert cfg.format_name == "alina-2026-08"
    assert cfg.fmt.body_font == "inherit"
    assert cfg.fmt.visual_anchor == "bottom"
```

Run: `just check`
Expected: зелено

- [ ] **Step 5: Документы, память, коммит**

Дописать в `docs/CHANGELOG.md` секцию сверху:

```markdown
## 2026-08-26 — Форк ревьюера слит в генератор: профиль форматирования вместо правки файла ([#8](https://github.com/dataengy/MLInside-course/issues/8))

- Разбор `MLInside_Введение-в-dbt_v3.15 (1).pptx` против собранного 3.15: правки системны
  (буллеты → кегль мастера, визуал к нижней кромке 7.0″, таблицы на 2.45″, колонка
  буллетов адаптивная, пустые плейсхолдеры сняты) и потому переехали в **профиль
  генератора** `alina-2026-08`, а не в один `.pptx` — иначе следующий `just build` их бы
  затёр.
- Три регрессии пересохранения через Google Slides (тема Corbel → Calibri, потерянные
  заметки титула, склейка абзацев) в мерж НЕ взяты и названы в отчёте.
- Новая лента `src/preza_merge/` (`propose → решения человека → apply → verify`),
  `settings/merge.yml`, `settings/formats.yml`, хук форк-кандидатов, агент
  `preza-merge-keeper`. Спека: [docs/preza-merge-lane.md](preza-merge-lane.md).
- Нотация версии расширена до `x.y.z[+descr]`; результат — `v3.19.1+alina-fmt` (70 слайдов),
  паблишер видит его как новую версию.
```

Закрыть открытый вопрос в `docs/course-qa.md`: убрать чекбокс «Перенос дизайн-правок менеджера
в генератор» из «## Открытые вопросы» и перенести его в таблицу «Отвеченные» с ответом «правки
перенесены в профиль `alina-2026-08` (`settings/formats.yml`), дека собирается с ними —
`v3.19.1+alina-fmt`; Dagster ждёт скачивания её файла из чата». Проверить счётчик:
`just course-status`.

Обновить `.claude/CLAUDE-curr-status.md` (новая секция сверху: что сделано, что осталось —
включая незакрытый форк Dagster v1.4).
Записать промпты сессии в `.claude/.PROMPTS-LOG.md` и `.PROMPTS-LOG-ru.md`.

Записать память `~/.claude/projects/-Users-nk-myg-github--dataengy-MLInside-course/memory/preza_merge_lane.md`:

```markdown
---
name: preza-merge-lane
description: Лента слияния форков ревьюеров с веткой автора через профиль форматирования генератора
metadata:
  type: project
---

Форк ревьюера (правленый `.pptx`) сливается НЕ в файл, а в генератор: правки выражаются
правилами и пишутся в именованный профиль `settings/formats.yml`, дека выбирает его через
`deck.format`. Мерж, записанный только в `.pptx`, умирает при следующем `just build`.

Команды: `just preza-merge-{propose,apply,verify}`; решения по правилам принимает человек
(`decision:` в `*.proposal.yml`), `apply` отказывается работать, пока есть `null`.
Первый кейс (2026-08-26): форк Алины поверх dbt-деки v3.15 → профиль `alina-2026-08` →
`v3.19.1+alina-fmt`. Регрессии экспорта Google Slides (шрифты темы, заметки, склейка
абзацев) не переносятся, но перечисляются в отчёте.

Спека: `docs/preza-merge-lane.md`. Смежные ленты: [[deck-publish-pipeline]],
[[schedule-gsheet-accents-lane]].
```

и строку в `MEMORY.md`:

```markdown
- [preza_merge lane](preza_merge_lane.md) — форк ревьюера → профиль генератора, не в .pptx; propose/apply/verify
```

Коммит:

```bash
git add docs/reviews/merge settings/formats.yml content/preza-dbt-v3-content.yml \
        docs/CHANGELOG.md .claude/CLAUDE-curr-status.md .claude/.PROMPTS-LOG.md \
        .claude/.PROMPTS-LOG-ru.md src/tests/test_content.py
git commit -m "feat(preza): dbt-дека слита с форком ревьюера → v3.19.1+alina-fmt (#8)"
```

Затем закрыть задачу:

```bash
gh issue close 8 --comment "Лента реализована; dbt-дека слита в v3.19.1+alina-fmt, верификация пройдена. Правила: R1 (кегль мастера), R2 (визуал к 7.0″), R3 (таблицы 2.45″), R4 (адаптивная колонка), R6 (пустые плейсхолдеры), R11 (обводка код-панелей). Закрывает открытый вопрос «Перенос дизайн-правок менеджера в генератор» из #7. Остаётся форк Dagster v1.4 — файл менеджера ещё не скачан из чата."
gh issue comment 7 --body "*Claude:* Открытый вопрос «Перенос дизайн-правок менеджера в генератор» закрыт лентой preza_merge (#8): правки перенесены в профиль \`alina-2026-08\`, dbt-дека пересобрана как v3.19.1+alina-fmt. Форк Dagster v1.4 ещё не скачан из чата — как появится, та же лента."
```

---

## Порядок задач

Task 1 → **Task 3** → Task 2 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10 → Task 11 → Task 12 → Task 13 → Task 14 → Task 15.

Task 3 идёт раньше Task 2, потому что фикстура `Config` в тесте Task 2 использует поля `fmt` / `format_name`, которые вводит Task 3. Задачи 6 и 7–13 независимы от 1–5 и могут выполняться параллельно другим исполнителем, если Task 15 запускается последней.
