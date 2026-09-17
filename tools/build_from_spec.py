#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a SquareLine project from a **declarative screen spec** (JSON).

Why
---
Historically "add a project" meant "copy the nearest builder and edit ~450 lines
of Python screen definitions".  That made every new panel a code review, and it
made "given input -> expected output" regression testing impossible: there was no
input, only code.

This is the other half of the fix (the first half is the engine/content split in
tools/engine/).  A spec is data; the compiler is engine-only code; `tools/engine/`
is never touched to add a screen.

    spec JSON  ->  build_from_spec.py  ->  tools/engine/  ->  .spj

Scope: this covers the *regular* case well - panels, labels, images, arcs, a
swipe ring, and the five built-in actions.  Bespoke geometry (radial icon rings,
chord-width math, pre-baked clock hands) still belongs in a screens/<x>.py module;
tools/screens/aiwatch_apple.py is the worked example of that.  The boundary is
deliberate: the spec must stay small enough to read in one go.

Usage
-----
    python tools/build_from_spec.py tools/spec/specwidget.json
    python tools/build_from_spec.py tools/spec/specwidget.json --assets <dir> --out <dir>
    python tools/build_from_spec.py --example          # print a commented skeleton

Spec reference
--------------
Top level: name, width, height, shape (RECT|RECTANGLE|CIRCLE), description,
lvgl_version, assets_subdir, spec_docs[], palette{}, fonts[], ranges_text[],
ranges_num[], symbols{}, skip, screens[], order[], initial_screen, animations[].

  assets_subdir: which *source* asset pack to read from
      (<assets root>/<assets_subdir>).  It ONLY chooses the inputs.
      It is NEVER written into a reference: an IMAGE always records the flat
      path `assets/<file>`, never `assets/<assets_subdir>/<file>`.  Writing the
      subdir into `asset` makes every image report `missing` (the project then
      points at a file it does not have).  Default: "images".

screen: name, bg, children[]
child:  type (PANEL|LABEL|IMAGE|ARC), name, rect [x,y,w,h] (screen-absolute,
        top-left), hidden, children[] (PANEL only), events[]
  PANEL  : bg, radius, clickable
  LABEL  : text, font, color, align (LEFT|CENTER|RIGHT)
           height must be >= the font's line_height or CJK is clipped; that
           value is only known after a build, so use
           tools/LABEL_SIZING.md (or layout.label_sized) for the spec-time
           estimate and read the `lineheight:` build line for the truth.
  IMAGE  : asset (FLAT path relative to the project dir — `assets/img_x.png`,
           NOT `assets/<assets_subdir>/img_x.png`), rotation
  ARC    : value, max, indicator, track, width, angles [from, to]

colours are a palette key, a "#rrggbb"/"#rrggbbaa" string, or [r,g,b,a].
event:  on (CLICKED|PRESSED|RELEASED|SCREEN_LOAD_START|SCREEN_LOADED|
        SCREEN_UNLOAD_START|SCREEN_UNLOADED|GESTURE_LEFT|GESTURE_RIGHT|
        GESTURE_UP|GESTURE_DOWN), actions[]
action: CHANGE_SCREEN{target}, HIDE{object}, SHOW{object},
        SET_OPACITY{object,value}, PLAY_ANIMATION{animation,object}
        object = "name" (same screen) | "screen/name" | {"screen":..,"name":..}
animation: name, target (object ref), tracks[{property, frames[[value,ms]..],
        duration}], duration, path (linear|ease_in|ease_out|overshoot),
        loop_infinite
"""

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from engine.squareline_engine import *          # noqa: F401,F403
from engine import squareline_engine as _E      # noqa: F401

SPEC_VERSION = "squareline-spec/1"

TYPE_FACTORY = {}
GESTURES = {"GESTURE_LEFT": "GESTURE_LEFT(GESTURE)",
            "GESTURE_RIGHT": "GESTURE_RIGHT(GESTURE)",
            "GESTURE_UP": "GESTURE_UP(GESTURE)",
            "GESTURE_DOWN": "GESTURE_DOWN(GESTURE)"}
ALIGN = {"LEFT": "LEFT", "CENTER": "CENTER", "RIGHT": "RIGHT"}


# ---------------------------------------------------------------- helpers --
def fail(msg):
    raise SystemExit("spec error: " + msg)


def parse_colour(v, palette, where):
    if v is None:
        return list(CLEAR)
    if isinstance(v, (list, tuple)):
        if len(v) == 3:
            return [v[0], v[1], v[2], 255]
        if len(v) == 4:
            return list(v)
        fail("%s: colour array needs 3 or 4 components, got %r" % (where, v))
    if not isinstance(v, str):
        fail("%s: colour must be a name, hex string or array, got %r" % (where, v))
    if v in palette:
        return parse_colour(palette[v], {}, where)
    s = v.strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 6:
            return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255]
        if len(h) == 8:
            return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)]
        fail("%s: hex colour must be #rrggbb or #rrggbbaa, got %r" % (where, v))
    fail("%s: unknown colour %r (not in palette %s)"
         % (where, v, sorted(palette) or "[]"))


def rect_of(obj, where):
    r = obj.get("rect")
    if not r or len(r) != 4:
        fail("%s: needs \"rect\": [x, y, w, h] (screen-absolute, top-left)" % where)
    return [int(v) for v in r]


def obj_ref(spec_screen, v, where):
    """'name' | 'screen/name' | {'screen':..,'name':..} -> engine placeholder."""
    if isinstance(v, dict):
        if not v.get("screen") or not v.get("name"):
            fail("%s: object ref needs screen+name, got %r" % (where, v))
        return O(v["screen"], v["name"])
    if not isinstance(v, str):
        fail("%s: object ref must be a string or object, got %r" % (where, v))
    if "/" in v:
        s, n = v.split("/", 1)
        return O(s, n)
    return O(spec_screen, v)


def compile_actions(spec, screen, acts, palette, where):
    out = []
    for a in acts or []:
        kind = (a.get("type") or "").upper()
        if kind == "CHANGE_SCREEN":
            t = a.get("target")
            if not t:
                fail("%s: CHANGE_SCREEN needs \"target\"" % where)
            out.append(act_change(S(t), int(a.get("speed", 150))))
        elif kind == "HIDE":
            out.append(hide(obj_ref(screen, a.get("object"), where)))
        elif kind == "SHOW":
            out.append(show(obj_ref(screen, a.get("object"), where)))
        elif kind == "SET_OPACITY":
            out.append(act_opa(obj_ref(screen, a.get("object"), where),
                               int(a.get("value", 255))))
        elif kind == "PLAY_ANIMATION":
            nm = a.get("animation")
            if nm not in ANIM_INDEX:
                fail("%s: PLAY_ANIMATION -> undeclared animation %r "
                     "(declare it in \"animations\")" % (where, nm))
            ref = a.get("object")
            out.append(act_anim(nm, obj_ref(screen, ref, where) if ref else ""))
        else:
            fail("%s: unknown action %r (CHANGE_SCREEN|HIDE|SHOW|SET_OPACITY|"
                 "PLAY_ANIMATION)" % (where, kind))
    return out


def compile_events(spec, screen, events, palette, where):
    out = []
    for e in events or []:
        kind = (e.get("on") or "CLICKED").upper()
        kind = GESTURES.get(kind, kind)
        name = e.get("name") or ("%s_%s" % (screen, kind.split("(")[0].lower()))
        acts = compile_actions(spec, screen, e.get("actions"), palette,
                               "%s/event %s" % (where, kind))
        out.append(ev(kind, name, acts))
    return out


# ------------------------------------------------------------ object kinds --
def mk_panel(spec, screen, o, palette, where):
    x, y, w, h = rect_of(o, where)
    kids = [compile_child(spec, screen, c, palette, where) for c in o.get("children") or []]
    return mk_container(o["name"], x, y, w, h,
                        bg=parse_colour(o.get("bg"), palette, where + "/bg"),
                        radius=int(o.get("radius", 0)),
                        events=compile_events(spec, screen, o.get("events"), palette, where),
                        hidden=bool(o.get("hidden")),
                        children=kids or None)


def mk_label_of(spec, screen, o, palette, where):
    x, y, w, h = rect_of(o, where)
    if not o.get("font"):
        fail("%s: LABEL needs \"font\" (a codename from the top-level fonts[])" % where)
    align = ALIGN.get(str(o.get("align", "LEFT")).upper())
    if align is None:
        fail("%s: align must be LEFT|CENTER|RIGHT" % where)
    return mk_label(o["name"], x, y, w, h, str(o.get("text", "")), o["font"],
                    color=parse_colour(o.get("color"), palette, where + "/color"),
                    align=align,
                    events=compile_events(spec, screen, o.get("events"), palette, where),
                    hidden=bool(o.get("hidden")))


def mk_image_of(spec, screen, o, palette, where):
    x, y, w, h = rect_of(o, where)
    if not o.get("asset"):
        fail("%s: IMAGE needs \"asset\" (path relative to the project dir, "
             "e.g. assets/img_x.png)" % where)
    asset = str(o["asset"])
    # Catch the single most common spec mistake at author time.  `assets_subdir`
    # selects the input pack only; it never belongs in the emitted reference, so
    # `assets/<subdir>/x.png` names a file the project will not have and every
    # image comes back "missing" (seen as "39 images, all missing").
    sub = spec.get("assets_subdir", "images")
    if sub and asset.replace("\\", "/").startswith("assets/%s/" % sub):
        fail("%s: IMAGE \"asset\" must be the FLAT path assets/<file>, got %r.\n"
             "         \"assets_subdir\": %r only picks the SOURCE pack and is "
             "never written into a reference —\n"
             "         write \"asset\": \"assets/%s\" instead."
             % (where, asset, sub, asset.replace("\\", "/").split("/", 2)[-1]))
    return mk_image(o["name"], x, y, w, h, asset,
                    events=compile_events(spec, screen, o.get("events"), palette, where),
                    hidden=bool(o.get("hidden")),
                    rotation=int(o.get("rotation", 0)))


def mk_arc_of(spec, screen, o, palette, where):
    x, y, w, h = rect_of(o, where)
    if w != h:
        fail("%s: ARC must be square (w == h), got %dx%d" % (where, w, h))
    ang = o.get("angles", [0, 360])
    if len(ang) != 2:
        fail("%s: angles must be [from, to]" % where)
    return mk_arc(o["name"], x, y, w,
                  int(o.get("value", 0)), int(o.get("max", 100)),
                  parse_colour(o.get("indicator"), palette, where + "/indicator"),
                  parse_colour(o.get("track"), palette, where + "/track"),
                  int(o.get("width", 10)),
                  bg_angles=(int(ang[0]), int(ang[1])))


TYPE_FACTORY.update({"PANEL": mk_panel, "CONTAINER": mk_panel,
                     "LABEL": mk_label_of, "IMAGE": mk_image_of, "ARC": mk_arc_of})


def compile_child(spec, screen, o, palette, where):
    t = (o.get("type") or "").upper()
    if t not in TYPE_FACTORY:
        fail("%s: unknown type %r (PANEL|LABEL|IMAGE|ARC)" % (where, t))
    if not o.get("name"):
        fail("%s: every object needs a unique \"name\"" % where)
    return TYPE_FACTORY[t](spec, screen, o, palette, "%s/%s" % (where, o["name"]))


# ------------------------------------------------------------------ build --
class SpecProject(object):
    """Compiles a spec dict into the callables the engine expects."""

    def __init__(self, spec, path="<inline>"):
        self.spec = spec
        self.path = path
        v = spec.get("$schema")
        if v and v != SPEC_VERSION:
            fail("%s: unknown $schema %r (expected %r)" % (path, v, SPEC_VERSION))
        for need in ("name", "width", "height", "screens"):
            if not spec.get(need):
                fail("%s: missing required key %r" % (path, need))
        self.palette = spec.get("palette", {}) or {}
        # Screen names must be known *before* the engine's configure() runs, so
        # derive them straight from the spec here rather than waiting for
        # build_screens() (which runs later, inside build_project).  self.names is
        # kept as the runtime-populated list build_screens() fills (duplicate
        # detection + screen_events ordering); screen_names is the eager view.
        self.screen_names = [sc.get("name") for sc in spec["screens"]]
        self.names = []

    def build_animations(self):
        for a in self.spec.get("animations", []) or []:
            where = "animations/%s" % a.get("name")
            if not a.get("name") or not a.get("target"):
                fail("%s: needs name + target" % where)
            target = obj_ref("", a["target"], where)
            tracks = []
            for t in a.get("tracks", []) or []:
                if not t.get("property") or not t.get("frames"):
                    fail("%s: each track needs property + frames" % where)
                tracks.append((t["property"],
                               [(int(f[0]), int(f[1])) for f in t["frames"]],
                               int(t.get("duration", a.get("duration", 300)))))
            add_anim(a["name"], target, tracks,
                     duration=int(a.get("duration", 300)),
                     path=a.get("path", "ease_out"),
                     loop_infinite=bool(a.get("loop_infinite", False)))

    def build_screens(self):
        out = {}
        for sc in self.spec["screens"]:
            name = sc.get("name")
            if not name:
                fail("screens[]: every screen needs a \"name\"")
            if name in out:
                fail("duplicate screen name %r" % name)
            where = "screen %s" % name
            self.names.append(name)
            kids = [compile_child(self.spec, name, c, self.palette, where)
                    for c in sc.get("children") or []]
            out[name] = {
                "bg": parse_colour(sc.get("bg"), self.palette, where + "/bg"),
                "children": kids,
            }
        return out

    def screen_events(self, name, props):
        """The swipe ring, driven by the spec's `order`."""
        order = self.spec.get("order") or self.screen_names
        if name in order:
            pos = order.index(name)
            if pos > 0:
                props.append(ev("GESTURE_RIGHT(GESTURE)", "scr_prev",
                                [act_change(S(order[pos - 1]))]))
            if pos < len(order) - 1:
                props.append(ev("GESTURE_LEFT(GESTURE)", "scr_next",
                                [act_change(S(order[pos + 1]))]))
        for e in (self.spec.get("screen_events", {}) or {}).get(name, []) or []:
            props.extend(compile_events(self.spec, name, [e], self.palette,
                                        "screen_events/%s" % name))

    def descriptor(self):
        s = self.spec
        return {
            "name": s["name"],
            "width": int(s["width"]),
            "height": int(s["height"]),
            "shape": s.get("shape", "RECT"),
            "description": s.get("description", s["name"]),
            "lvgl_version": s.get("lvgl_version", "9.2.2"),
            "theme_dark": s.get("theme_dark", True),
            "assets_subdir": s.get("assets_subdir", "images"),
            # Optional: let the spec carry its own asset pack (repo-root relative)
            # so `build_from_spec.py <spec>` alone reproduces the project.
            "assets": s.get("assets"),
            "spec_docs": tuple(s.get("spec_docs", ())),
            "fonts": [(f["codename"], f["ttf"], int(f["size"]), f.get("kind", "text"))
                      for f in s.get("fonts", []) or []],
            "ranges_text": s.get("ranges_text", ["0x20-0x7E", "0x00B0"]),
            "ranges_num": s.get("ranges_num", ["0x20-0x7E", "0x00B0"]),
            "symbols": s.get("symbols", {"text": ""}),
            "skip": set(s.get("skip", "")),
            "screens": self.screen_names,
            "order": s.get("order") or self.screen_names,
            "initial_screen": s.get("initial_screen") or (
                self.screen_names[0] if self.screen_names else ""),
            "build_screens": self.build_screens,
            "build_animations": self.build_animations,
            "screen_events": self.screen_events,
        }


EXAMPLE = """{
  "$schema": "squareline-spec/1",
  "name": "SpecWidget",
  "width": 320, "height": 320, "shape": "RECT",
  "description": "declarative-spec demo",
  "assets_subdir": "images",
  "spec_docs": ["SpecWidget设计规格文档.md"],
  "palette": {
    "BG":    [8, 14, 26, 255],
    "CARD":  [20, 20, 22, 255],
    "TRACK": [38, 38, 42, 255],
    "WHITE": [255, 255, 255, 255],
    "BLUE":  "#0A84FF",
    "GREEN": "#30D158"
  },
  "fonts": [
    {"codename": "Title20", "ttf": "noto-sans-sc-v40-chinese-simplified-500.ttf",
     "size": 20, "kind": "text"}
  ],
  "symbols": {"time": "0123456789:", "number": "0123456789:.%", "text": ""},
  "screens": [
    {"name": "home", "bg": "BG", "children": [
      {"type": "LABEL", "name": "clock", "rect": [60, 28, 200, 34],
       "text": "10:09", "font": "Title20", "color": "WHITE", "align": "CENTER"},
      {"type": "ARC", "name": "ring", "rect": [80, 96, 160, 160],
       "value": 68, "max": 100, "indicator": "GREEN", "track": "TRACK", "width": 12}
    ]},
    {"name": "settings", "bg": "BG", "children": [
      {"type": "PANEL", "name": "card", "rect": [16, 40, 288, 120],
       "bg": "CARD", "radius": 14, "children": [
         {"type": "LABEL", "name": "title", "rect": [32, 60, 256, 28],
          "text": "设置", "font": "Title20", "color": "WHITE", "align": "LEFT"}
       ],
       "events": [{"on": "CLICKED", "actions": [
         {"type": "CHANGE_SCREEN", "target": "home"}]}]}
    ]}
  ],
  "order": ["home", "settings"],
  "initial_screen": "home"
}
"""


def main():
    args = sys.argv[1:]
    if "--example" in args:
        print(EXAMPLE)
        return 0
    specs = [a for a in args if not a.startswith("-") and a.endswith(".json")]
    if not specs:
        sys.exit("usage: python tools/build_from_spec.py <spec.json> "
                 "[--assets <dir>] [--out <dir>]    (--example prints a skeleton)")
    path = specs[0]
    if not os.path.exists(path):
        sys.exit("no such spec: " + path)
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    print("spec      :", path)
    proj = SpecProject(spec, path)
    return build(proj.descriptor())


if __name__ == "__main__":
    sys.exit(main())
