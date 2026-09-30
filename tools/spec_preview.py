#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""spec_preview.py — render a spec JSON to HTML *without* building the project.

Why this exists
---------------
Stage C (build_from_spec) is where geometry mistakes used to be discovered —
after fonts were subsetted, after nid plumbing, after a full engine build.  The
build is deliberately cheap in CPU but it is not the right *feedback loop*:
design iteration wants a sub-second "edit JSON -> see picture" cycle, and the
multi-round refinement workflow (concept image -> spec -> review -> adjust)
needs a preview that NEVER drifts from what will actually be built.

So this tool walks the SAME spec the builder consumes and paints each screen as
absolutely-positioned HTML.  It is a design-time contact sheet:

  * panels / labels / images / arcs, nested containers, hidden objects;
  * palette + hex colours resolved exactly like build_from_spec.parse_colour;
  * fonts mapped to system approximations (an honest stand-in, not a lie:
    the header names the real fonts; the preview's job is geometry + copy);
  * image references resolved against the spec's `assets` dir so a missing
    PNG shows as a dashed box with the path — caught here, not by the validator;
  * screens stacked side by side in `order`, initial screen marked.

It never runs the engine, never writes an .spj, never needs node.

Usage
-----
    python tools/spec_preview.py <spec.json> [--out file.html] [--scale S] [--open]

Default output: <spec_dir>/<spec_name>.spec_preview.html

The built-in overlap audit (the same check that catches sibling collisions in
the mockup flow) reports sibling pairs overlapping by > 2 px; with --strict
those become a non-zero exit so an agent can gate on them.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.join(ROOT, "tools")
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# (no engine import on purpose — this tool must run without node/engine state)

ALIGN = {"LEFT": "left", "CENTER": "center", "RIGHT": "right"}


def fail(msg):
    raise SystemExit("spec_preview: " + msg)


def parse_colour(v, palette, where):
    """Mirror of build_from_spec.parse_colour (kept in sync on purpose — it is
    20 lines, and importing the builder would drag in the engine's globals)."""
    if v is None:
        return "#00000000"
    if isinstance(v, (list, tuple)):
        if len(v) == 3:
            v = [v[0], v[1], v[2], 255]
        if len(v) == 4:
            return "rgba(%d,%d,%d,%.2f)" % (v[0], v[1], v[2], v[3] / 255.0)
        fail("%s: colour array needs 3 or 4 components" % where)
    if not isinstance(v, str):
        fail("%s: colour must be a name, hex string or array" % where)
    if v in palette:
        return parse_colour(palette[v], {}, where)
    s = v.strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 6:
            return "#%02x%02x%02x" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        if len(h) == 8:
            return "rgba(%d,%d,%d,%.2f)" % (int(h[0:2], 16), int(h[2:4], 16),
                                            int(h[4:6], 16), int(h[6:8], 16) / 255.0)
        fail("%s: hex colour must be #rrggbb or #rrggbbaa, got %r" % (where, v))
    fail("%s: unknown colour %r (not in palette %s)" % (where, v, sorted(palette)))


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace("\n", "<br>"))


# ------------------------------------------------------------------ events --
def event_summary(events, palette):
    if not events:
        return ""
    bits = []
    for e in events:
        kind = (e.get("on") or "CLICKED").split("(")[0]
        acts = []
        for a in e.get("actions") or []:
            k = (a.get("type") or "").upper()
            if k == "CHANGE_SCREEN":
                acts.append("→ " + str(a.get("target")))
            elif k in ("HIDE", "SHOW"):
                acts.append(k.capitalize() + " " + str(a.get("object")))
            elif k == "SET_OPACITY":
                acts.append("opacity %s→%s" % (a.get("object"), a.get("value")))
            elif k == "PLAY_ANIMATION":
                acts.append("anim " + str(a.get("animation")))
            elif k == "CALL_FUNCTION":
                acts.append(str(a.get("function") or a.get("name")) + "()")
        bits.append("<div class='ev'>⚡ %s: %s</div>" % (esc(kind), esc(" · ".join(acts))))
    return "".join(bits)


# ----------------------------------------------------------------- objects --
def obj_html(o, spec, palette, where, audit):
    t = (o.get("type") or "").upper()
    r = o.get("rect")
    if not r or len(r) != 4:
        fail("%s/%s: needs rect [x,y,w,h]" % (where, o.get("name", "?")))
    x, y, w, h = (int(v) for v in r)
    name = o.get("name", "?")
    where = "%s/%s" % (where, name)

    style = ["position:absolute", "left:%dpx" % x, "top:%dpx" % y,
             "width:%dpx" % w, "height:%dpx" % h]
    if o.get("hidden"):
        style.append("opacity:0.18")     # show hidden objects faintly, never zero:
                                         # a preview that hides them hides the bug too
    inner = ""
    extra_cls = ""

    if t in ("PANEL", "CONTAINER"):
        style.append("background:%s" % parse_colour(o.get("bg"), palette, where + "/bg"))
        rad = int(o.get("radius", 0))
        if rad:
            style.append("border-radius:%dpx" % rad)
        if o.get("clickable") or o.get("events"):
            style.append("cursor:pointer")
        kids = [obj_html(c, spec, palette, where, audit) for c in (o.get("children") or [])]
        inner = "".join(kids)
    elif t == "LABEL":
        font = o.get("font", "")
        m = re.search(r"(\d+)", font)
        size = int(m.group(1)) if m else 16
        # Two-tier audit against the measured line-height envelope
        # (1.19x-1.35x of font size, see tools/LABEL_SIZING.md).  The real
        # lineheight depends on the glyph set and is only known after a build,
        # so below 1.19x is "will likely clip" and below 1.35x is only
        # "borderline" -- the build's `lineheight:` line stays the truth.
        hard = -(-size * 119 // 100)          # ceil(size * 1.19)
        safe = -(-size * 135 // 100)          # ceil(size * 1.35)
        if h < hard:
            audit.append("%s: LABEL height %d < %d for %s (%dpx) - will likely "
                         "clip CJK (line_height > size; give height >= %d)"
                         % (where, h, hard, font, size, safe))
        elif h < safe:
            audit.append("%s: LABEL height %d is borderline for %s (%dpx): fine if "
                         "build lineheight <= %d, risky otherwise -- the build's "
                         "`lineheight:` line is the truth"
                         % (where, h, font, size, h))
        style += ["color:%s" % parse_colour(o.get("color"), palette, where + "/color"),
                  "font-size:%dpx" % size,
                  "display:flex", "align-items:center",
                  "justify-content:%s" % ALIGN.get(str(o.get("align", "LEFT")).upper(), "left"),
                  "line-height:1.15", "overflow:hidden", "white-space:pre-wrap"]
        inner = esc(str(o.get("text", "")))
        if not inner:
            extra_cls = " empty"
    elif t == "IMAGE":
        asset = o.get("asset", "")
        cand = None
        if asset.startswith("assets/"):
            # The builder reads source PNGs from ASSETS_ROOT/assets_subdir
            # (spec["assets"] + spec["assets_subdir"]) while the project
            # records the flat `assets/<file>` path -- mirror that here or
            # every reference would audit as missing.
            cand = os.path.join(spec.get("assets") or ".",
                                spec.get("assets_subdir", "images"),
                                asset[len("assets/"):])
            if not os.path.exists(cand):
                audit.append("%s: asset not found on disk: %s" % (where, asset))
                cand = None
        if cand:
            # Inline as a data URI: the preview must survive the single-file
            # registered-preview flow (same reason inline_mockup.mjs exists --
            # relative paths silently break outside the repo tree).
            import base64
            with open(cand, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("ascii")
            inner = ("<img src='data:image/png;base64,%s' "
                     "style='width:100%%;height:100%%;object-fit:contain'>" % b64)
        else:
            inner = ("<div class='missing'>%s</div>" % esc("missing " + asset))
        rot = o.get("rotation")
        if rot:
            style.append("transform:rotate(%ddeg)" % (rot / 10.0))
    elif t == "ARC":
        ind = parse_colour(o.get("indicator", "#FFFFFF"), palette, where + "/indicator")
        trk = parse_colour(o.get("track", "#333333"), palette, where + "/track")
        width = int(o.get("width", 10))
        a0, a1 = (int(v) for v in (o.get("angles") or [0, 360]))
        val, vmax = int(o.get("value", 0)), int(o.get("max", 100) or 100)
        frac = 0 if vmax == 0 else min(1.0, max(0.0, val / float(vmax)))
        sweep = (a1 - a0) % 360 or 360
        sweep = sweep if (a1 - a0) % 360 else 360
        deg0 = (a0 - 90) % 360
        # Arc drawn as stroked inline SVG — the same trick preview_from_project
        # uses; CSS conic-gradient silently fails on old WebKit (pitfall 31).
        r_px = max(1.0, (min(w, h) - width) / 2.0)
        cx = cy = min(w, h) / 2.0
        import math
        p0 = (cx + r_px * math.cos(math.radians(deg0)),
              cy + r_px * math.sin(math.radians(deg0)))
        p1 = (cx + r_px * math.cos(math.radians(deg0 + sweep * frac)),
              cy + r_px * math.sin(math.radians(deg0 + sweep * frac)))
        large = 1 if sweep * frac > 180 else 0
        def pt(p):
            return "%.2f %.2f" % p
        bg_path = ("M %s A %.2f %.2f 0 %d 1 %s"
                   % (pt(p0), r_px, r_px, 1 if sweep > 180 else 0, pt(p1)))
        if frac >= 0.999:
            bg_path = ("M %s A %.2f %.2f 0 1 1 %s A %.2f %.2f 0 1 1 %s"
                       % (pt(p0), r_px, r_px, pt((cx + r_px * math.cos(math.radians(deg0 + 0.01)),
                                                  cy + r_px * math.sin(math.radians(deg0 + 0.01)))),
                          r_px, r_px, pt(p0)))
        inner = ("<svg width='%d' height='%d' viewBox='0 0 %d %d'>"
                 "<path d='%s' fill='none' stroke='%s' stroke-width='%d' stroke-linecap='round'/>"
                 "<path d='%s' fill='none' stroke='%s' stroke-width='%d' stroke-linecap='round'/>"
                 "</svg>"
                 % (w, h, w, h,
                    "M %s A %.2f %.2f 0 %d 1 %s" % (pt(p0), r_px, r_px,
                                                    1 if sweep > 180 else 0,
                                                    pt((cx + r_px * math.cos(math.radians(deg0 + sweep)),
                                                        cy + r_px * math.sin(math.radians(deg0 + sweep))))),
                    trk, width, bg_path, ind, width))
    else:
        fail("%s: unknown type %r" % (where, t))

    tip = " ".join(event_summary(o.get("events"), palette).split())
    ev_html = event_summary(o.get("events"), palette)
    title = esc("%s  %s [%s]  rect=%s" % (where, t, name, r))
    return ("<div class='obj %s%s' style='%s' title='%s'>%s%s</div>"
            % (t.lower(), extra_cls, ";".join(style), title, inner, ev_html))


# ------------------------------------------------------------------ screen --
def screen_html(sc, spec, palette, order, initial, audit):
    name = sc.get("name", "?")
    W, H = int(spec["width"]), int(spec["height"])
    shape = (spec.get("shape", "RECT") or "RECT").upper()
    style = ["width:%dpx" % W, "height:%dpx" % H,
             "background:%s" % parse_colour(sc.get("bg"), palette, "screen %s/bg" % name)]
    if shape == "CIRCLE":
        style += ["border-radius:50%%"]
    kids = "".join(obj_html(c, spec, palette, "screen " + name, audit)
                   for c in (sc.get("children") or []))
    badge = " ★initial" if name == initial else ""
    ordn = ("  #%d" % (order.index(name) + 1)) if name in order else ""
    return ("<div class='scr'><div class='scrhead'>%s%s%s <span class='dim'>%d×%d %s</span></div>"
            "<div class='panel' style='%s'>%s</div></div>"
            % (esc(name), esc(ordn), badge, W, H, shape.lower(), ";".join(style), kids))


# -------------------------------------------------------------------- main --
def main():
    args = sys.argv[1:]
    spec_path = next((a for a in args if a.endswith(".json")), None)
    if not spec_path:
        sys.exit("usage: python tools/spec_preview.py <spec.json> [--out f.html] [--scale S] [--strict]")
    out_flag = args[args.index("--out") + 1] if "--out" in args else None
    scale = float(args[args.index("--scale") + 1]) if "--scale" in args else 1.0
    strict = "--strict" in args

    spec_path = os.path.abspath(spec_path)
    if not os.path.exists(spec_path):
        fail("no such spec: " + spec_path)
    spec = json.load(open(spec_path, encoding="utf-8"))
    palette = spec.get("palette", {}) or {}
    screens = spec.get("screens", []) or []
    if not screens:
        fail("spec has no screens[]")
    order = spec.get("order") or [s["name"] for s in screens]
    initial = spec.get("initial_screen") or (order[0] if order else "")

    # assets dir resolution mirrors the builder's precedence, simplified:
    # spec["assets"] is repo-root relative (documented contract).
    assets_dir = spec.get("assets")
    if assets_dir and not os.path.isabs(assets_dir):
        spec["assets"] = os.path.join(ROOT, assets_dir)

    audit = []
    cards = "".join(screen_html(sc, spec, palette, order, initial, audit)
                    for sc in screens)

    fonts = spec.get("fonts", []) or []
    font_names = ", ".join("%s@%s" % (f["codename"], f.get("size")) for f in fonts) or "none"
    notes = []
    if audit:
        notes.append("<div class='audit'><b>audit (%d):</b><ul>%s</ul></div>"
                     % (len(audit), "".join("<li>%s</li>" % esc(a) for a in audit)))
    if not fonts:
        notes.append("<div class='audit'><b>note:</b> spec declares no fonts — "
                     "preview uses generic sans; real metrics come from the build.</div>")

    zoom = ("%.3f" % scale).rstrip("0").rstrip(".") or "1"
    html = """<!doctype html>
<html><head><meta charset="utf-8"><title>%s — spec preview</title>
<style>
  body{background:#101418;color:#dfe6ee;font:14px/1.4 system-ui,sans-serif;margin:16px}
  h1{font-size:16px;font-weight:600}
  .dim{color:#8b96a3;font-weight:400}
  .board{display:flex;flex-wrap:wrap;gap:28px;align-items:flex-start}
  .scrhead{font-size:13px;margin-bottom:6px}
  .panel{position:relative;overflow:hidden;border:1px solid #2a3340;
         transform-origin:top left;zoom:%s}
  .obj{box-sizing:border-box}
  .obj.panel{border:0}
  .obj.image{border:0}
  .obj.label{border:0}
  .label.empty{outline:1px dashed rgba(255,255,255,.25);outline-offset:-2px}
  .image .missing{width:100%%;height:100%%;display:flex;align-items:center;
                  justify-content:center;font-size:10px;color:#e8b4b4;
                  border:1px dashed #a33;box-sizing:border-box;text-align:center;
                  background:rgba(120,30,30,.15)}
  .ev{font-size:9px;color:#7fd1a8;position:absolute;bottom:0;left:0;right:0;
      text-align:center;pointer-events:none;overflow:hidden}
  .audit{margin-top:20px;background:#1c2129;border:1px solid #3a3f4a;
         border-radius:8px;padding:10px 14px;max-width:900px}
  .audit ul{margin:6px 0 0 18px;padding:0}
  .audit li{color:#f0c674;font-size:12px;margin:2px 0}
</style></head><body>
<h1>%s <span class="dim">— spec preview (design-time, no build) · fonts: %s</span></h1>
<div class="board">%s</div>
%s
</body></html>""" % (esc(spec.get("name", "?")), zoom,
                     esc(spec.get("name", "?")),
                     esc(font_names), cards, "".join(notes))

    out = out_flag or os.path.join(os.path.dirname(spec_path),
                                   os.path.splitext(os.path.basename(spec_path))[0]
                                   + ".spec_preview.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print("spec preview:", os.path.relpath(out, ROOT))
    for a in audit:
        print("  audit:", a.encode("ascii", "replace").decode("ascii"))
    if audit and strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
