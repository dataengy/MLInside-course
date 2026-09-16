"""Прогнать демо 1 ЧЕРЕЗ БРАУЗЕР: те же шаги, что на записи, с кадрами и проверками.

Зачем. `just smoke` проверяет граф без браузера, а на записи зритель смотрит в UI — и
ломается обычно то, чего смоук не видит: не подхватился Reload, не отрисовались метаданные,
проверка висит серой. Этот скрипт проходит сценарий глазами браузера и проверяет, что
видно ИМЕННО ТО, что обещает README.

Двойное назначение:
  · репетиция — увидеть, что увидит зритель, ничего не показывая вживую;
  · кадры для screenshot fallback деки (скилл ui-screenshots-for-decks).

    PORT=3001 just ui                 # весь сценарий, кадры в .ui-shots/
    PORT=3001 just ui --headed        # то же, но видно окно браузера
    PORT=3001 just ui --no-prep       # не готовить состояние, снять как есть

Сервер поднимать заранее в другом окне: `PORT=3001 just dev`.

ТРИ ВЕЩИ, КОТОРЫЕ ЗДЕСЬ НЕ ОЧЕВИДНЫ

1. ДВИЖОК — СИСТЕМНЫЙ CHROME (channel="chrome"), а не хромиум playwright: в кеше
   ms-playwright обычно лежит сборка под другую версию playwright, и launch() падает на
   «Executable doesn't exist at .../chromium_headless_shell-NNNN». Лестница движков —
   скилл browser-automation-setup.

2. ГРАФ СВЁРНУТ В ГРУППЫ. На /asset-groups Dagster 1.13 рисует не три ассета, а два
   бокса групп — `features` (2) и `ml` (1). Имён ассетов в тексте страницы при этом НЕТ,
   и наивная проверка «на странице есть feature_table» проваливается на живом графе.
   Раскрытие задаётся URL-параметром, через запятую:
       /asset-groups/?expanded=global@global:features,global@global:ml
   Через `|` вместо запятой — не работает (молча остаётся свёрнутым).
   На записи это значит: чтобы показать три узла, группы надо РАСКРЫТЬ.

3. ПОДГОТОВКА НЕ ТРОГАЕТ .dagster_home. `just reset` его удаляет, а сервер уже поднят и
   держит в нём SQLite — снос на ходу ломает живой `dg dev`. Поэтому состояние «до демо»
   здесь делается мягко: пересобрать признаки на срез по умолчанию и убрать defs/ml.py.
   История запусков остаётся, и это правильно: проверки смотрят на ГРАФ, а не на /runs.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

from playwright.async_api import Page, async_playwright

DEMO = Path(__file__).resolve().parents[1]  # .../01-quickstart
PROJ = DEMO / "ml-platform"
DEFS_ML = PROJ / "src/ml_platform/defs/ml.py"
ASSETS = ("feature_table", "training_dataset", "trained_model")

# см. пункт 2 в докстринге модуля
GRAPH = "/asset-groups/?expanded=" + urllib.parse.quote(
    "global@global:features,global@global:ml", safe=""
)


class Walkthrough:
    def __init__(self, page: Page, base: str, out: Path, run_steps: bool) -> None:
        self.pg = page
        self.base = base
        self.out = out
        self.run_steps = run_steps
        self.step = 0
        self.problems: list[str] = []

    async def shot(self, name: str) -> None:
        self.step += 1
        await self.pg.screenshot(path=str(self.out / f"{self.step:02d}-{name}.png"))
        print(f"  кадр → {self.step:02d}-{name}.png")

    def sh(self, *cmd: str, cwd: Path) -> None:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if proc.returncode != 0:
            self.problems.append(f"{' '.join(cmd)} упал: {proc.stderr[-400:]}")

    def just(self, *recipe: str) -> None:
        """Шаг, который на записи делают в ТЕРМИНАЛЕ, а не в UI."""
        if not self.run_steps:
            print(f"  (пропущен just {' '.join(recipe)})")
            return
        print(f"  just {' '.join(recipe)}")
        self.sh("just", *recipe, cwd=DEMO)

    async def goto(self, route: str, wait_text: str | None = None) -> None:
        await self.pg.goto(self.base + route, wait_until="networkidle")
        if wait_text:
            try:
                await self.pg.wait_for_selector(f"text={wait_text}", timeout=30_000)
            except Exception:
                self.problems.append(f"{route}: не дождались «{wait_text}»")
        await self.pg.wait_for_timeout(2000)

    async def expect(self, needle: str, where: str) -> None:
        if needle not in await self.pg.inner_text("body"):
            self.problems.append(f"{where}: на странице нет «{needle}»")

    async def expect_absent(self, needle: str, where: str) -> None:
        if needle in await self.pg.inner_text("body"):
            self.problems.append(f"{where}: на странице ЕСТЬ «{needle}», а не должно быть")

    async def click_text(self, label: str, where: str) -> bool:
        try:
            await self.pg.click(f"text={label}", timeout=10_000)
            await self.pg.wait_for_timeout(3000)
            return True
        except Exception:
            self.problems.append(f"{where}: не нашлась кнопка «{label}»")
            return False

    async def wait_all_materialized(self, timeout_s: int = 120) -> None:
        """Ждать, пока на графе у всех трёх ассетов появится «Materialized»."""
        for _ in range(timeout_s // 3):
            await self.pg.reload(wait_until="networkidle")
            await self.pg.wait_for_timeout(1500)
            body = await self.pg.inner_text("body")
            if body.count("Materialized") >= len(ASSETS):
                return
        self.problems.append("не дождались материализации всех трёх ассетов на графе")

    # ── подготовка: см. пункт 3 в докстринге ──────────────────────────────────
    def prepare(self) -> None:
        print("\n── подготовка · состояние «до демо» (без сноса .dagster_home)")
        if not self.run_steps:
            print("  (пропущена)")
            return
        self.sh("uv", "run", "python", "../scripts/make_features.py", cwd=PROJ)
        if DEFS_ML.exists():
            DEFS_ML.unlink()
        print("  признаки на срез по умолчанию, defs/ml.py убран")

    async def run(self) -> None:
        print("\n── шаг 1 · пустой граф: Dagster поднят, ассетов нет")
        await self.goto("/asset-groups")
        await self.click_text("Reload definitions", "шаг 1")
        await self.goto("/asset-groups")
        await self.expect("Empty graph", "шаг 1")
        await self.shot("empty-graph")

        print("\n── шаг 2 · три ассета и проверка появились после Reload")
        self.just("add-assets")
        await self.goto("/asset-groups")
        await self.click_text("Reload definitions", "шаг 2")
        await self.goto(GRAPH, wait_text="feature_table")
        for key in ASSETS:
            await self.expect(key, "шаг 2")
        await self.shot("graph-three-assets")

        print("\n── шаг 3 · Materialize all — жест из UI, как на записи")
        await self.click_text("Materialize all", "шаг 3")
        await self.wait_all_materialized()
        await self.expect("1 / 1 Passed", "шаг 3 (проверка на карточке)")
        await self.shot("graph-materialized")

        print("\n── шаг 4 · карточка trained_model: метаданные модели")
        await self.goto("/assets/trained_model", wait_text="roc_auc")
        await self.expect("0.6049", "шаг 4 (roc_auc)")
        await self.shot("trained-model-metadata")

        print("\n── шаг 5 · training_dataset: проверка net_propuskov зелёная")
        await self.goto("/assets/training_dataset")
        await self.click_text("Checks", "шаг 5")
        await self.expect("net_propuskov", "шаг 5")
        await self.shot("asset-check")

        print("\n── шаг 6 · «пришли новые данные»: ниже — устаревшее")
        self.just("new-data")
        await self.goto(GRAPH, wait_text="feature_table")
        # В UI это слово — «Unsynced», а не «stale»: на карточке и на графе Dagster 1.13
        # пишет Unsynced (N). Проверяем именно «(1)» — ровно ОДИН ассет ниже, а не два:
        # это то расхождение со слайдом, о котором README («stale ставится только
        # ПРЯМОМУ потомку»); trained_model пометки не получает.
        await self.expect("Unsynced (1)", "шаг 6 (устаревший потомок)")
        await self.expect_absent("Unsynced (2)", "шаг 6")
        await self.shot("stale-after-new-data")

        print("\n── шаг 7 · пересчитать всё ниже: модель на новых данных")
        self.just("downstream")
        await self.goto("/assets/trained_model", wait_text="roc_auc")
        await self.expect("0.6225", "шаг 7 (roc_auc на срезе 2018-03-15)")
        await self.shot("fresh-again")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default=os.environ.get("PORT", "3000"))
    ap.add_argument("--out", default=str(DEMO / ".ui-shots"))
    ap.add_argument("--headed", action="store_true", help="показать окно браузера")
    ap.add_argument("--no-prep", action="store_true", help="не готовить состояние и не звать just")
    args = ap.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=not args.headed)
        page = await browser.new_page(viewport={"width": 1680, "height": 1000})
        try:
            await page.goto(base, wait_until="domcontentloaded", timeout=15_000)
        except Exception:
            print(f"UI не отвечает на {base} — поднимите сервер: PORT={args.port} just dev")
            await browser.close()
            return 2

        wt = Walkthrough(page, base, out, run_steps=not args.no_prep)
        wt.prepare()
        await wt.run()
        await browser.close()

    print(f"\nкадры: {out}")
    if wt.problems:
        print("НЕ СОШЛОСЬ:")
        for prob in wt.problems:
            print(f"  · {prob}")
        return 1
    print("UI OK — демо 1 проходит в браузере целиком")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
