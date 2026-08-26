#!/usr/bin/env bash
# Stop hook: отправляет в Telegram деки, чья новейшая СОБРАННАЯ версия ещё не ушла.
#
# Почему на конец хода, а не на билд: preza_gen мятит новую minor-версию НА КАЖДЫЙ билд
# (_resolve_naming сканирует data/generated/), поэтому «отправлять на каждую сборку» — это
# спам в курсовой топик. Публикатор берёт только НОВЕЙШУЮ версию деки, промежуточные
# пропускает, а курсор гарантирует «одна версия — одна отправка». Итог: не более одного
# сообщения на деку за ход.
#
# Выключатель: settings/publish.yml → telegram.auto_send: false (без правки кода).
# Отправляется только лег tg: drive/sheet остаются явной командой (их отказы — про квоту
# и права, чинятся человеком). Fail-open: любая проблема — молчаливый exit 0.
# Спека: docs/deck-publish-pipeline.md.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null || exit 0

# Stop-хук не должен рекурсивно будить сам себя.
INPUT="$(cat 2>/dev/null || echo '{}')"
case "$INPUT" in *'"stop_hook_active":true'*) exit 0 ;; esac

[ -f content/presentations.yml ] || exit 0
[ -d data/generated ] || exit 0

# ── что отправлять: те же данные, что у SessionStart-хука, без сети ────────────
PENDING="$(python3 - <<'EOF' 2>/dev/null || true
import json, re, sys
from pathlib import Path

import yaml

cfg = yaml.safe_load(Path("settings/publish.yml").read_text(encoding="utf-8")) or {}
if not (cfg.get("telegram") or {}).get("auto_send", False):
    sys.exit(0)                                   # выключено в настройках

plan = yaml.safe_load(Path("content/presentations.yml").read_text(encoding="utf-8")) or {}
cursor = {}
cur = Path("data/.state/deck-publish-state.json")
if cur.is_file():
    try:
        cursor = json.loads(cur.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        cursor = {}

ver_re = re.compile(r"_v(\d+)\.(\d+)\.pptx$")
out = []
for entry in plan.get("presentations") or []:
    name = entry.get("out_name")
    if not (name and entry.get("content")):
        continue
    built = []
    for path in Path("data/generated").glob(f"{name}_v*.pptx"):
        m = ver_re.search(path.name)
        if m and path.name[: m.start()] == name:
            built.append((int(m.group(1)), int(m.group(2))))
    if not built:
        continue
    newest = "%d.%d" % max(built)
    rec = cursor.get(name) or {}
    tg_ok = (rec.get("tg") or {}).get("status") == "ok"
    if rec.get("version") != newest or not tg_ok:
        out.append(f"{name} v{newest}")
print("\n".join(out))
EOF
)"
[ -n "$PENDING" ] || exit 0

# ── лок: два хода, закончившиеся одновременно, не публикуют одно и то же дважды ─
LOCK="data/.state/.auto-send.lock"
mkdir -p data/.state 2>/dev/null || exit 0
mkdir "$LOCK" 2>/dev/null || exit 0
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

echo "[deck-auto-send] новые версии → Telegram:"
echo "$PENDING" | while IFS= read -r line; do echo "  · $line"; done

if command -v just >/dev/null 2>&1; then
    OUT="$(just publish-new --only tg 2>&1)" || true
else
    OUT="$(PYTHONPATH=src uv run --extra gsheets python -m publisher run --only tg 2>&1)" || true
fi

# из простыни публикатора показываем только исход отправок
echo "$OUT" | grep -E "✓ sent|tg: (ok|error)|ERROR|Traceback" | head -8 || true
exit 0
