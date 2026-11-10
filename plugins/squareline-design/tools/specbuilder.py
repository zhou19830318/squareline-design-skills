# -*- coding: utf-8 -*-
"""specbuilder - write a squareline spec in Python instead of raw JSON.

Why: in two real projects every hand-written coordinate was a chance for a bug (a chip label with x < 0,
text placed by line-box centre so numerals sat 10 px high, duplicated event names ...).  This library
makes the common widgets one call each, places TEXT BY WHERE ITS INK SHOULD BE (using the real LVGL
font metrics), and records navigation so `slx.py check` can audit it.

    import sys; sys.path.insert(0, "<plugin>/tools")
    from specbuilder import Project
    P = Project("Demo", 360, 360, "CIRCLE", palette={...}, fonts=[...])
    P.screen("home", children=[P.label("clock", 180, 150, 220, "10:42", "Big60"),
                               P.image("face", [0, 0, 360, 360], "face_idle", events=[P.go("menu")])],
             gestures={"GESTURE_LEFT": "menu"})
    P.write("Demo.spec.json")

All rects are screen-absolute.  Labels: `cx, cy` = centre of the INK (not of the line box).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)


class Project(object):
    def __init__(self, name, width, height, shape, palette, fonts, symbols=None, ranges_text=None, ranges_num=None,
                 spec_docs=None, node="node", toolkit=ROOT, touch_feedback=None):
        self.name, self.w, self.h, self.shape = name, width, height, shape.upper()
        self.palette, self.fonts = dict(palette), list(fonts)
        self.symbols = symbols if symbols is not None else {"number": "0123456789:"}
        self.ranges_text = ranges_text or ["0x20-0x7E", "0x00B0", "0x2026"]
        self.ranges_num = ranges_num or ["0x30-0x3A"]
        self.spec_docs = spec_docs if spec_docs is not None else ["%s设计规格文档.md" % name]
        self.node, self.toolkit = node, toolkit
        self.touch_feedback = touch_feedback        # e.g. 170: every clickable object dims to opacity 170 while pressed
        self.screens, self.nav, self.anims, self.screen_events = [], [], [], {}
        self.intent = {}            # "screen/object" -> {"ink_cy": y, "text": ...}  (written next to the spec for `slx.py truth`)
        self.fsize = {f["codename"]: int(f["size"]) for f in self.fonts}
        self.fttf = {f["codename"]: f["ttf"] for f in self.fonts}
        self.fkind = {f["codename"]: f.get("kind", "text") for f in self.fonts}
        self._fm = {}

    # ------------------------------------------------------------------ fonts
    def metrics(self, font):
        if font not in self._fm:
            from slxlib import deps
            deps.ensure()
            from slxlib.fontfit import font_metrics
            restricted = self.symbols.get(self.fkind[font], "") if self.fkind[font] != "text" else None
            rng = ",".join(self.ranges_num) if restricted is not None else "0x20-0x7E,0x00B0"
            self._fm[font] = font_metrics(self.toolkit, self.fttf[font], self.fsize[font], self.node, rng, restricted)
        return self._fm[font]

    def lh(self, font):
        """Safe LABEL height: >= the real line height and >= ceil(size*1.35)."""
        return max(-(-self.fsize[font] * 135 // 100), self.metrics(font).lh)

    # ---------------------------------------------------------- primitives
    def label(self, name, cx, cy, w, text, font, color="WHITE", align="CENTER", x=None, ink=True):
        """cy = vertical centre of the INK (ink=True) or of the line box (ink=False).
        x given -> explicit left edge (use for LEFT/RIGHT aligned text); otherwise centred on cx."""
        h = self.lh(font)
        if ink:
            m = self.metrics(font)
            top = cy - (m.baseline - m.ink_center_up(text))
            self._pending_intent = {"ink_cy": round(float(cy), 1), "text": text}
        else:
            top = cy - h / 2.0
        left = x if x is not None else round(cx - w / 2.0)
        o = {"type": "LABEL", "name": name, "rect": [int(left), int(round(top)), int(w), int(h)],
             "text": text, "font": font, "color": color, "align": align}
        if ink:
            o["_intent"] = self._pending_intent       # stripped again in to_spec()
        return o

    @staticmethod
    def image(name, rect, asset, events=None, hidden=False):
        o = {"type": "IMAGE", "name": name, "rect": list(rect), "asset": "assets/%s.png" % asset}
        if events:
            o["events"] = events
        if hidden:
            o["hidden"] = True
        return o

    @staticmethod
    def panel(name, rect, bg, radius=0, events=None, hidden=False, children=None):
        o = {"type": "PANEL", "name": name, "rect": list(rect), "bg": bg, "radius": radius}
        if events:
            o["events"] = events
        if hidden:
            o["hidden"] = True
        if children:
            o["children"] = children
        return o

    @staticmethod
    def arc(name, rect, value, indicator, track, width, max_=100, angles=(270, 269)):
        """Progress ring.  angles=(270,269) starts at 12 o'clock (LVGL's default is 3 o'clock)."""
        return {"type": "ARC", "name": name, "rect": list(rect), "value": value, "max": max_,
                "indicator": indicator, "track": track, "width": width, "angles": list(angles)}

    # ------------------------------------------------------------ events
    @staticmethod
    def go(target, on="CLICKED"):
        return {"on": on, "name": None, "actions": [{"type": "CHANGE_SCREEN", "target": target}]}

    @staticmethod
    def acts(on, *a):
        return {"on": on, "name": None, "actions": list(a)}

    @staticmethod
    def show(o):
        return {"type": "SHOW", "object": o}

    @staticmethod
    def hide(o):
        return {"type": "HIDE", "object": o}

    @staticmethod
    def play(anim, obj):
        return {"type": "PLAY_ANIMATION", "animation": anim, "object": obj}

    # ----------------------------------------------------------- composites
    def title(self, text, cy=40, font="Title22"):
        return self.label("title", 180, cy, 160, text, font, "WHITE")

    def pill(self, icon, text, color_font="WHITE", rect=(95, 298, 170, 34), bg="PILL", font="Small16"):
        """Translucent prompt pill with a leading icon (error/warning text over a face)."""
        x, y, w, h = rect
        return self.panel("tip", list(rect), bg, h // 2, children=[
            self.image("tip_icon", [x + 14, y + (h - 16) // 2, 16, 16], icon),
            self.label("tip_text", 0, y + h / 2.0, w - 50, text, font, color_font, "CENTER", x=x + 35)])

    def bars(self, heights, cx=180, cy=322, w=6, gap=5, color="WAVE"):
        n = len(heights)
        x0 = cx - (n * w + (n - 1) * gap) // 2
        return [self.panel("wave_%d" % (i + 1), [x0 + i * (w + gap), cy - h // 2, w, h], color, w // 2) for i, h in enumerate(heights)]

    def dots(self, cy=40, d=12, color="CYAN", xs=(150, 180, 210)):
        return [self.panel("dot_%d" % (i + 1), [cx - d // 2, cy - d // 2, d, d], color, d // 2) for i, cx in enumerate(xs)]

    def chevron_link(self, name, rect, text, target, font="Small16", icon="icon_chevron_right", bg="CARD2"):
        x, y, w, h = rect
        return self.panel(name, list(rect), bg, h // 2, [self.go(target)], children=[
            self.label("%s_t" % name, 0, y + h / 2.0, w - 44, text, font, "WHITE", "CENTER", x=x + 14),
            self.image("%s_i" % name, [x + w - 28, y + h // 2 - 8, 16, 16], icon)])

    def chip_group(self, prefix, label_text, label_cy, opts, default, chip_w, gap, chip_y, chip_h=34, x0=None,
                   off="CARD2", on="BLUE2", font="Small16"):
        """Radio chips.  Draw order matters: OFF plates (clickable) -> ON plates (only the default visible)
        -> texts on top, so a text is never covered by its own selected plate."""
        n = len(opts)
        total = n * chip_w + (n - 1) * gap
        left = x0 if x0 is not None else 180 - total // 2
        objs = [self.label("%s_lbl" % prefix, 0, label_cy, 200, label_text, font, "DIM", "LEFT", x=left + 4)]
        names_on = ["%s_%d_on" % (prefix, i) for i in range(n)]
        xs = [left + i * (chip_w + gap) for i in range(n)]
        for i in range(n):
            others = [self.hide(names_on[j]) for j in range(n) if j != i]
            objs.append(self.panel("%s_%d_off" % (prefix, i), [xs[i], chip_y, chip_w, chip_h], off, chip_h // 2,
                                   [self.acts("CLICKED", self.show(names_on[i]), *others)]))
        for i in range(n):
            objs.append(self.panel(names_on[i], [xs[i], chip_y, chip_w, chip_h], on, chip_h // 2, hidden=(i != default)))
        for i, text in enumerate(opts):
            objs.append(self.label("%s_%d_t" % (prefix, i), xs[i] + chip_w // 2, chip_y + chip_h / 2.0, chip_w, text, font, "WHITE"))
        return objs

    def switch(self, prefix, cx, cy, on=True, w=52, h=28, off_bg="CARD2", on_bg="BLUE2", knob="WHITE"):
        x, y, k = cx - w // 2, cy - h // 2, h - 6
        return [self.panel("%s_off" % prefix, [x, y, w, h], off_bg, h // 2,
                           [self.acts("CLICKED", self.show("%s_on" % prefix), self.show("%s_knob_on" % prefix))]),
                self.panel("%s_knob_off" % prefix, [x + 3, y + 3, k, k], knob, k // 2),
                self.panel("%s_on" % prefix, [x, y, w, h], on_bg, h // 2,
                           [self.acts("CLICKED", self.hide("%s_on" % prefix), self.hide("%s_knob_on" % prefix))], hidden=not on),
                self.panel("%s_knob_on" % prefix, [x + w - k - 3, y + 3, k, k], knob, k // 2, hidden=not on)]

    def slider(self, prefix, x, y, w, pct, h=8, track="TRACK", fill="CYAN", knob="WHITE"):
        f = round(w * pct / 100.0)
        return [self.panel("%s_track" % prefix, [x, y, w, h], track, h // 2),
                self.panel("%s_fill" % prefix, [x, y, f, h], fill, h // 2),
                self.panel("%s_knob" % prefix, [x + f - 9, y - 5, 18, 18], knob, 9)]

    def toggle_tile(self, prefix, cx, cy, icon, label_text, on=True, d=76, off_bg="CARD2", on_bg="BLUE2", label_font="Small16"):
        x, y = cx - d // 2, cy - d // 2
        return [self.panel("%s_off" % prefix, [x, y, d, d], off_bg, d // 2, [self.acts("CLICKED", self.show("%s_on" % prefix))]),
                self.panel("%s_on" % prefix, [x, y, d, d], on_bg, d // 2, [self.acts("CLICKED", self.hide("%s_on" % prefix))], hidden=not on),
                self.image("%s_ic" % prefix, [cx - 15, cy - 15, 30, 30], icon),
                self.label("%s_lbl" % prefix, cx, cy + d / 2.0 + 16, 80, label_text, label_font, "WHITE")]

    def link_tile(self, prefix, cx, cy, icon, label_text, target, d=76, bg="CARD2", label_font="Small16"):
        return [self.panel("%s_btn" % prefix, [cx - d // 2, cy - d // 2, d, d], bg, d // 2, [self.go(target)]),
                self.image("%s_ic" % prefix, [cx - 15, cy - 15, 30, 30], icon),
                self.label("%s_lbl" % prefix, cx, cy + d / 2.0 + 16, 80, label_text, label_font, "WHITE")]

    # -------------------------------------------------------------- screens
    def screen(self, name, children, kind="aux", desc="", face=None, events=None, gestures=None, bg=None):
        """gestures={"GESTURE_LEFT": "target", ...} is shorthand for screen events."""
        evs = list(events or [])
        for on, tgt in (gestures or {}).items():
            evs.append(self.go(tgt, on))
        self.screens.append({"name": name, "bg": bg or "BG", "children": children})
        self.nav.append({"name": name, "kind": kind, "desc": desc, "face": face})
        if evs:
            self.screen_events.setdefault(name, []).extend(evs)

    def animation(self, name, target, prop, frames, duration, loop=True, path="ease_out"):
        self.anims.append({"name": name, "target": target, "duration": duration, "path": path, "loop_infinite": loop,
                           "tracks": [{"property": prop, "frames": frames, "duration": duration}]})

    def on_load(self, screen, *actions):
        self.screen_events.setdefault(screen, []).append(self.acts("SCREEN_LOAD_START", *actions))

    def _add_touch_feedback(self):
        """PRESSED -> SET_OPACITY(value), RELEASED -> SET_OPACITY(255) on every object that has a CLICKED event
        (both events are in the editor-verified set).  Requirement 'every touch gets immediate visual feedback'."""
        if not self.touch_feedback:
            return

        def walk(ch):
            for o in ch:
                evs = o.get("events") or []
                if any(e["on"] == "CLICKED" for e in evs) and not any(e["on"] == "PRESSED" for e in evs):
                    evs += [self.acts("PRESSED", {"type": "SET_OPACITY", "object": o["name"], "value": int(self.touch_feedback)}),
                            self.acts("RELEASED", {"type": "SET_OPACITY", "object": o["name"], "value": 255})]
                    o["events"] = evs
                walk(o.get("children", []) or [])
        for s in self.screens:
            walk(s["children"])

    def _unique_event_names(self):
        def fix(scr, o):
            for e in o.get("events", []) or []:
                e["name"] = "%s_%s_%s" % (scr, o["name"], e["on"].lower())
            for c in o.get("children", []) or []:
                fix(scr, c)
        for s in self.screens:
            for c in s["children"]:
                fix(s["name"], c)
        for scr, evs in self.screen_events.items():
            seen = {}
            for e in evs:
                k = "%s_scr_%s" % (scr, e["on"].lower())
                seen[k] = seen.get(k, 0) + 1
                e["name"] = k if seen[k] == 1 else "%s_%d" % (k, seen[k])

    def _collect_intent(self):
        def walk(scr, ch):
            for o in ch:
                it = o.pop("_intent", None)
                if it:
                    self.intent["%s/%s" % (scr, o["name"])] = it
                walk(scr, o.get("children", []) or [])
        for s in self.screens:
            walk(s["name"], s["children"])

    def to_spec(self, order=None, initial=None, description=None):
        self._add_touch_feedback()
        self._unique_event_names()
        self._collect_intent()
        return {"$schema": "squareline-spec/1", "name": self.name, "width": self.w, "height": self.h, "shape": self.shape,
                "description": description or "%s - %dx%d %s" % (self.name, self.w, self.h, self.shape.lower()),
                "assets_subdir": "images", "spec_docs": self.spec_docs, "theme_dark": True,
                "palette": self.palette, "fonts": self.fonts, "ranges_text": self.ranges_text, "ranges_num": self.ranges_num,
                "symbols": self.symbols, "screens": self.screens,
                "order": order if order is not None else [self.screens[0]["name"]],
                "initial_screen": initial or self.screens[0]["name"],
                "animations": self.anims, "screen_events": self.screen_events}

    def write(self, path, **kw):
        spec = self.to_spec(**kw)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(spec, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        with open(os.path.splitext(os.path.splitext(path)[0])[0] + ".layout.intent.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.intent, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        return spec
