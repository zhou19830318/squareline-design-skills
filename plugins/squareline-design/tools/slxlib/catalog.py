# -*- coding: utf-8 -*-
"""Error catalog: code -> (title, why, fix).  `slx.py explain <CODE|text>` prints these.
Every lint finding carries a code from here, so a model that cannot reason about a message
can still look the fix up."""

CATALOG = {
    "E-SPEC-KEY": ("Missing top-level key", "The spec needs name, width, height, shape, palette, fonts, screens.",
                   "Copy the skeleton from `slx.py init`, or `python3 tools/build_from_spec.py --example`."),
    "E-SHAPE": ("Bad panel shape", "shape must be RECT or CIRCLE; a CIRCLE panel must be square (width == height).",
                "Fix width/height/shape in the spec header."),
    "E-FONT-DUP": ("Duplicate font codename", "Two fonts share a codename, so one overwrites the other's generated files.",
                   "Give every fonts[] entry a unique codename such as Title22 / Body18."),
    "E-FONT-TTF": ("Font file not found", "fonts[].ttf must be a file in <toolkit>/fonts/ or <project>/assets/fonts/.",
                   "Use one of the bundled Noto Sans SC files, or copy your TTF into <project>/assets/fonts/ and check its licence."),
    "E-FONT-KIND": ("Font kind has no symbol set",
                    "Only kind \"text\" is built in. Any other kind (e.g. \"number\") must be declared in the top-level "
                    "\"symbols\" map, otherwise the build dies with KeyError.",
                    "Add e.g. \"symbols\": {\"number\": \"0123456789:\"} to the spec."),
    "W-FONT-MIN": ("Font very small", "Below ~14 px text is hard to read on a ~1.85-inch / 195 ppi panel.",
                   "Use >= 16 px for secondary text, >= 18 px for body text, unless the requirement forces smaller."),
    "E-GLYPH": ("Character missing from a restricted font",
                "A non-text font contains symbols[kind] PLUS the code points in spec.ranges_num (ranges_num is shared by all "
                "non-text fonts). A LABEL using such a font has a character outside both, so it would render blank.",
                "Use a kind=\"text\" font for that label, or add the character to symbols[kind] / ranges_num. "
                "To keep a digits-only font small, set ranges_num to [\"0x30-0x3A\"] instead of the whole ASCII block."),
    "W-LABEL-H": ("LABEL box may be shorter than the font's line height",
                  "line_height is not a constant: it depends on the font AND the glyph set the project includes "
                  "(measured 1.17-1.31 x size). The build refuses a box shorter than the true value.",
                  "Use h >= ceil(size * 1.35); read the `lineheight:` line of the build output for the truth."),
    "E-OBJ-RECT": ("Bad rect", "rect must be [x, y, w, h] with integer-like numbers and w,h > 0.", "Fix the rect."),
    "E-OBJ-NAME": ("Bad object/screen name", "Names become C identifiers (ui_<screen>_<object>): letters, digits, underscore; "
                   "not starting with a digit.", "Rename, e.g. \"Wi-Fi tile\" -> \"wifi_tile\"."),
    "E-OBJ-DUP": ("Duplicate object name in a screen", "Object names must be unique inside one screen.", "Rename one of them."),
    "E-SCREEN-DUP": ("Duplicate screen name", "Screen names must be unique.", "Rename one."),
    "E-INITIAL": ("initial_screen does not exist", "initial_screen must name a screen.", "Fix initial_screen."),
    "E-COLOR": ("Unknown colour", "A colour must be a palette key, \"#rrggbb\", \"#rrggbbaa\" or [r,g,b,a].",
                "Add the key to palette, or write the hex value."),
    "E-FONT-REF": ("LABEL font not declared", "LABEL.font must be a codename from the top-level fonts[].", "Declare the font or fix the codename."),
    "E-LABEL-H": ("LABEL box not taller than the font size",
                  "line_height is always larger than the font size (it includes ascender + descender), so the text is certainly clipped.",
                  "Use h >= ceil(size * 1.35)."),
    "E-IMG-PATH": ("IMAGE asset path not flat",
                   "IMAGE.asset must be `assets/<file>.png` (flat). Writing `assets/images/<file>.png` makes every picture 'missing'.",
                   "Change to assets/<name>.png; assets_subdir only says where the source PNGs live."),
    "E-IMG-MISSING": ("Picture file not found", "The PNG is neither generated nor copied into <project>/assets/images/.",
                      "Add it to assets.manifest.json (lucide/svg/builtin/raster) and run `slx.py assets <proj>`, or drop the PNG in assets/images/."),
    "W-IMG-SIZE": ("Picture size differs from its rect", "A picture scaled at run time looks blurry and costs CPU.",
                   "Re-render the asset at the rect's native size, or change the rect to the PNG size."),
    "W-IMG-ORPHAN": ("Picture not used by any screen", "It will not ship in the project.", "Use it, or delete it from the manifest."),
    "E-EVENT-KIND": ("Event kind not in the verified set",
                     "Only CLICKED, PRESSED, RELEASED, PRESS_LOST, VALUE_CHANGED, SCREEN_LOAD_START/LOADED/UNLOAD_START/UNLOADED and "
                     "GESTURE_LEFT/RIGHT/UP/DOWN are known to open in SquareLine Studio. LONG_PRESSED and DOUBLE_CLICKED are NOT verified; "
                     "writing them risks a project the editor cannot open.",
                     "Wire CLICKED or a gesture instead, and implement long-press / double-click in C with LV_EVENT_LONG_PRESSED / "
                     "LV_EVENT_DOUBLE_CLICKED. Record it in the spec doc as a deviation."),
    "E-EVENT-DUP": ("Duplicate event name", "Event names become C function names and must be globally unique.",
                    "Name events <screen>_<object>_<event>, or leave `name` out and let the builder derive it."),
    "E-ACT-TYPE": ("Unknown action type", "Allowed: CHANGE_SCREEN, SHOW, HIDE, SET_OPACITY, PLAY_ANIMATION, CALL_FUNCTION.", "Fix the action."),
    "E-ACT-SCREEN": ("CHANGE_SCREEN target does not exist", "The target screen is not in screens[].", "Fix the target name."),
    "E-ACT-OBJ": ("Action object not found", "object = \"name\" (same screen) or \"screen/name\".", "Fix the reference."),
    "E-ANIM-REF": ("PLAY_ANIMATION names an unknown animation", "animation must match animations[].name.", "Fix the name."),
    "E-ANIM-TARGET": ("Animation target not found", "animations[].target must be \"screen/object\".", "Fix the target."),
    "W-ORDER-RING": ("Implicit swipe ring over many screens",
                     "`order` missing or empty = ALL screens are chained into one left/right swipe ring.",
                     "For non-linear navigation write \"order\": [\"<first screen>\"] and wire everything else with explicit events."),
    "E-CIRCLE": ("Object outside the round screen", "The painted extent (rounded corners / text ink included) leaves the circle by > 4 px: it is clipped on the real panel.",
                 "Move/shrink it. Rule of thumb: keep every visible corner within r - 5% of the centre."),
    "W-CIRCLE-CLIP": ("Corner clipped by the round screen", "A corner pokes out of the circle by a few pixels.", "Nudge it inwards."),
    "W-CIRCLE-TIGHT": ("Within 5 px of the rim", "Fine on screen, but the bezel may hide it.", "Leave ~5% breathing room."),
    "E-RECT-CANVAS": ("Rect outside the canvas", "Part of the object lies outside 0..width / 0..height.",
                      "Usually a coordinate bug (e.g. x computed from 0 instead of the element centre)."),
    "W-TAP": ("Touch target small", "Clickable objects under ~36 px are hard to hit on a wearable.", "Enlarge the object or its hit area."),
    "E-NAV-DEAD": ("Screen with no way back", "From this screen the initial screen cannot be reached again - a dead end in the simulator and on device.",
                   "Add a gesture or a button that leads back."),
    "W-NAV-UNREACH": ("Screen not reachable by touch", "No path of CHANGE_SCREEN actions leads here from the initial screen. Fine for event-driven "
                      "states (wake-up, errors), but the designer cannot walk to it in the simulator.",
                      "Add a 'state preview' page that links to every event-driven screen."),
    "W-DOC-MISSING": ("Spec doc missing", "spec_docs lists a file that is not next to the project, so the glyph headroom comes only from UI text.",
                      "Write the design spec doc (section 6.1 = every string, including future ones) before building."),
    "W-DOC-TEMPLATE": ("Spec doc still looks like the template", "Template placeholders are still present.", "Fill the doc; it is the source of truth."),
    # builder / validator / runtime messages seen in practice
    "KeyError: 'number'": ("Build crashes with KeyError on a font kind", "See E-FONT-KIND.", "Declare the symbol set in spec.symbols."),
    "missing on disk": ("Validator: image files missing", "Pictures referenced by the .spj are not in the project assets.", "See E-IMG-PATH / E-IMG-MISSING."),
    "控件高度": ("Builder: control height < line height", "See E-LABEL-H.", "h >= ceil(size*1.35)."),
    "strtype not in official examples": ("Validator: unknown strtype", "The editor's save form may differ from the builder's; do not 'fix' the builder first.",
                                         "See references/pipeline-handbook.md pitfall 11."),
    "occlusion suspects": ("Validator: text covered by a later-drawn container", "A container drawn after a label covers it.",
                           "Draw the text object AFTER the panels (z-order = list order)."),
    "OSError: cannot write mode": ("Pillow cannot save the image mode", "Convert to RGB/RGBA first.", "img.convert('RGBA')"),
    "Pillow": ("Pillow / numpy missing", "slx needs Pillow and numpy for the image tools.", "pip install pillow numpy --break-system-packages"),
}


def lookup(q):
    q_low = q.lower()
    hits = [(k, v) for k, v in CATALOG.items() if q_low == k.lower()]
    if not hits:
        hits = [(k, v) for k, v in CATALOG.items() if q_low in k.lower() or q_low in v[0].lower() or q_low in v[1].lower()]
    return hits
