#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Validate the generated SquareLine project.

Checks
  1. .spj parses; every object has guid / properties / saved_objtypeKey
  2. every emitted `strtype` appears in an official example project
     (against the frozen tools/schema_snapshot.json — no local SquareLine
     install required; a local install is used only as an extra cross-check)
  3. nids are unique project-wide
  4. CHANGE SCREEN targets resolve to a real screen
  5. every IMAGE/Asset exists on disk
  6. every Text_Font refers to a declared font codename
  7. font artefacts (.c/.bin/.fcfg) are complete
  8. event graph: handler shape, action schemas, and every object/screen
     reference inside an action resolves to a real guid
  9. PLAY ANIMATION names resolve; animations are well formed
 10. an object that carries a CLICKED event is actually Clickable
Run: python tools/validate_squareline_project.py
"""

import glob
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, "tools", "schema_snapshot.json")
# Only consulted when explicitly set — a local install is a *bonus* cross-check,
# never a prerequisite.  (Reading it by default is what made check 2 degrade to
# a silent WARN inside containers.)
SQUARELINE_DIR = os.environ.get("SQUARELINE_STUDIO")
EXAMPLES = os.path.join(SQUARELINE_DIR, "examples") if SQUARELINE_DIR else None
# Drop .spj files here to extend the legal-strtype set without a Studio install.
EXTRA_REFERENCE_DIR = os.path.join(ROOT, "tools", "extra_reference")


def load_reference_strtypes():
    """Returns (known:set, sources:list[str], fatal:str|None).

    Sources, in priority order:
      1. tools/schema_snapshot.json        — shipped, always available
      2. tools/extra_reference/*.spj       — user drop-in
      3. $SQUARELINE_STUDIO/examples/**    — cross-check when a Studio is present
    """
    known, sources, fatal = set(), [], None

    if os.path.exists(SNAPSHOT):
        try:
            snap = json.load(open(SNAPSHOT, encoding="utf-8"))
            known |= set(snap.get("strtypes", {}))
            sources.append("%s (%d strtypes, editor %s)"
                           % (os.path.relpath(SNAPSHOT, ROOT),
                              len(snap.get("strtypes", {})),
                              snap.get("editor_version", "?")))
        except Exception as e:
            fatal = "schema_snapshot.json is unreadable: %s" % e
    else:
        fatal = ("tools/schema_snapshot.json is missing — check 2 would be blind. "
                 "Regenerate with: python tools/sq_catalog.py")

    extra = sorted(glob.glob(os.path.join(EXTRA_REFERENCE_DIR, "*.spj")))
    if extra:
        n = len(known)
        known |= collect_strtypes(extra)
        sources.append("tools/extra_reference (%d file(s), +%d strtypes)"
                       % (len(extra), len(known) - n))

    if EXAMPLES and os.path.isdir(EXAMPLES):
        ref = (glob.glob(EXAMPLES + "/**/*.spj", recursive=True) +
               glob.glob(EXAMPLES + "/**/*.ecomp", recursive=True))
        n = len(known)
        known |= collect_strtypes(ref)
        sources.append("$SQUARELINE_STUDIO/examples (%d file(s), +%d strtypes)"
                       % (len(ref), len(known) - n))
    return known, sources, fatal


def resolve_project():
    """argv[1] = squareline/<name> dir or .spj file; default: first *.spj
    under <root>/squareline.  Returns (dir, spj_path)."""
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        p = sys.argv[1]
        if p.endswith(".spj"):
            return os.path.dirname(p), p
        cand = sorted(glob.glob(os.path.join(p, "*.spj")))
        if cand:
            return p, cand[0]
        sys.exit("no .spj in " + p)
    base = os.path.join(ROOT, "squareline")
    cand = sorted(glob.glob(os.path.join(base, "*", "*.spj")))
    if not cand:
        sys.exit("no .spj under " + base + " — pass one: python tools/validate_squareline_project.py squareline/<name>")
    if len(cand) > 1:
        print("multiple projects, using:", cand[0], "(pass one explicitly for another)")
    return os.path.dirname(cand[0]), cand[0]

REF_ACTION_FIELDS = {
    "CHANGE SCREEN": {"Screen_to", "Fade_mode", "Speed", "Delay"},
    "MODIFY FLAG": {"Object", "Flag", "Action"},
    "MODIFY STATE": {"Object", "State", "Action"},
    "SET OPACITY": {"Target", "Value"},
    "PLAY ANIMATION": {"FunctionName", "Animation", "Target", "Delay"},
    "CALL FUNCTION": {"Function_name", "Dont_export_function"},
}
EVENT_KINDS = {"CLICKED", "SCREEN_LOAD_START", "SCREEN_LOADED",
               "SCREEN_UNLOAD_START", "SCREEN_UNLOADED", "PRESSED", "RELEASED",
               "PRESS_LOST", "VALUE_CHANGED", "GESTURE_RIGHT(GESTURE)",
               "GESTURE_LEFT(GESTURE)", "GESTURE_UP(GESTURE)",
               "GESTURE_DOWN(GESTURE)", "CHECKED(VALUE_CHANGED)",
               "UNCHECKED(VALUE_CHANGED)"}
FUNC_OK = {"anim_callback_set_opacity", "anim_callback_get_opacity",
           "anim_callback_set_x", "anim_callback_get_x",
           "anim_callback_set_y", "anim_callback_get_y",
           "anim_callback_set_width", "anim_callback_get_width",
           "anim_callback_set_height", "anim_callback_get_height",
           "anim_callback_set_image_angle", "anim_callback_get_image_angle",
           "anim_callback_set_image_zoom", "anim_callback_get_image_zoom",
           "anim_callback_set_image_frame", "anim_callback_get_image_frame"}
PATH_INT = {"linear": 0, "ease_in": 1, "ease_out": 2, "overshoot": 4}

# strtypes the editor writes on save but shipped examples predate.  Evidence:
# the editor's own backup zip of this project contains 296 State_trickle and
# zero Clickable:True, matching the builder's minimised serialisation.
SAVED_FORM_ONLY = {"OBJECT/State_trickle"}


def collect_strtypes(paths):
    seen = set()

    def walk(o):
        if isinstance(o, dict):
            if "strtype" in o:
                seen.add(o["strtype"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for f in paths:
        try:
            walk(json.load(open(f, encoding="utf-8")))
        except Exception:
            pass
    return seen


def main():
    OUT, spj_path = resolve_project()
    known, sources, snapshot_fatal = load_reference_strtypes()
    print("reference strtypes:", len(known),
          "" if known else "(none — check 2 is disabled)")
    for s in sources:
        print("  from:", s)

    spj = json.load(open(spj_path, encoding="utf-8"))
    print("parsed:", spj_path)

    problems = []
    warns = []
    if snapshot_fatal:
        problems.append(snapshot_fatal)
    used = set()
    screens = {}          # guid -> name
    objects = {}          # guid -> (screen, name)
    clickable = {}        # guid -> bool
    nids = []
    handlers = []
    actions = []
    anim_names = {a["properties"][1]["strval"]: a for a in spj.get("animations", [])}

    def obj_name(props):
        return next((p["strval"] for p in props
                     if p.get("strtype") == "OBJECT/Name"), "?")

    def walk(o, screen=None, path="/"):
        if isinstance(o, dict):
            if "strtype" in o:
                used.add(o["strtype"])
            if "nid" in o:
                nids.append(o["nid"])
            if o.get("strtype") == "_event/EventHandler":
                handlers.append((o, screen, path))
            if o.get("strtype") == "_event/action":
                actions.append((o, screen, path))
            if "saved_objtypeKey" in o:
                if "properties" not in o:
                    problems.append("object without properties: " + path)
                props = o.get("properties") or []
                nm = obj_name(props)
                key = o["guid"]
                objects[key] = (screen, nm)
                # Clickability: official examples write Clickable:False only and
                # imply True from event handlers; the editor's current save form
                # replaces the flag with OBJECT/State_trickle on event-less
                # objects (see builder obj_base docstring + backup zip evidence).
                clickable[key] = (any(
                    p.get("strtype") == "OBJECT/Clickable"
                    and p.get("strval") == "True" for p in props) or any(
                    p.get("strtype") == "OBJECT/State_trickle"
                    and p.get("strval") == "True" for p in props) or any(
                    p.get("strtype") == "_event/EventHandler" for p in props))
                if o.get("saved_objtypeKey") == "SCREEN":
                    screens[key] = nm
                    screen = nm
            for k, v in o.items():
                walk(v, screen, path + k + "/")
        elif isinstance(o, list):
            for v in o:
                walk(v, screen, path)

    walk(spj)

    # panel geometry lives in spj["info"] (width/height/shape); the .sll is
    # just a copy.  NOTE: spj root SCREEN nodes do NOT carry OBJECT/Size —
    # never try to read the panel size from them (learned the hard way).
    info = spj.get("info", {})
    # Never *default* the panel size: a wrong default silently weakens every
    # geometry check downstream (it once made a 240x240 project validate as
    # 410x502).  Missing size is a hard error, not a guess.
    if not info.get("width") or not info.get("height"):
        problems.append("spj['info'] has no width/height — panel geometry is "
                        "authoritative there, not on the SCREEN nodes")
        screen_size = [info.get("width") or 0, info.get("height") or 0]
    else:
        screen_size = [info["width"], info["height"]]
    print("screen size:", "x".join(map(str, screen_size)),
          "| shape:", info.get("shape", "RECT"))

    if known:
        unknown = sorted(t for t in used
                         if t not in known and t not in SAVED_FORM_ONLY)
        if unknown:
            problems.append("strtypes not found in official examples: %s" % unknown)
    else:
        problems.append("no reference strtype set available — check 2 cannot run "
                        "(regenerate tools/schema_snapshot.json)")

    dup_nid = {n for n, c in Counter(nids).items() if c > 1}
    print("nids:", len(nids), "unique:", len(set(nids)), "duplicates:", len(dup_nid))
    if dup_nid:
        problems.append("duplicate nid(s): %s" % sorted(dup_nid)[:10])

    print("screens (%d): %s" % (len(screens), sorted(screens.values())))

    # ---- event handlers -------------------------------------------------
    print("objects:", len(objects), "| event handlers:", len(handlers),
          "| actions:", len(actions))
    for h, scr, path in handlers:
        kind = h.get("strval")
        if kind not in EVENT_KINDS:
            problems.append("unknown event kind %r at %s" % (kind, path))
        kids = h.get("childs") or []
        kinds = [c.get("strtype") for c in kids if isinstance(c, dict)]
        for need in ("_custom/name", "_custom/condition_C", "_custom/condition_P"):
            if need not in kinds:
                problems.append("handler %r missing %s (%s)" % (kind, need, path))
        acts = [c for c in kids if isinstance(c, dict)
                and c.get("strtype") == "_event/action"]
        if not acts:
            problems.append("handler %r has no action (%s)" % (kind, path))
        if kind == "CLICKED" and not any(
                h.get("nid") == a.get("nid") for a in []):
            pass

    # ---- actions --------------------------------------------------------
    for a, scr, path in actions:
        kind = a.get("strval")
        if kind not in REF_ACTION_FIELDS:
            problems.append("unknown action %r at %s" % (kind, path))
            continue
        fields = {}
        for c in a.get("childs") or []:
            t = c.get("strtype", "")
            if t.startswith(kind + "/"):
                fields[t.split("/", 1)[1]] = c
        missing = {"Name", "Call", "CallC"} | REF_ACTION_FIELDS[kind]
        for need in sorted(missing - set(fields)):
            problems.append("%s missing field %s (%s)" % (kind, need, path))
        for key in ("Object", "Target"):
            if key in fields:
                ref = fields[key].get("strval")
                if ref not in objects and ref not in screens:
                    problems.append("%s/%s -> unknown guid %s (%s)"
                                    % (kind, key, ref, path))
        if kind == "PLAY ANIMATION":
            fn = (fields.get("FunctionName") or {}).get("strval")
            if fn not in anim_names:
                problems.append("PLAY ANIMATION -> undeclared animation %r (%s)"
                                % (fn, path))
            tgt = (fields.get("Target") or {}).get("strval")
            anim = anim_names.get(fn)
            if anim:
                probe = (anim["properties"][5] or {}).get("strval")
                if probe and probe not in objects:
                    problems.append("animation %r TestTarget -> unknown guid %s"
                                    % (fn, probe))
        if kind == "CHANGE SCREEN":
            ref = (fields.get("Screen_to") or {}).get("strval")
            if ref not in screens:
                problems.append("CHANGE SCREEN -> unknown screen guid %s (%s)"
                                % (ref, path))
            if (fields.get("Fade_mode") or {}).get("strval") != "FADE_ON":
                warns.append("non-FADE_ON transition at %s" % path)

    # a CLICKED handler must sit on a clickable object
    def find_owner(node, target_nid):
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, list) and any(
                    isinstance(p, dict) and p.get("nid") == target_nid for p in props):
                return node.get("guid")
            for v in node.values():
                r = find_owner(v, target_nid)
                if r:
                    return r
        elif isinstance(node, list):
            for v in node:
                r = find_owner(v, target_nid)
                if r:
                    return r
        return None

    for h, scr, path in handlers:
        if h.get("strval") != "CLICKED":
            continue
        owner = find_owner(spj, h.get("nid"))
        if owner is None:
            problems.append("CLICKED handler with no owner object (%s)" % path)
        elif not clickable.get(owner, False):
            problems.append("CLICKED handler on non-clickable object %s (%s)"
                            % (objects.get(owner), path))

    # ---- animations -----------------------------------------------------
    print("animations:", len(anim_names))
    for name, a in anim_names.items():
        pas = a.get("propertyAnimations") or []
        if not pas:
            problems.append("animation %r has no property animation" % name)
        for pa in pas:
            props = {p.get("strtype"): p for p in pa.get("properties") or []}
            setter = (props.get("PROPERTYANIMATION/PropertyFunction") or {}).get("strval")
            getter = (props.get("PROPERTYANIMATION/PropertyGetter") or {}).get("strval")
            if setter not in FUNC_OK:
                problems.append("animation %r unknown setter %r" % (name, setter))
            if getter not in FUNC_OK:
                problems.append("animation %r unknown getter %r" % (name, getter))
            pname = (props.get("PROPERTYANIMATION/Path") or {}).get("strval")
            if PATH_INT.get(pname) != pa.get("Path"):
                problems.append("animation %r path int/name mismatch (%s/%s)"
                                % (name, pa.get("Path"), pname))
            if not pa.get("KeyFrames"):
                problems.append("animation %r track without keyframes" % name)

    # ---- assets ---------------------------------------------------------
    assets, fonts = [], []

    def collect(o):
        if isinstance(o, dict):
            if o.get("strtype") == "IMAGE/Asset":
                assets.append(o.get("strval"))
            if o.get("strtype") == "_style/Text_Font":
                fonts.append(o.get("strval"))
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)

    collect(spj)
    missing = sorted({a for a in assets
                      if not os.path.exists(os.path.join(OUT, a.replace("/", os.sep)))})
    print("image refs:", len(set(assets)), "| missing on disk:", missing)
    if missing:
        problems.append("missing image files: %s" % missing)

    declared = set()
    for f in glob.glob(os.path.join(OUT, "assets", "fonts", "*.fcfg")):
        declared.add(json.load(open(f, encoding="utf-8"))["codename"])
        base = f[:-5]
        for ext in (".c", ".bin"):
            if not os.path.exists(base + ext):
                problems.append("font artefact missing: %s%s" % (base, ext))
    undeclared = sorted({f for f in fonts if f not in declared})
    print("declared fonts:", sorted(declared))
    print("font refs:", sorted(set(fonts)), "| undeclared:", undeclared)
    if undeclared:
        problems.append("undeclared fonts: %s" % undeclared)

    # ---- guids ----------------------------------------------------------
    guids = []
    collect_g = []

    def collect_guid(o):
        if isinstance(o, dict):
            if "guid" in o:
                collect_g.append(o["guid"])
            for v in o.values():
                collect_guid(v)
        elif isinstance(o, list):
            for v in o:
                collect_guid(v)

    collect_guid(spj)
    dg = {g for g, c in Counter(collect_g).items() if c > 1}
    print("guids:", len(collect_g), "unique:", len(set(collect_g)))
    if dg:
        problems.append("duplicate guids: %s" % sorted(dg)[:5])

    # ---- draw order / occlusion ----------------------------------------
    # a LABEL covered by a later, opaque sibling will not be readable on device
    def rects(node, parent, z, acc, force_show=(), force_hide=()):
        props = node.get("properties") or []
        nm = obj_name(props)
        kind = node.get("saved_objtypeKey")
        if kind is None:
            return
        if nm in force_hide:
            return
        if get(props, "OBJECT/Hidden") == "True" and nm not in force_show:
            return
        ox, oy = get(props, "OBJECT/Position", "intarray", [0, 0]) or [0, 0]
        w, h = get(props, "OBJECT/Size", "intarray", [1, 1]) or [1, 1]
        px, py, pw, ph = parent
        x = int(round(px + pw / 2.0 + ox - w / 2.0))
        y = int(round(py + ph / 2.0 + oy - h / 2.0))
        acc.append((z, nm, kind, x, y, w, h, props))
        for i, c in enumerate(node.get("children", []) or []):
            rects(c, (x, y, w, h), z + [i], acc, force_show, force_hide)

    def get(props, strtype, key="strval", default=None):
        for p in props:
            if p.get("strtype") == strtype:
                return p.get(key, default)
        return default

    def opaque(props):
        for p in props:
            if isinstance(p, dict) and p.get("part") == "lv.PART.MAIN":
                for s in p.get("childs", []):
                    for sp in s.get("childs", []):
                        if sp.get("strtype") == "_style/Bg_Color":
                            ia = sp.get("intarray") or [0, 0, 0, 0]
                            return len(ia) < 4 or ia[3] > 200
        return False

    def overlap(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ow = max(0, min(ax + aw, bx + bw) - max(ax, bx))
        oh = max(0, min(ay + ah, by + bh) - max(ay, by))
        return ow * oh

    occluded = 0
    for sc in spj["root"]["children"]:
        nm = obj_name(sc["properties"])
        acc = []
        for i, c in enumerate(sc.get("children", [])):
            rects(c, (0, 0, screen_size[0], screen_size[1]), [i], acc)
        for z, name, kind, x, y, w, h, props in acc:
            if kind != "LABEL":
                continue
            area = w * h
            for z2, name2, kind2, x2, y2, w2, h2, props2 in acc:
                if z2 <= z or name2 == name:
                    continue
                if kind2 not in ("PANEL", "CONTAINER", "IMAGE"):
                    continue
                hit = overlap((x, y, w, h), (x2, y2, w2, h2))
                if hit < area * 0.35:
                    continue
                if kind2 == "IMAGE" or opaque(props2):
                    occluded += 1
                    warns.append("%s: 文字 %r 被后绘制的 %s(%s) 遮挡 ~%d%%"
                                 % (nm, get(props, "LABEL/Text"), kind2,
                                    name2, int(100.0 * hit / area)))
                    break
    print("occlusion suspects:", occluded)

    # ---- 生成代码语法检查 ----------------------------------------------
    # SquareLine 会把 LABEL/Text 原样拼进 `set_text("…")`（导出 C 是
    # lv_label_set_text，内置模拟器是 Micropython）。文本里的**真实换行 / 裸双引号 /
    # 裸反斜杠**会截断字符串字面量 → 模拟器 SyntaxError → 报 "LVGL crashed"。
    # 这里按同样的方式拼一遍并交给 Python 编译，把这个坑变成自动可检。
    gen_texts = []

    def collect_texts(o, screen=None):
        if isinstance(o, dict) and "properties" in o:
            nm = obj_name(o["properties"])
            for p in o["properties"]:
                if p.get("strtype", "").endswith("/Text"):
                    gen_texts.append((screen, nm, p.get("strval") or ""))
        if isinstance(o, dict):
            for c in o.get("children", []):
                collect_texts(c, screen)

    for sc in spj["root"].get("children", []):
        collect_texts(sc, obj_name(sc.get("properties", [])))

    for screen, nm, v in gen_texts:
        if any(ch in v for ch in "\n\r\""):
            problems.append("文本含未转义的换行/引号，会截断生成代码: %s/%s -> %r"
                            % (screen, nm, v[:36]))
    gen_src = "\n".join('ui_%d.set_text("%s")' % (i, v)
                        for i, (_s, _n, v) in enumerate(gen_texts))
    try:
        compile(gen_src, "<generated>", "exec")
        print("generated code: syntax OK (%d set_text lines)" % len(gen_texts))
    except SyntaxError as e:
        problems.append("生成代码语法错误 line %s: %s (text=%r)"
                        % (e.lineno, e.msg, (e.text or "")[:60]))

    print()
    for w in warns:
        print("WARN -", w)
    if problems:
        print("!! PROBLEMS")
        for p in problems:
            print("  -", p)
        return 1
    print("OK - project validated, no problems found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
