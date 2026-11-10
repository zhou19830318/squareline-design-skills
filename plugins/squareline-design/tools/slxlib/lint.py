# -*- coding: utf-8 -*-
"""Pre-build lint for a squareline spec.  Everything the .spj validator cannot know (it checks
file shape) and everything the builder reports only as a Python traceback.

run(proj_dir, spec, toolkit_root) -> list[Finding]
Each Finding has a stable code (see catalog.py) so `slx.py explain <code>` can expand it.
"""
import math
import os
import re
from collections import defaultdict, deque

from .catalog import CATALOG

EVENT_OK = {"CLICKED", "PRESSED", "RELEASED", "PRESS_LOST", "VALUE_CHANGED", "SCREEN_LOAD_START", "SCREEN_LOADED",
            "SCREEN_UNLOAD_START", "SCREEN_UNLOADED", "GESTURE_LEFT", "GESTURE_RIGHT", "GESTURE_UP", "GESTURE_DOWN",
            "CHECKED", "UNCHECKED"}
ACTION_OK = {"CHANGE_SCREEN", "SHOW", "HIDE", "SET_OPACITY", "PLAY_ANIMATION", "CALL_FUNCTION"}
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FLAT = re.compile(r"^assets/[^/\\]+\.(png|PNG)$")


class Finding(object):
    def __init__(self, level, code, where, msg, hint=None):
        self.level, self.code, self.where, self.msg = level, code, where, msg
        self.hint = hint or (CATALOG.get(code, ("", "", ""))[2])

    def line(self):
        s = "%-5s %-14s %s: %s" % (self.level, self.code, self.where, self.msg)
        if self.hint:
            s += "\n      fix: " + self.hint
        return s

    def as_dict(self):
        return {"level": self.level, "code": self.code, "where": self.where, "message": self.msg, "fix": self.hint}


def walk(children, depth=0):
    for o in children or []:
        yield o
        for c in walk(o.get("children"), depth + 1):
            yield c


def parse_ranges(rs):
    """["0x20-0x7E", "0x00B0"] -> set of code points."""
    out = set()
    for r in rs or []:
        try:
            a, _, b = str(r).partition("-")
            lo = int(a, 16)
            hi = int(b, 16) if b else lo
            out.update(range(lo, hi + 1))
        except ValueError:
            pass
    return out


def _png_size(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def run(proj, spec, tk_root):
    F = []
    add = lambda level, code, where, msg, hint=None: F.append(Finding(level, code, where, msg, hint))

    # ---------------------------------------------------------------- header
    for k in ("name", "width", "height", "shape", "palette", "fonts", "screens"):
        if k not in spec:
            add("ERROR", "E-SPEC-KEY", "spec", "missing top-level key %r" % k)
    if F:
        return F
    W, H = int(spec["width"]), int(spec["height"])
    shape = str(spec["shape"]).upper()
    if shape not in ("RECT", "CIRCLE") or (shape == "CIRCLE" and W != H):
        add("ERROR", "E-SHAPE", "spec", "shape=%s width=%s height=%s" % (shape, W, H))
    round_ = shape == "CIRCLE"
    R = W / 2.0
    palette = spec.get("palette") or {}
    if spec.get("assets"):
        add("WARN", "W-ASSETS-KEY", "spec", "spec has an \"assets\" key; slx passes --assets, which overrides it",
            "Remove it so the spec is not tied to one machine's path.")

    # ----------------------------------------------------------------- fonts
    fonts = {}
    symbols = spec.get("symbols") or {}
    for f in spec["fonts"]:
        cn = f.get("codename")
        if cn in fonts:
            add("ERROR", "E-FONT-DUP", "fonts", "codename %r declared twice" % cn)
        fonts[cn] = f
        ttf = f.get("ttf", "")
        if not (os.path.exists(os.path.join(tk_root, "fonts", ttf)) or os.path.exists(os.path.join(proj, "assets", "fonts", ttf))):
            add("ERROR", "E-FONT-TTF", "fonts/%s" % cn, "ttf %r not found in toolkit fonts/ or <project>/assets/fonts/" % ttf)
        kind = f.get("kind", "text")
        if kind != "text" and kind not in symbols:
            add("ERROR", "E-FONT-KIND", "fonts/%s" % cn, "kind %r has no entry in spec.symbols" % kind)
        if int(f.get("size", 0)) < 14:
            add("WARN", "W-FONT-MIN", "fonts/%s" % cn, "size %s px" % f.get("size"))
    fsz = {k: int(v.get("size", 16)) for k, v in fonts.items()}

    # --------------------------------------------------------------- screens
    names = [s.get("name") for s in spec["screens"]]
    seen = set()
    for n in names:
        if n in seen:
            add("ERROR", "E-SCREEN-DUP", "screens", "screen %r declared twice" % n)
        seen.add(n)
        if not isinstance(n, str) or not IDENT.match(n):
            add("ERROR", "E-OBJ-NAME", "screen %r" % n, "not a valid identifier")
    start = spec.get("initial_screen") or (names[0] if names else None)
    if start not in names:
        add("ERROR", "E-INITIAL", "spec", "initial_screen %r is not a screen" % start)
    order = spec.get("order") or []
    if not order and len(names) > 3:
        add("WARN", "W-ORDER-RING", "spec", "no `order`: all %d screens are chained into one swipe ring" % len(names))

    # ------------------------------------------------------- objects & refs
    obj_by_screen = {s["name"]: {} for s in spec["screens"]}
    for sc in spec["screens"]:
        for o in walk(sc["children"]):
            nm = o.get("name")
            if nm in obj_by_screen[sc["name"]]:
                add("ERROR", "E-OBJ-DUP", "%s/%s" % (sc["name"], nm), "object name used twice in this screen")
            obj_by_screen[sc["name"]][nm] = o
            if not isinstance(nm, str) or not IDENT.match(nm):
                add("ERROR", "E-OBJ-NAME", "%s/%s" % (sc["name"], nm), "not a valid identifier")
    anim_names = {a.get("name") for a in spec.get("animations") or []}
    event_names = defaultdict(list)

    def colour_ok(v):
        if v is None:
            return True
        if isinstance(v, (list, tuple)):
            return len(v) in (3, 4)
        return v in palette or bool(HEX.match(str(v)))

    def check_colour(v, where):
        if not colour_ok(v):
            add("ERROR", "E-COLOR", where, "%r is neither a palette key nor #rrggbb[aa]" % (v,))

    def resolve(ref, scr):
        if isinstance(ref, dict):
            return obj_by_screen.get(ref.get("screen", scr), {}).get(ref.get("name"))
        if "/" in str(ref):
            s_, o_ = str(ref).split("/", 1)
            return obj_by_screen.get(s_, {}).get(o_)
        return obj_by_screen.get(scr, {}).get(ref)

    def check_events(evs, scr, where):
        for e in evs or []:
            on = e.get("on")
            if on not in EVENT_OK:
                add("ERROR", "E-EVENT-KIND", where, "event %r is not in the verified set" % on)
            if e.get("name"):
                event_names[e["name"]].append(where)
            for a in e.get("actions", []):
                t = a.get("type")
                if t not in ACTION_OK:
                    add("ERROR", "E-ACT-TYPE", where, "action type %r" % t)
                elif t == "CHANGE_SCREEN" and a.get("target") not in names:
                    add("ERROR", "E-ACT-SCREEN", where, "target %r is not a screen" % a.get("target"))
                elif t in ("SHOW", "HIDE", "SET_OPACITY", "PLAY_ANIMATION") and not resolve(a.get("object"), scr):
                    add("ERROR", "E-ACT-OBJ", where, "object %r not found" % (a.get("object"),))
                if t == "PLAY_ANIMATION" and a.get("animation") not in anim_names:
                    add("ERROR", "E-ANIM-REF", where, "animation %r not declared" % a.get("animation"))

    img_dir = os.path.join(proj, "assets", "images")
    on_disk = set(os.listdir(img_dir)) if os.path.isdir(img_dir) else set()
    used_imgs = set()
    for sc in spec["screens"]:
        sn = sc["name"]
        check_colour(sc.get("bg"), "%s (screen bg)" % sn)
        check_events(spec.get("screen_events", {}).get(sn), sn, "%s (screen event)" % sn)
        for o in walk(sc["children"]):
            where = "%s/%s" % (sn, o.get("name"))
            r = o.get("rect")
            if not (isinstance(r, (list, tuple)) and len(r) == 4 and all(isinstance(v, (int, float)) for v in r) and r[2] > 0 and r[3] > 0):
                add("ERROR", "E-OBJ-RECT", where, "rect=%r" % (r,))
                continue
            x, y, w, h = r
            if x < 0 or y < 0 or x + w > W or y + h > H:
                add("ERROR", "E-RECT-CANVAS", where, "rect %s outside the %dx%d canvas" % (list(r), W, H))
            for key in ("color", "bg", "indicator", "track"):
                check_colour(o.get(key), "%s.%s" % (where, key))
            check_events(o.get("events"), sn, where)
            t = o.get("type")
            if t == "LABEL":
                fnt = o.get("font")
                if fnt not in fonts:
                    add("ERROR", "E-FONT-REF", where, "font %r not declared" % fnt)
                else:
                    if h <= fsz[fnt]:
                        add("ERROR", "E-LABEL-H", where, "h=%s <= font size %s: line height is always > size, the text WILL be clipped" % (h, fsz[fnt]))
                    elif h < -(-fsz[fnt] * 131 // 100):
                        add("WARN", "W-LABEL-H", where, "h=%s may be below the line height of a %s px font (measured ratios 1.17-1.31); the build's `lineheight:` line is authoritative" % (h, fsz[fnt]),
                            "Use h >= ceil(size * 1.35) to be safe.")
                    kind = fonts[fnt].get("kind", "text")
                    if kind != "text" and kind in symbols:
                        allowed = set(ord(c) for c in symbols[kind]) | parse_ranges(spec.get("ranges_num"))
                        bad = sorted({c for c in str(o.get("text", "")) if ord(c) not in allowed})
                        if bad:
                            add("ERROR", "E-GLYPH", where, "text %r has %s outside symbols[%r] + ranges_num" % (o.get("text"), bad, kind))
            elif t == "IMAGE":
                a = o.get("asset", "")
                if not FLAT.match(a):
                    add("ERROR", "E-IMG-PATH", where, "asset %r" % a)
                base = os.path.basename(a)
                used_imgs.add(base)
                if base not in on_disk:
                    add("ERROR", "E-IMG-MISSING", where, "%s not in <project>/assets/images/" % base)
                else:
                    sz = _png_size(os.path.join(img_dir, base))
                    if sz and (sz[0] != int(w) or sz[1] != int(h)):
                        add("WARN", "W-IMG-SIZE", where, "PNG is %dx%d but rect is %dx%d" % (sz[0], sz[1], w, h))
            # touch target
            if any(e.get("on") == "CLICKED" for e in (o.get("events") or [])) and min(w, h) < 36:
                add("WARN", "W-TAP", where, "clickable object is %dx%d" % (w, h))
    for nm, where in event_names.items():
        if len(where) > 1:
            add("ERROR", "E-EVENT-DUP", where[0], "event name %r used %d times" % (nm, len(where)))
    for a in spec.get("animations") or []:
        if not resolve(a.get("target"), start or ""):
            add("ERROR", "E-ANIM-TARGET", "animation %s" % a.get("name"), "target %r not found" % a.get("target"))
    for orphan in sorted(on_disk - used_imgs):
        if orphan.lower().endswith(".png"):
            add("WARN", "W-IMG-ORPHAN", "assets/images/%s" % orphan, "not used by any screen")

    # ----------------------------------------------------------- round layout
    def ink(o):
        size = fsz.get(o.get("font"), 16)
        wd = sum(size if ord(c) > 0x2E80 else 0.58 * size for c in str(o.get("text", "")))
        x, _, bw, _ = o["rect"]
        al = str(o.get("align", "LEFT")).upper()
        if al == "CENTER":
            return x + bw / 2.0 - wd / 2, x + bw / 2.0 + wd / 2
        if al == "RIGHT":
            return x + bw - wd, x + bw
        return x, x + wd

    def extent(o):
        x, y, w, h = o["rect"]
        cy_ = H / 2.0
        if o["type"] == "LABEL":
            a, b = ink(o)
            return max(math.hypot(px - R, py - cy_) for px, py in [(a, y + 3), (b, y + 3), (a, y + h - 3), (b, y + h - 3)])
        if o["type"] == "ARC":
            return math.hypot(x + w / 2.0 - R, y + h / 2.0 - cy_) + w / 2.0
        rad = min(int(o.get("radius", 0)) if o["type"] == "PANEL" else 0, int(w) // 2, int(h) // 2)
        if rad:
            return max(math.hypot(cx - R, cy - cy_) + rad for cx in (x + rad, x + w - rad) for cy in (y + rad, y + h - rad))
        return max(math.hypot(px - R, py - cy_) for px in (x, x + w) for py in (y, y + h))

    if round_:
        for sc in spec["screens"]:
            for o in walk(sc["children"]):
                r = o.get("rect")
                if not (isinstance(r, (list, tuple)) and len(r) == 4) or o.get("hidden") or (r[2], r[3]) == (W, H):
                    continue
                if r[0] < 0 or r[1] < 0 or r[0] + r[2] > W or r[1] + r[3] > H:
                    continue                      # already reported as E-RECT-CANVAS
                e = extent(o)
                where = "%s/%s" % (sc["name"], o.get("name"))
                if e > R + 4:
                    add("ERROR", "E-CIRCLE", where, "painted extent %.0f > r=%.0f" % (e, R))
                elif e > R:
                    add("WARN", "W-CIRCLE-CLIP", where, "corner clipped by ~%.0f px" % (e - R))
                elif e > R - 5:
                    add("WARN", "W-CIRCLE-TIGHT", where, "within 5 px of the rim (%.0f / %.0f)" % (e, R))

    # -------------------------------------------------------------- navigation
    g = defaultdict(set)
    for sc in spec["screens"]:
        evs = [e for o in walk(sc["children"]) for e in (o.get("events") or [])]
        evs += (spec.get("screen_events") or {}).get(sc["name"], []) or []
        for e in evs:
            for a in e.get("actions", []):
                if a.get("type") == "CHANGE_SCREEN" and a.get("target") in names:
                    g[sc["name"]].add(a["target"])
    ring = order or names
    for i, n in enumerate(ring):
        if n not in names:
            continue
        if i > 0 and ring[i - 1] in names:
            g[n].add(ring[i - 1])
        if i < len(ring) - 1 and ring[i + 1] in names:
            g[n].add(ring[i + 1])
    rev = defaultdict(set)
    for u, vs in g.items():
        for v in vs:
            rev[v].add(u)

    def reach(src, gr):
        seen_, q = {src}, deque([src])
        while q:
            for v in gr[q.popleft()]:
                if v not in seen_:
                    seen_.add(v)
                    q.append(v)
        return seen_
    if start in names:
        fwd, back = reach(start, g), reach(start, rev)
        for n in names:
            if n not in fwd:
                add("WARN", "W-NAV-UNREACH", n, "cannot be reached from %r by touch" % start)
            if n not in back:
                add("ERROR", "E-NAV-DEAD", n, "has no way back to %r" % start)

    # -------------------------------------------------------------------- docs
    for d in spec.get("spec_docs") or []:
        p = os.path.join(proj, d)
        if not os.path.exists(p):
            add("WARN", "W-DOC-MISSING", d, "not found next to the project")
        else:
            head = open(p, encoding="utf-8", errors="ignore").read(1500)
            if "模板" in head.split("\n", 1)[0] or head.count("<...>") + head.count("`<") > 3:
                add("WARN", "W-DOC-TEMPLATE", d, "still looks like the template")
    return F
