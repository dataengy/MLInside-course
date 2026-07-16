"""preza_gen.renderers.html — render a Content model → a self-contained HTML deck.

One <section> per slide; theme colors/fonts as CSS vars; images inlined as data URIs;
speaker notes rendered as a small footer per slide. Print-friendly (page-break per slide).
"""

from __future__ import annotations

import base64
import html as _html
from pathlib import Path

from ..settings import Config, Content
from ..utils import log, parse_runs

_MIME = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "svg": "svg+xml"}


def _esc(s) -> str:
    return _html.escape(str(s))


def _media_dir(cfg: Config) -> Path:
    return cfg.out_dir.parent / "source" / "media"


def _data_uri(path: Path) -> str:
    mime = _MIME.get(path.suffix.lstrip(".").lower(), "png")
    return f"data:image/{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def _bullets(bullets) -> str:
    lis = []
    for item in bullets:
        text, lvl = (item[0], item[1]) if isinstance(item, (list, tuple)) else (item, 0)
        lis.append(f'<li class="l{lvl}">{_esc(text)}</li>')
    return "<ul>" + "".join(lis) + "</ul>"


def _notes(text: str) -> str:
    paras = []
    for para in text.split("\n\n"):
        runs = []
        for seg, b, u, it in parse_runs(para):
            s = _esc(seg)
            if b:
                s = f"<b>{s}</b>"
            if u:
                s = f"<u>{s}</u>"
            if it:
                s = f"<i>{s}</i>"
            runs.append(s)
        paras.append("<p>" + "".join(runs) + "</p>")
    return "".join(paras)


def _materials(materials: list) -> str:
    if not materials:
        return ""
    links = " · ".join(
        f'<a href="{_esc(m["url"])}" target="_blank" rel="noopener">{_esc(m.get("label") or m["url"])}</a>'
        for m in materials
    )
    return f'<div class="materials">📚 Материалы: {links}</div>'


def _table(t: dict) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in t["headers"])
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>" for row in t["rows"]
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _code(code: str, caption: str) -> str:
    cap = f'<div class="codecap">{_esc(caption)}</div>' if caption else ""
    return f'{cap}<pre class="code">{_esc(code.rstrip(chr(10)))}</pre>'


def render(cfg: Config, content: Content) -> Path:
    media = _media_dir(cfg)
    th = cfg.theme
    sections = []
    for spec in content.slides:
        parts = [f"<h1>{_esc(spec.title)}</h1>"] if spec.title else []
        if spec.kind == "title" and spec.subtitle:
            parts.append(f'<p class="subtitle">{_esc(spec.subtitle)}</p>')
        side = ""
        if spec.kind == "table" and spec.table:
            parts.append(_table(spec.table))
        elif spec.kind in ("agenda", "content"):
            body = _bullets(spec.bullets) if spec.bullets else ""
            img_path = media / spec.image if spec.image else None
            if img_path is not None and img_path.is_file():
                parts.append(
                    f'<div class="split"><div class="txt">{body}</div>'
                    f'<div class="img"><img src="{_data_uri(img_path)}"/></div></div>'
                )
                side = " has-side"
            elif spec.code and spec.bullets:
                parts.append(
                    f'<div class="split"><div class="txt">{body}</div>'
                    f'<div class="img">{_code(spec.code, spec.code_caption)}</div></div>'
                )
                side = " has-side"
            elif spec.code:
                parts.append(_code(spec.code, spec.code_caption))
                side = " has-side"
            else:
                parts.append(body)
        if spec.materials:
            parts.append(_materials(spec.materials))
        if spec.notes:
            parts.append(f'<aside class="notes">{_notes(spec.notes)}</aside>')
        sections.append(f'<section class="slide {spec.kind}{side}">{"".join(parts)}</section>')

    css = f"""
    :root{{--accent:#{th.accent};--alt:#{th.alt};--font:'{th.font}',system-ui,-apple-system,sans-serif}}
    *{{box-sizing:border-box}} body{{margin:0;font-family:var(--font);color:#{th.dark};background:#e9e9ee}}
    .slide{{position:relative;width:1280px;min-height:720px;margin:24px auto;background:#fff;padding:52px 64px;box-shadow:0 2px 14px rgba(0,0,0,.15)}}
    .slide h1{{font-size:34px;margin:0 0 22px;border-bottom:3px solid var(--accent);display:inline-block;padding-bottom:6px}}
    .slide.section{{background:#000;color:#fff}} .slide.section h1{{color:#fff;border:none;font-size:46px;margin-top:8%}}
    .slide.title{{display:flex;flex-direction:column;justify-content:center}} .slide.title h1{{font-size:60px;text-transform:uppercase;border:none}} .slide.title .subtitle{{color:var(--accent);font-size:24px}}
    .slide.closing{{display:flex;align-items:center}} .slide.closing h1{{font-size:48px;border:none}}
    ul{{font-size:22px;line-height:1.55;padding-left:26px}} li{{margin:7px 0}} li::marker{{color:var(--accent)}} li.l1{{margin-left:24px;font-size:19px;list-style:circle}}
    .slide:not(.has-side) ul{{font-size:27px;line-height:1.6}} .slide:not(.has-side) li.l1{{font-size:22px}}
    .split{{display:flex;gap:34px;align-items:center}} .split .txt{{flex:1.1}} .split .img{{flex:1;text-align:center}} .split img{{max-width:100%;max-height:520px;object-fit:contain}}
    .code{{background:#0D1117;color:#E6EDF3;font-family:'Consolas','SF Mono',Menlo,monospace;font-size:14px;line-height:1.45;padding:16px 18px;border-radius:8px;border:1px solid var(--accent);overflow:auto;white-space:pre;text-align:left}}
    .codecap{{font-size:14px;font-weight:700;margin:0 0 6px}} .split .img .code{{max-height:540px}}
    table{{border-collapse:collapse;width:100%;font-size:18px}} th{{background:var(--accent);color:#fff;text-align:left;padding:10px}} td{{padding:8px 10px}} tr:nth-child(even) td{{background:var(--alt)}}
    .materials{{position:absolute;right:64px;bottom:22px;font-size:13px;color:#505050;text-align:right;max-width:70%}} .materials a{{color:#5F5F5F}}
    .slide.section .materials,.slide.title .materials,.slide.closing .materials{{color:#bbb}} .slide.section .materials a{{color:#ccc}}
    .notes{{display:block;margin-top:18px;padding-top:12px;border-top:1px dashed #ccc;color:#555;font-size:14px}}
    .notes p{{margin:6px 0}} .notes b{{color:#111}} .notes u{{text-decoration-color:var(--accent)}}
    @media print{{body{{background:#fff}} .slide{{margin:0;box-shadow:none;page-break-after:always}}}}
    """
    doc = (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f"<title>{_esc(cfg.out_name)}</title><style>{css}</style></head><body>"
        + "".join(sections)
        + "</body></html>"
    )
    out = cfg.out_dir / f"{cfg.out_name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    log.success(f"html → {out}")
    return out
