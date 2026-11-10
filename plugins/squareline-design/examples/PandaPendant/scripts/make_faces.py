#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cut the 20 expression frames out of the user's design board into FULL-BLEED 360x360 PNGs.

Product requirement: the panda's white fur fills the whole 360x360 screen and merges with the
white shell -- no black background, no head outline, no ears, no dark rim anywhere.

Method (per expression cell)
  1. Crop a square around the face's TRUE symmetry axis (nose / eye mid-point), not the fur bbox
     (the dark ear bases pull the bbox ~8px off-axis).
  2. The head is a wide ellipse (~215 x 184).  Everything outside a slightly shrunk head ellipse
     (black backdrop, dark ear bases, halo) is replaced by FUR WHITE extended radially from the
     fur just inside the boundary.  Only fur-white pixels are sampled, so eye patches, tears,
     hearts, sunglasses... never smear outward.
  3. The outermost ring is blended toward SHELL_WHITE so the screen edge disappears into the shell.

These are DESIGN-TIME PLACEHOLDERS (upscaled ~1.8x from a ~220px board render, fur extension
synthesised).  Production frames must be rendered full-bleed by the 3D pipeline (camera close
enough that fur covers the whole canvas) and exported 256x256 RGB565.

env: PANDA_CROP (source crop side, default 188)   SHELL_WHITE (hex, default #FFFFFF)
     SHELL_BLEND (0..1 lift strength at the rim, default 0.92)   LIFT_START (default 0.45)
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BOARD = os.path.join(PROJ, "concept", "board_face_ui_20.png")
OUT = os.path.join(PROJ, "assets", "images")

SIDE = int(os.environ.get("PANDA_CROP", "188"))
SHELL = tuple(int(os.environ.get("SHELL_WHITE", "#FFFFFF").lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
SHELL_BLEND = float(os.environ.get("SHELL_BLEND", "0.92"))   # lift strength at the rim
LIFT_START = float(os.environ.get("LIFT_START", "0.45"))     # fraction of the half-side where the lift begins

# face symmetry axis per grid cell (board px).  Calibrated from the head's left/right/top/bottom
# edges and the nose: +8px / +5px from the fur-bbox centres the first version used.
COLS = [140, 387, 630, 877, 1122]
ROWS = [208, 457, 708, 959]
HEAD_A, HEAD_B = 104.0, 90.0          # shrunk head ellipse half-axes (board px) = "safe fur"
HEAD_B_TOP = 80.0                      # upper half is tighter: the dark ear bases start there
IDS = ["idle", "happy_wink", "curious", "surprised", "laugh",
       "think_paw", "listen", "speak", "sleepy", "sleep",
       "sad", "confused", "angry", "shy", "confident",
       "cried", "love", "tired", "abnormal", "celebrate"]
EXCLUDED = {"think_paw"}   # shows a paw on the chin; spec forbids hands (§3.1/§6.1)


_BOARD_LUM = None


def head_center(i):
    """Per-cell head centre from its silhouette (lum>48 incl. ear bases): left/right extents on the
    middle rows, top/bottom on the middle columns.  The offset from the nominal grid is clipped so a
    decoration (sweat drop, tears, sparkles) cannot drag the crop away from the face."""
    global _BOARD_LUM
    if _BOARD_LUM is None:
        _BOARD_LUM = np.asarray(Image.open(BOARD).convert("RGB")).astype(int).mean(axis=2)
    r, c = divmod(i, 5)
    cx, cy = COLS[c], ROWS[r]
    win = _BOARD_LUM[cy - 118:cy + 108, cx - 125:cx + 125] > 48
    xx = np.where(win[100:140, :].any(axis=0))[0]
    yy = np.where(win[:, 105:145].any(axis=1))[0]
    dx = (xx.min() + xx.max()) / 2.0 - 125
    dy = (yy.min() + yy.max()) / 2.0 - 118
    return cx + int(round(min(max(dx, -6), -1))), cy + int(round(min(max(dy, -2), 1)))


def crop_cell(i):
    cx, cy = head_center(i)
    h = SIDE // 2
    return Image.open(BOARD).convert("RGB").crop((cx - h, cy - h, cx + h, cy + h))


def fill_outside_head(img):
    """Replace everything outside the head ellipse by radially extended fur white."""
    a = np.asarray(img).astype(float)
    n = a.shape[0]
    c = (n - 1) / 2.0
    yy, xx = np.mgrid[0:n, 0:n]
    dx, dy = xx - c, yy - c
    theta = np.arctan2(dy, dx)
    rr = np.hypot(dx, dy)
    # ellipse radius along each ray
    Bv = np.where(dy < 0, HEAD_B_TOP, HEAD_B)
    rb = (HEAD_A * Bv) / np.sqrt((Bv * np.cos(theta)) ** 2 + (HEAD_A * np.sin(theta)) ** 2)
    lum = a.mean(axis=2)
    fur = (lum > 175) & (a[..., 0] > 200) & (a[..., 2] > 190) & (rr < rb)          # fur-white only
    # colour of the fur just inside the boundary, per angle bin
    NB = 720
    ang = ((theta + np.pi) / (2 * np.pi) * NB).astype(int) % NB
    band = fur & (rr > rb - 14)
    col = np.zeros((NB, 3))
    cnt = np.zeros(NB)
    for k in range(3):
        col[:, k] = np.bincount(ang[band], weights=a[..., k][band], minlength=NB)
    cnt = np.bincount(ang[band], minlength=NB).astype(float)
    ok = cnt > 3
    col[ok] /= cnt[ok][:, None]
    if not ok.any():
        col[:] = (240, 232, 240)
    else:                                   # angles with no clean fur: interpolate circularly
        idx = np.arange(NB)
        for k in range(3):
            col[:, k] = np.interp(idx, np.r_[idx[ok] - NB, idx[ok], idx[ok] + NB],
                                  np.r_[col[ok, k], col[ok, k], col[ok, k]])
    # smooth along the angle (circular gaussian)
    sig = 10
    kern = np.exp(-0.5 * (np.arange(-4 * sig, 4 * sig + 1) / sig) ** 2)
    kern /= kern.sum()
    for k in range(3):
        ext = np.r_[col[-4 * sig:, k], col[:, k], col[:4 * sig, k]]
        col[:, k] = np.convolve(ext, kern, mode="same")[4 * sig:-4 * sig]
    fill = col[ang]                          # (n, n, 3)
    # soft fur-like shading: slightly lighter further out
    fill = fill + (255 - fill) * np.clip((rr - rb) / 140.0, 0, 1)[..., None] * 0.35
    # feathered blend between photo (inside) and fill (outside the ellipse)
    w = np.clip((rr - (rb - 7)) / 9.0, 0, 1)[..., None]
    out = a * (1 - w) + fill * w
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def to_shell(img):
    """Lift the fur continuously from the middle to the rim towards the shell white.

    Only LIGHT pixels are lifted (weight by luminance), so eye patches, nose, mouth and the
    coloured decorations keep their values.  A continuous lift (not a hard ring) is what hides
    the seam between the photographed head and the synthesised fur beyond it, and the 3D
    edge-darkening the render has near the head silhouette.
    """
    a = np.asarray(img).astype(float)
    n = a.shape[0]
    c = (n - 1) / 2.0
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.hypot(xx - c, yy - c) / (n / 2.0)
    t = np.clip((d - LIFT_START) / (1.0 - LIFT_START), 0, 1)
    t = t * t * (3 - 2 * t)                                  # smoothstep 0 -> 1 toward the rim
    lum = a.mean(axis=2)
    light = np.clip((lum - 80.0) / 60.0, 0, 1)               # 0 for dark features, 1 for fur / grey rim
    k = (t * light * SHELL_BLEND)[..., None]
    out = a * (1 - k) + np.array(SHELL, float) * k
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def face(i):
    im = fill_outside_head(crop_cell(i))
    im = im.resize((360, 360), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=2))
    return to_shell(im)


def feathered(img, size, feather=0.14):
    """Soft-edged round version for the small face on the (dark) time/weather page."""
    im = img.resize((size, size), Image.LANCZOS).convert("RGB")
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.sqrt((xx - (size - 1) / 2) ** 2 + (yy - (size - 1) / 2) ** 2) / (size / 2)
    a = np.clip((1.0 - d) / feather, 0, 1)
    return Image.fromarray((np.asarray(im).astype(float) * a[..., None]).astype("uint8"))


def thumb(img, size=60):
    big = img.resize((size * 4, size * 4), Image.LANCZOS)
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    out = Image.composite(big, Image.new("RGB", big.size, (0, 0, 0)), m)
    return out.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new("RGB", (5 * 130, 4 * 130), (30, 30, 36))
    kept, edge = [], []
    for i, name in enumerate(IDS):
        f = face(i)
        sheet.paste(f.resize((120, 120), Image.LANCZOS), ((i % 5) * 130 + 5, (i // 5) * 130 + 5))
        if name in EXCLUDED:
            continue
        fid = "%02d_%s" % (i + 1, name)
        f.save(os.path.join(OUT, "face_%s.png" % fid), optimize=True)
        thumb(f, 60).save(os.path.join(OUT, "thumb_%s.png" % fid), optimize=True)
        if name == "idle":
            feathered(f, 170).save(os.path.join(OUT, "face_mini_idle.png"), optimize=True)
        arr = np.asarray(f).astype(int)
        ring = np.r_[arr[0], arr[-1], arr[:, 0], arr[:, -1]]          # the 4 canvas edges
        edge.append(ring.min(axis=0))
        kept.append(fid)
    # drop the old glow asset: nothing may tint the rim any more
    g = os.path.join(OUT, "fx_glow_cyan.png")
    if os.path.exists(g):
        os.remove(g)
    sheet.save(os.path.join(PROJ, "preview", "faces_contact_sheet.png"))
    em = np.array(edge).min(axis=0)
    print("faces: %d | excluded: %s | darkest canvas-edge pixel over all frames: RGB%s" % (len(kept), sorted(EXCLUDED), tuple(int(v) for v in em)))


if __name__ == "__main__":
    sys.exit(main())
