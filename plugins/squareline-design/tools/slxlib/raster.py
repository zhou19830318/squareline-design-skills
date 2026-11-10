# -*- coding: utf-8 -*-
"""Manifest source "raster": cut / resize / mask a region of a bitmap the user supplied (a concept board).

  {"name":"img_face_idle","source":"raster","file":"concept/board.png","crop":[x0,y0,x1,y1],
   "size":[360,360],            # or an int for a square; the PNG is written at exactly this size
   "mask":"circle",             # optional: antialiased circle (outside = bg colour, or transparent with "alpha":true)
   "feather":0.12,              # optional with mask: soft edge, fraction of the radius
   "bg":"#000000", "alpha":false, "sharpen":true,
   "provenance":"user concept art (user-provided, user confirmed it may be used)"}   <- REQUIRED

Default policy of the pipeline is to REDRAW assets; cropping from the concept is allowed only for art the
user supplied and wants reused, and `provenance` makes that decision visible.
"""
import os

from PIL import Image, ImageDraw, ImageFilter


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def render(entry, proj):
    src = entry["file"]
    path = src if os.path.isabs(src) else os.path.join(proj, src)
    if not os.path.exists(path):
        raise FileNotFoundError("raster source not found: %s" % path)
    im = Image.open(path).convert("RGBA")
    if entry.get("crop"):
        im = im.crop(tuple(int(v) for v in entry["crop"]))
    size = entry["size"]
    w, h = (size, size) if isinstance(size, int) else (int(size[0]), int(size[1]))
    im = im.resize((w, h), Image.LANCZOS)
    if entry.get("sharpen"):
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=2))
    if entry.get("mask") == "circle":
        k = 4
        m = Image.new("L", (w * k, h * k), 0)
        ImageDraw.Draw(m).ellipse((0, 0, w * k - 1, h * k - 1), fill=255)
        m = m.resize((w, h), Image.LANCZOS)
        f = float(entry.get("feather", 0) or 0)
        if f > 0:
            import numpy as np
            yy, xx = np.mgrid[0:h, 0:w]
            d = np.hypot(xx - (w - 1) / 2.0, yy - (h - 1) / 2.0) / (min(w, h) / 2.0)
            m = Image.fromarray((np.clip((1.0 - d) / f, 0, 1) * 255).astype("uint8"))
        if entry.get("alpha"):
            im.putalpha(m)
        else:
            bg = Image.new("RGBA", (w, h), _hex(entry.get("bg", "#000000")) + (255,))
            im = Image.composite(im, bg, m)
    out = os.path.join(proj, "assets", "images", entry["name"] + ".png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    (im if entry.get("alpha") else im.convert("RGB")).save(out, optimize=True)
    return out, (w, h)
