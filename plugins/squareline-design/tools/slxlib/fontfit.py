# -*- coding: utf-8 -*-
"""fit-font: from a MEASURED ink box of a piece of text in the concept image, find the font size that
reproduces it, and the LABEL rect that puts it there.

Why not just PIL: PIL's text layout is ~4% wider than the LVGL font lv_font_conv really generates
(measured: "14:30" at 60 px is 161.0 px in PIL, 154.6 px in the generated font).  So PIL only seeds the
search; the answer comes from running the real lv_font_conv at a few sizes and reading the glyph
metrics (and line_height / base_line) out of the generated .c file -- the same numbers LVGL uses.
"""
import math
import os
import re
import shutil
import subprocess
import tempfile

TTF = {"700": "noto-sans-sc-v40-chinese-simplified-700.ttf",
       "500": "noto-sans-sc-v40-chinese-simplified-500.ttf",
       "400": "noto-sans-sc-v40-chinese-simplified-regular.ttf"}
PIL_WIDTH_CORRECTION = 0.965        # used only when node is missing


def _pil_ink(root, weight, size, text):
    from PIL import ImageFont
    f = ImageFont.truetype(os.path.join(root, "fonts", TTF[weight]), size)
    l, t, r, b = f.getbbox(text, anchor="ls")
    return r - l, b - t


def parse_lvgl_c(c_text):
    """Return (glyph_for(codepoint) -> (adv_px, box_w, box_h, ofs_x, ofs_y), line_height, base_line)."""
    dsc = [tuple(map(int, d)) for d in re.findall(
        r"\{\.bitmap_index = (\d+), \.adv_w = (\d+), \.box_w = (\d+), \.box_h = (\d+), \.ofs_x = (-?\d+), \.ofs_y = (-?\d+)\}", c_text)]
    ulists = {m.group(1): [int(x, 0) for x in m.group(2).replace("\n", " ").split(",") if x.strip()]
              for m in re.finditer(r"static const uint16_t (unicode_list_\d+)\[\] = \{([^}]*)\}", c_text)}
    cm = []
    for m in re.finditer(r"\.range_start = (\d+), \.range_length = (\d+), \.glyph_id_start = (\d+),\s*"
                         r"\.unicode_list = (\w+), \.glyph_id_ofs_list = (\w+), \.list_length = (\d+), \.type = (\w+)", c_text):
        cm.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), m.group(7)))
    lh = int(re.search(r"\.line_height = (\d+)", c_text).group(1))
    bl = int(re.search(r"\.base_line = (\d+)", c_text).group(1))

    def glyph(cp):
        for start, length, gid0, ul, typ in cm:
            if start <= cp < start + length:
                if typ.endswith("FORMAT0_TINY"):
                    gid = gid0 + (cp - start)
                elif typ.endswith("SPARSE_TINY") and ul in ulists and (cp - start) in ulists[ul]:
                    gid = gid0 + ulists[ul].index(cp - start)
                else:
                    continue
                d = dsc[gid]
                return d[1] / 16.0, d[2], d[3], d[4], d[5]
        return None
    return glyph, lh, bl


def lvgl_probe(root, weight, size, text, node="node", ranges="0x20-0x7E,0x00B0"):
    """Run the real lv_font_conv for `text` at `size`; return dict(ink_w, ink_h, line_height, base_line, ink_cy_rel_baseline)."""
    lfc = os.path.join(root, "tools", "node_modules", "lv_font_conv", "lv_font_conv.js")
    chars = "".join(sorted(set(text) | set(" ")))
    tmp = tempfile.mkdtemp(prefix="slxfit_")
    try:
        out = os.path.join(tmp, "p.c")
        r = subprocess.run([node, lfc, "--font", os.path.join(root, "fonts", TTF[weight]), "--bpp", "4", "--size", str(size),
                            "--range", ranges, "--symbols", chars, "--no-compress", "--no-prefilter", "--format", "lvgl",
                            "--lv-font-name", "probe", "-o", out], capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or not os.path.exists(out):
            return None
        glyph, lh, bl = parse_lvgl_c(open(out, encoding="utf-8").read())
        x, left, right, top, bot = 0.0, None, 0.0, -9999, 9999
        for i, ch in enumerate(text):
            g = glyph(ord(ch))
            if g is None:
                return None
            adv, bw, bh, ox, oy = g
            if bw == 0:                      # space
                x += adv
                continue
            if left is None:
                left = x + ox
            right = x + ox + bw
            x += adv
            top, bot = max(top, oy + bh), min(bot, oy)
        return {"ink_w": right - left, "ink_h": top - bot, "line_height": lh, "base_line": bl,
                "ink_cy_up": (top + bot) / 2.0}          # ink centre ABOVE the baseline
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def report(root, text, w, h, weight="400", cy=None, cx=None, box_w=None, node="node", ranges="0x20-0x7E,0x00B0", prefer="width"):
    if w is None and h is None:
        raise SystemExit("fit-font needs --w and/or --h (the measured ink box, in panel px)")
    # 1) seed with PIL (corrected), 2) refine with the real converter
    seed = None
    for s in range(8, 161):
        iw, ih = _pil_ink(root, weight, s, text)
        iw *= PIL_WIDTH_CORRECTION
        e = abs((iw - w) / w) if w else abs((ih - h) / h)
        if seed is None or e < seed[0]:
            seed = (e, s)
    s0 = seed[1]
    probes = {}
    exact = shutil.which(node) is not None
    for s in range(max(8, s0 - 5), s0 + 6):
        p = lvgl_probe(root, weight, s, text, node, ranges) if exact else None
        if p is None:
            iw, ih = _pil_ink(root, weight, s, text)
            p = {"ink_w": iw * PIL_WIDTH_CORRECTION, "ink_h": ih, "line_height": int(math.ceil(s * 1.25)), "base_line": int(round(s * 0.2)),
                 "ink_cy_up": ih / 2.0, "approx": True}
            exact = False
        probes[s] = p
    by_w = min(probes, key=lambda s: abs(probes[s]["ink_w"] - w)) if w else None
    by_h = min(probes, key=lambda s: abs(probes[s]["ink_h"] - h)) if h else None
    L = ["text %r  weight %s  measured ink box w=%s h=%s   [%s]" % (text, weight, w, h, "exact: real lv_font_conv glyph metrics" if exact else "APPROXIMATE (node missing): PIL x0.965")]
    for lab, s in (("by width ", by_w), ("by height", by_h)):
        if s:
            L.append("  %s -> %3d px   ink would be %.1f x %.1f" % (lab, s, probes[s]["ink_w"], probes[s]["ink_h"]))
    size = (by_h if (prefer == "height" and by_h) else by_w) or by_h
    p = probes[size]
    if by_w and by_h and abs(by_w - by_h) > 1:
        L.append("  NOTE width and height disagree by %d px: the concept typeface has different proportions than Noto. Chose WIDTH "
                 "(keeps the layout footprint); the ink will be %.1f px %s than measured. Use `--prefer height` to pick the other."
                 % (abs(by_w - by_h), abs(p["ink_h"] - h), "taller" if p["ink_h"] > h else "shorter") if prefer != "height" else
                 "  NOTE width and height disagree by %d px; chose HEIGHT as asked (ink width will be %.1f vs measured %.1f)." % (abs(by_w - by_h), p["ink_w"], w))
    L.append("  recommended size %d px -> ink %.1f x %.1f ; line_height %d (LABEL h >= %d, safe %d) ; baseline %d px below the box top"
             % (size, p["ink_w"], p["ink_h"], p["line_height"], p["line_height"], int(math.ceil(size * 1.35)), p["line_height"] - p["base_line"]))
    if cy is not None:
        top_y = cy - ((p["line_height"] - p["base_line"]) - p["ink_cy_up"])
        L.append("  to centre the ink at y=%s: LABEL rect y = %d  (computed from the generated font, not a rule of thumb)" % (cy, round(top_y)))
    if cx is not None and box_w:
        L.append("  to centre at x=%s with CENTER align: rect x = %d, w = %d" % (cx, round(cx - box_w / 2.0), box_w))
    if not (p.get("approx")):
        L.append("  note: line_height / baseline depend on the glyph set the project includes. This used ranges=%s; pass --ranges equal to "
                 "your spec's ranges_num (number fonts) or ranges_text (text fonts). The build's `lineheight:` line is final." % ranges)
    return "\n".join(L), size


# ----------------------------------------------------------------------------------------------
# Per-font metrics for the widget library: ONE converter run per font gives line_height, base_line
# and the ink centre of typical glyph classes, so a label can be placed by where its INK should be.
CJK_SAMPLE = "国字中日月永龍文周六晴"
_FM_CACHE = {}


class FontMetrics(object):
    def __init__(self, line_height, base_line, cy_up):
        self.lh, self.bl, self.cy_up = line_height, base_line, cy_up

    @property
    def baseline(self):                    # px below the label top where the baseline sits (LVGL model)
        return self.lh - self.bl

    def ink_center_up(self, text):
        """Ink centre above the baseline for this kind of text."""
        if any(ord(c) > 0x2E80 for c in text):
            return self.cy_up["cjk"]
        if any(c.isalpha() and c.islower() for c in text) and not any(c.isdigit() for c in text):
            return self.cy_up["lower"]
        return self.cy_up["digits"]


def font_metrics(root, ttf, size, node="node", ranges="0x20-0x7E,0x00B0", restricted=None):
    """restricted=None for a normal text font; for a number/symbol font pass its symbol string: ONLY those glyphs
    (plus `ranges`) are in the font, so line_height/base_line must be probed with exactly that set."""
    key = (root, ttf, size, ranges, restricted)
    if key in _FM_CACHE:
        return _FM_CACHE[key]
    weight = "700" if "-700" in ttf else ("500" if "-500" in ttf else "400")
    chars = ("0123456789" + restricted) if restricted is not None else ("0123456789" + "xvzcseaou" + CJK_SAMPLE)
    lfc = os.path.join(root, "tools", "node_modules", "lv_font_conv", "lv_font_conv.js")
    tmp = tempfile.mkdtemp(prefix="slxfm_")
    fm = None
    try:
        out = os.path.join(tmp, "p.c")
        r = subprocess.run([node, lfc, "--font", os.path.join(root, "fonts", ttf), "--bpp", "4", "--size", str(size), "--range", ranges,
                            "--symbols", chars, "--no-compress", "--no-prefilter", "--format", "lvgl", "--lv-font-name", "probe", "-o", out],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and os.path.exists(out):
            glyph, lh, bl = parse_lvgl_c(open(out, encoding="utf-8").read())

            def centre(s):
                tops, bots = [], []
                for ch in s:
                    g = glyph(ord(ch))
                    if g and g[1]:
                        tops.append(g[4] + g[2])
                        bots.append(g[4])
                return (max(tops) + min(bots)) / 2.0 if tops else size * 0.36
            dig = centre("0123456789")
            if restricted is not None:
                fm = FontMetrics(lh, bl, {"digits": dig, "lower": dig, "cjk": dig})
            else:
                fm = FontMetrics(lh, bl, {"digits": dig, "lower": centre("xvzcseaou"), "cjk": centre(CJK_SAMPLE)})
    except Exception:
        fm = None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if fm is None:                          # no node: ratios measured on Noto Sans SC
        fm = FontMetrics(int(round(size * 1.24)), int(round(size * 0.29)),
                         {"digits": size * 0.36, "lower": size * 0.27, "cjk": size * 0.40})
    _FM_CACHE[key] = fm
    return fm
