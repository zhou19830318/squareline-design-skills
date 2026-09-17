#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Re-render a generated .spj back to HTML so the layout can be eyeballed
without opening SquareLine Studio.  Reads squareline/<name>/<name>.spj and
writes squareline/<name>/preview_from_project.html next to it.

Every card is drawn from the project file itself (positions, sizes, colours,
fonts, images, events).  Extra cards re-draw a screen with one interaction
state forced open, so the event graph can be reviewed too.

Truly project-agnostic:
  * panel geometry (width/height/shape) comes from spj["info"];
  * the screen list comes from the .spj's own screen order;
  * the font table is built from assets/fonts/*.fcfg.
Nothing is keyed off a specific project's screen names anymore — that used to
make the tool crash with `KeyError: 'health'` the moment it was pointed at the
other example.

Optional sidecar `<Name>.preview.json` next to the .spj adds human labels and
interaction-state cards (both are judgement calls, not derivable):

    {
      "titles": {"home": "App 网格", "ai": "Gemini"},
      "states": [
        {"screen": "ai", "show": ["voice_view"], "hide": ["st_idle"],
         "caption": "聆听中：波形容器显示"}
      ]
    }

Run: python tools/preview_from_project.py [squareline/<name> | path/to/x.spj]
     [--only screen1,screen2] [--scale 1.5]
"""

import html
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_project():
    """argv[1] = squareline/<name> dir or .spj file; default: first *.spj under
    <root>/squareline.  Returns (project_dir, spj_path)."""
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        p = sys.argv[1]
        if p.endswith(".spj"):
            return os.path.dirname(p), p
        cand = sorted(__import__("glob").glob(os.path.join(p, "*.spj")))
        if cand:
            return p, cand[0]
        sys.exit("no .spj in " + p)
    base = os.path.join(ROOT, "squareline")
    cand = sorted(__import__("glob").glob(os.path.join(base, "*", "*.spj")))
    if not cand:
        sys.exit("no .spj under " + base + " — pass one: python tools/preview_from_project.py squareline/<name>")
    if len(cand) > 1:
        print("multiple projects, using:", cand[0], "(pass one explicitly for another)")
    return os.path.dirname(cand[0]), cand[0]


OUT, SPJ_PATH = resolve_project()
PROJECT_NAME = os.path.splitext(os.path.basename(SPJ_PATH))[0]

_spj = json.load(open(SPJ_PATH, encoding="utf-8"))
INFO = _spj.get("info", {})

# Panel geometry is authoritative in spj["info"].  Never fall back to a default:
# a wrong default silently mis-scales every card (it once drew a 240x240 round
# panel inside a 410x502 rectangle).
if not INFO.get("width") or not INFO.get("height"):
    sys.exit("ERROR: %s has no info.width/height - panel geometry lives there, "
             "not on the SCREEN nodes." % SPJ_PATH)
SW, SH = INFO["width"], INFO["height"]
CIRCLE = INFO.get("shape", "RECT") == "CIRCLE"


def load_font_src(src_dir):
    """{codename: (ttf basename, size_px, css_weight)} straight from the
    project's own font config files - no per-project table to keep in sync."""
    import glob as _glob
    table = {}
    for f in sorted(_glob.glob(os.path.join(src_dir, "assets", "fonts", "*.fcfg"))):
        try:
            cfg = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        code = cfg.get("codename")
        ttf = os.path.basename(str(cfg.get("ttf_path", "")).replace("\\", "/"))
        size = cfg.get("size") or 16
        if not code or not ttf:
            continue
        # weight only affects the @font-face rule; the TTF file name says it
        weight = 700 if "-700" in ttf else (500 if "-500" in ttf else 400)
        table[code] = (ttf, size, weight)
    return table


FONT_SRC = load_font_src(OUT)
DEFAULT_FONT = next(iter(FONT_SRC.values()),
                    ("noto-sans-sc-v40-chinese-simplified-regular.ttf", 16, 400))


def load_sidecar(out_dir, project):
    """Optional <Name>.preview.json: titles + interaction-state cards."""
    p = os.path.join(out_dir, project + ".preview.json")
    if not os.path.exists(p):
        return {}, []
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("WARN - %s is not readable (%s); ignoring" % (os.path.basename(p), e))
        return {}, []
    titles = d.get("titles", {}) or {}
    states = [(s["screen"], set(s.get("show", [])), set(s.get("hide", [])),
               s.get("caption", "")) for s in (d.get("states") or [])
              if s.get("screen")]
    return titles, states


TITLES, STATES = load_sidecar(OUT, PROJECT_NAME)


def get(props, strtype, key="strval", default=None):
    for p in props:
        if p.get("strtype") == strtype:
            return p.get(key, default)
    return default


def rgba(arr):
    a = arr[3] / 255.0 if len(arr) > 3 else 1.0
    return "rgba(%d,%d,%d,%.3f)" % (arr[0], arr[1], arr[2], a)


def main_style_of(props):
    for p in props:
        if isinstance(p, dict) and p.get("part") == "lv.PART.MAIN":
            st = {}
            for s in p.get("childs", []):
                for sp in s.get("childs", []):
                    st[sp["strtype"]] = sp
            return st
    return {}


def part_style(props, part):
    for p in props:
        if isinstance(p, dict) and p.get("part") == part:
            st = {}
            for s in p.get("childs", []):
                for sp in s.get("childs", []):
                    st[sp["strtype"]] = sp
            return st
    return {}


def arc_svg(x, y, w, h, start_lv, sweep, ind_deg, ind_rgba, bg_rgba, width):
    """Draw an LVGL ARC as inline SVG (two stroked circle segments).

    Why SVG and not `conic-gradient`: the CSS version renders as an empty ring
    on any engine without conic-gradient support — notably the old WebKit in
    `wkhtmltoimage`, which is what a lot of sandboxes ship.  The failure is
    silent (the .spj is correct, only the picture is wrong), so the reviewer
    could not visually confirm the rings at all.  Stroked SVG arcs are
    supported by every rasteriser down to ancient WebKit/IE, which makes the
    preview portable *and* actually checkable.

    LVGL angles: 0deg is at 3 o'clock and proceeds clockwise.  SVG y grows
    downward, so a clockwise LVGL sweep is the same direction in SVG.
    """
    cx, cy = x + w / 2.0, y + h / 2.0
    r = max(1.0, (min(w, h) - width) / 2.0)
    stroke = max(1, int(round(width)))

    def pt(deg):
        rad = math.radians(deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    def seg(from_deg, span, colour):
        """One stroked arc path; None when the span is empty."""
        if span <= 0.01:
            return None
        sx, sy = pt(from_deg)
        ex, ey = pt(from_deg + span)
        # a full 360 arc degenerates to a single point, so draw two halves
        if span >= 359.9:
            mx, my = pt(from_deg + 180)
            return ('<path d="M %.2f %.2f A %.2f %.2f 0 0 1 %.2f %.2f '
                    'A %.2f %.2f 0 0 1 %.2f %.2f" fill="none" stroke="%s" '
                    'stroke-width="%d" stroke-linecap="butt"/>'
                    % (sx, sy, r, r, mx, my, r, r, ex, ey, colour, stroke))
        large = 1 if span > 180 else 0
        return ('<path d="M %.2f %.2f A %.2f %.2f 0 %d 1 %.2f %.2f" fill="none" '
                'stroke="%s" stroke-width="%d" stroke-linecap="butt"/>'
                % (sx, sy, r, r, large, ex, ey, colour, stroke))

    parts = []
    track = seg(start_lv, sweep, rgba(bg_rgba))
    if track:
        parts.append(track)
    ind_part = seg(start_lv, ind_deg, rgba(ind_rgba))
    if ind_part:
        parts.append(ind_part)

    return ('<svg class="o" width="%d" height="%d" viewBox="0 0 %d %d" '
            'style="left:%dpx;top:%dpx;overflow:visible">%s</svg>'
            % (w, h, w, h, x, y, "".join(parts)))


def render_node(node, parent, force_show, force_hide, screen_bg, out):
    """parent = (px, py, pw, ph) absolute rect of the containing object."""
    props = node.get("properties") or []
    kind = node.get("saved_objtypeKey")
    name = get(props, "OBJECT/Name", "strval", "?")
    if name in force_hide:
        return
    if get(props, "OBJECT/Hidden", "strval", "False") == "True" and name not in force_show:
        return

    ox, oy = get(props, "OBJECT/Position", "intarray", [0, 0])
    w, h = get(props, "OBJECT/Size", "intarray", [1, 1])
    px, py, pw, ph = parent
    x = int(round(px + pw / 2.0 + ox - w / 2.0))
    y = int(round(py + ph / 2.0 + oy - h / 2.0))
    st = main_style_of(props)

    if kind == "LABEL":
        text = html.escape(str(get(props, "LABEL/Text", "strval", "")))
        # spj stores LVGL escapes as literal backslash-n; HTML needs a real break
        text = text.replace("\\n", "<br>")
        font = st.get("_style/Text_Font", {}).get("strval", "")
        colour = st.get("_style/Text_Color", {}).get("intarray", [255, 255, 255, 255])
        align = st.get("_style/Text_Align", {}).get("strval", "LEFT").lower()
        _ttf, size, weight = FONT_SRC.get(font, DEFAULT_FONT)
        out.append('<div class="o lbl" style="left:%dpx;top:%dpx;width:%dpx;'
                   'height:%dpx;font-size:%dpx;font-weight:%d;color:%s;'
                   'text-align:%s;font-family:F%d;line-height:%dpx">%s</div>'
                   % (x, y, w, h, size, weight, rgba(colour), align, size,
                      round(size * 1.22), text))
    elif kind == "IMAGE":
        asset = get(props, "IMAGE/Asset", "strval", "")
        rot = get(props, "IMAGE/Rotation", "integer", 0) or 0
        extra = "transform:rotate(%.1fdeg);" % (rot / 10.0) if rot else ""
        out.append('<img class="o" src="%s" style="left:%dpx;top:%dpx;width:%dpx;'
                   'height:%dpx;%s" alt="%s">' % (asset, x, y, w, h, extra, name))
    elif kind in ("PANEL", "CONTAINER"):
        bg = st.get("_style/Bg_Color", {}).get("intarray", [0, 0, 0, 0])
        radius = st.get("_style/Bg_Radius", {}).get("integer", 0)
        clickable = get(props, "OBJECT/Clickable", "strval", "False") == "True"
        out.append('<div class="o pnl%s" style="left:%dpx;top:%dpx;width:%dpx;'
                   'height:%dpx;background:%s;border-radius:%dpx"></div>'
                   % (" tap" if clickable else "", x, y, w, h, rgba(bg), radius))
    elif kind == "ARC":
        value = get(props, "ARC/Value", "integer", 0) or 0
        rng = get(props, "ARC/Range", "intarray", [0, 100])
        angles = get(props, "ARC/Bg_angles", "intarray", [0, 360])
        frac = 0.0 if not rng[1] else float(value) / float(rng[1])
        start_lv, end_lv = angles[0], angles[1]
        sweep = 360.0 if (start_lv == 0 and end_lv == 360) else \
            float((end_lv - start_lv) % 360)
        ind_deg = max(0.0, min(sweep, frac * sweep))
        ind = part_style(props, "lv.PART.INDICATOR").get("_style/Arc_Color", {})
        bgc = part_style(props, "lv.PART.MAIN").get("_style/Arc_Color", {})
        width = part_style(props, "lv.PART.MAIN").get("_style/Arc_Width", {}
                                                       ).get("integer", 16)
        out.append(arc_svg(x, y, w, h, start_lv, sweep, ind_deg,
                           ind.get("intarray", [255, 45, 138, 255]),
                           bgc.get("intarray", [40, 40, 44, 255]), width))

    for c in node.get("children", []) or []:
        render_node(c, (x, y, w, h), force_show, force_hide, screen_bg, out)


def screen_bg_of(sc):
    st = main_style_of(sc["properties"])
    return rgba(st.get("_style/Bg_Color", {}).get("intarray", [0, 0, 0, 255]))


def count_handlers(node):
    n = 0
    if isinstance(node, dict):
        if node.get("strtype") == "_event/EventHandler":
            n += 1
        for v in node.values():
            n += count_handlers(v)
    elif isinstance(node, list):
        for v in node:
            n += count_handlers(v)
    return n


def main():
    args = [a for a in sys.argv[1:]]
    only = None
    scale = 1.0
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))
    if "--scale" in args:
        scale = float(args[args.index("--scale") + 1])

    spj = _spj
    by_name = {}
    for sc in spj["root"]["children"]:
        by_name[get(sc["properties"], "OBJECT/Name", "strval", "?")] = sc
    # the .spj's screen order *is* the switch order - derive it, don't hardcode
    screens = [nm for nm in by_name if only is None or nm in only]
    print("screens:", screens)

    faces = "".join(
        "@font-face{font-family:'F%d';src:url('assets/fonts/%s') "
        "format('truetype');font-weight:%d;font-display:block}\n"
        % (size, ttf, weight) for ttf, size, weight in FONT_SRC.values())

    def card(screen, force_show, force_hide, caption, tag=""):
        sc = by_name[screen]
        bg = screen_bg_of(sc)
        out = []
        for c in sc.get("children", []):
            render_node(c, (0, 0, SW, SH), force_show, force_hide, bg, out)
        n = count_handlers(sc)
        return ('<figure><div class="watch"><div class="screen" style="background:%s">'
                '%s</div></div><figcaption><b>%s%s</b><span>%s</span>'
                '<em>本屏事件 %d 个</em></figcaption></figure>'
                % (bg, "".join(out), screen, (" · " + TITLES.get(screen, "")) if not tag else (" · " + tag),
                   caption, n))

    n_initial = len(screens)
    cards = [card(nm, set(), set(), "初始状态") for nm in screens]

    state_cards = []
    for screen, fs, fh, cap in STATES:
        if screen not in by_name:
            print("WARN - sidecar state refers to unknown screen %r; skipped" % screen)
            continue
        if only is not None and screen not in only:
            continue
        state_cards.append(card(screen, fs, fh, cap, tag="交互态"))
    cards += state_cards
    states_html = ""
    if state_cards:
        states_html = ('<h2>② 交互态（强制展开）</h2>\n<div class="grid">%s</div>'
                       % "".join(cards[n_initial:]))

    doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>%s — SquareLine 工程反渲染预览</title>
<style>
%s
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b0d12;color:#e8ecf4;font-family:system-ui,"Segoe UI",sans-serif;padding:28px}
h1{font-size:20px;font-weight:600;margin-bottom:6px}
h2{font-size:15px;font-weight:600;margin:30px 0 14px;color:#c3cad6}
p.sub{color:#8b93a3;font-size:13px;margin-bottom:24px;max-width:900px;line-height:1.6}
.grid{display:flex;flex-wrap:wrap;gap:26px;zoom:%s}
figure{display:flex;flex-direction:column;gap:8px}
.watch{padding:8px;border-radius:%dpx;background:linear-gradient(150deg,#454b54,#23262b 22%%,#111316 55%%,#2c3037 88%%,#14161a);
  box-shadow:0 14px 30px rgba(0,0,0,.6),inset 0 1px 1px rgba(255,255,255,.16)}
.screen{position:relative;width:%dpx;height:%dpx;border-radius:%dpx;overflow:hidden;
  box-shadow:inset 0 0 0 1px #000}
.o{position:absolute;display:block}
.lbl{white-space:pre-wrap;overflow:hidden}
.pnl{display:block}
.pnl.tap{outline:1px dashed rgba(120,200,255,.35);outline-offset:-1px}
svg.o{overflow:visible}
img.o{object-fit:contain}
figcaption{font-size:12px;color:#9aa3b2;display:flex;flex-direction:column;gap:2px;text-align:center}
figcaption b{color:#e8ecf4;font-size:13px}
figcaption span{color:#c3cad6}
figcaption em{color:#6f7887;font-style:normal;font-size:11px;line-height:1.4;max-width:410px}
</style></head><body>
<h1>%s · SquareLine Studio 工程反渲染</h1>
<p class="sub">本页由 <code>%s.spj</code> 直接解析生成 —— 位置、尺寸、颜色、字体、图片、事件数量均取自工程文件本身（面板 %d×%d，%s）。
虚线框标出的是带 CLICKED 事件的可点区域。下半部分是强制展开某个交互状态后的样子，用于核对事件逻辑。</p>
<h2>① 各屏初始状态</h2>
<div class="grid">%s</div>
%s
</body></html>""" % (
    PROJECT_NAME, faces, scale,
    8 + (SW // 2 if CIRCLE else 24),
    SW, SH, (SW // 2) if CIRCLE else 24,
    PROJECT_NAME, PROJECT_NAME, SW, SH, ("CIRCLE" if CIRCLE else "RECT"),
    "".join(cards[:n_initial]), states_html)

    dst = os.path.join(OUT, "preview_from_project.html")
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    print("written:", dst, "| cards:", len(cards), "| panel: %dx%d %s" % (SW, SH, "CIRCLE" if CIRCLE else "RECT"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
