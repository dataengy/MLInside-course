"""План блоков записи лекции — ``recording.blocks`` записи плана против порядка слайдов деки.

Правило менеджера курса: при монтаже запись режут на уроки до ``lecture.block_max_min`` минут,
поэтому лекцию заранее делят на смысловые блоки и на записи между ними делают паузу.
План — курируемое поле ``content/presentations.yml → recording.blocks``: список
``{title, from, to}``, где ``from``/``to`` — id слайдов (устойчивы к перестановкам, в отличие
от номеров). Блоки должны покрывать деку целиком, по порядку и без наложений — иначе при
записи «потеряется» кусок или один и тот же слайд попадёт в два урока.

Оценка длительности — ``count × lecture.min_per_slide`` (эвристика; см. docs/course-rules.md).
Структурные дефекты — ошибки; блок длиннее лимита — предупреждение (лимит «примерно»),
``--strict`` делает его ошибкой.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from course.settings import REPO_ROOT, read_yaml, require


@dataclass(frozen=True)
class Block:
    title: str
    from_id: str
    to_id: str
    start: int  # номера слайдов, 1-based, включительно
    end: int

    @property
    def count(self) -> int:
        return self.end - self.start + 1

    def est_min(self, min_per_slide: float) -> float:
        return round(self.count * min_per_slide, 1)


@dataclass
class Plan:
    out_name: str
    content: str
    total_slides: int
    blocks: list[Block] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def est_total_min(self, min_per_slide: float) -> float:
        return round(self.total_slides * min_per_slide, 1)


def slide_ids(content_yml: Path) -> list[str]:
    """id слайдов деки в порядке показа (читаем только, без round-trip)."""
    slides = read_yaml(content_yml).get("content") or []
    return [str(s.get("id") or "") for s in slides]


def build(entry: dict, ids: list[str]) -> Plan:
    """Собрать план из записи ``presentations.yml`` и порядка id слайдов.

    >>> ids = ["a", "b", "c", "d"]
    >>> e = {"out_name": "x", "content": "x.yml",
    ...      "recording": {"blocks": [{"title": "1", "from": "a", "to": "b"},
    ...                               {"title": "2", "from": "c", "to": "d"}]}}
    >>> p = build(e, ids); p.ok, [(b.start, b.end) for b in p.blocks]
    (True, [(1, 2), (3, 4)])
    >>> build({"out_name": "x", "content": "x.yml",
    ...        "recording": {"blocks": [{"title": "1", "from": "a", "to": "b"}]}}, ids).errors
    ['последний блок «1» кончается на слайде 2, а в деке 4 — хвост не покрыт']
    """
    plan = Plan(
        out_name=str(entry.get("out_name") or "?"),
        content=str(entry.get("content") or "?"),
        total_slides=len(ids),
    )
    if not ids or any(not i for i in ids):
        plan.errors.append("у слайдов деки нет id — план блоков не к чему привязать")
        return plan
    if len(set(ids)) != len(ids):
        plan.errors.append(
            "id слайдов не уникальны — сначала почините деку (just preza-slides list)"
        )
        return plan
    raw = ((entry.get("recording") or {}).get("blocks")) or []
    if not raw:
        plan.errors.append("recording.blocks пуст — план блоков записи не задан")
        return plan

    pos = {sid: n for n, sid in enumerate(ids, start=1)}
    expected_start = 1
    for n, b in enumerate(raw, start=1):
        title = str(b.get("title") or f"блок {n}")
        from_id, to_id = str(b.get("from") or ""), str(b.get("to") or "")
        missing = [x for x in (from_id, to_id) if x not in pos]
        if missing:
            plan.errors.append(f"блок «{title}»: нет слайда с id {', '.join(missing)}")
            continue
        start, end = pos[from_id], pos[to_id]
        if start > end:
            plan.errors.append(
                f"блок «{title}»: from ({from_id}, №{start}) позже to ({to_id}, №{end})"
            )
            continue
        if start != expected_start:
            kind = "наложение на предыдущий" if start < expected_start else "пропуск слайдов"
            plan.errors.append(
                f"блок «{title}» начинается с №{start}, ожидался №{expected_start} — {kind}"
            )
        plan.blocks.append(Block(title, from_id, to_id, start, end))
        expected_start = end + 1
    if plan.blocks and not plan.errors and plan.blocks[-1].end != len(ids):
        last = plan.blocks[-1]
        plan.errors.append(
            f"последний блок «{last.title}» кончается на слайде {last.end}, "
            f"а в деке {len(ids)} — хвост не покрыт"
        )
    return plan


def overlong(plan: Plan, rules: dict) -> list[str]:
    """Блоки, чья оценка длиннее ``lecture.block_max_min`` (предупреждения)."""
    limit = float(require(rules, "lecture.block_max_min"))
    mps = float(require(rules, "lecture.min_per_slide"))
    return [
        f"блок {n} «{b.title}»: {b.count} сл. ≈ {b.est_min(mps):g} мин > {limit:g}"
        for n, b in enumerate(plan.blocks, start=1)
        if b.est_min(mps) > limit
    ]


def render(plan: Plan, rules: dict, fmt: str = "text") -> str:
    """Таблица блоков (``text`` для терминала, ``md`` для вставки в docs)."""
    limit = float(require(rules, "lecture.block_max_min"))
    mps = float(require(rules, "lecture.min_per_slide"))
    lo, hi = require(rules, "lecture.duration_min")
    head = (
        f"{plan.out_name} — {plan.total_slides} слайдов ≈ {plan.est_total_min(mps):g} мин "
        f"(лимит блока {limit:g} мин · {mps:g} мин/слайд · ориентир лекции {lo}–{hi} мин)"
    )
    lines = [head]
    if plan.errors:
        lines += [f"  ✗ {e}" for e in plan.errors]
    if fmt == "md":
        lines.append("")
        lines.append("| # | блок | слайды | кол-во | ≈ мин |")
        lines.append("|---|---|---|---|---|")
        for n, b in enumerate(plan.blocks, start=1):
            flag = " ⚠" if b.est_min(mps) > limit else ""
            lines.append(
                f"| {n} | {b.title} | {b.start}–{b.end} | {b.count} | {b.est_min(mps):g}{flag} |"
            )
    else:
        width = max([len(b.title) for b in plan.blocks] + [4])
        lines.append(f"  {'#':>2}  {'блок':<{width}}  {'слайды':>8}  {'кол':>3}  {'≈мин':>5}")
        for n, b in enumerate(plan.blocks, start=1):
            flag = "  ⚠" if b.est_min(mps) > limit else ""
            lines.append(
                f"  {n:>2}  {b.title:<{width}}  {f'{b.start}–{b.end}':>8}  {b.count:>3}  "
                f"{b.est_min(mps):>5g}{flag}"
            )
    warns = overlong(plan, rules)
    if warns:
        lines += [f"  ⚠ {w} — разбейте или договоритесь с монтажёром" for w in warns]
    return "\n".join(lines)


def plans_from(entries: list[dict], root: Path = REPO_ROOT) -> list[Plan]:
    """Планы для всех записей плана с ``recording.blocks`` (деки без плана пропускаются)."""
    out = []
    for e in entries:
        if not e.get("content") or not (e.get("recording") or {}).get("blocks"):
            continue
        content = root / str(e["content"])
        if not content.is_file():
            p = Plan(str(e.get("out_name") or "?"), str(e["content"]), 0)
            p.errors.append(f"контент-файл не найден: {content}")
            out.append(p)
            continue
        out.append(build(e, slide_ids(content)))
    return out
