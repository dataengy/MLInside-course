#!/usr/bin/env python3
"""edit_slides — правки контент-YAML деки по id слайда, без переформатирования файла.

Зачем не yaml.safe_dump: round-trip нормализует блочные скаляры и кавычки во ВСЁМ файле,
и правка одного слайда приезжает диффом на тысячу строк. Здесь файл режется на текстовые
блоки по строкам ``- kind:``; нетронутые слайды остаются байт-в-байт.

Команды:

    python3 scripts/preza/edit_slides.py CONTENT.yml list
    python3 scripts/preza/edit_slides.py CONTENT.yml extract --id 033-x -o /tmp/block.yml
    python3 scripts/preza/edit_slides.py CONTENT.yml remove  --id 033-x --id 034-y
    python3 scripts/preza/edit_slides.py CONTENT.yml move    --id 045-z --after 044-w
    python3 scripts/preza/edit_slides.py CONTENT.yml insert  --file block.yml --after 008-q

Перенос слайда между деками = extract из источника → remove там же → insert в приёмник
(id при этом обычно меняют: он уникален в пределах деки).

После записи проверяются уникальность id и парсибельность YAML; при провале файл
не перезаписывается. Дальше по пайплайну: .tmp/lint_content_scalars.py → preza-validate →
preza-review → just build.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

MARKER = "- kind:"
SETTINGS = Path(__file__).resolve().parents[2] / "settings" / "config.yml"


def refuse_if_excluded(path: Path) -> None:
    """Запрет правки деки, чей предмет ведёт другой лектор.

    Список — ``deck_generation.editing_excluded`` в ``settings/config.yml``. Читается
    fail-loud: нечитаемые настройки НЕ открывают запрет (иначе битый yaml молча снимал бы
    защиту). Проверка стоит на единственной точке записи, поэтому её нельзя обойти,
    выбрав другую команду; ``list``/``extract`` (чтение) продолжают работать.
    """
    try:
        doc = yaml.safe_load(SETTINGS.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise click.ClickException(f"не читаются настройки {SETTINGS}: {exc}") from exc
    excluded = (doc.get("deck_generation") or {}).get("editing_excluded") or []
    root = SETTINGS.parent.parent
    if any(path.resolve() == (root / str(e)).resolve() for e in excluded):
        raise click.ClickException(
            f"{path} — вне нашей зоны правки: предмет ведёт другой лектор "
            "(settings/config.yml → deck_generation.editing_excluded). "
            "Читать (list/extract) можно; чтобы править — сначала снять деку из списка."
        )


def split_blocks(text: str) -> tuple[str, list[str]]:
    """(шапка до `content:`, список текстовых блоков слайдов)."""
    head, sep, body = text.partition("content:\n")
    if not sep:
        raise click.ClickException("в файле нет ключа `content:` — это не контент-YAML деки")
    blocks, cur = [], []
    for line in body.splitlines(keepends=True):
        if line.startswith(MARKER) and cur:
            blocks.append("".join(cur))
            cur = [line]
        else:
            cur.append(line)
    if cur:
        blocks.append("".join(cur))
    return head + "content:\n", blocks


def _sid(block: str) -> str | None:
    for line in block.splitlines():
        if line.startswith("  id: "):
            return line[6:].strip()
    return None


def _index(blocks: list[str], slide_id: str) -> int:
    ids = [_sid(b) for b in blocks]
    if slide_id not in ids:
        raise click.ClickException(f"слайд {slide_id!r} не найден; см. `list`")
    return ids.index(slide_id)


def _write(path: Path, head: str, blocks: list[str]) -> None:
    """Записать, предварительно проверив право на правку, YAML и уникальность id."""
    refuse_if_excluded(path)
    text = head + "".join(blocks)
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise click.ClickException(f"результат не парсится как YAML, файл не тронут: {exc}")
    ids = [s.get("id") for s in (doc.get("content") or []) if isinstance(s, dict)]
    dupes = sorted({i for i in ids if i and ids.count(i) > 1})
    if dupes:
        raise click.ClickException(f"дублирующиеся id, файл не тронут: {', '.join(dupes)}")
    path.write_text(text, encoding="utf-8")
    click.secho(f"✓ {path}: {len(blocks)} слайд(ов)", fg="green")


@click.group()
@click.argument("content_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
def cli(ctx: click.Context, content_path: Path) -> None:
    """Правки CONTENT_PATH по id слайда с сохранением форматирования."""
    ctx.obj = (content_path, *split_blocks(content_path.read_text(encoding="utf-8")))


@cli.command("list")
@click.pass_obj
def list_slides(obj) -> None:
    """Позиция, kind и id каждого слайда."""
    _, _, blocks = obj
    for pos, block in enumerate(blocks, start=1):
        kind = block.split("\n", 1)[0].removeprefix(MARKER).strip()
        click.echo(f"{pos:>3}  {kind:<8} {_sid(block) or '—'}")


@cli.command()
@click.option("--id", "slide_id", required=True, help="id слайда")
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), help="куда писать (по умолчанию stdout)")
@click.pass_obj
def extract(obj, slide_id: str, out: Path | None) -> None:
    """Выгрузить блок слайда как есть — для переноса в другую деку."""
    _, _, blocks = obj
    block = blocks[_index(blocks, slide_id)]
    if out:
        out.write_text(block, encoding="utf-8")
        click.secho(f"✓ {out}", fg="green")
    else:
        click.echo(block, nl=False)


@cli.command()
@click.option("--id", "slide_ids", required=True, multiple=True, help="id слайда (можно повторять)")
@click.pass_obj
def remove(obj, slide_ids: tuple[str, ...]) -> None:
    """Удалить слайды по id."""
    path, head, blocks = obj
    for slide_id in slide_ids:
        blocks.pop(_index(blocks, slide_id))
    _write(path, head, blocks)


@cli.command()
@click.option("--id", "slide_id", required=True)
@click.option("--after", "after_id")
@click.option("--before", "before_id")
@click.pass_obj
def move(obj, slide_id: str, after_id: str | None, before_id: str | None) -> None:
    """Переставить слайд относительно другого."""
    path, head, blocks = obj
    block = blocks.pop(_index(blocks, slide_id))
    blocks.insert(_anchor(blocks, after_id, before_id), block)
    _write(path, head, blocks)


@cli.command()
@click.option("--file", "block_file", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--after", "after_id")
@click.option("--before", "before_id")
@click.pass_obj
def insert(obj, block_file: Path, after_id: str | None, before_id: str | None) -> None:
    """Вставить слайд(ы) из файла относительно якорного id."""
    path, head, blocks = obj
    incoming = split_blocks("content:\n" + block_file.read_text(encoding="utf-8"))[1]
    at = _anchor(blocks, after_id, before_id)
    blocks[at:at] = incoming
    _write(path, head, blocks)


def _anchor(blocks: list[str], after_id: str | None, before_id: str | None) -> int:
    """Позиция вставки по --after/--before (ровно один из них)."""
    if bool(after_id) == bool(before_id):
        raise click.ClickException("нужен ровно один якорь: --after ID или --before ID")
    return _index(blocks, after_id) + 1 if after_id else _index(blocks, before_id)


if __name__ == "__main__":
    sys.exit(cli())
