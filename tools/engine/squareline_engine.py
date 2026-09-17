#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""squareline_engine - the content-independent half of the .spj builders.

Why this file exists
--------------------
`build_squareline_apple.py` and `build_squareline_project.py` were two
self-contained ~1500-line scripts.  They shared 46 functions and 40 of those
were *byte-identical* - the property plumbing, the coordinate rebaser, the event
and animation serialisation, the font subsetting, the glyph/metric verifier.
Only `build_screens()` plus its palette differed.  That is the classic "engine
welded to content" shape: every new panel meant editing another copy of the
engine, and an engine bug had to be found and fixed twice.

Layout now:

    tools/engine/squareline_engine.py   <- this file. No project content.
    tools/screens/<project>.py          <- palette + FONTS + build_screens() + PROJECT descriptor
    tools/spec/<project>.json           <- declarative alternative, see tools/build_from_spec.py

Adding a project must never require editing this directory.

Usage from a screen module
--------------------------
    from engine.squareline_engine import *      # noqa: F401,F403
    ...                                          # palette, FONTS, build_screens()
    PROJECT = {...}                              # descriptor, see configure()
    ENGINE_BUILD(PROJECT)

State
-----
The engine keeps module-level state (nid / guid counters, the animation list,
the object-guid table) because the builders author ~200 objects with plain
function calls.  `configure()` resets all of it, so one process can build several
projects back to back - the eval suite does exactly that.
"""

import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys

# this file lives in tools/engine/, so the package root is three levels up
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# lv_font_conv is the only thing that needs Node.  Resolve it the boring way:
# PATH first, SQUARELINE_NODE_BIN only if node lives somewhere unusual (same
# convention as SQUARELINE_STUDIO / SQUARELINE_ASSETS).
NODE = os.environ.get("SQUARELINE_NODE_BIN") or "node"
LFC = os.path.join(ROOT, "tools", "node_modules", "lv_font_conv", "lv_font_conv.js")

# --------------------------------------------------------------------------
# project descriptor
# --------------------------------------------------------------------------
# Everything a project has to supply.  Set by configure(); the defaults are the
# engine-side placeholders so that `from ... import *` never explodes.
PROJECT = {}
PROJECT_NAME = ""
SW, SH = 0, 0                     # panel size in design px (2 px ~= 1 dp)
SHAPE = "RECT"                    # RECT | CIRCLE
DESCRIPTION = ""
LVGL_VERSION = "9.2.2"
THEME_DARK = True
THEME_COLOR1 = 5
THEME_COLOR2 = 0
SRC_IMAGES = ""
SRC_FONTS = ""
ASSETS_ROOT = ""
OUT = ""
OUT_ASSETS = ""
OUT_FONTS = ""
FONTS = []                        # [(codename, ttf, size, kind)]
RANGES_TEXT = ["0x20-0x7E"]         # NOT -0x7F: U+007F (DEL) exists in no TTF
RANGES_NUM = ["0x20-0x7E"]          # and merely produces a missing-glyph warning
SYMBOLS = {"text": ""}
SKIP = set()                      # codepoints to never request from a font
SPEC_DOCS = ()                    # spec markdown, for glyph headroom
ALL_SCREENS = []                  # every screen name, switch order
ORDER = []                        # screens wired to swipe-left / swipe-right
INITIAL_SCREEN = ""               # which screen the editor opens on

# generic colours the engine itself needs (project palettes live in screens/)
WHITE = [255, 255, 255, 255]
BLACK = [0, 0, 0, 255]
CLEAR = [0, 0, 0, 0]


def _flag(name, default=None):
    """Read `--name value` straight out of argv (no argparse, this module also
    runs as a library-ish script)."""
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def dump_json(path, obj, indent=2):
    """Write JSON with LF endings **on every host**.

    This is not cosmetic.  ``open(path, "w")`` translates every ``\\n`` to
    ``os.linesep``, so the same spec built on Windows produced CRLF project
    files while Linux produced LF.  The committed golden projects were built on
    Windows, so a Linux rebuild differed in *every* engine-written file
    (.spj/.sll/.slp/Themes.slt/project.info/*.fcfg) and the regression suite
    opened red on the exact platform the pipeline targets.  Pinning
    ``newline="\\n"`` makes the artifact bytes a function of the spec alone,
    which is also what git and the editor want.
    """
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=indent)


def configure(project):
    """Install a project descriptor and reset every bit of engine state."""
    global PROJECT, PROJECT_NAME, SW, SH, SHAPE, DESCRIPTION, LVGL_VERSION
    global THEME_DARK, THEME_COLOR1, THEME_COLOR2
    global SRC_IMAGES, SRC_FONTS, OUT, OUT_ASSETS, OUT_FONTS
    global FONTS, RANGES_TEXT, RANGES_NUM, SYMBOLS, SKIP, SPEC_DOCS
    global ALL_SCREENS, ORDER, INITIAL_SCREEN, ASSETS_ROOT

    PROJECT = dict(project)
    PROJECT_NAME = PROJECT["name"]
    SW, SH = PROJECT["width"], PROJECT["height"]
    SHAPE = PROJECT.get("shape", "RECT")
    DESCRIPTION = PROJECT.get("description", PROJECT_NAME)
    LVGL_VERSION = PROJECT.get("lvgl_version", "9.2.2")
    THEME_DARK = PROJECT.get("theme_dark", True)
    THEME_COLOR1 = PROJECT.get("theme_color1", 5)
    THEME_COLOR2 = PROJECT.get("theme_color2", 0)

    FONTS = PROJECT["fonts"]
    RANGES_TEXT = PROJECT.get("ranges_text", RANGES_TEXT)
    RANGES_NUM = PROJECT.get("ranges_num", RANGES_NUM)
    SYMBOLS = PROJECT.get("symbols", SYMBOLS)
    SKIP = PROJECT.get("skip", SKIP)
    SPEC_DOCS = tuple(PROJECT.get("spec_docs", ()))
    ALL_SCREENS = list(PROJECT["screens"])
    ORDER = list(PROJECT.get("order", ALL_SCREENS))
    INITIAL_SCREEN = PROJECT.get("initial_screen", ALL_SCREENS[0] if ALL_SCREENS else "")

    # Where the assets come from / where the project goes.  Precedence:
    #   --assets  >  $SQUARELINE_ASSETS  >  PROJECT["assets"]  >  <repo>/assets
    # `PROJECT["assets"]` lets an example carry its own asset pack, so the bare
    # command (`python tools/build_squareline_apple.py`) rebuilds the archived
    # project without the caller having to remember a flag.  Relative paths are
    # resolved against the repo root, not the cwd.
    ASSETS_ROOT = _flag("--assets") or os.environ.get("SQUARELINE_ASSETS") \
        or PROJECT.get("assets") or os.path.join(ROOT, "assets")
    if not os.path.isabs(ASSETS_ROOT):
        ASSETS_ROOT = os.path.join(ROOT, ASSETS_ROOT)
    SRC_IMAGES = PROJECT.get("src_images") or os.path.join(
        ASSETS_ROOT, PROJECT.get("assets_subdir", "images"))
    # Source TTFs: prefer the project's own asset pack, fall back to the shared
    # fonts/ shipped at the repo root (that is what `cp fonts/*.ttf assets/fonts/`
    # in the README is about; a spec with no image assets needs no asset pack).
    _apack_fonts = os.path.join(ASSETS_ROOT, "fonts")
    SRC_FONTS = _apack_fonts if os.path.isdir(_apack_fonts) else os.path.join(ROOT, "fonts")
    out_root = _flag("--out") or os.environ.get("SQUARELINE_OUT") \
        or os.path.join(ROOT, "squareline", PROJECT_NAME)
    OUT = os.path.abspath(out_root)
    OUT_ASSETS = os.path.join(OUT, "assets")
    OUT_FONTS = os.path.join(OUT_ASSETS, "fonts")

    # reset mutable engine state
    _nid[0] = 0
    _guid[0] = 0
    _deepid[0] = 0
    del ANIMS[:]
    ANIM_INDEX.clear()
    OBJ_GUIDS.clear()
    return PROJECT


# --------------------------------------------------------------------------
# spec doc -> font glyph headroom
# --------------------------------------------------------------------------
def _find_spec_docs():
    """Locate the design spec / resource manifest, the source of the font glyph
    *headroom*.

    SKILL.md's rule is "collect the charset from the SPEC DOC so future copy
    edits stay covered".  It used to look only at the repo root, where the docs
    do not actually live (they sit next to the mockup, in examples/<Name>/), so
    headroom silently came out empty and every font shipped with barely enough
    glyphs.  Search the real places, honour --spec / SQUARELINE_SPEC, and let the
    caller shout when nothing is found.
    """
    found = []
    explicit = _flag("--spec") or os.environ.get("SQUARELINE_SPEC")
    if explicit:
        found.append(explicit)
    # The spec doc sits next to the mockup, one level above the asset pack:
    #   examples/AIWatchApple/AIWatchApple设计规格文档.md
    #   examples/AIWatchApple/assets/images_apple/*.png
    base_dirs = []
    for d in (os.path.dirname(ASSETS_ROOT), ASSETS_ROOT, OUT, ROOT):
        if d and d not in base_dirs:
            base_dirs.append(d)
    for doc in SPEC_DOCS:
        for d in base_dirs:
            p = os.path.join(d, doc)
            if os.path.exists(p):
                found.append(os.path.abspath(p))
                break
    if not found and SPEC_DOCS:
        import glob as _glob
        for doc in SPEC_DOCS:
            hits = sorted(_glob.glob(os.path.join(ROOT, "**", doc), recursive=True))
            if hits:
                found.append(hits[0])
    return found


def doc_charset():
    """Headroom: every char used by the spec docs, so later text edits render."""
    docs = _find_spec_docs()
    if not docs:
        print("WARN      : spec doc(s) %s not found - fonts get NO glyph headroom "
              "(pass --spec <file> or set SQUARELINE_SPEC)" % (SPEC_DOCS,))
        return set()
    chars = set()
    for p in docs:
        print("spec doc  :", p)
        with open(p, encoding="utf-8") as fh:
            for ch in fh.read():
                if ch in "\n\r\t " or ch in SKIP:
                    continue
                chars.add(ch)
    print("headroom  : %d chars from %d spec doc(s)" % (len(chars), len(docs)))
    return chars


# --------------------------------------------------------------------------
# .spj property plumbing
# --------------------------------------------------------------------------
_nid = [0]


def nid():
    """One monotonic counter: official projects keep property nids unique per
    property, so never reuse a constant across objects."""
    _nid[0] += 1
    return _nid[0]


ev_nid = nid


def p_str(n, strtype, value, inh=10):
    return {"nid": nid(), "strtype": strtype, "strval": value, "InheritedType": inh}


def p_int(n, strtype, value, inh=6):
    """整数属性节点。

    SquareLine 的序列化器在值为 0 时**省略 `integer` 键、但保留属性节点本身**
    （实测：74 个 `IMAGE/Rotation` 里 73 个只有 strtype+InheritedType，只有
    1800° 那个带 integer）。照抄这个约定，否则每次导出都会与编辑器保存后的
    形态差上百个节点。
    """
    d = {"nid": nid(), "strtype": strtype}
    if value:
        d["integer"] = value
    d["InheritedType"] = inh
    return d


def p_arr(n, strtype, value, inh=7, flags=None):
    d = {"nid": nid()}
    if flags is not None:
        d["flags"] = flags
    d["strtype"] = strtype
    d["intarray"] = list(value)
    d["InheritedType"] = inh
    return d


def p_grp(n, strtype, flags=None):
    d = {"nid": nid()}
    if flags is not None:
        d["flags"] = flags
    d["strtype"] = strtype
    d["InheritedType"] = 1
    return d


def style_block(part_strtype, part_name, part_list, sstate_props, nid_main):
    """One lv.PART.* style sheet containing only the DEFAULT state."""
    state_children = []
    for i, prop in enumerate(sstate_props):
        prop["nid"] = nid()
        state_children.append(prop)
    return {
        "part": part_name,
        "childs": [{
            "nid": nid(),
            "strtype": "_style/StyleState",
            "strval": "DEFAULT",
            "childs": state_children,
            "InheritedType": 1,
        }],
        "nid": nid(),
        "strtype": part_strtype,
        "strval": part_list,
        "InheritedType": 11,
    }


def s_bg(color, radius=None):
    out = []
    if radius is not None:
        # 与 p_int 同约定：值为 0 时留节点、省 integer 键
        node = {"strtype": "_style/Bg_Radius", "InheritedType": 6}
        if radius:
            node["integer"] = int(radius)
        out.append(node)
    # 注意：官方的 _style/* 属性节点一律不带 flags，不要自造 flags:4096
    out.append({"strtype": "_style/Bg_Color",
                "intarray": list(color), "InheritedType": 7})
    return out


def s_text(font, color, align="LEFT"):
    return [
        {"strtype": "_style/Text_Color",
         "intarray": list(color), "InheritedType": 7},
        {"strtype": "_style/Text_Font", "strval": font, "InheritedType": 3},
        {"strtype": "_style/Text_Align", "strval": align, "InheritedType": 3},
    ]


def s_arc(color, width, rounded=True):
    return [
        {"strtype": "_style/Arc_Color", "intarray": list(color), "InheritedType": 7},
        {"strtype": "_style/Arc_Width", "integer": int(width), "InheritedType": 6},
        {"strtype": "_style/Arc_Rounded", "strval": "True" if rounded else "False",
         "InheritedType": 2},
    ]


# --------------------------------------------------------------------------
# object placeholders: resolved to real guids once every object exists
# --------------------------------------------------------------------------
def S(name):
    """screen placeholder"""
    return "@s:" + name


def O(screen, name):
    """object placeholder"""
    return "@o:%s/%s" % (screen, name)


_guid = [0]


def new_guid():
    _guid[0] += 1
    i = _guid[0]
    return "GUID%08d-%06dS%d90" % (10000000 + i * 137, 300000 + i * 13, 900 + i)


GUID_RE = re.compile(r"^@(?:s|o):")


# --------------------------------------------------------------------------
# animations
# --------------------------------------------------------------------------
ANIMS = []
ANIM_INDEX = {}

FUNC = {
    "opacity": ("anim_callback_set_opacity", "anim_callback_get_opacity"),
    "x": ("anim_callback_set_x", "anim_callback_get_x"),
    "y": ("anim_callback_set_y", "anim_callback_get_y"),
    "width": ("anim_callback_set_width", "anim_callback_get_width"),
    "height": ("anim_callback_set_height", "anim_callback_get_height"),
    "image_angle": ("anim_callback_set_image_angle", "anim_callback_get_image_angle"),
    "image_zoom": ("anim_callback_set_image_zoom", "anim_callback_get_image_zoom"),
    "image_frame": ("anim_callback_set_image_frame", "anim_callback_get_image_frame"),
}
PATH_INT = {"linear": 0, "ease_in": 1, "ease_out": 2, "overshoot": 4}
_deepid = [0]


def next_deepid():
    _deepid[0] += 1
    return -(1000000 + _deepid[0] * 7)


def add_anim(name, target, tracks, duration=300, path="ease_out",
             loop_infinite=False, loop_count=0, image_set=""):
    """tracks: list of (property, [(value, time_ms), ...], track_duration)."""
    fn_name = re.sub(r"[^0-9A-Za-z]+", "", name.title()) or "Anim"
    fn_name = fn_name[0].lower() + fn_name[1:] + "_Animation"
    pas = []
    for i, (prop, frames, dur) in enumerate(tracks):
        setter, getter = FUNC[prop]
        frames = sorted(frames, key=lambda f: f[1])
        pas.append({
            "Path": PATH_INT[path],
            "KeyFrames": [{"Value": v, "Time": float(t), "InheritedType": 1}
                          for v, t in frames],
            "TimeReference": 0,
            "ValueReference": 0,
            "EarlyApply": False,
            "ImageSet": image_set,
            "PlaybackTime": 0,
            "PlaybackDelay": 0,
            "LoopCount": loop_count,
            "LoopDelay": 0,
            "LoopInfinite": bool(loop_infinite),
            "guid": new_guid(),
            "deepid": next_deepid(),
            "dont_export": False,
            "locked": False,
            "saved_objtypeKey": "PROPERTYANIMATION",
            "InheritedType": 1,
            "properties": [
                p_str(0, "PROPERTYANIMATION/Name", "%s %d" % (name, i), 10),
                p_str(0, "PROPERTYANIMATION/VariableName",
                      "PropertyAnimation_%d" % i, 10),
                p_str(0, "PROPERTYANIMATION/PropertyFunction", setter, 10),
                p_int(0, "PROPERTYANIMATION/StartValue", frames[0][0], 6),
                p_int(0, "PROPERTYANIMATION/EndValue", None, 6),
                p_str(0, "PROPERTYANIMATION/AbsoluteReference", "True", 2),
                p_int(0, "PROPERTYANIMATION/Delay", None, 6),
                p_int(0, "PROPERTYANIMATION/Duration", dur, 6),
                p_str(0, "PROPERTYANIMATION/Path", path, 3),
                p_int(0, "PROPERTYANIMATION/FullAnimationDuration", dur, 6),
                p_int(0, "PROPERTYANIMATION/LoopCount", loop_count, 6),
                p_str(0, "PROPERTYANIMATION/Forward", "True", 2),
                p_str(0, "PROPERTYANIMATION/Backward", "False", 2),
                p_str(0, "PROPERTYANIMATION/EarlyApply", "False", 2),
                p_str(0, "PROPERTYANIMATION/PropertyGetter", getter, 10),
                p_int(0, "PROPERTYANIMATION/LoopDelay", None, 6),
                p_int(0, "PROPERTYANIMATION/PlaybackDelay", None, 6),
                p_int(0, "PROPERTYANIMATION/PlaybackTime", None, 6),
                p_str(0, "PROPERTYANIMATION/LoopInfinite",
                      "True" if loop_infinite else "False", 2),
                p_str(0, "PROPERTYANIMATION/ImageSet", image_set, 14),
            ],
        })
    anim = {
        "propertyAnimations": pas,
        "guid": new_guid(),
        "deepid": next_deepid(),
        "dont_export": False,
        "locked": False,
        "properties": [
            p_str(0, "ELOANIMATION/Name", name, 10),
            p_str(0, "ELOANIMATION/FunctionName", fn_name, 10),
            p_str(0, "ELOANIMATION/AnimationTargetObjectType", "BASIC", 10),
            p_str(0, "ELOANIMATION/PlayType", "Forward", 3),
            p_str(0, "ELOANIMATION/Loop", "True" if loop_infinite else "False", 2),
            p_str(0, "ELOANIMATION/TestTarget", target, 10),
            p_str(0, "ELOANIMATION/TargetTypeFilter", "", 10),
        ],
        "saved_objtypeKey": "ELOANIMATION",
    }
    ANIM_INDEX[name] = anim
    ANIMS.append(anim)
    return name


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------
def _act(kind, pairs, call, callc):
    return {
        "nid": ev_nid(),
        "strtype": "_event/action",
        "strval": kind,
        "childs": ([p_str(0, kind + "/Name", kind, 10),
                    p_str(0, kind + "/Call", call, 10),
                    p_str(0, kind + "/CallC", callc, 10)]
                   + [v for v in pairs]),
        "InheritedType": 10,
    }


def act_change(target, speed=150):
    return _act(
        "CHANGE SCREEN",
        [p_str(0, "CHANGE SCREEN/Screen_to", target, 9),
         p_str(0, "CHANGE SCREEN/Fade_mode", "FADE_ON", 3),
         p_int(0, "CHANGE SCREEN/Speed", speed, 6),
         p_int(0, "CHANGE SCREEN/Delay", None, 6)],
        "ChangeScreen( <{Screen_to}>, lv.SCR_LOAD_ANIM.<{Fade_mode}>, <{Speed}>, <{Delay}>)",
        "_ui_screen_change( &<{Screen_to}>, LV_SCR_LOAD_ANIM_<{Fade_mode}>, <{Speed}>, <{Delay}>, &<{Screen_to}>_screen_init);",
    )


def act_flag(obj, flag="HIDDEN", action="ADD"):
    return _act(
        "MODIFY FLAG",
        [p_str(0, "MODIFY FLAG/Object", obj, 9),
         p_str(0, "MODIFY FLAG/Flag", flag, 3),
         p_str(0, "MODIFY FLAG/Action", action, 3)],
        'ModifyFlag( <{Object}>, lv.obj.FLAG.<{Flag}>, "<{Action}>")',
        "_ui_flag_modify( <{Object}>, LV_OBJ_FLAG_<{Flag}>, _UI_MODIFY_FLAG_<{Action}>);",
    )


def hide(obj):
    return act_flag(obj, "HIDDEN", "ADD")


def show(obj):
    return act_flag(obj, "HIDDEN", "REMOVE")


def act_opa(target, value=255):
    return _act(
        "SET OPACITY",
        [p_str(0, "SET OPACITY/Target", target, 9),
         p_int(0, "SET OPACITY/Value", value, 6)],
        "set_opacity( <{Target}>, <{Value}>)",
        "_ui_opacity_set( <{Target}>, <{Value}>);",
    )


def act_anim(anim_name, target, delay=None):
    fn = ANIM_INDEX[anim_name]["properties"][1]["strval"]
    return _act(
        "PLAY ANIMATION",
        [p_str(0, "PLAY ANIMATION/FunctionName", fn, 10),
         p_str(0, "PLAY ANIMATION/Animation", anim_name, 8),
         p_str(0, "PLAY ANIMATION/Target", target, 9),
         p_int(0, "PLAY ANIMATION/Delay", delay, 6)],
        "<{FunctionName}>(<{Target}>, <{Delay}>)",
        "<{FunctionName}>(<{Target}>, <{Delay}>);",
    )


def ev(kind, name, actions):
    return {
        "disabled": False,
        "nid": ev_nid(),
        "strtype": "_event/EventHandler",
        "strval": kind,
        "childs": ([p_str(0, "_custom/name", name, 10),
                    p_str(0, "_custom/condition_C", "", 10),
                    p_str(0, "_custom/condition_P", "", 10)]
                   + list(actions)),
        "InheritedType": 4,
    }


# --------------------------------------------------------------------------
# object builders
# --------------------------------------------------------------------------
def obj_base(name, x, y, w, h, objtype, clickable=False, hidden=False, events=None):
    """OBJECT/* defaults + typed marker.

    Positions are authored in ABSOLUTE screen coordinates (top-left corner,
    the same convention as the HTML mockup).  `rebase()` converts the whole
    tree to SquareLine's parent-centre-relative offsets in one pass at the
    end, so nesting a widget inside a panel can never drift.

    Three fields follow SquareLine's own *minimised* serialisation -- the form
    the editor rewrites the file into on its first save.  Emitting the verbose
    form instead makes every save produce a diff of a thousand nodes, so match
    the editor::

      * ``OBJECT/Hidden``    -- written ONLY when True (False is the default).
      * ``OBJECT/Clickable`` -- written ONLY when the object has NO event
                                handlers; with handlers, clickability is implied.
      * ``OBJECT/State_trickle`` -- replaces ``OBJECT/Clickable`` for event-less
                                objects (SquareLine's rename on save).
    """
    props = [
        p_str(10, "OBJECT/Name", name, 10),
        p_grp(20, "OBJECT/Layout"),
        {
            "Flow": 0, "Wrap": False, "Reversed": False, "MainAlignment": 0,
            "CrossAlignment": 0, "TrackAlignment": 0, "LayoutType": 0,
            "nid": nid(), "strtype": "OBJECT/Layout_type", "strval": "No_layout",
            "InheritedType": 13,
        },
        p_grp(40, "OBJECT/Transform"),
        p_arr(50, "OBJECT/Position", [int(x), int(y)], 7, flags=17),
        p_arr(60, "OBJECT/Size", [int(w), int(h)], 7, flags=17),
        p_str(70, "OBJECT/Align", "CENTER", 3),
        # 官方写法：无 flags，InheritedType=6（不是把 6 塞进 flags）
        {"nid": nid(), "strtype": "OBJECT/Extend_click_area", "InheritedType": 6},
    ]
    if hidden:
        props.append(p_str(85, "OBJECT/Hidden", "True", 2))
    props.append(p_grp(90, "OBJECT/Flags", 1048576))
    if not events:
        # 无事件对象：Clickable 由 State_trickle 承载（SquareLine 保存后的形态）
        props.append(p_str(110, "OBJECT/State_trickle",
                           "True" if clickable else "False", 2))
    props += [
        p_grp(225, "OBJECT/Scrolling", 1048576),
        p_str(300, "OBJECT/Scrollbar_mode", "AUTO", 3),
        p_str(310, "OBJECT/Scroll_direction", "ALL", 3),
        p_str(314, "OBJECT/Scroll_snap_x", "NONE", 3),
        p_str(315, "OBJECT/Scroll_snap_y", "NONE", 3),
        p_grp(320, "OBJECT/States", 1048576),
    ]
    return props


def rebase(node, parent):
    """absolute top-left -> offset from the parent's centre (SquareLine form)."""
    props = node.get("properties") or []
    pos = next((p for p in props if p.get("strtype") == "OBJECT/Position"), None)
    size = next((p for p in props if p.get("strtype") == "OBJECT/Size"), None)
    if pos is None or size is None:
        # screens carry no geometry: they fill the display
        rect = parent
    else:
        x, y = pos["intarray"]
        w, h = size["intarray"]
        px, py, pw, ph = parent
        pos["intarray"] = [int(round(x + w / 2.0 - (px + pw / 2.0))),
                           int(round(y + h / 2.0 - (py + ph / 2.0)))]
        rect = (x, y, w, h)
    for c in node.get("children", []) or []:
        rebase(c, rect)


def mk_container(name, x, y, w, h, bg=CLEAR, radius=0, events=None, hidden=False,
                 children=None):
    """方块/卡片一律用 CONTAINER，**不要用 PANEL**。

    SquareLine 里两者都是 lv_obj，但导出行为不同：
      * **CONTAINER** 导出时会调用 `lv_obj_remove_style_all()`，把默认主题样式全部清掉；
      * **PANEL** 保留默认主题样式 —— LVGL 9 默认主题会给普通 lv_obj 套上
        `theme->styles.card`，其中 `border_width = 2px` 且 `border_post = true`
        （边框画在所有子控件之上）。

    样式词表里**没有 `Border_Width` 这个属性**（只有 `Border_Color`），所以用 PANEL 根本
    没法把那条边框关掉 —— 结果每个分组容器/透明命中区都会渲染成一个**空框框**。
    官方示例里纯分组、命中区、状态容器也一律用 CONTAINER。
    """
    props = obj_base(name, x, y, w, h, "CONTAINER",
                     clickable=bool(events), hidden=hidden, events=events)
    props.append(p_str(1005, "CONTAINER/Edited", "False", 2))
    props.append(style_block("CONTAINER/Style_main", "lv.PART.MAIN",
                             "lv.PART.MAIN, Rectangle, Pad, Text, Transform",
                             s_bg(bg, radius), 1040))
    props.append({
        "part": "lv.PART.SCROLLBAR", "childs": [], "nid": nid(),
        "strtype": "CONTAINER/Style_scrollbar",
        "strval": "lv.PART.SCROLLBAR, Rectangle, Pad", "InheritedType": 11,
    })
    props.extend(events or [])
    node = {"guid": new_guid(), "properties": props, "saved_objtypeKey": "CONTAINER"}
    if children:
        node["children"] = children
    return node


def esc_text(s):
    """LABEL/Text 存的是「C 字符串体」，不是原文。

    SquareLine 会把这里的内容**原样**拼进生成的代码（导出 C 时是
    `lv_label_set_text(ui_x, "…")`，内置模拟器是 Micropython 的
    `ui_x.set_text("…")`）。所以：
      * 真实换行必须写成**字面量 \\n**（反斜杠+n 两个字符）——这是官方示例的约定，
        写真实换行会把字符串截断 → 模拟器 SyntaxError → "LVGL crashed"。
      * 裸反斜杠 / 双引号也必须转义，否则同样会截断字符串。
    """
    if s is None:
        return s
    s = s.replace("\\", "\\\\")        # 先处理真反斜杠（此时还没有人为的反斜杠）
    s = s.replace('"', '\\"')          # 真双引号
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "\\n")         # 真实换行 -> 字面量 \n
    return s


def mk_label(name, x, y, w, h, text, font, color=WHITE, align="LEFT",
             events=None, hidden=False):
    props = obj_base(name, x, y, w, h, "LABEL",
                     clickable=bool(events), hidden=hidden, events=events)
    props.append(p_grp(1010, "LABEL/Label"))
    props.append(p_str(1020, "LABEL/Long_mode", "WRAP", 3))
    props.append(p_str(1030, "LABEL/Text", esc_text(text), 10))
    props.append(style_block("LABEL/Style_main", "lv.PART.MAIN",
                             "lv.PART.MAIN, Text, Rectangle, Pad, Transform",
                             s_text(font, color, align), 1040))
    props.extend(events or [])
    return {"guid": new_guid(), "properties": props, "saved_objtypeKey": "LABEL"}


def mk_image(name, x, y, w, h, asset, events=None, hidden=False, rotation=0):
    props = obj_base(name, x, y, w, h, "IMAGE",
                     clickable=bool(events), hidden=hidden, events=events)
    props.append(p_str(1050, "IMAGE/Overflow_visible", "False", 2))
    props.append(p_grp(1060, "IMAGE/Image"))
    props.append(p_str(1070, "IMAGE/Asset", asset, 5))
    props.append(p_arr(1080, "IMAGE/Pivot", [0, 0], 7))
    props.append(p_int(1090, "IMAGE/Rotation", rotation, 6))
    props.append(p_int(1100, "IMAGE/Scale", 256, 6))
    props.append(p_str(1110, "IMAGE/Inner_align", "CENTER", 3))
    props.append({
        "part": "lv.PART.MAIN", "childs": [], "nid": nid(),
        "strtype": "IMAGE/Style_main",
        "strval": "lv.PART.MAIN, Rectangle, Image, Transform", "InheritedType": 11,
    })
    props.extend(events or [])
    return {"guid": new_guid(), "properties": props, "saved_objtypeKey": "IMAGE"}


def mk_arc(name, x, y, size, value, vmax, ind_color, bg_color, width,
           bg_angles=(0, 360)):
    props = obj_base(name, x, y, size, size, "ARC")
    props.append(p_str(1050, "ARC/Overflow_visible", "False", 2))
    props.append(p_grp(1060, "ARC/Arc"))
    props.append(p_arr(1070, "ARC/Range", [0, vmax], 7))
    props.append(p_int(1080, "ARC/Value", value, 6))
    props.append(p_arr(1090, "ARC/Bg_angles", list(bg_angles), 7))
    props.append(p_str(1100, "ARC/Mode", "NORMAL", 3))
    props.append(p_grp(1110, "ARC/Rotation", 6))
    props.append(style_block("ARC/Style_main", "lv.PART.MAIN",
                             "lv.PART.MAIN, Rectangle, Pad, Arc, Transform",
                             s_arc(bg_color, width), 1040))
    props.append(style_block("ARC/Style_indicator", "lv.PART.INDICATOR",
                             "lv.PART.INDICATOR, Rectangle, Pad, Arc",
                             s_arc(ind_color, width), 1030))
    props.append({
        "part": "lv.PART.KNOB", "childs": [{
            "nid": nid(), "strtype": "_style/StyleState", "strval": "DEFAULT",
            "childs": [{"strtype": "_style/Bg_Color",
                        "intarray": list(CLEAR), "InheritedType": 7}],
            "InheritedType": 1}],
        "nid": nid(), "strtype": "ARC/Style_knob",
        "strval": "lv.PART.KNOB, Rectangle, Pad", "InheritedType": 11,
    })
    return {"guid": new_guid(), "properties": props, "saved_objtypeKey": "ARC"}


def mk_chain(screen, prefix, pairs, n, rect):
    """A ring of transparent hit panels: each advances the state, then hands the
    hit target to the next one. Only the visible panel is clickable (hidden
    objects are excluded from LVGL hit-testing), so a 3-state cycle works with
    built-in actions alone."""
    x, y, w, h = rect
    out = []
    for i in range(n):
        acts = list(pairs[i]) + [hide(O(screen, "%s_%d" % (prefix, i))),
                                 show(O(screen, "%s_%d" % (prefix, (i + 1) % n)))]
        out.append(mk_container("%s_%d" % (prefix, i), x, y, w, h, CLEAR, 0,
                            hidden=(i > 0),
                            events=[ev("CLICKED", "%s_step_%d" % (prefix, i), acts)]))
    return out




# --------------------------------------------------------------------------
# project assembly
# --------------------------------------------------------------------------
def build_project():
    PROJECT["build_animations"]()
    screens = PROJECT["build_screens"]()

    guids = {name: new_guid() for name in ALL_SCREENS}
    root_children = []

    for idx, name in enumerate(ALL_SCREENS):
        spec = screens[name]
        props = screen_shell(name, spec["bg"], tappable=True)
        children = spec["children"]

        if name in ORDER:
            pos = ORDER.index(name)
            if pos > 0:
                props.append(ev("GESTURE_RIGHT(GESTURE)", "scr_prev",
                                [act_change(S(ORDER[pos - 1]))]))
            if pos < len(ORDER) - 1:
                props.append(ev("GESTURE_LEFT(GESTURE)", "scr_next",
                                [act_change(S(ORDER[pos + 1]))]))
        # Project-specific screen wiring (a screen outside the swipe ring, a
        # load-time animation, ...).  PROJECT["screen_events"](name, props) is
        # optional; the two shipped projects use it for their voice screen.
        hook = PROJECT.get("screen_events")
        if hook:
            hook(name, props)

        root_children.append({
            "guid": guids[name],
            "children": children,
            "isPage": True,
            "editor_posx": 500 + (idx % 4) * 560,
            "editor_posy": -500 - (idx // 4) * 660,
            "properties": props,
            "saved_objtypeKey": "SCREEN",
        })

    for node in root_children:
        rebase(node, (0, 0, SW, SH))

    info = {
        "name": PROJECT_NAME + ".spj",
        "depth": 1,
        "width": SW,
        "height": SH,
        "rotation": 0,
        "offset_x": 0,
        "offset_y": 0,
        "shape": SHAPE,
        "multilang": "DISABLE",
        "description": DESCRIPTION,
        "board": "CMake/Eclipse/VScode with SDL for development on PC",
        "board_version": "v2.0.2",
        "editor_version": "1.6.2",
        "image": "",
        "export_temp_image": False,
        "force_export_images": False,
        "flat_export": False,
        "advanced_alpha": False,
        "pointfilter": False,
        "theme_simplified": False,
        "theme_dark": THEME_DARK,
        "theme_color1": THEME_COLOR1,
        "theme_color2": THEME_COLOR2,
        "custom_variable_prefix": "ui",
        "separate_screen_save": False,
        "hierarchy_state_save": False,
        "reverse_event_order": False,
        "backup_cnt": 4,
        "autosave_cnt": 0,
        "group_color_cnt": 0,
        "imagebytearrayprefix": "",
        "lvgl_version": LVGL_VERSION,
        "callfuncsexport": "C_FILE",
        "imageexport": "SOURCE",
        "lvgl_include_path": "",
        "naming": "Name",
        "naming_force_lowercase": False,
        "naming_add_subcomponent": False,
        "nidcnt": 1000412,
        "BitDepth": 16,
        "Name": PROJECT_NAME,
    }
    spj = {
        "root": {
            "guid": new_guid(),
            "children": root_children,
            "properties": [{
                "nid": 1000205,
                "strtype": "STARTEVENTS/Name",
                "strval": "___initial_actions0",
                "InheritedType": 10,
            }],
            "saved_objtypeKey": "STARTEVENTS",
        },
        "animations": ANIMS,
        "selected_theme": "Default",
        "selected_screen": guids[INITIAL_SCREEN],
        "info": info,
    }
    return spj, info, guids


def resolve_placeholders(tree, guids):
    def fix(o):
        if isinstance(o, dict):
            v = o.get("strval")
            if isinstance(v, str) and GUID_RE.match(v):
                if v.startswith("@s:"):
                    o["strval"] = guids[v[3:]]
                else:
                    scr, nm = v[3:].split("/", 1)
                    o["strval"] = OBJ_GUIDS[(scr, nm)]
            for x in o.values():
                fix(x)
        elif isinstance(o, list):
            for x in o:
                fix(x)

    fix(tree)


def collect_object_guids(spj):
    """Map (screen, object-name) -> guid after the tree exists."""
    table = {}
    for sc in spj["root"]["children"]:
        sname = next(p["strval"] for p in sc["properties"]
                     if p.get("strtype") == "OBJECT/Name")

        def walk(n):
            nm = next((p["strval"] for p in n.get("properties", [])
                       if p.get("strtype") == "OBJECT/Name"), None)
            if nm:
                table[(sname, nm)] = n["guid"]
            for c in n.get("children", []) or []:
                walk(c)

        walk(sc)
    return table


OBJ_GUIDS = {}


def screen_shell(name, bg, width=None, height=None, tappable=False):
    width = SW if width is None else width
    height = SH if height is None else height
    props = [
        p_str(10, "OBJECT/Name", name, 10),
        p_grp(20, "OBJECT/Layout"),
        {
            "Flow": 0, "Wrap": False, "Reversed": False, "MainAlignment": 0,
            "CrossAlignment": 0, "TrackAlignment": 0, "LayoutType": 0,
            "nid": nid(), "strtype": "OBJECT/Layout_type", "strval": "No_layout",
            "InheritedType": 13,
        },
        p_grp(40, "OBJECT/Transform"),
        p_grp(90, "OBJECT/Flags", 1048576),
        p_grp(225, "OBJECT/Scrolling", 1048576),
        p_str(230, "OBJECT/Scrollable", "False", 2),
        p_str(300, "OBJECT/Scrollbar_mode", "AUTO", 3),
        p_str(310, "OBJECT/Scroll_direction", "ALL", 3),
        p_str(314, "OBJECT/Scroll_snap_x", "NONE", 3),
        p_str(315, "OBJECT/Scroll_snap_y", "NONE", 3),
        p_grp(320, "OBJECT/States", 1048576),
        p_grp(1010, "SCREEN/Screen"),
        p_str(1020, "SCREEN/Temporary", "False", 2),
    ]
    props.append(style_block("SCREEN/Style_main", "lv.PART.MAIN",
                             "lv.PART.MAIN, Rectangle, Pad, Text",
                             s_bg(bg), 1040))
    props.append({
        "part": "lv.PART.SCROLLBAR", "childs": [], "nid": nid(),
        "strtype": "SCREEN/Style_scrollbar",
        "strval": "lv.PART.SCROLLBAR, Rectangle, Pad", "InheritedType": 11,
    })
    return props


# --------------------------------------------------------------------------
# assets
# --------------------------------------------------------------------------
def copy_images(spj):
    used = set()
    re_asset = re.compile(r"^assets/(.+)$")

    def walk(o):
        if isinstance(o, dict):
            if o.get("strtype") == "IMAGE/Asset":
                m = re_asset.match(str(o.get("strval", "")))
                if m:
                    used.add(m.group(1))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(spj)
    missing = []
    os.makedirs(OUT_ASSETS, exist_ok=True)
    for fn in sorted(used):
        src = os.path.join(SRC_IMAGES, fn)
        if not os.path.exists(src):
            missing.append(fn)
            continue
        shutil.copy2(src, os.path.join(OUT_ASSETS, fn))
    return sorted(used), missing


# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
def collect_label_texts(spj):
    out = []
    texts = {}

    def walk(o):
        if isinstance(o, dict):
            props = o.get("properties") or []
            txt = next((p.get("strval") for p in props
                        if p.get("strtype") == "LABEL/Text"), None)
            size = next((p.get("intarray") for p in props
                         if p.get("strtype") == "OBJECT/Size"), None)
            font = None
            for p in props:
                for st in (p.get("childs") or []):
                    for sp in (st.get("childs") or []):
                        if isinstance(sp, dict) and sp.get("strtype") == "_style/Text_Font":
                            font = sp.get("strval")
            if txt is not None and font:
                out.append((font, txt, size[0] if size else None,
                            size[1] if size else None))
                texts.setdefault(font, set()).update(txt)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(spj)
    return out, texts


def _charset_provenance(all_ui, headroom, have):
    """Report where the glyph set came from, so a *stale* spec doc is visible.

    The real risk this guards against: an engineer edits a spec markdown but the
    doc is never re-read, and a label then renders with missing glyphs - with
    nothing in the output explaining why.  The mirror case (doc edited, text
    never used) looks identical from the outside.  Counting the two sources
    separately makes both visible instead of silently trusting the doc.

    NOTE the direction of the dependency: `all_ui` (the real LABEL texts in the
    generated .spj) is the *primary* source and is always complete for the
    project as built.  The spec markdown only contributes extra headroom for
    copy that is not in the project yet.  So a stale doc can never break an
    existing label - it can only reduce future-proofing.  This line exists to
    make that headroom margin legible.
    """
    doc_new = {c for c in headroom if c not in all_ui and ord(c) in have}
    doc_dropped = {c for c in headroom if ord(c) not in have}
    parts = ["ui-text %d" % len(all_ui),
             "doc-headroom %d (+%d usable)" % (len(headroom), len(doc_new))]
    if doc_dropped:
        parts.append("doc-only %d not in TTF" % len(doc_dropped))
    return "charset   : " + ", ".join(parts)


def build_fonts(ui_texts):
    os.makedirs(OUT_FONTS, exist_ok=True)
    headroom = doc_charset()
    # every glyph the project can display, whatever font it was assigned to
    all_ui = set()
    for s in ui_texts.values():
        all_ui |= s
    made = []

    def normalise_font_c(path, ttf, size, ranges, symbols, base):
        """Make the generated .c host-independent.

        Two separate leaks, both of which showed up as spurious regression
        diffs:

        * lv_font_conv stamps the *absolute* ``--font`` / ``-o`` paths into the
          .c header comment, so the file differed between machines and between
          build directories for no functional reason.  That line is rewritten
          with repo-relative paths.
        * lv_font_conv writes the host's line ending, so a Windows build gave
          CRLF where a Linux build gave LF.  The rewrite always runs (not only
          when the header matched) and pins ``newline="\\n"``, so the file is
          LF-only everywhere.
        """
        with open(path, encoding="utf-8") as fh:      # universal newlines -> \n
            txt = fh.read()
        rel = "assets/fonts/" + ttf
        want = (" * Opts: --font " + rel + " --bpp 4 --size " + str(size) +
                " --range " + ",".join(ranges) + " --symbols " + symbols +
                " --no-compress --no-prefilter --format lvgl" +
                " --lv-font-name " + base + " -o assets/fonts/" + base + ".c")
        out, hit = [], 0
        for line in txt.splitlines(True):
            if line.startswith(" * Opts: "):
                out.append(want + "\n")
                hit += 1
            else:
                out.append(line)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(out))
        return hit
    for codename, ttf, size, kind in FONTS:
        src_ttf = os.path.join(SRC_FONTS, ttf)
        dst_ttf = os.path.join(OUT_FONTS, ttf)
        if not os.path.exists(dst_ttf):
            shutil.copy2(src_ttf, dst_ttf)
        have = ttf_cmap(dst_ttf)
        if kind == "text":
            # headroom only for glyphs the TTF really has, so nothing is declared
            # that the rasterizer would silently drop
            sym_set = all_ui | {c for c in headroom if ord(c) in have} | {"\u00b0"}
        else:
            sym_set = set(SYMBOLS[kind])
        symbols = "".join(c for c in sorted(sym_set) if ord(c) in have or c in " ")
        ranges = RANGES_TEXT if kind == "text" else RANGES_NUM
        common = ["--font", dst_ttf, "--bpp", "4", "--size", str(size),
                  "--range", ",".join(ranges), "--symbols", symbols,
                  "--no-compress", "--no-prefilter"]
        base = "ui_font_" + codename
        for fmt, ext in (("lvgl", "c"), ("bin", "bin")):
            out = os.path.join(OUT_FONTS, base + "." + ext)
            args = ([NODE, LFC] + common +
                    ["--format", fmt, "--lv-font-name", base, "-o", out])
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(out):
                raise RuntimeError("font %s (%s) failed: %s %s"
                                   % (codename, fmt, r.stdout, r.stderr))
        normalise_font_c(os.path.join(OUT_FONTS, base + ".c"),
                         ttf, size, ranges, symbols, base)
        fcfg = {
            "codename": codename,
            "ttf_path": "/assets/fonts/" + ttf,
            "bin_path": "/assets/fonts\\" + base + ".bin",
            "c_path": "/assets/fonts\\" + base + ".c",
            "cfg_path": "/assets/fonts\\" + base + ".fcfg",
            "size": size,
            "bpp": 4,
            "letters": 0,
            "ranges": list(ranges),
            "symbols": symbols,
            "customparams": "--no-compress --no-prefilter",
            "uploaded": False,
        }
        dump_json(os.path.join(OUT_FONTS, base + ".fcfg"), fcfg, indent=2)
        made.append({"codename": codename, "size": size, "symbols": symbols,
                     "ranges": ranges, "ttf": dst_ttf, "base": base})
    # stash the provenance so run_build() can print it instead of recomputing
    build_fonts.provenance = _charset_provenance(
        all_ui, headroom, ttf_cmap(os.path.join(OUT_FONTS, FONTS[0][1]))
        if FONTS else set())
    return made


# --------------------------------------------------------------------------
# verification: glyph coverage + metric fit
# --------------------------------------------------------------------------
def ttf_cmap(path):
    """Codepoint set of a TTF file (cmap formats 4 and 12).

    Format 4 segments routinely cover ranges whose glyph id resolves to 0
    (.notdef), so the idDelta / idRangeOffset tables are resolved properly
    instead of trusting the segment bounds.
    """
    d = open(path, "rb").read()
    n = struct.unpack(">H", d[4:6])[0]
    cmap_off = None
    for i in range(n):
        off = 12 + i * 16
        if d[off:off + 4] == b"cmap":
            cmap_off = struct.unpack(">I", d[off + 8:off + 12])[0]
    if cmap_off is None:
        return set()
    nsub = struct.unpack(">H", d[cmap_off + 2:cmap_off + 4])[0]
    best = None
    for i in range(nsub):
        r = cmap_off + 4 + i * 8
        _pid, _eid, o = struct.unpack(">HHI", d[r:r + 8])
        sub = cmap_off + o
        fmt = struct.unpack(">H", d[sub:sub + 2])[0]
        if fmt == 12:
            best = (12, sub)
        elif fmt == 4 and best is None:
            best = (4, sub)
    if best is None:
        return set()
    bfmt, boff = best
    s = set()
    if bfmt == 4:
        segx2 = struct.unpack(">H", d[boff + 6:boff + 8])[0]
        seg = segx2 // 2
        end_o = boff + 14
        start_o = end_o + segx2 + 2
        delta_o = start_o + segx2
        range_o = delta_o + segx2
        for i in range(seg):
            end = struct.unpack(">H", d[end_o + i * 2:end_o + i * 2 + 2])[0]
            start = struct.unpack(">H", d[start_o + i * 2:start_o + i * 2 + 2])[0]
            delta = struct.unpack(">h", d[delta_o + i * 2:delta_o + i * 2 + 2])[0]
            roff = struct.unpack(">H", d[range_o + i * 2:range_o + i * 2 + 2])[0]
            if start > end or start == 0xFFFF:
                continue
            for c in range(start, end + 1):
                if roff == 0:
                    gid = (c + delta) & 0xFFFF
                else:
                    p = range_o + i * 2 + roff + (c - start) * 2
                    if p + 2 > len(d):
                        continue
                    gid = struct.unpack(">H", d[p:p + 2])[0]
                    if gid:
                        gid = (gid + delta) & 0xFFFF
                if gid:
                    s.add(c)
    else:
        ngroups = struct.unpack(">I", d[boff + 12:boff + 16])[0]
        for i in range(ngroups):
            g = boff + 16 + i * 12
            a, b, gid = struct.unpack(">III", d[g:g + 12])
            if gid:
                s.update(range(a, b + 1))
    return s


def font_metrics(base):
    """line_height / base_line pulled from the generated LVGL C file."""
    p = os.path.join(OUT_FONTS, base + ".c")
    txt = open(p, encoding="utf-8", errors="ignore").read()
    lh = re.search(r"\.line_height = (\d+)", txt)
    bl = re.search(r"\.base_line = (-?\d+)", txt)
    return (int(lh.group(1)) if lh else None,
            int(bl.group(1)) if bl else None)


def text_width(text, size):
    """Rough advance-width estimate: CJK/fullwidth glyphs are ~1em, latin ~0.52em."""
    w = 0.0
    for ch in text:
        o = ord(ch)
        if ch in "\n":
            continue
        if o < 0x2000 or 0xFF01 <= o <= 0xFF60 or 0x3000 <= o <= 0x303F:
            w += size * (0.28 if ch == " " else 0.52)
        else:
            w += size
    return w


def verify(labeled, fonts_meta):
    """Return (errors, warnings, stats)."""
    errors, warns = [], []
    cov = {}
    sizes = {f["codename"]: f["size"] for f in fonts_meta}
    for f in fonts_meta:
        declared = set()
        for r in f["ranges"]:
            if "-" in r:
                a, b = r.split("-")
                declared |= set(range(int(a, 16), int(b, 16) + 1))
            else:
                declared.add(int(r, 16))
        declared |= {ord(c) for c in f["symbols"]}
        have = ttf_cmap(f["ttf"])
        cov[f["codename"]] = declared
        miss_ttf = sorted(c for c in declared
                          if c not in have and c != 0x20)
        if miss_ttf:
            warns.append("%s: TTF 里没有 %d 个声明字形 %s（会被跳过，不影响渲染）"
                         % (f["codename"], len(miss_ttf),
                            "".join(chr(c) for c in miss_ttf[:12])))

    lh = {f["codename"]: font_metrics(f["base"])[0] for f in fonts_meta}

    for font, text, bw, bh in labeled:
        if font not in cov:
            errors.append("文案引用了不存在的字体 %s：%r" % (font, text))
            continue
        miss = [ch for ch in text if ch not in " \n" and ord(ch) not in cov[font]]
        if miss:
            errors.append("%s 缺少字形 %s （文案 %r）"
                          % (font, "".join(dict.fromkeys(miss)), text))
            continue
        if not bw or not bh or not lh.get(font):
            continue
        line = lh[font]
        if bh < line:
            errors.append("%s 控件高度 %d < 行高 %d，中文上下会被裁切（文案 %r）"
                          % (font, bh, line, text))
            continue
        wid = text_width(text, sizes[font])
        rows = max(1, -(-int(wid) // int(bw * 1.02)))
        need = rows * line
        if need > bh:
            warns.append("%s 文案 %r 预计占 %d 行（需 %dpx，控件 %dpx），可能截断"
                         % (font, text, rows, need, bh))

    return errors, warns, {"coverage": {k: len(v) for k, v in cov.items()},
                           "line_height": lh}


# --------------------------------------------------------------------------
def run_build():
    os.makedirs(OUT_FONTS, exist_ok=True)
    for sub in ("backup", "cache", "components"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)

    spj, info, guids = build_project()
    global OBJ_GUIDS
    OBJ_GUIDS = collect_object_guids(spj)
    resolve_placeholders(spj["root"]["children"], guids)
    resolve_placeholders(spj["animations"], guids)

    used, missing = copy_images(spj)

    labeled, ui_texts = collect_label_texts(spj)
    fonts_meta = build_fonts(ui_texts)

    dump_json(os.path.join(OUT, PROJECT_NAME + ".spj"), spj, indent=2)
    dump_json(os.path.join(OUT, PROJECT_NAME + ".sll"), info, indent=4)
    dump_json(os.path.join(OUT, PROJECT_NAME + ".slp"), {
        "uiExportFolderPath": "", "projectExportFolderPath": "",
        "drive_stdio": "-", "drive_stdio_path": "",
        "drive_posix": "-", "drive_posix_path": "",
        "drive_win32": "-", "drive_win32_path": "",
        "drive_fatfs": "-", "drive_fatfs_path": "",
    }, indent=4)
    # Deterministic by default: rebuilding the same spec must produce a
    # byte-identical tree, otherwise the eval suite cannot diff it.  The editor
    # rewrites both fields the first time it saves, so nothing downstream cares.
    # Override with SQUARELINE_USER / SQUARELINE_BUILD_TIME if you want a stamp.
    dump_json(os.path.join(OUT, "project.info"), {
        "project_name": PROJECT_NAME + ".spj",
        "datetime": os.environ.get("SQUARELINE_BUILD_TIME")
                    or "2026-01-01T00:00:00.000000+00:00",
        "editor_version": "1.6.2",
        "project_version": 1,
        "user": os.environ.get("SQUARELINE_USER") or "squareline",
    }, indent=4)
    dump_json(os.path.join(OUT, "Themes.slt"),
              {"deftheme": {"name": "Default", "properties": []},
               "themes": [], "selected_theme": "Default"}, indent=2)

    errors, warns, stats = verify(labeled, fonts_meta)

    n_events = 0
    n_actions = 0

    def count(o):
        nonlocal n_events, n_actions
        if isinstance(o, dict):
            if o.get("strtype") == "_event/EventHandler":
                n_events += 1
            if o.get("strtype") == "_event/action":
                n_actions += 1
            for v in o.values():
                count(v)
        elif isinstance(o, list):
            for v in o:
                count(v)

    count(spj)

    print("project   :", OUT)
    print("screens   :", len(spj["root"]["children"]))
    print("objects   :", len(OBJ_GUIDS))
    print("events    : %d  (%d actions)" % (n_events, n_actions))
    print("animations:", len(ANIMS))
    print("images    : %d  missing: %s" % (len(used), missing))
    print("fonts     :", [(f["codename"], f["size"], len(f["symbols"])) for f in fonts_meta])
    print(getattr(build_fonts, "provenance", ""))
    print("coverage  :", stats["coverage"])
    print("lineheight:", stats["line_height"])
    for w in warns:
        print("WARN      :", w)
    for e in errors:
        print("ERROR     :", e)
    total = 0
    for _r, _d, files in os.walk(OUT):
        for f in files:
            total += 1
    print("files     :", total)
    return 1 if errors else 0



# --------------------------------------------------------------------------
# public entry point
# --------------------------------------------------------------------------
def build(project):
    """configure(project) + run the whole build.  Returns a process exit code."""
    configure(project)
    return run_build()


ENGINE_BUILD = build          # alias screen modules can import directly
