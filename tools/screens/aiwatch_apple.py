#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AIWatchApple - 240x240 CIRCLE, Apple-style watch UI.  CONTENT LAYER.

Everything project-specific lives here: the palette, the font subsets, the spec
doc used for glyph headroom, the screen definitions.  The serialisation engine is
*imported*, never copied - see tools/engine/squareline_engine.py for why that
split exists (40 byte-identical functions used to be duplicated across two
1500-line builders).

Build:
    python tools/build_squareline_apple.py
    python tools/build_squareline_apple.py --assets examples/AIWatchApple/assets
    python tools/build_squareline_apple.py --out /tmp/AIWatchApple

Adding a *new* panel should mean adding a sibling of this file (or a JSON spec
for tools/build_from_spec.py) - never editing tools/engine/.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.dirname(_HERE)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from engine.squareline_engine import *          # noqa: F401,F403
from engine import squareline_engine as _E      # noqa: F401

# --------------------------------------------------------------------------
# project identity
# --------------------------------------------------------------------------
PROJECT_NAME = "AIWatchApple"
SW, SH = 240, 240                      # round panel; must match info.width/height
SPEC_DOCS = ("AIWatchApple设计规格文档.md",)

# source TTFs, copied into the project by the engine (fonts/ at the repo root)
REGULAR = "noto-sans-sc-v40-chinese-simplified-regular.ttf"
MEDIUM = "noto-sans-sc-v40-chinese-simplified-500.ttf"
BOLD = "noto-sans-sc-v40-chinese-simplified-700.ttf"

# --------------------------------------------------------------------------
# palette  (r, g, b, a)  -- 4th component = opacity, as SquareLine stores it
WHITE = [255, 255, 255, 255]
T2 = [255, 255, 255, 158]
T3 = [255, 255, 255, 97]
NEAR = [237, 237, 237, 255]
ABLUE = [10, 132, 255, 255]      # iOS system blue
ARED = [255, 69, 58, 255]        # iOS system red
AGREEN = [48, 209, 88, 255]      # iOS system green
APURPLE = [191, 90, 242, 255]    # iOS system purple
ACYAN = [100, 210, 255, 255]     # iOS system cyan
APINK = [255, 45, 138, 255]
AYELLOW = [255, 214, 10, 255]
AORANGE = [255, 159, 10, 255]
AGRAY = [142, 142, 147, 255]     # iOS system gray
CARDD = [20, 20, 22, 255]        # #141416 card
CARD = CARDD
BUBBLEC = [28, 28, 46, 255]      # #1C1C2E gemini bubble
GRAY = [44, 44, 46, 255]         # #2C2C2E (grid circle)
BTN = [28, 28, 30, 255]
LINE = [38, 38, 42, 255]
BLACK = [0, 0, 0, 255]
HOME_BG = BLACK
CLEAR = [0, 0, 0, 0]
DIM = [0, 0, 0, 178]


# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
FONTS = [
    # codename, ttf, size, kind
    ("TimeBig44", BOLD, 44, "time"),
    ("Number36", BOLD, 36, "number"),
    ("Title20", MEDIUM, 20, "text"),
    ("Body15", REGULAR, 15, "text"),
    ("Caption13", REGULAR, 13, "text"),
]
# leading text block only where a font actually needs latin/fullwidth forms
# NOTES on the exact ranges (both learned from permanent warnings):
#   * 0x20-0x7E, not -0x7F: U+007F (DEL) is in no TTF.
#   * the fullwidth block is split around U+FF4A (ｊ) and U+FF5A (ｚ), which
#     Noto Sans SC does not carry either.  Requesting them only buys noise.
RANGES_TEXT = ["0x20-0x7E", "0x00B0", "0x2014", "0x2018-0x2019",
               "0x201C-0x201D", "0x2026", "0x3001", "0x3002",
               "0x300A-0x300B", "0xFF01-0xFF49", "0xFF4B-0xFF59",
               "0xFF5B-0xFF5E"]
RANGES_NUM = ["0x20-0x7E", "0x00B0"]
SKIP = set("\u2103\u2248\u251c\U0001f4cd\u26a0\U0001f4a1\u23f8\u2192"
           "\U0001f50b\u25b6\u2500\ufe0f")
DIGITS = "0123456789"
SYMBOLS = {
    "time": DIGITS + ":\u6708\u5468\u65e5\u4e8c\u4e09\u56db\u516d",
    "number": DIGITS + ":.%\u00b0C\u6b65\u5361\u8def\u91cc\u65f6\u5206\u5929",
    # "text" is filled in at build time from the strings the project really uses
    "text": "",
}


# --------------------------------------------------------------------------
# screens  (240x240 round, Apple style)
# --------------------------------------------------------------------------
# home radial layout: gemini hero disc 64px dead-centre, 8 app circles 44px
# evenly on a r=76 ring, offset 22.5° so the top centre stays clear for the clock
APP_ICONS = [
    # key, glyph asset, circle colour, angle deg (0 = 12 o'clock), target screen
    ("weather",  "img_apple_icon_weather.png",  ABLUE,  22.5, "weather"),
    ("heart",    "img_apple_icon_heart.png",    ARED,   67.5, "health"),
    ("settings", "img_apple_icon_settings.png", AGRAY, 112.5, "settings"),
    ("message",  "img_apple_icon_message.png",  ABLUE, 157.5, None),
    ("music",    "img_apple_icon_music.png",    APINK, 202.5, None),
    ("grid",     "img_apple_icon_grid.png",     GRAY,  247.5, None),
    ("steps",    "img_apple_icon_runner.png",   AGREEN, 292.5, "steps"),
    ("clock",    "img_apple_icon_clock.png",    WHITE, 337.5, "clock"),
]
HOME_CX, HOME_CY, RING_R = 120, 120, 76


def ring_pos(deg, r=RING_R, cx=HOME_CX, cy=HOME_CY):
    rad = deg * math.pi / 180.0
    return (int(round(cx + r * math.sin(rad))),
            int(round(cy - r * math.cos(rad))))


def row_geo(top, h=32, margin=4):
    """Chord-fit row for the settings list: width taken at the row's NARROWER
    edge, so the rounded card stays fully inside the 240 circle while the
    long edges visually hug the bezel."""
    d = max(abs(top - 120), abs(top + h - 120))
    half = math.sqrt(max(0.0, 120.0 ** 2 - d * d)) - margin
    w = int(2 * half)
    return ((SW - w) // 2, top, w, h)

ORDER = ["home", "clock", "weather", "health", "steps", "ai", "settings"]
ALL_SCREENS = ORDER

# weather cycle: key, 64px hero icon, 24px hourly icon, temperature, condition, range
WEATHER = [
    ("sunny",     "img_apple_weather_sunny_64.png",     "img_apple_weather_sunny_24.png",     "26°C", "晴",       "28° / 18°"),
    ("cloudy",    "img_apple_weather_cloudy_64.png",    "img_apple_weather_cloudy_24.png",    "22°C", "局部多云", "24° / 16°"),
    ("overcast",  "img_apple_weather_overcast_64.png",  "img_apple_weather_overcast_24.png",  "19°C", "阴",       "21° / 15°"),
    ("rain",      "img_apple_weather_rain_64.png",      "img_apple_weather_rain_24.png",      "16°C", "小雨",     "18° / 12°"),
    ("heavyrain", "img_apple_weather_heavyrain_64.png", "img_apple_weather_heavyrain_24.png", "13°C", "大雨",     "15° / 10°"),
    ("thunder",   "img_apple_weather_thunder_64.png",   "img_apple_weather_thunder_24.png",   "14°C", "雷阵雨",   "17° / 11°"),
    ("snow",      "img_apple_weather_snow_64.png",      "img_apple_weather_snow_24.png",      "-2°C", "小雪",     "1° / -8°"),
    ("fog",       "img_apple_weather_fog_64.png",       "img_apple_weather_fog_24.png",       "12°C", "雾",       "15° / 9°"),
]
# hourly forecast columns on the default (cloudy) state
HOURS = [("img_apple_weather_cloudy_24.png", "22°"),
         ("img_apple_weather_sunny_24.png",  "24°"),
         ("img_apple_weather_sunny_24.png",  "23°"),
         ("img_apple_moon_24.png",           "19°")]
HOUR_CX = [66, 102, 138, 174]

# clock face: baked-rotation tick/hand PNGs, positions from mockup_apple.html
TICKS = [
    ("tk_12", "img_apple_tick_M0.png",   114, 7,  12, 12),
    ("tk_1",  "img_apple_tick_m30.png",  166, 15, 12, 12),
    ("tk_2",  "img_apple_tick_m60.png",  206, 55, 12, 12),
    ("tk_3",  "img_apple_tick_M90.png",  221, 114, 12, 12),
    ("tk_4",  "img_apple_tick_m120.png", 206, 173, 12, 12),
    ("tk_5",  "img_apple_tick_m150.png", 166, 213, 12, 12),
    ("tk_6",  "img_apple_tick_M180.png", 114, 221, 12, 12),
    ("tk_7",  "img_apple_tick_m210.png", 62,  213, 12, 12),
    ("tk_8",  "img_apple_tick_m240.png", 22,  173, 12, 12),
    ("tk_9",  "img_apple_tick_M270.png", 7,   114, 12, 12),
    ("tk_10", "img_apple_tick_m300.png", 22,  55, 12, 12),
    ("tk_11", "img_apple_tick_m330.png", 62,  15, 12, 12),
]


def build_screens():
    screens = {}

    # ---------------------------------------------------------------- home
    ch = []
    for key, icon, colour, deg, target in APP_ICONS:
        cx, cy = ring_pos(deg)
        ch.append(mk_container("cir_" + key, cx - 22, cy - 22, 44, 44, colour, 22,
                               events=([ev("CLICKED", "go_" + key,
                                           [act_change(S(target))])]
                                       if target else None)))
        ch.append(mk_image("img_" + key, cx - 12, cy - 12, 24, 24,
                           "assets/" + icon))
    # centre hero: baked gradient gemini disc
    ch.append(mk_image("cir_gemini", 88, 88, 64, 64,
                       "assets/img_apple_circle_gemini64.png",
                       events=[ev("CLICKED", "go_gemini",
                                  [act_change(S("ai"))])]))
    screens["home"] = {"bg": HOME_BG, "children": [
        mk_label("lbl_time", 0, 4, SW, 24, "10:09", "Title20", WHITE, "CENTER",
                 events=[ev("CLICKED", "go_clock", [act_change(S("clock"))])]),
        mk_image("img_battery", 148, 12, 18, 10, "assets/img_apple_battery.png"),
    ] + ch + [
        mk_container("dot0", 102, 218, 6, 6, WHITE, 3),
        mk_container("dot1", 112, 218, 6, 6, [90, 90, 90, 255], 3),
        mk_container("dot2", 122, 218, 6, 6, [90, 90, 90, 255], 3),
        mk_container("dot3", 132, 218, 6, 6, [90, 90, 90, 255], 3),
    ]}

    # --------------------------------------------------------------- clock
    clock = []
    for nm, asset, x, y, w, h in TICKS:
        clock.append(mk_image(nm, x, y, w, h, "assets/" + asset))
    clock += [
        # hands pivot at the SCREEN centre: canvas centre == (120,120);
        # drawn under the text so the big time stays readable
        mk_image("hand_hour", 48, 48, 144, 144, "assets/img_apple_hand_hour.png"),
        mk_image("hand_min", 16, 16, 208, 208, "assets/img_apple_hand_minute.png"),
        mk_image("hand_sec", 4, 4, 232, 232, "assets/img_apple_hand_second.png"),
        mk_container("hub", 116, 116, 8, 8, ABLUE, 4),
        mk_label("lbl_time", 0, 32, SW, 54, "10:09", "TimeBig44", WHITE, "CENTER"),
        mk_label("lbl_date", 0, 92, SW, 22, "周二 4月22日", "Caption13", T2, "CENTER"),
        mk_image("img_steps_ico", 96, 194, 14, 14, "assets/img_apple_footsteps.png"),
        mk_label("lbl_steps", 114, 190, 60, 22, "7532", "Caption13", T2, "LEFT"),
        mk_container("hit_face", 30, 30, 180, 180, CLEAR, 0,
                     events=[ev("CLICKED", "back_home", [act_change(S("home"))])]),
    ]
    screens["clock"] = {"bg": BLACK, "children": clock}

    # ------------------------------------------------------------- weather
    wx = [
        mk_image("img_pin", 56, 20, 16, 16, "assets/img_apple_pin.png"),
        mk_label("lbl_city", 78, 16, 92, 24, "旧金山", "Body15", NEAR, "LEFT"),
    ]
    # hero region: 8 stacked states, tap cycles — kept inside the round safe area
    region = (28, 44, 184, 108)
    for i, (key, hero, hour_ico, temp, desc, rng) in enumerate(WEATHER):
        wx.append(mk_container("wx_%s" % key, region[0], region[1], region[2],
                           region[3], CLEAR, 0, hidden=(i > 0),
                           events=[ev("CLICKED", "wx_cycle_%s" % key,
                                      [hide(O("weather", "wx_%s" % key)),
                                       show(O("weather", "wx_%s" % WEATHER[(i + 1) % len(WEATHER)][0]))])],
                           children=[
            # children are authored in ABSOLUTE screen coords (rebase() converts)
            mk_image("img_big_%s" % key, 36, 50, 64, 64, "assets/" + hero),
            mk_label("lbl_temp_%s" % key, 112, 58, 90, 46, temp, "Number36",
                     WHITE, "RIGHT"),
            mk_label("lbl_desc_%s" % key, 36, 116, 168, 26, desc, "Body15",
                     WHITE, "LEFT"),
            mk_label("lbl_rng_%s" % key, 36, 134, 168, 18,
                     "最高 %s" % rng.replace(" / ", " 最低 ").replace("° /", "°"),
                     "Caption13", T2, "LEFT"),
        ]))
    # hourly row (shared, on top of the state stack) — narrowed to the chord
    for i, (ico, tt) in enumerate(HOURS):
        c = HOUR_CX[i]
        wx.append(mk_image("img_hour%d" % i, c - 10, 160, 20, 20, "assets/" + ico))
        wx.append(mk_label("lbl_ht%d" % i, c - 13, 186, 26, 18, tt, "Caption13",
                           T2, "CENTER"))
    screens["weather"] = {"bg": BLACK, "children": wx}

    # -------------------------------------------------------------- health
    rows = [("SpO2", "98%", "img_apple_health_drop.png", ARED),
            ("体温", "36.5°C", "img_apple_health_temp.png", ACYAN),
            ("睡眠", "7时48分", "img_apple_health_sleep.png", APURPLE)]
    hl = [
        # bpm group lowered to the vertical centre of the upper half
        mk_image("img_heart", 50, 28, 24, 24, "assets/img_apple_health_heart.png"),
        mk_label("lbl_bpm", 82, 20, 64, 46, "72", "Number36", WHITE, "LEFT"),
        mk_label("lbl_unit", 142, 42, 36, 18, "bpm", "Caption13", T3, "LEFT"),
        mk_image("img_trace", 24, 66, 192, 56, "assets/img_apple_health_trace.png"),
    ]
    for i, (nm, val, ico, colour) in enumerate(rows):
        top = 126 + i * 32
        hl.append(mk_container("row%d" % i, 52, top, 136, 28, CARDD, 12))
        hl.append(mk_container("dot%d" % i, 60, top + 5, 18, 18, colour, 9))
        hl.append(mk_image("ico%d" % i, 63, top + 8, 12, 12, "assets/" + ico))
        hl.append(mk_label("nm%d" % i, 86, top + 4, 62, 20, nm, "Body15",
                           NEAR, "LEFT"))
        hl.append(mk_label("va%d" % i, 118, top + 4, 62, 20, val, "Body15",
                           NEAR, "RIGHT"))
    screens["health"] = {"bg": BLACK, "children": hl}

    # --------------------------------------------------------------- steps
    ring_rect = (72, 62, 96)
    st = [
        mk_image("img_runner", 108, 16, 24, 24, "assets/img_apple_steps_runner.png"),
        # slimmer ring + smaller step count: fuller, better-proportioned dial
        mk_arc("arc_ring", ring_rect[0], ring_rect[1], ring_rect[2], 94, 100,
               AGREEN, [48, 209, 88, 41], 8),
        mk_label("lbl_steps", 0, 92, SW, 28, "7532", "Title20", WHITE, "CENTER"),
        mk_label("lbl_unit", 0, 122, SW, 18, "steps", "Caption13", T3, "CENTER"),
    ]
    stats = [("flame", "img_apple_steps_flame.png", "320", "kcal"),
             ("km", "img_apple_steps_location.png", "5.8", "km"),
             ("flr", "img_apple_steps_floors.png", "9", "floors")]
    for i, (key, ico, num, unit) in enumerate(stats):
        cx = 64 + i * 56
        st.append(mk_image("ico_%s" % key, cx - 7, 162, 14, 14, "assets/" + ico))
        st.append(mk_label("num_%s" % key, cx - 26, 176, 52, 26, num, "Title20",
                           WHITE, "CENTER"))
        st.append(mk_label("un_%s" % key, cx - 26, 202, 52, 18, unit, "Caption13",
                           T3, "CENTER"))
    screens["steps"] = {"bg": BLACK, "children": st}

    # ------------------------------------------------------------------ ai
    # two exclusive views: chat_view (conversation) <-> voice_view (mic+wave);
    # the waveform now lives in its own zone above the mic — no overlap.
    # frames live inside wv_container (52,82): absolute (60,84)
    wv_frames = [mk_image("wv_%d" % f, 60, 84, 120, 28,
                          "assets/img_apple_ai_waveform_frame%02d.png" % (f + 1),
                          hidden=True)
                 for f in range(5)]
    chat = [
        mk_container("hit_back", 14, 12, 44, 44, CLEAR, 0,
                     events=[ev("CLICKED", "back_home", [act_change(S("home"))])]),
        mk_image("img_back", 26, 18, 16, 16, "assets/img_apple_ai_chevron_left.png"),
        mk_image("img_star", 104, 10, 32, 32, "assets/img_apple_ai_star.png"),
        mk_image("img_more", 198, 18, 16, 16, "assets/img_apple_ai_more.png"),
        mk_label("lbl_title", 0, 46, SW, 28, "Gemini", "Title20", WHITE, "CENTER"),
        # user bubble (right, blue)
        mk_container("bubble_user", 96, 78, 120, 42, ABLUE, 12),
        mk_label("lbl_user", 108, 84, 98, 30, "天气怎么样？",
                 "Body15", WHITE, "LEFT"),
        # gemini reply bubble (left, navy)
        mk_container("bubble", 24, 128, 178, 52, BUBBLEC, 14),
        mk_label("lbl_bubble", 38, 134, 152, 40, "你好！今天有什么可以帮你？",
                 "Body15", WHITE, "LEFT"),
        # mic FAB -> enter voice mode
        mk_container("hit_voice", 94, 182, 52, 52, BTN, 26,
                     events=[ev("CLICKED", "to_voice",
                                [hide(O("ai", "chat_view")),
                                 show(O("ai", "voice_view"))])]),
        mk_image("img_mic_fab", 108, 196, 24, 24, "assets/img_apple_ai_mic.png"),
    ]
    # mic 3-state chain: idle -> listening -> speaking -> idle
    states = [("idle", "st_idle", "img_apple_ai_mic.png"),
              ("listen", "st_listen", "img_apple_ai_mic_listening.png"),
              ("speak", "st_speak", "img_apple_ai_mic_speaking.png")]
    voice = [
        mk_image("img_star2", 106, 14, 28, 28, "assets/img_apple_ai_star.png"),
        mk_label("lbl_title2", 0, 48, SW, 24, "Gemini", "Title20", WHITE, "CENTER"),
        mk_container("wv_container", 52, 82, 136, 32, CLEAR, 0, hidden=True,
                     children=wv_frames),
    ]
    for i, (key, nm, mic) in enumerate(states):
        nxt = states[(i + 1) % 3][1]
        # icons toggle in lockstep with their state containers, otherwise all
        # three stack on the same spot (idle mic + listening mic + audio-lines)
        acts = [hide(O("ai", nm)), show(O("ai", nxt)),
                hide(O("ai", "img_mic_%d" % i)),
                show(O("ai", "img_mic_%d" % ((i + 1) % 3)))]
        if key == "listen":
            acts += [show(O("ai", "wv_container"))]
        if key == "speak":
            acts += [hide(O("ai", "wv_container"))]
        voice.append(mk_container(nm, 86, 132, 68, 68, BTN, 34, hidden=(i > 0),
                                  children=None,
                                  events=[ev("CLICKED", "mic_%s" % key, acts)]))
        voice.append(mk_image("img_mic_%d" % i, 108, 154, 24, 24, "assets/" + mic,
                              hidden=(i > 0)))
    voice.append(mk_label("lbl_collapse", 76, 208, 88, 22, "收起", "Body15", T3,
                          "CENTER",
                          events=[ev("CLICKED", "to_chat",
                                     [hide(O("ai", "voice_view")),
                                      show(O("ai", "chat_view"))])]))
    ai = [mk_container("chat_view", 0, 0, SW, SH, CLEAR, 0, children=chat),
          mk_container("voice_view", 0, 0, SW, SH, CLEAR, 0, hidden=True,
                       children=voice)]
    screens["ai"] = {"bg": BLACK, "children": ai}

    # ------------------------------------------------------------ settings
    # chord-fit rows: each row's width follows the circle at its own height,
    # so the list visually hugs the round bezel (like the reference)
    rows = [("Wi-Fi", "已连接", "已关闭", "img_apple_settings_wifi.png", ABLUE),
            ("蓝牙", "开", "关", "img_apple_settings_bluetooth.png", ACYAN),
            ("显示", "自动", "手动", "img_apple_settings_brightness.png", AYELLOW),
            ("声音", "70%", "静音", "img_apple_settings_volume.png", APURPLE)]
    ROW_TOPS = [38, 74, 110, 146]
    se = [
        mk_label("lbl_title", 0, 8, SW, 26, "设置", "Title20", WHITE, "CENTER"),
    ]
    for i, (nm, va, vb, ico, colour) in enumerate(rows):
        top = ROW_TOPS[i]
        rx, _, rw, rh = row_geo(top)
        acts = [hide(O("settings", "va_%d" % i)),
                show(O("settings", "vb_%d" % i)),
                show(O("settings", "hit_%d" % i))]
        se.append(mk_container("row%d" % i, rx, top, rw, rh, CARDD, 12,
                           events=[ev("CLICKED", "row%d_toggle" % i, acts)]))
        se.append(mk_container("dot%d" % i, rx + 8, top + 5, 22, 22, colour, 11))
        se.append(mk_image("ico%d" % i, rx + 13, top + 10, 12, 12, "assets/" + ico))
        se.append(mk_label("nm%d" % i, rx + 36, top + 5, 40, 22, nm, "Body15",
                           [242, 242, 242, 255], "LEFT"))
        se.append(mk_label("va_%d" % i, rx + rw - 72, top + 7, 44, 18, va,
                           "Caption13", T3, "RIGHT"))
        se.append(mk_label("vb_%d" % i, rx + rw - 72, top + 7, 44, 18, vb,
                           "Caption13", T3, "RIGHT", hidden=True))
        se.append(mk_image("chev%d" % i, rx + rw - 24, top + 9, 10, 14,
                           "assets/img_apple_chevron.png"))
    for i, (nm, va, vb, ico, colour) in enumerate(rows):
        top = ROW_TOPS[i]
        rx, _, rw, rh = row_geo(top)
        se.append(mk_container("hit_%d" % i, rx, top, rw, rh, CLEAR, 12, hidden=True,
                           events=[ev("CLICKED", "row%d_back" % i,
                                      [show(O("settings", "va_%d" % i)),
                                       hide(O("settings", "vb_%d" % i)),
                                       hide(O("settings", "hit_%d" % i))])]))
    # about row (chord-fitted too)
    a3x, _, a3w, _ = row_geo(178)
    se += [
        mk_container("row3", a3x, 178, a3w, 32, CARDD, 12,
                     events=[ev("CLICKED", "open_about",
                                [show(O("settings", "panel_about"))])]),
        mk_container("dot3", a3x + 8, 183, 22, 22, AGRAY, 11),
        mk_image("ico3", a3x + 13, 188, 12, 12, "assets/img_apple_settings_info.png"),
        mk_label("nm3", a3x + 36, 183, 42, 22, "关于", "Body15", [242, 242, 242, 255], "LEFT"),
        mk_image("chev3", a3x + a3w - 24, 187, 10, 14, "assets/img_apple_chevron.png"),
        mk_container("panel_about", 0, 0, SW, SH, DIM, 0, hidden=True,
                     events=[ev("CLICKED", "close_about",
                                [hide(O("settings", "panel_about"))])],
                     children=[mk_container("a_card", 32, 76, 176, 88, CARDD, 16,
                                            children=[
            mk_label("a_title", 48, 88, 144, 22, "关于本机", "Body15", WHITE, "LEFT"),
            mk_label("a_body", 48, 112, 144, 44,
                     "AIWatch 圆形 240\n系统  PrimeClaw OS", "Caption13", T2, "LEFT"),
        ])]),
    ]
    screens["settings"] = {"bg": BLACK, "children": se}

    return screens


# --------------------------------------------------------------------------
# animations that are referenced by events
# --------------------------------------------------------------------------
def build_animations():
    # ai screen: a 5-frame chase over the waveform, looping forever
    for f in range(5):
        add_anim("wave %d" % f, O("ai", "wv_%d" % f),
                 [("opacity", [(0, f * 80), (255, f * 80 + 40), (0, f * 80 + 80)],
                   400)],
                 duration=400, path="linear", loop_infinite=True)
    # steps: one-shot confirmation pulse on the activity ring
    add_anim("ring start", O("steps", "arc_ring"),
             [("opacity", [(90, 0), (255, 220), (200, 320)], 320)],
             duration=320, path="ease_out")


# --------------------------------------------------------------------------
# project-specific screen wiring (engine hook, see build_project)
# --------------------------------------------------------------------------
def screen_events(name, props):
    """The ai screen starts its waveform chase as soon as it loads."""
    if name == "ai":
        props.append(ev("SCREEN_LOAD_START", "start_wave",
                        [act_anim("wave %d" % f, O("ai", "wv_%d" % f))
                         for f in range(5)]))


# --------------------------------------------------------------------------
# project descriptor - the whole engine contract, in one place
# --------------------------------------------------------------------------
PROJECT = {
    "name": PROJECT_NAME,
    "width": SW,
    "height": SH,
    "shape": "CIRCLE",
    "description": "AIWatch Apple 风格圆形表 UI — 240x240 CIRCLE, 7 屏 + 完整交互事件",
    "lvgl_version": "9.2.2",
    "theme_dark": True,
    "theme_color1": 5,
    "theme_color2": 0,
    "assets_subdir": "images_apple",
    # Own asset pack, so `python tools/build_squareline_apple.py` alone rebuilds
    # the archived project (no --assets flag needed).  Repo-root relative.
    "assets": "examples/AIWatchApple/assets",
    "spec_docs": SPEC_DOCS,
    "fonts": FONTS,
    "ranges_text": RANGES_TEXT,
    "ranges_num": RANGES_NUM,
    "symbols": SYMBOLS,
    "skip": SKIP,
    "screens": ALL_SCREENS,
    "order": ORDER,
    "initial_screen": "home",
    "build_screens": build_screens,
    "build_animations": build_animations,
    "screen_events": screen_events,
}
