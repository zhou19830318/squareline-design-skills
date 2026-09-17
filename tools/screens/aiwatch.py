#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AIWatch - 410x502 rectangular watch UI.  CONTENT LAYER.

Everything project-specific lives here: the palette, the font subsets, the spec
docs used for glyph headroom, the screen definitions.  The serialisation engine
is *imported*, never copied - see tools/engine/squareline_engine.py for why that
split exists (40 byte-identical functions used to be duplicated across two
1500-line builders).

Build:
    python tools/build_squareline_project.py
    python tools/build_squareline_project.py --assets examples/AIWatch/assets
    python tools/build_squareline_project.py --out /tmp/AIWatch

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
PROJECT_NAME = "AIWatch"
SW, SH = 410, 502                      # rectangular panel; must match info.width/height
SPEC_DOCS = ("AI手表UI设计规格文档.md", "AIWatch图片字体资源清单.md")

# source TTFs, copied into the project by the engine (fonts/ at the repo root)
REGULAR = "noto-sans-sc-v40-chinese-simplified-regular.ttf"
MEDIUM = "noto-sans-sc-v40-chinese-simplified-500.ttf"
BOLD = "noto-sans-sc-v40-chinese-simplified-700.ttf"

# --------------------------------------------------------------------------
# palette  (r, g, b, a)  --  4th component = opacity, as SquareLine stores it
# --------------------------------------------------------------------------

WHITE = [255, 255, 255, 255]
T2 = [255, 255, 255, 158]
T3 = [255, 255, 255, 97]
NEAR = [237, 237, 237, 255]
BLUE = [59, 130, 246, 255]
SKY = [46, 124, 246, 255]
PURPLE = [139, 92, 246, 255]
RED = [255, 90, 60, 255]
GREEN = [61, 216, 116, 255]
PINK = [255, 45, 138, 255]
YELLOW = [255, 214, 10, 255]
CARD = [20, 20, 22, 255]
GRAY = [46, 48, 54, 255]
BTN = [30, 32, 36, 255]
LINE = [38, 38, 42, 255]
BLACK = [0, 0, 0, 255]
HOME_BG = [8, 14, 26, 255]
BUBBLE = [48, 48, 90, 255]
CLEAR = [0, 0, 0, 0]
DIM = [0, 0, 0, 178]


# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
FONTS = [
    # codename, ttf, size, kind
    ("TimeDisplay72", BOLD, 72, "time"),
    ("NumberBold48", BOLD, 48, "number"),
    ("Title22", MEDIUM, 22, "text"),
    ("Body16", REGULAR, 16, "text"),
    ("Caption12", REGULAR, 12, "text"),
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
    "time": DIGITS + ":\u6708\u5468\u65e5\u4e0a\u4e0b\u5348",
    "number": DIGITS + ":.%-+\u00b0C\u6b65\u5361\u8def\u91cc\u516c\u91cc\u65f6",
    # "text" is filled in at build time from the strings the project really uses
    "text": "",
}


# --------------------------------------------------------------------------
# screens
# --------------------------------------------------------------------------
APP_ICONS = [
    ("clock", "时间", "img_home_icon_clock.png", BLUE, 0, 0),
    ("weather", "天气", "img_home_icon_weather.png", SKY, 0, 1),
    ("ai", "AI对话", "img_home_icon_ai.png", PURPLE, 0, 2),
    ("pomodoro", "番茄时钟", "img_home_icon_tomato.png", RED, 1, 0),
    ("steps", "计步", "img_home_icon_runner.png", GREEN, 1, 1),
    ("mp3", "MP3", "img_home_icon_music.png", PURPLE, 1, 2),
    ("settings", "设置", "img_home_icon_settings.png", GRAY, 2, 1),
]
COL_CX = [79, 205, 331]
ROW_TOP = [120, 244, 368]

ORDER = ["home", "clock", "weather", "ai", "pomodoro", "steps", "mp3", "settings"]
ALL_SCREENS = ORDER + ["ai_voice"]

# weather cycle: key, 72px icon, temperature, condition, range
WEATHER = [
    ("sunny", "img_weather_icon_sunny_72.png", "24°C", "晴", "26° / 14°"),
    ("cloudy", "img_weather_icon_cloudy_72.png", "18°C", "多云", "22° / 12°"),
    ("overcast", "img_weather_icon_overcast_72.png", "16°C", "阴", "20° / 11°"),
    ("rain", "img_weather_icon_rain_72.png", "13°C", "小雨", "16° / 9°"),
    ("heavyrain", "img_weather_icon_heavyrain_72.png", "11°C", "大雨", "14° / 8°"),
    ("thunder", "img_weather_icon_thunder_72.png", "12°C", "雷阵雨", "15° / 8°"),
    ("snow", "img_weather_icon_snow_72.png", "-2°C", "小雪", "1° / -6°"),
    ("fog", "img_weather_icon_fog_72.png", "14°C", "雾", "18° / 10°"),
]
HOURS = [("11时", "img_weather_icon_sunny_28.png", "20°"),
         ("14时", "img_weather_icon_cloudy_28.png", "21°"),
         ("17时", "img_weather_icon_overcast_28.png", "19°"),
         ("20时", "img_weather_icon_rain_28.png", "16°")]
HOUR_CX = [51, 154, 256, 359]

SONGS = [("Yesterday", "The Beatles", "01:24 / 02:03"),
         ("Hey Jude", "The Beatles", "00:42 / 07:11"),
         ("Imagine", "John Lennon", "02:05 / 03:07")]


def build_screens():
    screens = {}

    # ---------------------------------------------------------------- home
    ch = []
    for key, label, icon, colour, row, col in APP_ICONS:
        cx = COL_CX[col]
        top = ROW_TOP[row]
        ch.append(mk_container("ico_" + key, cx - 42, top, 84, 84, colour, 42,
                           events=[ev("CLICKED", "go_" + key, [act_change(S(key))])]))
        ch.append(mk_image("img_" + key, cx - 20, top + 22, 40, 40, "assets/" + icon))
        ch.append(mk_label("lb_" + key, cx - 55, top + 88, 110, 28, label,
                           "Title22", T2, "CENTER"))
    screens["home"] = {"bg": HOME_BG, "children": [
        mk_label("lbl_time", 32, 24, 190, 62, "10:27", "NumberBold48", WHITE, "LEFT",
                 events=[ev("CLICKED", "go_clock", [act_change(S("clock"))])]),
        mk_label("lbl_date", 32, 88, 230, 32, "4月26日 周六", "Title22", T2, "LEFT"),
        mk_image("img_wifi", 272, 38, 18, 18, "assets/img_status_wifi.png"),
        mk_image("img_battery", 300, 41, 22, 12, "assets/img_status_battery_frame.png"),
        mk_label("lbl_batt", 330, 30, 60, 30, "78%", "Title22", T2, "LEFT"),
    ] + ch}

    # --------------------------------------------------------------- clock
    screens["clock"] = {"bg": BLACK, "children": [
        mk_image("img_wallpaper", 0, 0, SW, SH, "assets/img_watchface_bg_01.png"),
        mk_label("lbl_date", 0, 146, SW, 32, "4月26日 周六", "Title22",
                 [255, 255, 255, 217], "CENTER"),
        mk_label("lbl_time", 0, 176, SW, 100, "10:27", "TimeDisplay72", WHITE, "CENTER"),
        mk_image("img_pin", 152, 294, 15, 17, "assets/img_watchface_icon_location.png"),
        mk_label("lbl_city", 175, 288, 90, 30, "北京", "Title22",
                 [255, 255, 255, 235], "LEFT"),
        mk_container("card_weather", 20, 408, 370, 80, [0, 0, 0, 97], 28,
                 events=[ev("CLICKED", "go_weather", [act_change(S("weather"))])]),
        mk_image("img_wico", 44, 424, 48, 48, "assets/img_watchface_icon_weather_mini.png"),
        mk_label("lbl_temp", 112, 420, 140, 34, "18°C", "Title22", WHITE, "LEFT"),
        mk_label("lbl_desc", 112, 456, 260, 26, "多云  22° / 12°", "Body16", T2, "LEFT"),
    ]}

    # ------------------------------------------------------------- weather
    wx = [
        mk_image("img_pin", 32, 26, 18, 18, "assets/img_weather_icon_location_pin.png"),
        mk_label("lbl_city", 58, 20, 120, 32, "北京", "Title22", NEAR, "LEFT"),
        mk_label("lbl_status", 250, 20, 128, 32, "10:27", "Title22", WHITE, "RIGHT"),
    ]
    region = (24, 84, 362, 248)
    for i, (key, ico, temp, desc, rng) in enumerate(WEATHER):
        nxt = (i + 1) % len(WEATHER)
        wx.append(mk_container("wx_%s" % key, region[0], region[1], region[2], region[3],
                           CLEAR, 0, hidden=(i > 0),
                           events=[ev("CLICKED", "wx_cycle_%s" % key,
                                      [hide(O("weather", "wx_%s" % key)),
                                       show(O("weather", "wx_%s" % WEATHER[nxt][0]))])],
                           children=[
            mk_image("img_big_%s" % key, 32, 92, 112, 112, "assets/" + ico),
            mk_label("lbl_temp_%s" % key, 172, 96, 190, 92, temp, "TimeDisplay72",
                     WHITE, "LEFT"),
            mk_label("lbl_sub_%s" % key, 172, 222, 200, 32, desc, "Title22", T2,
                     "LEFT"),
            mk_label("lbl_range_%s" % key, 172, 262, 194, 30, rng, "Title22", T3,
                     "LEFT"),
        ]))
    wx.append(mk_container("divider", 32, 308, 346, 1, LINE))
    for i in range(4):
        wx.append(mk_container("hl_%d" % i, HOUR_CX[i] - 52, 326, 104, 138,
                           [255, 255, 255, 22], 20, hidden=True))
    for i, (hh, ico, tt) in enumerate(HOURS):
        c = HOUR_CX[i]
        wx.append(mk_label("lbl_hour%d" % i, c - 48, 330, 96, 28, hh, "Title22",
                           T3, "CENTER"))
        wx.append(mk_image("img_hour%d" % i, c - 28, 364, 56, 56, "assets/" + ico))
        wx.append(mk_label("lbl_ht%d" % i, c - 48, 428, 96, 32, tt, "Title22", NEAR,
                           "CENTER"))
    for i in range(4):
        wx.append(mk_container("hit_hour%d" % i, HOUR_CX[i] - 52, 326, 104, 138, CLEAR, 0,
                           events=[ev("CLICKED", "pick_hour%d" % i,
                                      [show(O("weather", "hl_%d" % j)) if j == i
                                       else hide(O("weather", "hl_%d" % j))
                                       for j in range(4)])]))
    wx.append(mk_image("img_handle", 187, 486, 36, 4, "assets/img_weather_drag_handle.png"))
    screens["weather"] = {"bg": BLACK, "children": wx}

    # ------------------------------------------------------------------ ai
    hist = [("帮我写一份项目计划书", "04-26 09:15"),
            ("明天天气怎么样？", "04-25 20:32"),
            ("推荐一些适合阅读的书", "04-24 16:20")]
    ai = [
        mk_image("img_avatar_hd", 32, 28, 36, 36, "assets/img_ai_avatar_bot.png",
                 events=[ev("CLICKED", "go_voice", [act_change(S("ai_voice"))])]),
        mk_label("lbl_title", 80, 24, 150, 36, "AI对话", "Title22", WHITE, "LEFT"),
        mk_label("lbl_status", 250, 24, 128, 36, "10:27", "Title22", WHITE, "RIGHT"),
        mk_image("img_avatar_big", 32, 96, 80, 80, "assets/img_ai_avatar_bot.png"),
        mk_container("bubble", 124, 96, 248, 88, BUBBLE, 24),
        mk_label("lbl_bubble", 140, 112, 216, 58, "你好！有什么我可以帮你的吗？",
                 "Title22", WHITE, "LEFT"),
        mk_label("lbl_hist", 32, 216, 200, 32, "历史对话", "Title22", NEAR, "LEFT"),
    ]
    for i, (ttl, ts) in enumerate(hist):
        top = 252 + i * 78
        acts = []
        for j in range(len(hist)):
            v = 255 if j == i else 110
            acts.append(act_opa(O("ai", "row%d" % j), v))
            acts.append(act_opa(O("ai", "ttl%d" % j), v))
        ai.append(mk_pair_row("ai", i, top, ttl, ts, acts))
    screens["ai"] = {"bg": BLACK, "children": ai}

    # ------------------------------------------------------------ ai_voice
    wv_rect = (105, 236, 200, 60)
    wv_frames = [
        mk_image("wv_%d" % f, 105, 252, 200, 40,
                 "assets/img_ai_waveform_frame%02d.png" % (f + 1))
        for f in range(5)
    ]
    av = [
        mk_container("hit_back", 16, 16, 56, 56, CLEAR, 0,
                 events=[ev("CLICKED", "back_to_ai", [act_change(S("ai"))])]),
        mk_image("img_back", 37, 32, 14, 24, "assets/img_nav_back_arrow.png",
                 rotation=1800),
        mk_image("img_avatar", 165, 112, 80, 80, "assets/img_ai_avatar_bot.png"),
        mk_container("wv", wv_rect[0], wv_rect[1], wv_rect[2], wv_rect[3],
                 CLEAR, 0, hidden=True, children=wv_frames),
    ]
    states = [("idle", "st_idle", "img_ai_icon_mic_idle.png", "点击麦克风开始对话"),
              ("listen", "st_listen", "img_ai_icon_mic_listening.png", "正在聆听…"),
              ("speak", "st_speak", "img_ai_icon_mic_speaking.png", "AI 正在回复…")]
    for i, (key, nm, mic, txt) in enumerate(states):
        nxt = states[(i + 1) % 3][1]
        prv = states[(i - 1) % 3][1]
        acts = [hide(O("ai_voice", nm)), show(O("ai_voice", nxt))]
        if key == "idle":
            acts.append(show(O("ai_voice", "wv")))
        if key == "speak":
            acts.append(hide(O("ai_voice", "wv")))
        av.append(mk_container(nm, 0, 0, SW, SH, CLEAR, 0, hidden=(i > 0),
                           children=[
            mk_label("lbl_state_%d" % i, 0, 208, SW, 32, txt, "Title22", T2, "CENTER"),
            mk_container("mic_%d" % i, 157, 352, 96, 96, BTN, 48,
                     events=[ev("CLICKED", "voice_%s_to_%s" % (key, nxt), acts)],
                     children=[
                mk_image("img_mic_%d" % i, 181, 376, 48, 48, "assets/" + mic),
            ]),
        ]))
    screens["ai_voice"] = {"bg": BLACK, "children": av}

    # ------------------------------------------------------------ pomodoro
    po = [
        mk_image("img_ico", 32, 28, 32, 32, "assets/img_home_icon_tomato.png"),
        mk_label("lbl_title", 76, 24, 180, 36, "番茄时钟", "Title22", WHITE, "LEFT"),
        mk_label("lbl_status", 250, 24, 128, 36, "10:27", "Title22", WHITE, "RIGHT"),
        mk_arc("arc_ring", 81, 104, 248, 100, 100, PINK, [40, 40, 44, 255], 17),
        mk_image("img_tomato", 185, 178, 40, 40, "assets/img_home_icon_tomato.png"),
        mk_label("lbl_count", 105, 222, 200, 62, "25:00", "NumberBold48", WHITE, "CENTER"),
        mk_label("lbl_sub_idle", 105, 288, 200, 28, "专注时间", "Title22", T2, "CENTER"),
        mk_label("lbl_sub_run", 105, 288, 200, 28, "番茄钟运行中", "Title22", PINK,
                 "CENTER", hidden=True),
        mk_container("btn_run", 157, 378, 96, 96, PINK, 48,
                 events=[ev("CLICKED", "pomodoro_start",
                            [hide(O("pomodoro", "btn_run")),
                             show(O("pomodoro", "btn_pause")),
                             hide(O("pomodoro", "lbl_sub_idle")),
                             show(O("pomodoro", "lbl_sub_run")),
                             act_anim("ring start", O("pomodoro", "arc_ring"))])],
                 children=[mk_image("img_play", 188, 409, 34, 34,
                                    "assets/img_pomodoro_icon_play.png")]),
        mk_container("btn_pause", 157, 378, 96, 96, PINK, 48, hidden=True,
                 events=[ev("CLICKED", "pomodoro_stop",
                            [hide(O("pomodoro", "btn_pause")),
                             show(O("pomodoro", "btn_run")),
                             show(O("pomodoro", "lbl_sub_idle")),
                             hide(O("pomodoro", "lbl_sub_run"))])],
                 children=[mk_image("img_pause", 188, 409, 34, 34,
                                    "assets/img_pomodoro_icon_pause.png")]),
        mk_container("btn_list", 45, 390, 72, 72, BTN, 36,
                 events=[ev("CLICKED", "open_tasks",
                            [show(O("pomodoro", "panel_tasks"))])]),
        mk_image("img_list", 67, 412, 28, 28, "assets/img_pomodoro_icon_list.png"),
        mk_container("btn_cfg", 293, 390, 72, 72, BTN, 36,
                 events=[ev("CLICKED", "open_cfg",
                            [show(O("pomodoro", "panel_cfg"))])]),
        mk_image("img_cfg", 315, 412, 28, 28, "assets/img_pomodoro_icon_settings.png"),
    ]
    # task-list overlay
    tasks = [("写项目周报", "45分钟"), ("回复邮件", "25分钟"), ("整理资料", "15分钟")]
    tchildren = [mk_label("t_title", 44, 146, 240, 32, "任务清单", "Title22", WHITE,
                          "LEFT")]
    for i, (nm, tm) in enumerate(tasks):
        top = 196 + i * 58
        tchildren.append(mk_container("t_row%d" % i, 44, top, 322, 48, BTN, 16))
        tchildren.append(mk_label("t_nm%d" % i, 60, top + 10, 200, 28, nm, "Body16",
                                  NEAR, "LEFT"))
        tchildren.append(mk_label("t_tm%d" % i, 240, top + 10, 110, 28, tm, "Body16",
                                  T3, "RIGHT"))
    tchildren.append(mk_label("t_hint", 44, 372, 322, 24, "点击空白处关闭", "Caption12",
                              T3, "CENTER"))
    po.append(mk_container("panel_tasks", 0, 0, SW, SH, DIM, 0, hidden=True,
                       events=[ev("CLICKED", "close_tasks",
                                  [hide(O("pomodoro", "panel_tasks"))])],
                       children=[mk_container("t_card", 20, 120, 370, 262, CARD, 28,
                                          children=tchildren)]))
    # settings overlay
    opts = ["25 分钟", "45 分钟", "60 分钟"]
    cchildren = [mk_label("c_title", 44, 146, 240, 32, "专注时长", "Title22", WHITE,
                          "LEFT")]
    for i, o in enumerate(opts):
        top = 196 + i * 58
        cchildren.append(mk_container("c_hl%d" % i, 44, top, 322, 48,
                                  PINK if i == 0 else BTN, 16,
                                  hidden=(i > 0)))
        cchildren.append(mk_label("c_nm%d" % i, 60, top + 10, 240, 28, o,
                                  "Body16", NEAR, "LEFT"))
        cchildren.append(mk_container("c_hit%d" % i, 44, top, 322, 48, CLEAR, 16,
                                  events=[ev("CLICKED", "pick_cfg%d" % i,
                                             [show(O("pomodoro", "c_hl%d" % j)) if j == i
                                              else hide(O("pomodoro", "c_hl%d" % j))
                                              for j in range(3)])]))
    po.append(mk_container("panel_cfg", 0, 0, SW, SH, DIM, 0, hidden=True,
                       events=[ev("CLICKED", "close_cfg",
                                  [hide(O("pomodoro", "panel_cfg"))])],
                       children=[mk_container("c_card", 20, 120, 370, 262, CARD, 28,
                                          children=cchildren)]))
    screens["pomodoro"] = {"bg": BLACK, "children": po}

    # --------------------------------------------------------------- steps
    st = [
        mk_image("img_ico", 32, 28, 32, 32, "assets/img_home_icon_runner.png"),
        mk_label("lbl_title", 76, 24, 180, 36, "计步", "Title22", WHITE, "LEFT"),
        mk_label("lbl_status", 250, 24, 128, 36, "10:27", "Title22", WHITE, "RIGHT"),
        mk_arc("arc_ring", 93, 104, 224, 6820, 10000, GREEN, [61, 216, 116, 36], 16,
               bg_angles=(225, 223)),
        mk_image("img_shoe", 189, 168, 32, 32, "assets/img_steps_icon_shoe.png"),
        mk_label("lbl_steps", 105, 210, 200, 62, "6820步", "NumberBold48", WHITE, "CENTER"),
        mk_image("img_fire", 77, 348, 24, 24, "assets/img_steps_icon_fire.png"),
        mk_label("lbl_kcal", 113, 340, 90, 34, "320", "Title22", WHITE, "LEFT"),
        mk_label("lbl_kcal_u", 113, 374, 90, 24, "卡路里", "Body16", T3, "LEFT"),
        mk_image("img_loc", 241, 350, 20, 20, "assets/img_steps_icon_location.png"),
        mk_label("lbl_km", 273, 340, 80, 34, "4.8", "Title22", WHITE, "LEFT"),
        mk_label("lbl_km_u", 273, 374, 80, 24, "公里", "Body16", T3, "LEFT"),
        mk_container("btn_chart", 175, 426, 60, 60, BTN, 30,
                 events=[ev("CLICKED", "open_chart",
                            [show(O("steps", "panel_chart"))])]),
        mk_image("img_chart", 193, 444, 24, 24, "assets/img_steps_icon_chart.png"),
    ]
    week = ["一", "二", "三", "四", "五", "六", "日"]
    pct = [52, 68, 45, 80, 62, 90, 74]
    qchildren = [mk_label("q_title", 44, 146, 240, 32, "本周步数", "Title22", WHITE,
                          "LEFT")]
    for j in range(7):
        h = int(120 * pct[j] / 100.0)
        x = 46 + j * 44
        qchildren.append(mk_container("q_bar%d" % j, x, 330 - h, 24, h, GREEN, 8))
        qchildren.append(mk_label("q_day%d" % j, x - 10, 338, 44, 24, week[j],
                                  "Caption12", T3, "CENTER"))
    qchildren.append(mk_label("q_hint", 44, 372, 322, 24, "点击空白处关闭", "Caption12",
                              T3, "CENTER"))
    st.append(mk_container("panel_chart", 0, 0, SW, SH, DIM, 0, hidden=True,
                       events=[ev("CLICKED", "close_chart",
                                  [hide(O("steps", "panel_chart"))])],
                       children=[mk_container("q_card", 20, 120, 370, 262, CARD, 28,
                                          children=qchildren)]))
    screens["steps"] = {"bg": BLACK, "children": st}

    # ----------------------------------------------------------------- mp3
    mp = [
        mk_image("img_ico", 32, 32, 24, 24, "assets/img_music_icon_note.png"),
        mk_label("lbl_title", 68, 26, 130, 36, "MP3", "Title22", WHITE, "LEFT"),
        mk_label("lbl_status", 250, 26, 128, 36, "10:27", "Title22", WHITE, "RIGHT"),
    ]
    for i, (song, artist, tm) in enumerate(SONGS):
        grp = (32, 104, 346, 336)
        mp.append(mk_container("sg_%d" % i, grp[0], grp[1], grp[2], grp[3], CLEAR, 0,
                           hidden=(i > 0), children=[
            mk_image("img_album_%d" % i, 32, 104, 96, 96,
                     "assets/img_music_album_placeholder.png"),
            mk_label("lbl_song_%d" % i, 152, 118, 226, 40, song, "Title22", WHITE,
                     "LEFT"),
            mk_label("lbl_artist_%d" % i, 152, 162, 226, 30, artist, "Title22", T2,
                     "LEFT"),
            mk_label("lbl_t_%d" % i, 32, 414, 346, 26, tm, "Body16", T2, "CENTER"),
        ]))
    mp += [
        mk_container("btn_prev", 29, 296, 80, 80, CLEAR, 0),
        mk_image("img_prev", 53, 320, 32, 32, "assets/img_music_icon_prev.png"),
        mk_container("btn_stop", 153, 284, 104, 104, PINK, 52,
                 events=[ev("CLICKED", "music_pause",
                            [hide(O("mp3", "btn_stop")),
                             show(O("mp3", "btn_go"))])],
                 children=[mk_image("img_pause", 187, 318, 36, 36,
                                    "assets/img_music_icon_pause.png")]),
        mk_container("btn_go", 153, 284, 104, 104, PINK, 52, hidden=True,
                 events=[ev("CLICKED", "music_play",
                            [hide(O("mp3", "btn_go")),
                             show(O("mp3", "btn_stop")),
                             act_anim("track progress", O("mp3", "bar_fill"))])],
                 children=[mk_image("img_play", 187, 318, 36, 36,
                                    "assets/img_music_icon_play.png")]),
        mk_container("btn_next", 301, 296, 80, 80, CLEAR, 0),
        mk_image("img_next", 325, 320, 32, 32, "assets/img_music_icon_next.png"),
        mk_container("bar_track", 32, 396, 346, 6, [255, 255, 255, 36], 3),
        mk_container("bar_fill", 32, 396, 236, 6, PINK, 3),
        mk_container("btn_shfl_off", 36, 458, 26, 26, CLEAR, 0,
                 events=[ev("CLICKED", "shuffle_on",
                            [hide(O("mp3", "btn_shfl_off")),
                             show(O("mp3", "btn_shfl_on"))])]),
        mk_image("img_shfl_off", 36, 458, 26, 26, "assets/img_music_icon_shuffle.png"),
        mk_container("btn_shfl_on", 36, 458, 26, 26, CLEAR, 0, hidden=True,
                 events=[ev("CLICKED", "shuffle_off",
                            [hide(O("mp3", "btn_shfl_on")),
                             show(O("mp3", "btn_shfl_off"))])]),
        mk_image("img_shfl_on", 36, 458, 26, 26,
                 "assets/img_music_icon_shuffle_active.png"),
        mk_image("img_volume", 348, 458, 26, 26, "assets/img_music_icon_volume.png"),
    ]
    # next / prev cycle: 3-state ring of hit panels over each transport button
    for k in range(3):
        cur, nxt = k, (k + 1) % 3
        prev = (k - 1) % 3
        mp.append(mk_container("nh_%d" % k, 301, 296, 80, 80, CLEAR, 0, hidden=(k > 0),
                           events=[ev("CLICKED", "music_next_%d" % k,
                                      [hide(O("mp3", "sg_%d" % cur)),
                                       show(O("mp3", "sg_%d" % nxt)),
                                       hide(O("mp3", "nh_%d" % k)),
                                       show(O("mp3", "nh_%d" % nxt)),
                                       hide(O("mp3", "ph_%d" % k)),
                                       show(O("mp3", "ph_%d" % nxt))])]))
    for k in range(3):
        cur, prev = k, (k - 1) % 3
        mp.append(mk_container("ph_%d" % k, 29, 296, 80, 80, CLEAR, 0, hidden=(k > 0),
                           events=[ev("CLICKED", "music_prev_%d" % k,
                                      [hide(O("mp3", "sg_%d" % cur)),
                                       show(O("mp3", "sg_%d" % prev)),
                                       hide(O("mp3", "ph_%d" % k)),
                                       show(O("mp3", "ph_%d" % prev)),
                                       hide(O("mp3", "nh_%d" % k)),
                                       show(O("mp3", "nh_%d" % prev))])]))
    screens["mp3"] = {"bg": BLACK, "children": mp}

    # ------------------------------------------------------------ settings
    # mockup: icon + name + right-aligned value + chevron.  Tapping the row
    # flips the value; an overlay hit panel (armed only after the flip) flips
    # it back, which gives a working two-state toggle with built-in actions.
    rows = [("蓝牙", "已连接", "未连接", "img_settings_icon_bluetooth.png", BLUE),
            ("亮度", "自动", "手动", "img_settings_icon_brightness.png", YELLOW),
            ("声音", "70%", "静音", "img_settings_icon_volume.png", PURPLE),
            ("语言", "简体中文", "English", "img_settings_icon_language.png", SKY),
            ("关于本机", "", "", "img_settings_icon_about.png", GRAY)]
    se = [
        mk_image("img_ico", 32, 32, 22, 22, "assets/img_settings_icon_gear.png"),
        mk_label("lbl_title", 66, 26, 150, 36, "设置", "Title22", WHITE, "LEFT"),
        mk_label("lbl_status", 250, 26, 128, 36, "10:27", "Title22", WHITE, "RIGHT"),
    ]
    for i, (nm, va, vb, ico, colour) in enumerate(rows):
        top = 96 + i * 80
        if va:
            acts = [hide(O("settings", "va_%d" % i)),
                    show(O("settings", "vb_%d" % i)),
                    show(O("settings", "hit_%d" % i))]
        else:
            acts = [show(O("settings", "panel_about"))]
        se.append(mk_container("row%d" % i, 32, top, 346, 70, CARD, 28,
                           events=[ev("CLICKED", "row%d_toggle" % i, acts)]))
        se.append(mk_container("dot%d" % i, 54, top + 13, 44, 44, colour, 22))
        se.append(mk_image("ico%d" % i, 65, top + 24, 22, 22, "assets/" + ico))
        se.append(mk_label("nm%d" % i, 116, top + 19, 90, 32, nm, "Title22",
                           [242, 242, 242, 255], "LEFT"))
        if va:
            se.append(mk_label("va_%d" % i, 210, top + 21, 130, 28, va, "Title22",
                               T3, "RIGHT"))
            se.append(mk_label("vb_%d" % i, 210, top + 21, 130, 28, vb, "Title22",
                               T3, "RIGHT", hidden=True))
        se.append(mk_image("chev%d" % i, 344, top + 25, 12, 20,
                           "assets/img_nav_back_arrow.png"))
    for i, (nm, va, vb, ico, colour) in enumerate(rows):
        if not va:
            continue
        top = 96 + i * 80
        se.append(mk_container("hit_%d" % i, 32, top, 346, 70, CLEAR, 28, hidden=True,
                           events=[ev("CLICKED", "row%d_back" % i,
                                      [show(O("settings", "va_%d" % i)),
                                       hide(O("settings", "vb_%d" % i)),
                                       hide(O("settings", "hit_%d" % i))])]))
    se.append(mk_container("panel_about", 0, 0, SW, SH, DIM, 0, hidden=True,
                       events=[ev("CLICKED", "close_about",
                                  [hide(O("settings", "panel_about"))])],
                       children=[mk_container("a_card", 20, 150, 370, 200, CARD, 28,
                                          children=[
            mk_label("a_title", 44, 176, 240, 32, "关于本机", "Title22", WHITE,
                     "LEFT"),
            mk_label("a_body", 44, 222, 322, 100,
                     "AIWatch 智能手表\n型号  AIW-410\n系统  PrimeClaw OS 1.1\n"
                     "屏幕  410 × 502",
                     "Body16", T2, "LEFT"),
        ])]))
    screens["settings"] = {"bg": BLACK, "children": se}

    return screens


def mk_pair_row(screen, i, top, ttl, ts, acts):
    return mk_container("row%d" % i, 32, top, 346, 70, CARD, 24,
                    events=[ev("CLICKED", "hist_%d" % i, acts)],
                    children=[
        mk_image("ico%d" % i, 52, top + 21, 28, 28,
                 "assets/img_ai_icon_history_bubble.png"),
        mk_label("ttl%d" % i, 92, top + 10, 270, 28, ttl, "Title22",
                 [242, 242, 242, 255], "LEFT"),
        mk_label("ts%d" % i, 92, top + 40, 270, 22, ts, "Caption12", T3, "LEFT"),
    ])


# --------------------------------------------------------------------------
# animations that are referenced by events
# --------------------------------------------------------------------------
def build_animations():
    # ai_voice: a 5-frame chase over the waveform, looping forever
    for f in range(5):
        add_anim("wave %d" % f, O("ai_voice", "wv_%d" % f),
                 [("opacity", [(0, f * 80), (255, f * 80 + 40), (0, f * 80 + 80)],
                   400)],
                 duration=400, path="linear", loop_infinite=True)
    # pomodoro: one-shot confirmation pulse on the ring
    add_anim("ring start", O("pomodoro", "arc_ring"),
             [("opacity", [(90, 0), (255, 220), (200, 320)], 320)],
             duration=320, path="ease_out")
    # mp3: progress bar sweeps to full over the length of the track
    add_anim("track progress", O("mp3", "bar_fill"),
             [("width", [(236, 0), (346, 123000)], 123000)],
             duration=123000, path="linear")


# --------------------------------------------------------------------------
# project-specific screen wiring (engine hook, see build_project)
# --------------------------------------------------------------------------
def screen_events(name, props):
    """ai_voice is not part of the swipe ring: swiping right goes back to `ai`,
    and the waveform chase starts when the screen loads."""
    if name not in ORDER:
        props.append(ev("GESTURE_RIGHT(GESTURE)", "scr_back",
                        [act_change(S("ai"))]))
        props.append(ev("SCREEN_LOAD_START", "start_wave",
                        [act_anim("wave %d" % f, O("ai_voice", "wv_%d" % f))
                         for f in range(5)]))


# --------------------------------------------------------------------------
# project descriptor - the whole engine contract, in one place
# --------------------------------------------------------------------------
PROJECT = {
    "name": PROJECT_NAME,
    "width": SW,
    "height": SH,
    "shape": "RECTANGLE",
    "description": "AIWatch 智能手表 UI — 9 屏 + 完整交互事件",
    "lvgl_version": "9.2.2",
    "theme_dark": True,
    "theme_color1": 5,
    "theme_color2": 0,
    "assets_subdir": "images",
    # Own asset pack (repo-root relative) so the bare build command rebuilds the
    # archived project without `--assets`.
    "assets": "examples/AIWatch/assets",
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
