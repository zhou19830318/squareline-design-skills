# -*- coding: utf-8 -*-
"""scan: detect the elements of a concept image and report them in PANEL pixels.

A model with weak vision (or none) can not measure; a strong one measures slowly and unevenly.  This
gives a numeric first pass -- bounding boxes, colours, kind hints, rough font sizes -- plus an
overlay with numbered boxes so the model only has to NAME each box (icon "heart", text "10:42"),
not locate it.  It is a heuristic: always confirm with the overlay.

  slx.py scan <image> --find-screens            list the screens on a design board of separate screens/devices
                                                (NOT for a dense grid of faces/cards: give --screen the bounds by hand)
  slx.py scan <image> --screen x0 y0 x1 y1 --panel 360 [--shape circle|rect] [--tol 28] [--out dir]
"""
import json
import math
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

try:
    from scipy import ndimage as ndi
except Exception:                      # pragma: no cover - scipy is optional
    ndi = None


def _label(mask):
    if ndi is not None:
        lab, n = ndi.label(mask, structure=np.ones((3, 3)))
        return lab, n
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    n = 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1
        q = deque([(y, x)])
        lab[y, x] = n
        while q:
            cy, cx = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n
                        q.append((ny, nx))
    return lab, n


def _dilate(mask, r):
    if r <= 0:
        return mask
    if ndi is not None:
        return ndi.binary_dilation(mask, structure=np.ones((3, 3)), iterations=r)
    out = mask.copy()
    for _ in range(r):
        p = np.pad(out, 1)
        out = np.zeros_like(out)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                out |= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return out


def _bg_color(arr, mask=None):
    q = (arr // 8).reshape(-1, 3)
    if mask is not None:
        q = q[mask.reshape(-1)]
    keys, counts = np.unique(q, axis=0, return_counts=True)
    return keys[counts.argmax()] * 8 + 4


def _hex(c):
    return "#%02X%02X%02X" % tuple(int(v) for v in c)


def _boxes_from_mask(fgmask, D, min_px, dil=2):
    lab, n = _label(_dilate(fgmask, dil))
    boxes = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero((lab == i) & fgmask)
        if len(xs) >= min_px:
            boxes.append([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1])
    boxes.sort(key=lambda b: (b[0], b[1]))
    merged = True
    while merged:                              # merge the glyphs of one text line
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                ha, hb = a[3] - a[1], b[3] - b[1]
                vo = min(a[3], b[3]) - max(a[1], b[1])
                gap = max(a[0], b[0]) - min(a[2], b[2])
                if vo > 0.6 * min(ha, hb) and gap < 0.8 * min(ha, hb) and max(ha, hb) < 0.2 * D and min(ha, hb) < 0.2 * D:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes


def find_screens(img_path, tol=28):
    arr = np.asarray(Image.open(img_path).convert("RGB")).astype(int)
    H, W, _ = arr.shape
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    bg = _bg_color(border.reshape(1, -1, 3))
    mask = np.abs(arr - bg).max(axis=2) > tol
    lab, n = _label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        w, h = x1 - x0, y1 - y0
        if w * h < 0.04 * W * H:
            continue
        parts = max(1, int(round(w / float(h)))) if w > 1.6 * h else 1       # touching screens merge: split evenly
        for k in range(parts):
            px0 = x0 + k * w // parts
            px1 = x0 + (k + 1) * w // parts
            sub = mask[y0:y1, px0:px1]                      # everything painted in this cell, not one component
            fill = sub.sum() / float(sub.size)
            shape = "circle" if 0.62 <= fill <= 0.86 else ("rect" if fill > 0.9 else "unknown")
            out.append({"bbox": [int(px0), int(y0), int(px1), int(y1)], "shape": shape, "fill": round(float(fill), 3)})
    # drop boxes that sit inside another screen (rings, cards of a bigger screen)
    def inside(a, b):
        ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
        iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
        return ix * iy > 0.8 * (a[2] - a[0]) * (a[3] - a[1])
    out = [o for o in out if not any(p is not o and inside(o["bbox"], p["bbox"]) and
                                     (p["bbox"][2] - p["bbox"][0]) * (p["bbox"][3] - p["bbox"][1]) > (o["bbox"][2] - o["bbox"][0]) * (o["bbox"][3] - o["bbox"][1])
                                     for p in out)]
    out.sort(key=lambda s: (s["bbox"][1] // max(1, H // 8), s["bbox"][0]))
    return {"image_size": [W, H], "board_background": _hex(bg), "screens": out}


def scan(img_path, box, panel, shape="auto", tol=50, min_px=14):
    im = Image.open(img_path).convert("RGB")
    x0, y0, x1, y1 = box
    crop = im.crop((x0, y0, x1, y1))
    arr = np.asarray(crop).astype(int)
    h, w, _ = arr.shape
    D = float(max(w, h))
    scale = panel / D
    yy, xx = np.mgrid[0:h, 0:w]
    inside = np.ones((h, w), bool)
    if shape in ("circle", "auto"):
        r = D / 2.0
        circ = np.hypot(xx - (w - 1) / 2.0, yy - (h - 1) / 2.0) <= r * 0.985
        if shape == "circle" or (arr[~circ].mean() if (~circ).any() else 0) < 0 or True:
            inside = circ if shape == "circle" else inside
    bg = _bg_color(arr, inside)
    fg = (np.abs(arr - bg).max(axis=2) > tol) & inside
    boxes = _boxes_from_mask(fg, D, min_px)
    elems = []
    for b in boxes:
        bx0, by0, bx1, by1 = [int(v) for v in b]
        sub = fg[by0:by1, bx0:bx1]
        bw, bh = bx1 - bx0, by1 - by0
        fill = float(sub.sum()) / (bw * bh)
        px = arr[by0:by1, bx0:bx1][sub]
        col = np.median(px, axis=0) if len(px) else np.array([0, 0, 0])
        ncol = len({tuple(c) for c in (px // 32)}) if len(px) else 0
        if bw > 0.6 * D and bh > 0.6 * D and fill < 0.4:
            kind = "ring/arc"
        elif bw > 0.12 * D and bh > 0.12 * D and fill > 0.88:
            kind = "filled-rect/panel"
        elif bw > 0.1 * D and bh > 0.1 * D and 0.72 <= fill <= 0.86 and 0.85 < bw / float(bh) < 1.18:
            kind = "disc/round-button"
        elif ncol > 40 and bw > 0.25 * D and bh > 0.25 * D:
            kind = "image/photo"
        elif bh < 0.24 * D and bw / float(bh) > 1.25:
            kind = "text-like"
        elif bw < 0.22 * D and bh < 0.22 * D and 0.5 < bw / float(bh) < 2.0:
            kind = "icon-like"
        else:
            kind = "unknown"
        e = {"bbox_image": [bx0 + x0, by0 + y0, bx1 + x0, by1 + y0],
             "rect_panel": [int(round(bx0 * scale)), int(round(by0 * scale)), int(round(bw * scale)), int(round(bh * scale))],
             "center_panel": [round((bx0 + bx1) / 2.0 * scale, 1), round((by0 + by1) / 2.0 * scale, 1)],
             "color": _hex(col), "fill": round(fill, 2), "kind_hint": kind}
        if kind == "text-like":
            e["est_font_px_from_height"] = int(round(bh * scale / 0.72))
        elems.append(e)
    elems.sort(key=lambda e: (e["rect_panel"][1] // 12, e["rect_panel"][0]))
    for i, e in enumerate(elems, 1):
        e["id"] = i
    notes = []
    for e in elems:
        if e["kind_hint"] in ("ring/arc", "filled-rect/panel", "image/photo") and e["rect_panel"][2] > 0.5 * panel and e["rect_panel"][3] > 0.5 * panel:
            notes.append("element #%d is big (%s): text/icons printed ON it (a number over a ring) are merged into it and NOT listed separately. "
                         "Crop that region and run `scan --screen` on it again, or read them from the overlay." % (e["id"], e["kind_hint"]))
    return {"screen_bbox": [x0, y0, x1, y1], "panel": panel, "scale_image_to_panel": round(scale, 4),
            "background": _hex(bg), "tolerance": tol, "elements": elems, "notes": notes}, crop


COL = {"ring/arc": (255, 120, 0), "filled-rect/panel": (0, 200, 255), "disc/round-button": (0, 255, 120), "image/photo": (255, 0, 255),
       "text-like": (255, 255, 0), "icon-like": (255, 80, 160), "unknown": (200, 200, 200)}


def overlay(crop, result, path):
    z = 2
    im = crop.resize((crop.width * z, crop.height * z), Image.LANCZOS).convert("RGB")
    d = ImageDraw.Draw(im)
    x0, y0 = result["screen_bbox"][0], result["screen_bbox"][1]
    for e in result["elements"]:
        bx0, by0, bx1, by1 = [(v - o) * z for v, o in zip(e["bbox_image"], (x0, y0, x0, y0))]
        c = COL.get(e["kind_hint"], (200, 200, 200))
        d.rectangle((bx0, by0, bx1, by1), outline=c, width=2)
        d.rectangle((bx0, by0 - 14, bx0 + 8 + 7 * len(str(e["id"])), by0), fill=c)
        d.text((bx0 + 3, by0 - 13), str(e["id"]), fill=(0, 0, 0))
    im.save(path)
