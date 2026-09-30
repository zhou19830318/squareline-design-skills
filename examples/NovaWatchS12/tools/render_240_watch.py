# -*- coding: utf-8 -*-
"""
NovaWatchS12 — 240x240 圆形表盘 UI 渲染器（仿 Apple Watch Series 12 设计语言）

源真相：
  - UI需求清单.md            （屏幕清单 / 交互 / 文案 / 配色）
  - NovaWatchS12.spec.json   （456x456 绝对坐标版对象清单，本脚本按 240 画布重排）
  - assets/images/*.png      （全部为 alpha 蒙版线稿图标，可任意着色）
  - squareline/.../fonts/*.ttf（Noto Sans SC 700/500/400）

输出：preview_240/
  01_watchface.png ... 10_settings.png   （10 屏 240x240，圆外透明）
  variants_states.png                    （voice 三态 / workout 进行中 / alarms 关）
  overview_240.png                       （10 屏总览）

做法：4x 超采样（960）绘制矢量+文字 → LANCZOS 降到 240 → 圆形蒙版（边缘自带 AA）。
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets", "images")
FONTS = os.path.join(ROOT, "squareline", "NovaWatchS12", "assets", "fonts")
OUT = os.path.join(ROOT, "preview_240")

S = 4                 # 超采样倍率
W = 240               # 设计尺寸
R = W / 2.0           # 120
SAFE = 112.0          # 内容安全半径（spec 约定 r<=216 @456 → 112 @240）


# ----------------------------------------------------------------------------- 调色板
def hx(h: str, a: int = 255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


BG = hx("#000000")
CARD = hx("#1C1C1E")
CARD2 = hx("#2C2C2E")
TRACK = hx("#39393D")
DIM = hx("#98989F")
WHITE = hx("#FFFFFF")
GREEN = hx("#30D158")
BLUE = hx("#0A84FF")
ORANGE = hx("#FF9F0A")
PINK = hx("#FF2D55")
RED = hx("#FF453A")
HALO = (0, 0, 0, 185)          # 文字/指针的黑色描边（保证压在表盘上也可读）

FONT_FILES = {
    700: "noto-sans-sc-v40-chinese-simplified-700.ttf",
    500: "noto-sans-sc-v40-chinese-simplified-500.ttf",
    400: "noto-sans-sc-v40-chinese-simplified-regular.ttf",
}
_fcache: dict = {}


def F(weight: int, size: float) -> ImageFont.FreeTypeFont:
    """设计尺度字体（自动 ×S）。"""
    key = (weight, round(size, 2))
    if key not in _fcache:
        _fcache[key] = ImageFont.truetype(
            os.path.join(FONTS, FONT_FILES[weight]), max(1, int(round(size * S)))
        )
    return _fcache[key]


def FS(weight: int, size: float) -> ImageFont.FreeTypeFont:
    """1x 尺度字体（拼板/标注用，不乘 S）。"""
    key = ("1x", weight, size)
    if key not in _fcache:
        _fcache[key] = ImageFont.truetype(
            os.path.join(FONTS, FONT_FILES[weight]), max(1, int(round(size)))
        )
    return _fcache[key]


_icache: dict = {}


def icon_alpha(name: str) -> Image.Image:
    """返回图标 alpha 蒙版（源 PNG 均为纯黑+alpha 的线稿）。"""
    if name not in _icache:
        im = Image.open(os.path.join(ASSETS, name)).convert("RGBA")
        _icache[name] = im.getchannel("A")
    return _icache[name]


# ----------------------------------------------------------------------------- 画布
class Cv:
    def __init__(self, glow: bool = True):
        self.im = self._bg_layer() if glow else Image.new("RGBA", (W * S, W * S), BG)
        self.d = ImageDraw.Draw(self.im)
        self.checks: list = []

    @staticmethod
    def _bg_layer() -> Image.Image:
        """极淡的径向渐变（中心 #161619 → 边缘纯黑），避免大面积死黑。"""
        n = 60
        small = Image.new("RGBA", (n, n))
        px = small.load()
        for y in range(n):
            for x in range(n):
                t = min(1.0, math.hypot((x + 0.5 - n / 2) / (n / 2), (y + 0.5 - n / 2) / (n / 2)))
                k = (1.0 - t) ** 1.7
                px[x, y] = (int(24 * k), int(24 * k), int(28 * k), 255)
        return small.resize((W * S, W * S), Image.BICUBIC)

    # -- 安全区自检 ---------------------------------------------------------
    def _chk(self, bb, label, exempt=False):
        if exempt:
            return
        x0, y0, x1, y1 = bb
        worst = max(math.hypot(x - R, y - R) for x in (x0, x1) for y in (y0, y1))
        self.checks.append((worst, label))

    # -- 基础图元 -----------------------------------------------------------
    def circ(self, cx, cy, r, fill=None, outline=None, width=1.0, exempt=False, label=""):
        self.d.ellipse(
            [int((cx - r) * S), int((cy - r) * S), int((cx + r) * S), int((cy + r) * S)],
            fill=fill, outline=outline, width=max(1, int(round(width * S))),
        )
        self._chk((cx - r, cy - r, cx + r, cy + r), label or "circ", exempt)

    def rrect(self, x, y, w, h, rad, fill=None, outline=None, width=1.0, exempt=False, label=""):
        self.d.rounded_rectangle(
            [int(x * S), int(y * S), int((x + w) * S), int((y + h) * S)],
            radius=int(rad * S), fill=fill, outline=outline,
            width=max(1, int(round(width * S))),
        )
        self._chk((x, y, x + w, y + h), label or "rrect", exempt)

    def line(self, p1, p2, fill, width, exempt=True, label=""):
        self.d.line([int(p1[0] * S), int(p1[1] * S), int(p2[0] * S), int(p2[1] * S)],
                    fill=fill, width=max(1, int(round(width * S))))
        self._chk((min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
                  label or "line", exempt)

    def arc(self, cx, cy, r, start, end, fill, width, exempt=True, label=""):
        self.d.arc(
            [int((cx - r) * S), int((cy - r) * S), int((cx + r) * S), int((cy + r) * S)],
            start, end, fill=fill, width=max(1, int(round(width * S))),
        )
        self._chk((cx - r, cy - r, cx + r, cy + r), label or "arc", exempt)

    def ring(self, cx, cy, r, a0, a1, color, width, step=10.0):
        """圆头弧：整圈用原生 arc（最平滑），缺口弧用短线段拼出 Apple 活动环的圆头。"""
        span = a1 - a0
        if abs(span) < 0.4:
            return
        if abs(span) >= 355:
            self.arc(cx, cy, r, a0, a0 + 359.9, color, width)
            return
        n = max(2, min(180, int(abs(span) / 2.2) + 1))
        pts = []
        for i in range(n + 1):
            a = math.radians(a0 + span * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for i in range(n):
            self.line(pts[i], pts[i + 1], color, width)
        for p in (pts[0], pts[-1]):                       # 圆头
            self.circ(p[0], p[1], width / 2.0, fill=color)

    def icon(self, name, cx, cy, size, color=WHITE, alpha=255):
        a = icon_alpha(name)
        n = max(1, int(round(size * S)))
        a = a.resize((n, n), Image.LANCZOS)
        if alpha < 255:
            a = a.point(lambda v: int(v * alpha / 255))
        tint = Image.new("RGBA", (n, n), color)
        tint.putalpha(a)
        self.im.alpha_composite(tint, (int(round(cx * S - n / 2)), int(round(cy * S - n / 2))))
        self._chk((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2),
                  f"icon:{name}")

    def glow(self, cx, cy, r, color, peak=64, power=1.5):
        """柔光晕（径向渐变 alpha，alpha_composite 混合，避免 ImageDraw 直接写像素）。"""
        n = 64
        m = Image.new("L", (n, n), 0)
        px = m.load()
        for y in range(n):
            for x in range(n):
                t = min(1.0, math.hypot((x + 0.5 - n / 2) / (n / 2),
                                        (y + 0.5 - n / 2) / (n / 2)))
                px[x, y] = int(peak * max(0.0, 1.0 - t) ** power)
        side = max(2, int(round(2 * r * S)))
        m = m.resize((side, side), Image.BICUBIC)
        layer = Image.new("RGBA", (side, side), color)
        layer.putalpha(m)
        self.im.alpha_composite(layer, (int(round(cx * S - side / 2)),
                                       int(round(cy * S - side / 2))))
        self._chk((cx - r, cy - r, cx + r, cy + r), "glow", True)

    # -- 文字 ---------------------------------------------------------------
    def text(self, xy, s, size, weight=400, color=WHITE, anchor="mm", stroke=0.0,
             label=None):
        f = F(weight, size)
        sw = int(round(stroke * S))
        self.d.text((xy[0] * S, xy[1] * S), s, font=f, fill=color, anchor=anchor,
                    stroke_width=sw, stroke_fill=HALO if sw else None)
        bb = self.d.textbbox((xy[0] * S, xy[1] * S), s, font=f, anchor=anchor,
                             stroke_width=sw)
        self._chk((bb[0] / S, bb[1] / S, bb[2] / S, bb[3] / S), label or f"text:{s}")

    def rich(self, cx, cy, parts, size, weight=400, stroke=0.0, label=None):
        """一段多色文本（用于「心率 128 · 卡路里 486」这类混排）。"""
        f = F(weight, size)
        ws = [self.d.textlength(t, font=f) for t, _ in parts]
        x = cx * S - sum(ws) / 2.0
        sw = int(round(stroke * S))
        for (t, c), w in zip(parts, ws):
            self.d.text((x, cy * S), t, font=f, fill=c, anchor="lm",
                        stroke_width=sw, stroke_fill=HALO if sw else None)
            x += w
        half = sum(ws) / 2.0 / S
        self._chk((cx - half, cy - size * 0.7, cx + half, cy + size * 0.7),
                  label or "rich")

    # -- 收尾 ---------------------------------------------------------------
    def finish(self):
        img = self.im.resize((W, W), Image.LANCZOS)
        mask = Image.new("L", (W * S, W * S), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, W * S - 1, W * S - 1], fill=255)
        mask = mask.resize((W, W), Image.LANCZOS)
        # 关键：与圆形蒙版相乘，保留元素自身透明度（不能直接 putalpha 覆盖）
        img.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
        return img


# ----------------------------------------------------------------------------- 矢量图标
class Pen:
    """24x24 viewBox 画笔（Lucide 风格：2px 描边 + 圆头圆角），用于补全源位图缺失的图标。"""

    def __init__(self, cv, cx, cy, size, color, sw=2.0):
        self.cv, self.cx, self.cy = cv, cx, cy
        self.k = size / 24.0
        self.color = color
        self.w = sw * self.k

    def pt(self, x, y):
        return (self.cx + (x - 12) * self.k, self.cy + (y - 12) * self.k)

    def line(self, x1, y1, x2, y2, w=None):
        w = self.w if w is None else w * self.k
        self.cv.line(self.pt(x1, y1), self.pt(x2, y2), self.color, w)
        for x, y in ((x1, y1), (x2, y2)):
            p = self.pt(x, y)
            self.cv.circ(p[0], p[1], w / 2.0, fill=self.color, exempt=True)

    def poly(self, pts, w=None, close=False):
        seq = list(pts) + ([pts[0]] if close else [])
        for a, b in zip(seq, seq[1:]):
            self.line(a[0], a[1], b[0], b[1], w)

    def circle(self, x, y, r, w=None, fill=False):
        p = self.pt(x, y)
        rr = r * self.k
        if fill:
            self.cv.circ(p[0], p[1], rr, fill=self.color, exempt=True)
        else:
            w = self.w if w is None else w * self.k
            self.cv.circ(p[0], p[1], rr, outline=self.color, width=w, exempt=True)

    def rays(self, x, y, r0, r1, angles, w=None):
        for a in angles:
            m = math.radians(a)
            self.line(x + r0 * math.cos(m), y + r0 * math.sin(m),
                      x + r1 * math.cos(m), y + r1 * math.sin(m), w)

    def cloud(self, dx=0.0, dy=0.0, s=1.0):
        """实心云朵（圆+底托），dx/dy/s 供与太阳/雨滴组合。"""
        def P(x, y):
            return (self.cx + (x + dx - 12) * self.k * s, self.cy + (y + dy - 12) * self.k * s)
        for x, y, r in ((8.4, 13.6, 4.0), (12.9, 10.7, 4.7), (16.3, 13.8, 3.4)):
            p = P(x, y)
            self.cv.circ(p[0], p[1], r * self.k * s, fill=self.color, exempt=True)
        p = P(6.4, 14.6)
        self.cv.rrect(p[0], p[1], 11.6 * self.k * s, 4.6 * self.k * s, 2.3 * self.k * s,
                      fill=self.color, exempt=True)


def vi_alarm(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.circle(12, 13.2, 7.6)
    p.line(12, 9.4, 12, 13.4)
    p.line(12, 13.4, 14.1, 15.4)
    p.line(5.2, 3.4, 2.4, 6.2)
    p.line(21.6, 6.2, 18.8, 3.4)
    p.line(6.6, 19.0, 4.3, 21.2)
    p.line(17.4, 19.0, 19.7, 21.2)


def vi_timer(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.line(9.8, 2.6, 14.2, 2.6)
    p.circle(12, 13.8, 7.8)
    p.line(12, 13.8, 15.2, 10.8)


def vi_gear(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.circle(12, 12, 3.9, w=1.9)
    p.rays(12, 12, 5.0, 8.7, range(22, 360, 45), w=3.1)


def vi_sun(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.circle(12, 12, 4.1)
    p.rays(12, 12, 6.6, 9.4, range(0, 360, 45))


def vi_cloud_rain(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.cloud(dy=-1.0)
    for x in (8.4, 12.4, 16.4):
        p.line(x, 18.6, x - 1.3, 21.6, w=1.7)


def vi_cloud_sun(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.circle(16.6, 6.6, 2.9, w=1.8)
    p.rays(16.6, 6.6, 4.1, 6.0, (270, 315, 225), w=1.8)
    p.cloud(dx=-1.4, dy=2.6, s=0.92)


def vi_battery(cv, cx, cy, size, color):
    p = Pen(cv, cx, cy, size, color)
    p.cv.rrect(*p.pt(2.2, 7.2), 16.0 * p.k, 9.6 * p.k, 2.6 * p.k,
               outline=color, width=1.8 * p.k, exempt=True)
    p.line(20.6, 10.8, 20.6, 13.2, w=2.0)
    p.cv.rrect(*p.pt(4.6, 9.6), 11.2 * p.k, 4.8 * p.k, 1.2 * p.k,
               fill=color, exempt=True)


VI_ICONS = {
    "alarms": vi_alarm, "stopwatch": vi_timer, "settings": vi_gear, "sun": vi_sun,
    "cloud_rain": vi_cloud_rain, "cloud_sun": vi_cloud_sun, "battery": vi_battery,
}


# ----------------------------------------------------------------------------- 复用零件
def switch(cv, x, y, on=True, w=28.0, h=16.0):
    """Apple 风格开关：x/y 为左上角。"""
    rad = h / 2.0
    cv.rrect(x, y, w, h, rad, fill=GREEN if on else hx("#3A3A3C"), label="switch")
    kx = x + w - rad if on else x + rad
    cv.circ(kx, y + rad, rad - 1.6, fill=WHITE, exempt=True)


def pill_button(cv, cx, cy, w, h, text, size, bg, fg, weight=500):
    cv.rrect(cx - w / 2, cy - h / 2, w, h, h / 2, fill=bg, label=f"btn:{text}")
    cv.text((cx, cy - 0.5), text, size, weight=weight, color=fg, label=f"btntext:{text}")


def activity_rings(cv, cx, cy, outer_r, gap, width, vals):
    """三活动环（外→内：红/绿/蓝），Apple Activity 风格，12 点起顺时针。"""
    cols = [PINK if False else RED, GREEN, BLUE]
    cols = [hx("#FF2D55"), GREEN, BLUE]
    for i, v in enumerate(vals):
        r = outer_r - i * (width + gap)
        cv.ring(cx, cy, r, -90, 270, TRACK, width, )          # 轨道
        cv.ring(cx, cy, r, -90, -90 + 360 * v / 100.0, cols[i], width)  # 指示


# ----------------------------------------------------------------------------- 各屏
def s_watchface():
    cv = Cv()
    # 表圈
    cv.circ(R, R, 118.3, outline=hx("#2A2A2E"), width=2.4, exempt=True)
    cv.circ(R, R, 112.6, outline=hx("#1A1A1D"), width=1.0, exempt=True)
    # 刻度
    for i in range(60):
        a = math.radians(i * 6)
        if i % 15 == 0:
            l, w, c = 9.0, 2.4, hx("#E2E2E6")
        elif i % 5 == 0:
            l, w, c = 6.2, 2.0, hx("#9A9AA0")
        else:
            l, w, c = 3.0, 1.1, hx("#48484A")
        p1 = (R + 103.5 * math.cos(a), R + 103.5 * math.sin(a))
        p2 = (R + (103.5 + l) * math.cos(a), R + (103.5 + l) * math.sin(a))
        cv.line(p1, p2, c, w)
    # 指针（10:09:30）
    def hand(deg, length, width, color, tail=0.0):
        a = math.radians(deg)
        p1 = (R - tail * math.sin(a), R + tail * math.cos(a))
        p2 = (R + length * math.sin(a), R - length * math.cos(a))
        cv.line(p1, p2, (0, 0, 0, 170), width + 2.0)
        cv.line(p1, p2, color, width)
    hand(180, 45, 1.5, ORANGE, tail=9)                  # 秒针 → 下
    hand(304.5, 29.5, 3.4, (255, 255, 255, 235))        # 时针 → 10（避开日期行）
    hand(54, 41, 2.4, (255, 255, 255, 245))             # 分针 → 9 分
    cv.circ(R, R, 4.4, fill=(0, 0, 0, 190), exempt=True)
    cv.circ(R, R, 2.9, fill=ORANGE, exempt=True)
    # 数字时间 / 日期
    cv.text((R, 56), "10:09", 40, 700, WHITE, stroke=1.6, label="time")
    cv.text((R, 88), "周二 9月28日", 12.5, 400, DIM, stroke=1.2, label="date")
    # complications
    comps = [("img_comp_hr.png", "72", PINK, 56), ("img_comp_temp.png", "24°", ORANGE, 120),
             (None, "82%", GREEN, 184)]
    for name, val, col, x in comps:
        if name:
            cv.icon(name, x, 175, 15, col)
        else:
            vi_battery(cv, x, 175, 16, col)
        cv.text((x, 190.5), val, 11.5, 500, col, stroke=1.0, label=f"comp:{val}")
    cv.text((R, 216), "左滑 ›", 10.5, 400, hx("#B0B0B6", 205), label="hint")
    return cv


def s_apps():
    cv = Cv()
    apps = [(270, "health", "img_app_health.png"), (315, "weather", None),
            (0, "alarms", None), (45, "workout", "img_app_workout.png"),
            (90, "stopwatch", None), (135, "breathe", "img_app_breathe.png"),
            (180, "voice", "img_app_voice.png"), (225, "settings", None)]
    cv.glow(R, R, 68, BLUE, peak=54)                            # 中心微光
    for ang, key, mask in apps:
        a = math.radians(ang)
        cx, cy = R + 80 * math.cos(a), R + 80 * math.sin(a)
        cv.circ(cx, cy, 20, fill=hx("#222226"), outline=hx("#3D3D41"), width=1.1,
                label=f"appbtn:{key}")
        if mask:
            cv.icon(mask, cx, cy, 22, WHITE)
        else:
            fn = {"weather": vi_cloud_sun, "alarms": vi_alarm, "stopwatch": vi_timer,
                  "settings": vi_gear}[key]
            fn(cv, cx, cy, 23.5, WHITE)
    cv.icon("img_nova_core.png", R, R, 46, BLUE)
    return cv


def s_health():
    cv = Cv()
    activity_rings(cv, R, 86, 42, 5.5, 7.0, [68, 45, 80])
    cv.text((R, 156), "8642", 32, 700, WHITE, stroke=1.2, label="steps")
    cv.text((R, 181), "步数", 11, 400, DIM, label="steps_unit")
    cv.rich(R, 199, [("心率 ", hx("#AEAEB2")), ("128", PINK), ("  ·  ", hx("#5A5A5F")),
                     ("卡路里 ", hx("#AEAEB2")), ("486", ORANGE)], 10.5, 400,
            label="stat_line")
    return cv


def s_weather():
    cv = Cv()
    vi_sun(cv, R, 56, 48, ORANGE)
    cv.text((R, 98), "24°", 38, 700, WHITE, stroke=1.3, label="temp_big")
    cv.text((R, 128), "晴", 13, 500, DIM, label="cond")
    cv.line((66, 143), (174, 143), hx("#2C2C2E"), 1.0)
    hr = [("现在", "24°", 56, "cloud_sun"), ("15时", "26°", 98, "cloud_h2"),
          ("16时", "23°", 140, "cloud_rain"), ("20时", "19°", 182, "moon")]
    for t, tp, x, kind in hr:
        if kind == "cloud_sun":
            vi_cloud_sun(cv, x, 161, 24, hx("#D8D8DC"))
        elif kind == "cloud_rain":
            vi_cloud_rain(cv, x, 161, 24, hx("#D8D8DC"))
        elif kind == "moon":
            cv.icon("img_weather_h4.png", x, 161, 22, hx("#D8D8DC"))
        else:
            cv.icon("img_weather_h2.png", x, 161, 22, hx("#D8D8DC"))
        cv.text((x, 180), t, 10, 400, hx("#B0B0B6"), label=f"wtime:{t}")
        cv.text((x, 194), tp, 12, 500, WHITE, label=f"wtemp:{tp}")
    return cv


def s_alarms():
    cv = Cv()
    cv.text((R, 46), "闹钟", 15, 500, WHITE, label="al_title")
    rows = [("06:30", "工作日", True), ("07:30", "每天", True), ("22:30", "就寝", True)]
    y = 68
    for t, rep, on in rows:
        cv.rrect(46, y, 148, 38, 12, fill=CARD, label=f"row:{t}")
        cv.text((60, y + 14), t, 15.5, 500, WHITE, anchor="lm", label=f"altime:{t}")
        cv.text((60, y + 28.5), rep, 9.5, 400, DIM, anchor="lm", label=f"alrep:{t}")
        switch(cv, 154, y + 11, on)
        y += 46
    return cv


def _workout(active: bool):
    cv = Cv()
    cv.icon("img_workout_run.png", R, 74, 56, WHITE)
    cv.text((R, 122), "户外跑步", 17, 500, WHITE, label="wk_kind")
    cv.text((R, 148), "体能训练", 11, 400, DIM, label="wk_sub")
    if active:
        pill_button(cv, R, 194, 104, 40, "进行中", 15, CARD, GREEN, weight=500)
    else:
        pill_button(cv, R, 194, 104, 40, "开始", 15.5, GREEN, hx("#000000"), weight=700)
    return cv


def s_workout():
    return _workout(False)


def s_stopwatch():
    cv = Cv()
    cv.circ(R, R, 100, outline=hx("#26262A"), width=1.4, exempt=True)
    for i in range(12):
        a = math.radians(i * 30)
        cv.line((R + 92.5 * math.cos(a), R + 92.5 * math.sin(a)),
                (R + 97.5 * math.cos(a), R + 97.5 * math.sin(a)), hx("#3A3A3C"), 1.2)
    cv.text((R, 62), "秒表", 15, 500, WHITE, label="sw_title")
    cv.text((R, 106), "00:00.00", 33, 700, WHITE, stroke=1.2, label="sw_time")
    cv.text((R, 140), "00:05.24", 11, 400, DIM, label="sw_lap")
    pill_button(cv, 81, 183, 74, 34, "开始", 13.5, GREEN, hx("#000000"), weight=700)
    pill_button(cv, 159, 183, 74, 34, "重置", 13.5, CARD2, WHITE, weight=500)
    return cv


def s_breathe():
    cv = Cv()
    cv.glow(R, 102, 76, BLUE, peak=76, power=1.9)               # 环内柔光
    cv.ring(R, 102, 66, -90, 270, TRACK, 11)
    cv.ring(R, 102, 66, -90, 270, BLUE, 11)
    cv.text((R, 96), "呼吸", 18, 500, WHITE, label="br_title")
    cv.text((R, 120), "跟随圆环", 10.5, 400, hx("#D8D8DC", 205), label="br_hint1")
    cv.text((R, 196), "吸气  ·  呼气", 10.5, 400, DIM, label="br_hint2")
    return cv


def _voice(state: str):
    cv = Cv()
    wave = {"idle": ("img_wave_idle.png", hx("#5A5A5F"), "点击说话", DIM),
            "listening": ("img_wave_listening.png", GREEN, "在听…", GREEN),
            "speaking": ("img_wave_speaking.png", BLUE, "正在播报", BLUE)}[state]
    name, col, txt, tcol = wave
    if state != "idle":
        cv.glow(R, 70, 48, col, peak=74)
    cv.circ(R, 70, 30, fill=CARD, outline=hx("#3A3A3C"), width=1.2, label="mic_btn")
    cv.icon("img_app_voice.png", R, 70, 26, WHITE if state == "idle" else col)
    cv.icon(name, R, 138, 60, col)
    cv.text((R, 190), txt, 12, 500 if state != "idle" else 400, tcol, label="voice_hint")
    return cv


def s_voice():
    return _voice("idle")


def s_settings():
    cv = Cv()
    cv.text((R, 46), "设置", 15, 500, WHITE, label="st_title")
    rows = [("蓝牙", "已连接", BLUE), ("电量", "82%", GREEN)]
    y = 78
    for label_, val, col in rows:
        cv.rrect(46, y, 148, 40, 12, fill=CARD, label=f"st:{label_}")
        cv.text((60, y + 20), label_, 11, 400, WHITE, anchor="lm", label=f"stl:{label_}")
        cv.text((180, y + 20), val, 11, 500, col, anchor="rm", label=f"stv:{val}")
        y += 52
    cv.text((R, 196), "右滑返回应用", 10, 400, DIM, label="st_hint")
    return cv


# ----------------------------------------------------------------------------- 拼板
SHEET_BG = hx("#0B0B0D")
LABEL = hx("#C7C7CC")
SUBLABEL = hx("#8E8E93")


def sheet(cells, cols, title, sub, cell=288, lab_h=52, out=None):
    rows = math.ceil(len(cells) / cols)
    pad = 24
    head = 96
    wid = cols * cell + pad * 2
    hei = head + rows * (cell + lab_h) + pad
    sh = Image.new("RGBA", (wid, hei), SHEET_BG)
    d = ImageDraw.Draw(sh)
    d.text((pad + 8, 40), title, font=FS(700, 26), fill=WHITE, anchor="lm")
    d.text((pad + 8, 72), sub, font=FS(400, 12.5), fill=SUBLABEL, anchor="lm")
    for i, (img, name, cn) in enumerate(cells):
        r, c = divmod(i, cols)
        x0 = pad + c * cell
        y0 = head + r * (cell + lab_h)
        d.rounded_rectangle([int(x0 + (cell - W) / 2) - 1, int(y0) - 1,
                             int(x0 + (cell + W) / 2), int(y0 + W)],
                            radius=W / 2, outline=hx("#232327"), width=1)
        sh.alpha_composite(img, (int(x0 + (cell - W) / 2), int(y0)))
        d.text((x0 + cell / 2, y0 + W + 18), f"{i + 1:02d}  {cn}", font=FS(500, 16.5),
               fill=LABEL, anchor="mm")
        d.text((x0 + cell / 2, y0 + W + 37), name, font=FS(400, 11),
               fill=SUBLABEL, anchor="mm")
    if out:
        sh.save(out)
    return sh


# ----------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    screens = [
        ("01_watchface", "表盘", "watchface", s_watchface),
        ("02_apps", "应用", "apps", s_apps),
        ("03_health", "健身", "health", s_health),
        ("04_weather", "天气", "weather", s_weather),
        ("05_alarms", "闹钟", "alarms", s_alarms),
        ("06_workout", "训练", "workout", s_workout),
        ("07_stopwatch", "秒表", "stopwatch", s_stopwatch),
        ("08_breathe", "正念", "breathe", s_breathe),
        ("09_voice", "语音", "voice", s_voice),
        ("10_settings", "设置", "settings", s_settings),
    ]
    built = []
    warns = []
    for fname, cn, key, fn in screens:
        cv = fn()
        img = cv.finish()
        img.save(os.path.join(OUT, fname + ".png"))
        built.append((img, f"{key}", cn))
        for dist, label in cv.checks:
            if dist > SAFE + 0.6:
                warns.append((key, round(dist, 1), label))

    # 状态变体
    variants = [(_voice("idle"), "点击说话", "voice · 待机"),
                (_voice("listening"), "在听…", "voice · 聆听"),
                (_voice("speaking"), "正在播报", "voice · 播报"),
                (_workout(True), "开始 → 进行中", "workout · 进行中"),
                (s_alarms(), "开关态示例", "alarms · 关闭一档")]
    # alarms 变体：第 3 行关
    va = Cv()
    va.text((R, 46), "闹钟", 15, 500, WHITE, label="al_title")
    for i, (t, rep, on) in enumerate([("06:30", "工作日", True), ("07:30", "每天", True),
                                      ("22:30", "就寝", False)]):
        y = 68 + i * 46
        va.rrect(46, y, 148, 38, 12, fill=CARD)
        va.text((60, y + 14), t, 15.5, 500, WHITE if on else hx("#6E6E73"), anchor="lm")
        va.text((60, y + 28.5), rep, 9.5, 400, DIM, anchor="lm")
        switch(va, 154, y + 11, on)
    variants[4] = (va, "第 3 档关闭：时间变暗 + 开关置灰", "alarms · 关闭一档")

    sheet([(v[0].finish() if hasattr(v[0], "finish") else v[0], v[1], v[2]) for v in variants],
          5, "NovaWatchS12 · 240×240 状态变体", "voice 三态 / workout 进行中 / 闹钟开关两态",
          cell=288, lab_h=56, out=os.path.join(OUT, "variants_states.png"))

    sheet([(im, key, cn) for im, key, cn in built], 5,
          "NovaWatchS12 · 240×240 圆形表盘 UI 总览",
          "仿 Apple Watch Series 12 设计语言 · 10 屏 · 深色主题 · 圆外透明 · 素材全部原创（Lucide + 自绘）",
          cell=288, lab_h=56, out=os.path.join(OUT, "overview_240.png"))

    print(f"OK  -> {OUT}")
    print(f"screens=10  variants=5  warnings={len(warns)}")
    for k, dist, label in warns:
        print(f"  [safe>112] {k:10s} r={dist:6.1f}  {label}")


if __name__ == "__main__":
    main()
