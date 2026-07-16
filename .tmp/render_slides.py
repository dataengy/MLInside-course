#!/usr/bin/env python3
"""Reorder chosen 1-based slides to the front of a copy and qlmanage-render each to PNG (visual QA).

qlmanage only thumbnails slide 1, so we move each requested slide to the front of a throwaway copy.
Usage: python3 .tmp/render_slides.py <deck.pptx> 4 32 33
"""
import os
import subprocess
import sys

from pptx import Presentation

path = sys.argv[1]
nums = [int(x) for x in sys.argv[2:]] or [1]
out = ".tmp/render"
os.makedirs(out, exist_ok=True)
for n in nums:
    p = Presentation(path)
    lst = p.slides._sldIdLst
    ids = list(lst)
    lst.remove(ids[n - 1])
    lst.insert(0, ids[n - 1])
    f = f"{out}/slide{n:02}.pptx"
    p.save(f)
    subprocess.run(["qlmanage", "-t", "-s", "1500", "-o", out, f],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{out}/slide{n:02}.pptx.png")
