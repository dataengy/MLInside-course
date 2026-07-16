#!/usr/bin/env python3
"""Per-slide text + URLs/materials from a source deck (finds "Доп материалы" / hyperlink blocks).

Usage: python3 .tmp/extract_source.py <source_deck.pptx>
"""
import re
import sys
import zipfile

src = sys.argv[1] if len(sys.argv) > 1 else "data/source/NEW_ВШЭ_Семинар9-Практикум-по-dbt.pptx"
z = zipfile.ZipFile(src)
sn = lambda n: int(re.search(r"slide(\d+)", n).group(1))
for n in sorted([x for x in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", x)], key=sn):
    i = sn(n)
    xml = z.read(n).decode("utf-8", "ignore")
    txt = " ".join(re.findall(r"<a:t>([^<]*)</a:t>", xml))
    rels = f"ppt/slides/_rels/slide{i}.xml.rels"
    urls = []
    if rels in z.namelist():
        urls += re.findall(r'Target="(https?://[^"]+)"', z.read(rels).decode("utf-8", "ignore"))
    urls += re.findall(r"https?://[^\s\"<]+", txt)
    urls = sorted(set(u.rstrip(".,") for u in urls))
    if re.search(r"материал", txt, re.I) or urls:
        tag = "MAT" if re.search(r"материал", txt, re.I) else "url"
        print(f"[s{i:>2}] {tag}  {txt[:90]}")
        for u in urls[:5]:
            print(f"        {u}")
