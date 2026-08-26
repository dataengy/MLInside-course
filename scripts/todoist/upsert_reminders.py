#!/usr/bin/env python3
"""Мутирующий вход ленты напоминаний: settings/reminders.yml → задачи Todoist.

Живёт в scripts/ (а не в .tmp/), потому что ПИШЕТ во внешний сервис — конвенция репо:
.tmp/ только читает и рендерит. Вся проверяемая логика — в ``src/course/reminders.py``
(план/diff, ключи, рендер); здесь только HTTP-клиент и CLI.

    just course-reminders            # план, без записи
    just course-reminders-apply      # применить
    just course-reminders --list     # что сейчас в проектах ленты

Токен: ``TODOIST_API_TOKEN`` из окружения, иначе из ``~/.ai/.env.secrets``.
Spec: docs/course-rules.md#напоминания.
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from course import reminders as rem  # noqa: E402

API = "https://api.todoist.com/api/v1"
SECRETS = Path("~/.ai/.env.secrets").expanduser()


def token() -> str:
    tok = os.environ.get("TODOIST_API_TOKEN")
    if not tok and SECRETS.is_file():
        tok = subprocess.run(
            ["bash", "-c", f"set -a; . '{SECRETS}'; printf %s \"$TODOIST_API_TOKEN\""],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    if not tok:
        sys.exit(f"TODOIST_API_TOKEN не задан (env или {SECRETS})")
    return tok


def ssl_ctx() -> ssl.SSLContext:
    """CA-бандл: certifi, если стоит; сборки python.org идут без него."""
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
        if not ctx.get_ca_certs():
            sys.stderr.write(
                "warning: нет CA-бандла (pip install certifi) — TLS-проверка выключена\n"
            )
            ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        return ctx


class Client:
    def __init__(self) -> None:
        self.token, self.ctx = token(), ssl_ctx()

    def call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            API + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            sys.exit(
                f"{method} {path} → HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"
            )

    def tasks(self, project_id: str) -> list[dict]:
        out, cursor = [], None
        while True:
            d = self.call(
                "GET",
                f"/tasks?project_id={project_id}&limit=200"
                + (f"&cursor={cursor}" if cursor else ""),
            )
            out += d.get("results", d) if isinstance(d, dict) else d
            cursor = d.get("next_cursor") if isinstance(d, dict) else None
            if not cursor:
                return out


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    want = rem.load()
    c = Client()
    existing: list[dict] = []
    for pid in sorted({r.project_id for r in want}):
        existing += c.tasks(pid)
    if "--list" in argv:
        for t in sorted(existing, key=lambda t: ((t.get("due") or {}).get("date") or "9999")):
            due = ((t.get("due") or {}).get("date") or "—")[:10]
            print(f"  {due}  p{t.get('priority')}  [{rem.key_of(t) or '—'}]  {t['content'][:60]}")
        return 0
    changes = rem.plan(want, existing)
    print(rem.render(changes, apply))
    if not apply:
        return 0
    for ch in changes:
        if ch.kind == "create":
            c.call("POST", "/tasks", ch.fields)
        elif ch.kind == "update":
            c.call("POST", f"/tasks/{ch.task_id}", ch.fields)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
