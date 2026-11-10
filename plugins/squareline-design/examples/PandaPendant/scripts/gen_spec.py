#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate PandaPendant.spec.json + assets.manifest.json (+ nav table for the docs) with the plugin's
`specbuilder` widget library.  Text is placed by where its INK should be (real LVGL font metrics).
Re-run after editing, then `slx.py build`.   All rects are screen-absolute (360x360 round, r=180)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
for _c in (os.environ.get("SLX_TOOLS"), os.path.join(HERE, "..", "..", "..", "tools"), "/home/claude/plugin/squareline-design/tools"):
    if _c and os.path.exists(os.path.join(_c, "specbuilder.py")):
        sys.path.insert(0, _c)
        break
from specbuilder import Project                       # noqa: E402

NAME = "PandaPendant"
PALETTE = {
    "BG": "#000000",          # dark UI pages (settings, lists)                     [测得]
    "SHELL": "#F7F5F9",       # face screens: fur white that merges with the shell [估算]
    "CARD": "#0F1729", "CARD2": "#1B2538", "TRACK": "#24304A",
    "WHITE": "#FFFFFF", "DIM": "#8E9AB5", "CYAN": "#40CAFB", "WAVE": "#15C7FD", "BLUE2": "#1F7AE0",
    "GREEN": "#31DA38", "AMBER": "#FFB020", "RED": "#F85C7A", "PILL": "#000000B3",
}
T = "noto-sans-sc-v40-chinese-simplified-%s.ttf"
FONTS = [{"codename": "Big60", "ttf": T % "700", "size": 60, "kind": "number"},
         {"codename": "Title22", "ttf": T % "500", "size": 22, "kind": "text"},
         {"codename": "Body18", "ttf": T % "regular", "size": 18, "kind": "text"},
         {"codename": "Small16", "ttf": T % "regular", "size": 16, "kind": "text"}]
P = Project(NAME, 360, 360, "CIRCLE", PALETTE, FONTS, ranges_num=["0x30-0x3A"], touch_feedback=190)
label, image, panel, go, acts = P.label, P.image, P.panel, P.go, P.acts

FACE = {"idle": "face_01_idle", "happy": "face_02_happy_wink", "curious": "face_03_curious", "surprised": "face_04_surprised",
        "laugh": "face_05_laugh", "listen": "face_07_listen", "speak": "face_08_speak", "sleepy": "face_09_sleepy",
        "sleep": "face_10_sleep", "sad": "face_11_sad", "confused": "face_12_confused", "angry": "face_13_angry",
        "shy": "face_14_shy", "confident": "face_15_confident", "cried": "face_16_cried", "love": "face_17_love",
        "tired": "face_18_tired", "abnormal": "face_19_abnormal", "celebrate": "face_20_celebrate"}


def face(key, events=None):
    return image("face", [0, 0, 360, 360], FACE[key], events=events)


def add(name, kind, desc, children, face_key=None, events=None, gestures=None):
    P.screen(name, children, kind=kind, desc=desc, face=face_key, events=events, gestures=gestures,
             bg="SHELL" if kind in ("face", "emotion") else "BG")


def build_faces():
    add("home", "face", "Idle / default home. Hosts all home gestures. Hidden unread badge (UI_EVT_NOTIFICATION).",
        [face("idle", [go("listening")]),
         panel("badge", [257, 47, 26, 26], "RED", 13, hidden=True, children=[label("badge_n", 270, 60, 26, "1", "Small16", "WHITE")])],
        "idle", gestures={"GESTURE_DOWN": "quick_settings", "GESTURE_UP": "notification", "GESTURE_LEFT": "time_weather", "GESTURE_RIGHT": "personality"})
    add("wakeup", "face", "Wakeup: eyes open (runtime frame sequence). Hand-over to listening is event-driven (tap = demo).",
        [face("idle", [go("listening")])], "idle")
    add("listening", "face", "Listening: focused face + volume waveform (bars resized/opacity by audio level).",
        [face("listen", [go("thinking")])] + P.bars([10, 18, 28, 16, 34, 20, 30, 14, 8]), "listen", gestures={"GESTURE_DOWN": "home"})
    add("thinking", "face", "Thinking: face + 3 pulsing cyan dots on the forehead.",
        [face("curious", [go("speaking")])] + P.dots(), "curious")
    add("speaking", "face", "Speaking: mouth frames follow TTS (runtime); tap = interrupt.",
        [face("speak", [go("home")])], "speak", gestures={"GESTURE_DOWN": "home"})
    add("asr_failed", "face", "ASR failed: confused face + 没听清; tap = retry.",
        [face("confused", [go("listening")]), P.pill("icon_mic_off", "没听清")], "confused")
    add("llm_error", "face", "LLM request failed: confused face + 暂时无法回答; tap = retry.",
        [face("confused", [go("thinking")]), P.pill("icon_cloud_off", "暂时无法回答")], "confused")
    add("tts_error", "face", "TTS playback failed: mouth stopped (sad frame) + 播放失败; tap = back to idle.",
        [face("sad", [go("home")]), P.pill("icon_volume_x", "播放失败")], "sad")
    add("network_lost", "face", "Network lost: worried face + 网络已断开.",
        [face("abnormal", [go("reconnecting")]), P.pill("icon_wifi_off", "网络已断开")], "abnormal")
    add("reconnecting", "face", "Reconnecting: expectant face + 重新连接中 prompt.",
        [face("curious", [go("home")]), P.pill("icon_refresh_cw", "重新连接中")], "curious")
    add("battery_low", "face", "Low battery: tired face + 电量低 15% (reduce animation FPS in runtime).",
        [face("tired", [go("home")]), P.pill("icon_battery_low", "电量低 15%")], "tired")
    for scr, key, en in [("face_happy", "happy", "Happy"), ("face_laugh", "laugh", "Laugh"), ("face_excited", "celebrate", "Excited"),
                         ("face_curious", "curious", "Curious"), ("face_surprised", "surprised", "Surprised"), ("face_shy", "shy", "Shy"),
                         ("face_sad", "sad", "Sad"), ("face_confused", "confused", "Confused"), ("face_angry", "angry", "Angry"),
                         ("face_love", "love", "Love"), ("face_sleepy", "sleepy", "Sleepy"), ("face_sleep", "sleep", "Sleep"),
                         ("face_confident", "confident", "Confident (board only)"), ("face_cried", "cried", "Cried (board only)")]:
        add(scr, "emotion", "%s emotion frame. Tap = home; swipe right = character preview." % en,
            [face(key, [go("home")])], key, gestures={"GESTURE_RIGHT": "character_preview_1"})


def build_aux():
    add("time_weather", "aux", "Time, date, weather. Face stays small and un-covered. Swipe right = home.",
        [label("clock", 180, 70, 170, "14:30", "Big60"),
         label("date", 180, 118, 200, "11月7日 周五", "Body18", "DIM"),
         image("face_mini", [95, 137, 170, 170], "face_mini_idle"),
         image("wx_icon", [143, 312, 24, 24], "icon_cloud_sun"),
         label("wx_temp", 0, 324, 60, "26°C", "Body18", "WHITE", "LEFT", x=173)],
        "idle", gestures={"GESTURE_RIGHT": "home"})

    def card(i, y, h, icon, src, tm, ttl, body):
        ch = [image("n%d_ic" % i, [72, y + 12, 20, 20], icon),
              label("n%d_src" % i, 0, y + 22, 90, src, "Small16", "DIM", "LEFT", x=98),
              label("n%d_time" % i, 0, y + 22, 60, tm, "Small16", "DIM", "RIGHT", x=232),
              label("n%d_title" % i, 0, y + 46, 216, ttl, "Body18", "WHITE", "LEFT", x=72)]
        if body:
            ch.append(label("n%d_body" % i, 0, y + 68, 216, body, "Small16", "DIM", "LEFT", x=72))
        return panel("n%d" % i, [58, y, 244, h], "CARD", 18, children=ch)
    add("notification", "aux", "Notification list: source, title, short body. Vertical scroll in runtime; swipe right = home.",
        [P.title("通知", 36), card(1, 62, 82, "icon_message_circle", "消息", "14:28", "小李", "晚上一起吃饭吗？"),
         card(2, 152, 82, "icon_calendar", "日程", "14:00", "团队周会", "15:00 · 会议室 B"),
         card(3, 242, 56, "icon_bell", "提醒", "13:45", "记得喝水", None)], gestures={"GESTURE_RIGHT": "home"})

    qs = [P.title("快捷设置", 38)]
    qs += P.toggle_tile("wifi", 94, 120, "icon_wifi", "Wi-Fi", on=True)
    qs += P.toggle_tile("bt", 180, 120, "icon_bluetooth", "蓝牙", on=True)
    qs += P.link_tile("bright", 266, 120, "icon_sun", "亮度", "system_settings")
    qs += P.link_tile("vol", 94, 236, "icon_volume_2", "音量", "system_settings")
    qs += P.toggle_tile("dnd", 180, 236, "icon_bell_off", "勿扰", on=False)
    qs += P.link_tile("sleep", 266, 236, "icon_moon", "睡眠", "face_sleep")
    add("quick_settings", "aux", "Quick settings: Wi-Fi/BT/DND toggles, brightness+volume -> system settings, sleep. Swipe up = home.",
        qs, gestures={"GESTURE_UP": "home"})

    pc = [P.title("个性化", 36)]
    pc += P.chip_group("pers", "性格", 82, ["活泼", "温柔", "安静"], 1, 80, 8, 96)
    pc += P.chip_group("fb", "反馈强度", 154, ["弱", "中", "强"], 1, 80, 8, 168)
    pc += P.chip_group("act", "动画活跃度", 226, ["低", "中", "高"], 1, 80, 8, 240)
    pc.append(P.chevron_link("link_sleep", [110, 292, 140, 32], "睡眠设置", "sleep_settings"))
    add("personality", "aux", "Personality: character, feedback strength, animation activity. Swipe left = home.", pc, gestures={"GESTURE_LEFT": "home"})

    sc = [P.title("睡眠设置", 36)]
    sc += P.chip_group("auto", "自动休眠", 82, ["1分钟", "5分钟", "10分钟", "从不"], 1, 62, 6, 96)
    sc += P.chip_group("wake", "唤醒方式", 154, ["触摸", "语音", "都可以"], 2, 80, 8, 168)
    sc.append(label("anim_lbl", 0, 258, 120, "睡眠动画", "Body18", "WHITE", "LEFT", x=64))
    sc += P.switch("sw_anim", 252, 258, on=True)
    add("sleep_settings", "aux", "Sleep settings: auto-sleep timeout, wake method, sleep animation. Swipe right = personality.", sc,
        gestures={"GESTURE_RIGHT": "personality"})

    def kv(prefix, key, val, cy):
        return [label("%s_k" % prefix, 0, cy, 110, key, "Body18", "WHITE", "LEFT", x=62),
                label("%s_v" % prefix, 0, cy, 130, val, "Small16", "DIM", "RIGHT", x=168)]
    ss = [P.title("系统设置", 36)]
    ss += kv("bri", "亮度", "80%", 84) + P.slider("bri_s", 62, 104, 236, 80)
    ss += kv("volm", "音量", "60%", 142) + P.slider("volm_s", 62, 162, 236, 60)
    ss += kv("net", "网络", "Wi-Fi 已连接", 204) + kv("tsync", "时间同步", "自动", 240)
    ss.append(P.chevron_link("link_info", [100, 280, 160, 32], "存储与版本", "system_info"))
    add("system_settings", "aux", "System settings: brightness, volume, network, time sync. Swipe right = quick settings.", ss,
        gestures={"GESTURE_RIGHT": "quick_settings"})

    si = [P.title("存储与版本", 36),
          label("sd_k", 0, 84, 110, "SD 卡", "Body18", "WHITE", "LEFT", x=62), label("sd_v", 0, 84, 150, "12.3 / 29.8 GB", "Small16", "DIM", "RIGHT", x=148)]
    si += P.slider("sd_s", 62, 104, 236, 41)[:2]
    si += [label("ver_k", 0, 142, 110, "版本", "Body18", "WHITE", "LEFT", x=62), label("ver_v", 0, 142, 130, "v2.0.0", "Small16", "DIM", "RIGHT", x=168),
           P.chevron_link("link_prev", [86, 176, 188, 36], "角色预览", "character_preview_1"),
           P.chevron_link("link_exp", [86, 218, 188, 36], "表情管理", "expression_manager"),
           P.chevron_link("link_anim", [86, 260, 188, 36], "动画管理", "animation_manager")]
    add("system_info", "aux", "Storage + version, entry points to dev/preview pages. Swipe right = system settings.", si,
        gestures={"GESTURE_RIGHT": "system_settings"})

    pv = [("face_01_idle", "home"), ("face_02_happy_wink", "face_happy"), ("face_03_curious", "face_curious"), ("face_04_surprised", "face_surprised"),
          ("face_05_laugh", "face_laugh"), ("face_07_listen", "listening"), ("face_08_speak", "speaking"), ("face_09_sleepy", "face_sleepy"),
          ("face_10_sleep", "face_sleep"), ("face_11_sad", "face_sad"), ("face_12_confused", "face_confused"), ("face_13_angry", "face_angry"),
          ("face_14_shy", "face_shy"), ("face_15_confident", "face_confident"), ("face_16_cried", "face_cried"), ("face_17_love", "face_love"),
          ("face_18_tired", "battery_low"), ("face_19_abnormal", "network_lost"), ("face_20_celebrate", "face_excited")]
    for pi, items in enumerate([pv[:10], pv[10:]], 1):
        kids, k = [P.title("角色预览", 38)], 0
        for cnt, cy in [(3, 96), (4, 164), (3, 232)]:
            for c in range(cnt):
                if k >= len(items):
                    break
                asset, tgt = items[k]
                x = 180 - (cnt * 60 + (cnt - 1) * 8) // 2 + c * 68
                kids.append(image("th_%02d" % (k + 1), [x, cy - 30, 60, 60], asset.replace("face_", "thumb_"), [go(tgt)]))
                k += 1
        kids.append(label("page", 180, 296, 80, "%d / 3" % pi, "Small16", "DIM"))
        g = {"GESTURE_LEFT": "character_preview_2"} if pi == 1 else {"GESTURE_RIGHT": "character_preview_1", "GESTURE_LEFT": "state_preview"}
        if pi == 1:
            g["GESTURE_RIGHT"] = "system_info"
        add("character_preview_%d" % pi, "aux", "Character preview page %d/3: tap a thumbnail to open that expression. Swipe left/right = page." % pi, kids, gestures=g)

    states = [("唤醒", "wakeup"), ("聆听", "listening"), ("思考", "thinking"), ("说话", "speaking"), ("没听清", "asr_failed"), ("无法回答", "llm_error"),
              ("播放失败", "tts_error"), ("网络断开", "network_lost"), ("重连中", "reconnecting"), ("低电量", "battery_low")]
    kids = [P.title("状态预览", 38)]
    for k, (txt, tgt) in enumerate(states):
        x, y = 66 + (k % 2) * 120, 70 + (k // 2) * 42
        kids += [panel("st_%d" % (k + 1), [x, y, 108, 32], "CARD2", 16, [go(tgt)]), label("st_%d_t" % (k + 1), x + 54, y + 16, 108, txt, "Small16", "WHITE")]
    kids.append(label("page", 180, 296, 80, "3 / 3", "Small16", "DIM"))
    add("state_preview", "aux", "State preview page 3/3: jump to every voice/error state (they are event-driven on device). Swipe right = page 2.",
        kids, gestures={"GESTURE_RIGHT": "character_preview_2"})

    def mrow(i, y, name, meta, ok=True):
        return panel("r%d" % i, [58, y, 244, 36], "CARD", 18, children=[
            label("r%d_n" % i, 0, y + 18, 120, name, "Body18", "WHITE", "LEFT", x=76),
            label("r%d_m" % i, 0, y + 18, 70, meta, "Small16", "DIM", "RIGHT", x=190),
            image("r%d_s" % i, [276, y + 8, 20, 20], "icon_circle_check" if ok else "icon_triangle_alert")])
    em = [P.title("表情管理", 34), label("sum", 180, 66, 220, "19 个表情 · 已就绪 18", "Small16", "DIM")]
    for i, (n, m, ok) in enumerate([("首页陪伴", "24 帧", True), ("开心", "20 帧", True), ("好奇", "18 帧", True), ("聆听", "22 帧", True), ("疲惫", "缺失", False)]):
        em.append(mrow(i + 1, 86 + i * 44, n, m, ok))
    add("expression_manager", "aux", "Expression resource list (name, frames, status). Missing resource shows the fallback state. Swipe right = system info.",
        em, gestures={"GESTURE_RIGHT": "system_info"})

    def arow(i, y, name, meta, st, color):
        return panel("a%d" % i, [58, y, 244, 50], "CARD", 18, children=[
            label("a%d_n" % i, 0, y + 15, 150, name, "Body18", "WHITE", "LEFT", x=76),
            label("a%d_s" % i, 0, y + 15, 70, st, "Small16", color, "RIGHT", x=222),
            label("a%d_m" % i, 0, y + 36, 190, meta, "Small16", "DIM", "LEFT", x=76)])
    an = [P.title("动画管理", 34)]
    for i, (n, m, st, c) in enumerate([("anim_idle", "24 帧 · 12 FPS", "已加载", "GREEN"), ("anim_listening", "22 帧 · 15 FPS", "已加载", "GREEN"),
                                       ("anim_speaking", "20 帧 · 15 FPS", "加载中", "CYAN"), ("anim_sleep", "16 帧 · 12 FPS", "待加载", "DIM")]):
        an.append(arow(i + 1, 62 + i * 58, n, m, st, c))
    add("animation_manager", "aux", "Animation resource list (frames, FPS, load state). Swipe right = system info.", an,
        gestures={"GESTURE_RIGHT": "system_info"})


def build_anims():
    for n, lo, hi, d in (("think dot 1", 255, 90, 900), ("think dot 2", 90, 255, 900), ("think dot 3", 255, 90, 1200)):
        P.animation(n, "thinking/dot_%s" % n[-1], "opacity", [[lo, 0], [hi, d // 2], [lo, d]], d)
    P.on_load("thinking", *[P.play("think dot %d" % i, "thinking/dot_%d" % i) for i in (1, 2, 3)])


ICONS = [("icon_wifi", "wifi", 30, "#FFFFFF"), ("icon_bluetooth", "bluetooth", 30, "#FFFFFF"), ("icon_sun", "sun", 30, "#FFFFFF"),
         ("icon_volume_2", "volume-2", 30, "#FFFFFF"), ("icon_bell_off", "bell-off", 30, "#FFFFFF"), ("icon_moon", "moon", 30, "#FFFFFF"),
         ("icon_mic_off", "mic-off", 16, "#FFB020"), ("icon_cloud_off", "cloud-off", 16, "#FFB020"), ("icon_volume_x", "volume-x", 16, "#FFB020"),
         ("icon_wifi_off", "wifi-off", 16, "#FFB020"), ("icon_refresh_cw", "refresh-cw", 16, "#40CAFB"), ("icon_battery_low", "battery-low", 16, "#FFB020"),
         ("icon_cloud_sun", "cloud-sun", 24, "#FFC857"), ("icon_message_circle", "message-circle", 20, "#7BDBFB"), ("icon_calendar", "calendar", 20, "#8E9AFC"),
         ("icon_bell", "bell", 20, "#FFB020"), ("icon_chevron_right", "chevron-right", 16, "#8E9AB5"),
         ("icon_circle_check", "circle-check", 20, "#31DA38"), ("icon_triangle_alert", "triangle-alert", 20, "#FFB020")]


def main():
    build_faces()
    build_aux()
    build_anims()
    spec = P.write(os.path.join(PROJ, "%s.spec.json" % NAME),
                   description="Panda AI Pendant V2.0 - 360x360 round, face-only UI (Hybrid: SD-card frames + LVGL overlays)")
    with open(os.path.join(PROJ, "assets.manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"defaults": {"size": 24, "color": "#FFFFFF", "stroke_width": 2},
                   "icons": [{"name": n, "source": "lucide", "icon": i, "size": s, "color": c} for n, i, s, c in ICONS]}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(HERE, "nav.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(P.nav, fh, ensure_ascii=False, indent=1)
    print("screens: %d | animations: %d" % (len(spec["screens"]), len(spec["animations"])))


if __name__ == "__main__":
    sys.exit(main())
