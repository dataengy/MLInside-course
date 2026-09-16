"""Восстановить хардлинки между демо блока demo/02-dagster-simple.

Git хардлинков не хранит: после клона общие файлы (сырьё jaffle shop, scripts/status.py)
становятся обычными отдельными копиями. Работать всё продолжает, но правка в одной папке
перестаёт доезжать до другой — и демо тихо расходятся.

    python3 scripts/demo_files_link.py            # связать, что разошлось
    python3 scripts/demo_files_link.py --check    # только проверить, ничего не менять

БЕЗОПАСНОСТЬ. Связывание ПЕРЕТИРАЕТ копию файлом владельца, поэтому расходящиеся по
содержимому файлы не связываются никогда: такой случай — расхождение, которое надо
разобрать руками, а не замазать. Реестр — demo/02-dagster-simple/files.yml.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "demo" / "02-dagster-simple"
REGISTRY = BLOCK / "files.yml"

# Системный python3 в этом репозитории БЕЗ pyyaml — на этом уже стояли мёртвыми пять хуков.
# Поэтому при нехватке pyyaml перезапускаемся тем интерпретатором, у которого он есть:
# окружения демо ставят dbt, а dbt тянет pyyaml.
_INTERPRETERS = (
    ROOT / ".venv/bin/python",
    BLOCK / "02-dagster-dbt/ml-platform/.venv/bin/python",
    BLOCK / "01-quickstart/ml-platform/.venv/bin/python",
)


def _reexec_with_yaml() -> None:
    """Один раз перезапуститься интерпретатором, у которого есть pyyaml."""
    if os.environ.get("_DEMO_FILES_LINK_REEXEC"):
        return
    for candidate in _INTERPRETERS:
        if not candidate.is_file() or Path(sys.executable).resolve() == candidate.resolve():
            continue
        probe = os.spawnv(os.P_WAIT, str(candidate), [str(candidate), "-c", "import yaml"])
        if probe == 0:
            os.environ["_DEMO_FILES_LINK_REEXEC"] = "1"
            os.execv(str(candidate), [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="только проверить")
    args = parser.parse_args()

    try:
        import yaml
    except ModuleNotFoundError:
        _reexec_with_yaml()  # не вернётся, если нашёлся подходящий интерпретатор
        print(
            "нужен pyyaml, и ни одно окружение демо его не даёт — сначала "
            "`cd demo/02-dagster-simple/02-dagster-dbt && just setup`"
        )
        return 2

    if not REGISTRY.is_file():
        print(f"нет реестра {REGISTRY.relative_to(ROOT)}")
        return 1

    shared = yaml.safe_load(REGISTRY.read_text())["shared"]
    linked = relinked = 0
    problems: list[str] = []

    for name, entry in shared.items():
        owner = BLOCK / entry["owner"]
        if not owner.is_file():
            problems.append(f"{name}: нет владельца {entry['owner']}")
            continue
        owner_digest = sha256(owner)
        if owner_digest != entry["sha256"]:
            problems.append(
                f"{name}: владелец изменился, а files.yml не обновлён "
                f"({owner_digest[:12]} ≠ {entry['sha256'][:12]})"
            )
            continue
        for rel in entry["copies"]:
            copy = BLOCK / rel
            if copy == owner:
                continue
            if not copy.is_file():
                problems.append(f"{name}: нет копии {rel}")
                continue
            if os.stat(copy).st_ino == os.stat(owner).st_ino:
                linked += 1
                continue
            if sha256(copy) != owner_digest:
                problems.append(
                    f"{name}: {rel} РАЗОШЁЛСЯ с владельцем по содержимому — "
                    "связать нельзя, разобрать руками"
                )
                continue
            if args.check:
                problems.append(f"{name}: {rel} — отдельный файл (нужен just demo-files-link)")
                continue
            copy.unlink()
            os.link(owner, copy)
            relinked += 1

    for problem in problems:
        print(f"  · {problem}")
    verb = "проверено" if args.check else "готово"
    print(f"{verb}: уже связано {linked}, восстановлено {relinked}, проблем {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
