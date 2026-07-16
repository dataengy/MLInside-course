#!/usr/bin/env python3
"""Build a labeled contact sheet of a source deck's media (source-slide → image → filename).

Helps decide which source image belongs on which generated slide.
Usage: python3 .tmp/contact_sheet.py <source_deck.pptx>  →  .tmp/contact_sheet.png
"""
import os
import re
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

src = sys.argv[1] if len(sys.argv) > 1 else "data/source/NEW_ВШЭ_Семинар9-Практикум-по-dbt.pptx"
out, med = ".tmp/contact_sheet.png", ".tmp/media"
os.makedirs(med, exist_ok=True)
z = zipfile.ZipFile(src)
sn = lambda n: int(re.search(r"slide(\d+)", n).group(1))
items, seen = [], set()
rels = sorted([x for x in z.namelist() if re.match(r"ppt/slides/_rels/slide\d+\.xml\.rels$", x)], key=sn)
for n in rels:
    r = z.read(n).decode("utf-8", "ignore")
    for fn in re.findall(r'Target="\.\./media/([^"]+)"', r):
        if fn in seen or not fn.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        data = z.read(f"ppt/media/{fn}")
        open(f"{med}/{fn}", "wb").write(data)
        if len(data) < 25000:            # skip logos / tiny icons
            continue
        seen.add(fn)
        items.append((sn(n), fn))

cols, tw, th, lab, pad = 5, 340, 240, 22, 10
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad), (245, 245, 247))
dr = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
except Exception:
    font = ImageFont.load_default()
for i, (s, fn) in enumerate(items):
    r, c = divmod(i, cols)
    x, y = pad + c * (tw + pad), pad + r * (th + lab + pad)
    try:
        im = Image.open(f"{med}/{fn}").convert("RGB")
        im.thumbnail((tw, th))
        sheet.paste(im, (x + (tw - im.width) // 2, y + lab + (th - im.height) // 2))
    except Exception:
        pass
    dr.rectangle([x, y, x + tw, y + lab], fill=(36, 25, 255))
    dr.text((x + 4, y + 3), f"s{s} · {fn}", fill=(255, 255, 255), font=font)
sheet.save(out)
print(out, sheet.size)
