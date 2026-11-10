#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""layout.py — small composable helpers for authoring screen specs.

Why this exists
---------------
Writing a spec by hand means computing every `rect: [x, y, w, h]` yourself.  The
repetitive, error-prone parts are always the same three: a grid of equal tiles,
a vertical stack of "card rows", and an icon-next-to-text pair.  Doing that
arithmetic inline in JSON is where off-by-one and drifted-gutter bugs come from
(two cards 2px apart, a grid whose last column overflows the panel).

These helpers return *plain spec fragments* — the same dicts you would have
typed — so they drop straight into `children[]`.

Design rules
------------
* **Pure functions, no state.**  Take geometry in, return dicts out.  Nothing
  reads the filesystem and nothing mutates its arguments.
* **Screen-absolute rects.**  The spec's `rect` is screen-absolute with a
  top-left origin, so every helper computes absolute coordinates and accepts an
  explicit `origin=(x, y)`.  This matches `rect_of()` in build_from_spec.py.
* **Never invent heights for text.**  `label()` requires an explicit `height`,
  or you may pass `font_size` to get the safe `ceil(size * SAFE_RATIO)` value
  (see tools/LABEL_SIZING.md for why that ratio is needed).
* **Fail loudly at author time.**  `grid()` raises if the tiles cannot fit the
  given box, rather than silently emitting negative widths.

Usage
-----
    from layout import grid, stack, card_row, icon_text, label, panel

    # 3 columns x 2 rows filling a 360x220 region starting at (20, 60)
    tiles = grid(box=(20, 60, 360, 220), cols=3, rows=2,
                 gap_x=12, gap_y=12, factory=lambda x, y, w, h: panel(
                     name="t%s" % _n, rect=[x, y, w, h], radius=14))

    # a column of cards sharing a left/right margin
    rows = stack(origin=(24, 70), width=272, heights=[96, 96],
                 gap=16, factory=lambda x, y, w, h: panel(...))

    # icon + text on one line, text left-aligned after the icon
    pair = icon_text(icon={"type": "IMAGE", "name": "ic", "asset": "assets/img_wifi.png"},
                     text={"text": "已连接", "font": "Body16", "color": "WHITE"},
                     rect=[40, 88, 240, 24], icon_size=20, gap=10)

Run the self-test:  python tools/layout.py
"""

import math

# `line_height` is max(ascent)+max(descent) over the glyphs a font actually
# contains, so it is always > size and varies per project (measured 1.19-1.31).
# 1.35 is the conservative bound; see tools/LABEL_SIZING.md.
SAFE_RATIO = 1.35


def safe_text_height(font_size, lines=1):
    """Smallest height that will not clip CJK text at `font_size`."""
    return int(math.ceil(font_size * SAFE_RATIO)) * max(1, int(lines))


# ------------------------------------------------------------------ boxes ---
def grid(box, cols, rows, gap_x=0, gap_y=0, factory=None):
    """Tile `box` into cols x rows equal cells and call `factory(x, y, w, h)`.

    `box` is (x, y, w, h) screen-absolute.  Cell size is derived from the box
    minus the total gaps, so a `gap_x` of 12 with 3 columns removes exactly 24px
    from the usable width — the classic drift bug this replaces is computing the
    cell width first and then discovering the gaps no longer fit.

    Raises ValueError when the gaps alone consume the box (which would otherwise
    emit zero or negative cell sizes and produce an unopenable project).
    """
    x, y, w, h = box
    cols, rows = int(cols), int(rows)
    if cols < 1 or rows < 1:
        raise ValueError("grid: cols/rows must be >= 1, got %d x %d" % (cols, rows))
    if factory is None:
        raise ValueError("grid: factory is required")
    total_gx = gap_x * (cols - 1)
    total_gy = gap_y * (rows - 1)
    if total_gx >= w:
        raise ValueError("grid: gap_x %d x %d columns leaves no room in width %d"
                         % (gap_x, cols, w))
    if total_gy >= h:
        raise ValueError("grid: gap_y %d x %d rows leaves no room in height %d"
                         % (gap_y, rows, h))
    cw = (w - total_gx) // cols
    ch = (h - total_gy) // rows
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append(factory(x + c * (cw + gap_x), y + r * (ch + gap_y), cw, ch))
    return out


def stack(origin, width, heights, gap=0, factory=None, align="LEFT"):
    """Vertically stack items of the given heights under a shared origin.

    `heights` is a list of ints (one per item).  `align` LEFT/CENTER/RIGHT only
    shifts the x origin for a narrower item; pass per-item widths via
    `widths` if you need ragged rows — the common case is a uniform column, so
    that is the default.
    """
    x, y = origin
    if factory is None:
        raise ValueError("stack: factory is required")
    out = []
    cy = y
    for i, hh in enumerate(heights):
        out.append(factory(x, cy, width, hh))
        cy += hh + gap
    return out


def row(origin, height, widths, gap=0, factory=None):
    """Horizontally place items of the given widths at a shared origin."""
    x, y = origin
    if factory is None:
        raise ValueError("row: factory is required")
    out = []
    cx = x
    for ww in widths:
        out.append(factory(cx, y, ww, height))
        cx += ww + gap
    return out


def center_in(box, w, h):
    """Top-left x,y that centres a w x h item inside `box` (x, y, w, h)."""
    bx, by, bw, bh = box
    return (bx + (bw - w) // 2, by + (bh - h) // 2)


# --------------------------------------------------------------- widgets ----
def panel(name, rect, bg=None, radius=0, children=None, events=None,
          hidden=False, clickable=None):
    """A PANEL/CONTAINER child.  `clickable` is only written when given."""
    d = {"type": "PANEL", "name": name, "rect": list(rect)}
    if bg is not None:
        d["bg"] = bg
    if radius:
        d["radius"] = radius
    if children:
        d["children"] = list(children)
    if events:
        d["events"] = list(events)
    if hidden:
        d["hidden"] = True
    if clickable is not None:
        d["clickable"] = bool(clickable)
    return d


def label(name, rect, text, font, color="WHITE", align="CENTER", events=None,
          hidden=False):
    """A LABEL child.  `rect` may be [x, y, w, h] or [x, y, w] + font_size via
    `label_sized()` when you do not want to hand-compute the height."""
    d = {"type": "LABEL", "name": name, "rect": list(rect), "text": text,
         "font": font, "color": color, "align": align}
    if events:
        d["events"] = list(events)
    if hidden:
        d["hidden"] = True
    return d


def label_sized(name, xy, width, text, font_size, font, color="WHITE",
                align="CENTER", lines=1, **kw):
    """LABEL whose height is derived from the font size, not guessed.

    Bottoms the height on `ceil(font_size * 1.35) * lines` so the spec-time
    mistake "I set height = font size and the CJK got clipped" cannot happen.
    """
    h = safe_text_height(font_size, lines)
    return label(name, [xy[0], xy[1], width, h], text, font, color, align, **kw)


def image(name, rect, asset, rotation=None):
    """An IMAGE child.

    `asset` is the reference the PROJECT records, i.e. a flat
    `assets/img_x.png` — NOT `assets/images/img_x.png`.  The source pack is
    selected separately by the spec's `assets_subdir`; it never appears in the
    emitted path.  (Engineers have tripped on this; see the note in
    build_from_spec.py's IMAGE help.)
    """
    d = {"type": "IMAGE", "name": name, "rect": list(rect), "asset": asset}
    if rotation:
        d["rotation"] = rotation
    return d


def arc(name, rect, value, max_value=100, indicator="WHITE", track="TRACK",
        width=12, angles=None):
    """An ARC child (the ring gauge)."""
    d = {"type": "ARC", "name": name, "rect": list(rect), "value": value,
         "max": max_value, "indicator": indicator, "track": track,
         "width": width}
    if angles:
        d["angles"] = list(angles)
    return d


def icon_text(icon, text, rect, icon_size=20, gap=10, icon_first=True,
              icon_valign="CENTER"):
    """Icon + text on one line, returning [icon_dict, label_dict].

    `icon` carries the IMAGE fields (name, asset) but NOT its own rect — this
    helper owns the geometry so the pair stays aligned.  `text` carries the
    LABEL fields (text, font, color) plus an optional "align".  The text label
    expands to fill the remaining width, which keeps its own align meaningful
    (LEFT hugs the icon, RIGHT pushes to the box edge).
    """
    x, y, w, h = rect
    if icon_size > w:
        raise ValueError("icon_text: icon_size %d wider than box %d" % (icon_size, w))
    if gap >= w - icon_size:
        raise ValueError("icon_text: gap %d leaves no width for text in %d"
                         % (gap, w))
    if icon_first:
        ix, tx = x, x + icon_size + gap
    else:
        tx, ix = x, x + w - icon_size
    iy = y + (h - icon_size) // 2 if icon_valign == "CENTER" else y
    tw = w - icon_size - gap
    ic = {"type": "IMAGE", "name": icon.get("name", "icon"),
          "rect": [ix, iy, icon_size, icon_size],
          "asset": icon.get("asset")}
    if icon.get("rotation"):
        ic["rotation"] = icon["rotation"]
    lb = {"type": "LABEL", "name": text.get("name", "label"),
          "rect": [tx, y, tw, h], "text": text.get("text", ""),
          "font": text.get("font"), "color": text.get("color", "WHITE"),
          "align": text.get("align", "LEFT")}
    for extra in ("hidden", "events"):
        if extra in text:
            lb[extra] = text[extra]
    return [ic, lb]


def card_row(name, rect, label, value, label_font, value_font,
             label_color="WHITE", value_color="DIM", radius=16, bg="CARD",
             pad_x=16, events=None, value_width=100):
    """A settings-style card: a left label and a right-aligned value.

    Returns ONE panel dict with the two labels already inside, positioned by
    `pad_x` from the card edges and vertically centred — the standard iOS/watch
    settings row.  This is the single most repeated layout in the examples, and
    hand-placing the inner labels is where 2-4px vertical drift creeps in.
    """
    cx, cy, cw, ch = rect
    if pad_x * 2 + value_width >= cw:
        raise ValueError("card_row: padding+value_width leave no room in width %d"
                         % cw)
    lh = max(safe_text_height(_approx_size(label_font)),
             safe_text_height(_approx_size(value_font)))
    ly = cy + (ch - lh) // 2
    left = {"type": "LABEL", "name": name + "_label",
            "rect": [cx + pad_x, ly, cw - pad_x * 2 - value_width, lh],
            "text": label, "font": label_font, "color": label_color,
            "align": "LEFT"}
    right = {"type": "LABEL", "name": name + "_value",
             "rect": [cx + cw - pad_x - value_width, ly, value_width, lh],
             "text": value, "font": value_font, "color": value_color,
             "align": "RIGHT"}
    return panel(name, rect, bg=bg, radius=radius,
                 children=[left, right], events=events)


# Kept deliberately tiny and local: card_row needs *a* size to compute a row
# height, but it must not guess the project's font table.  Callers that care
# pass explicit heights through `stack()` instead.
_SIZE_HINTS = {"12": 12, "13": 13, "15": 15, "16": 16, "20": 20, "22": 22,
               "36": 36, "44": 44, "48": 48, "64": 64, "72": 72, "96": 96}


def _approx_size(font_codename):
    """size implied by a codename like 'Body16' -> 16.  Falls back to 16."""
    digits = "".join(ch for ch in str(font_codename) if ch.isdigit())
    return int(digits) if digits else 16


# --------------------------------------------------------------- self-test --
def _selftest():
    ok = True

    def chk(cond, msg):
        nonlocal ok
        if not cond:
            ok = False
            print("FAIL:", msg)

    tiles = grid((20, 60, 360, 220), 3, 2, 12, 12,
                 lambda x, y, w, h: {"rect": [x, y, w, h]})
    chk(len(tiles) == 6, "grid should emit 6 cells, got %d" % len(tiles))
    chk(tiles[0]["rect"] == [20, 60, 112, 104],
        "grid cell 0 wrong: %s" % tiles[0]["rect"])
    # right edge of the last column must land exactly on the box edge
    last = tiles[2]["rect"]
    chk(last[0] + last[2] == 380, "grid right edge %d != 380" % (last[0] + last[2]))
    bottom = tiles[5]["rect"]
    chk(bottom[1] + bottom[3] == 280, "grid bottom %d != 280" % (bottom[1] + bottom[3]))

    for bad in ((20, 60, 10, 220),):
        try:
            grid(bad, 3, 2, 12, 12, lambda *a: None)
            chk(False, "grid should reject gaps wider than the box")
        except ValueError:
            pass

    st = stack((24, 70), 272, [96, 96], 16, lambda x, y, w, h: {"rect": [x, y, w, h]})
    chk([i["rect"] for i in st] == [[24, 70, 272, 96], [24, 182, 272, 96]],
        "stack rects wrong: %s" % [i["rect"] for i in st])

    r = row((0, 0), 24, [40, 40, 40], 10, lambda x, y, w, h: {"rect": [x, y, w, h]})
    chk([i["rect"][0] for i in r] == [0, 50, 100], "row x positions wrong")

    chk(center_in((0, 0, 100, 50), 20, 10) == (40, 20), "center_in wrong")

    pair = icon_text({"name": "ic", "asset": "assets/img_a.png"},
                     {"name": "tx", "text": "已连接", "font": "Body16",
                      "color": "WHITE"},
                     [40, 88, 240, 24], icon_size=20, gap=10)
    ic, lb = pair
    chk(ic["rect"] == [40, 90, 20, 20], "icon_text icon rect %s" % ic["rect"])
    chk(lb["rect"] == [70, 88, 210, 24], "icon_text label rect %s" % lb["rect"])
    chk(ic["asset"] == "assets/img_a.png",
        "icon_text must keep the flat asset path convention")
    # the two must not overlap and must sit inside the box
    chk(ic["rect"][0] + ic["rect"][2] <= lb["rect"][0],
        "icon and text overlap")
    chk(lb["rect"][0] + lb["rect"][2] == 280, "label must reach the box edge")

    cr = card_row("card_x", [24, 72, 272, 96], "显示", "自动",
                  "Title20", "Body16")
    chk(cr["type"] == "PANEL" and len(cr["children"]) == 2, "card_row shape wrong")
    l0, l1 = cr["children"]
    chk(l0["align"] == "LEFT" and l1["align"] == "RIGHT", "card_row aligns wrong")
    chk(l1["rect"][0] + l1["rect"][2] == 24 + 272 - 16,
        "card_row value must end at the right padding")
    chk(l0["rect"][0] == 24 + 16, "card_row label must start at left padding")
    chk(cr["children"][0]["rect"][3] >= 20,
        "card_row row height must clear a 16px font's line height")

    chk(safe_text_height(16) == 22, "safe_text_height(16) = %d" % safe_text_height(16))
    chk(safe_text_height(16, 2) == 44, "safe_text_height(16, 2) wrong")
    chk(safe_text_height(96) == 130, "safe_text_height(96) = %d" % safe_text_height(96))

    # every helper must hand back JSON-serialisable plain data
    import json as _json
    _json.dumps({"tiles": tiles, "stack": st, "row": r, "pair": pair, "card": cr})
    print("self-test:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
