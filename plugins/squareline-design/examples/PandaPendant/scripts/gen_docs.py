#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write UI需求清单.md and PandaPendant设计规格文档.md.  Tables are generated from the spec,
so docs and project cannot drift.  Run after gen_spec.py."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
NAME = "PandaPendant"
spec = json.load(open(os.path.join(PROJ, "%s.spec.json" % NAME), encoding="utf-8"))
nav = json.load(open(os.path.join(HERE, "nav.json"), encoding="utf-8"))
manifest = json.load(open(os.path.join(PROJ, "assets.manifest.json"), encoding="utf-8"))
KIND = {"face": "脸部状态", "emotion": "情绪帧", "aux": "辅助页"}


def walk(children, depth=0):
    for c in children or []:
        yield depth, c
        yield from walk(c.get("children"), depth + 1)


def desc(o):
    t = o["type"]
    if t == "LABEL":
        return "「%s」%s %s" % (o["text"], o["font"], o["color"])
    if t == "IMAGE":
        return o["asset"].replace("assets/", "") + (" 〔初始隐藏〕" if o.get("hidden") else "")
    if t == "PANEL":
        return "bg %s r%s%s%s" % (o["bg"], o.get("radius", 0), " 〔初始隐藏〕" if o.get("hidden") else "",
                                  " 可点击" if o.get("events") else "")
    return ""


def action_str(a):
    t = a["type"]
    if t == "CHANGE_SCREEN":
        return "→ %s" % a["target"]
    if t in ("SHOW", "HIDE"):
        return "%s %s" % (t, a["object"])
    if t == "PLAY_ANIMATION":
        return "动画「%s」" % a["animation"]
    return t


# --------------------------------------------------------------- collect data --
texts = []
for s in spec["screens"]:
    for _, o in walk(s["children"]):
        if o["type"] == "LABEL" and o["text"] not in texts:
            texts.append(o["text"])
HEADROOM = ("周一 周二 周三 周四 周五 周六 周日 星期 上午 下午 晴 多云 阴 小雨 大雨 雷阵雨 雪 雾 风 "
            "没听清 请再说一遍 暂时无法回答 稍后再试 播放失败 网络已断开 网络恢复 已连接 未连接 重新连接中 重试 取消 "
            "电量低 正在充电 已充满 请充电 亮度 音量 勿扰 睡眠 蓝牙 开启 关闭 确定 返回 设置 "
            "活泼 温柔 安静 活跃 反馈 强度 性格 互动 偏好 通知 消息 日程 提醒 邮件 来电 "
            "1分钟 5分钟 10分钟 30分钟 从不 触摸 语音 唤醒 自动休眠 睡眠动画 "
            "存储 版本 时间同步 固件 缺失 已加载 加载中 待加载 帧 角色预览 表情管理 动画管理")

# --------------------------------------------------------------------- design --
D = []
w = D.append
w("# Panda AI Pendant UI 设计规格文档（%s 工程）\n" % NAME)
w("> 本文档是 `%s.spec.json` 的**源真相**：先改本文档，再重新生成/构建。§3–§5、§7 的表格由 `scripts/gen_docs.py` 从 spec 自动生成。\n" % NAME)
w("来源：`concept/Panda_AI_Pendant_UI_需求规格说明书_V2_0.md`（需求）＋ `concept/board_face_ui_20.png`（20 表情）＋ `concept/board_emotion_pages.png`（功能页/状态机概念）。\n")
w("## 1. 设备与画布\n")
w("- 面板：微雪 1.85\" 圆形触摸屏，**UI 画布 360×360 px，圆形**（圆心 (180,180)，r=180）；LVGL 9.2.2；SquareLine Studio 1.6.2；深色主题 `[来源：需求书 §2]`")
w("- 坐标：屏幕绝对坐标，左上角原点。实际 LCD 驱动分辨率/有效区域以最终硬件为准（需求书 §2 说明）")
w("- 混合方案：**脸部 = 全屏 `face` 图片对象**（运行时由 SD 卡帧序列替换，RGB565、12–15 FPS）＋ **叠加层 = 真 LVGL 对象**（波形、光点、提示条、文字、开关）。不做不可交互的全屏静态页（需求书附录 A-5）")
w("- 视觉硬约束（需求书 §3.1 + 产品补充）：**熊猫脸部的白色毛发铺满整张 360×360 屏幕，与白色外壳浑然一体**——屏幕边缘不得出现黑底、头部轮廓、耳朵、深色边或任何环形装饰；无身体/手；默认无状态栏。脸部屏背景色 `SHELL`，脸部帧边缘向壳白连续过渡\n")
w("### 1.1 调色板\n")
w("| 键 | 色值 | 用途 | 来源 |\n|---|---|---|---|")
src = {"SHELL": "估算", "BG": "测得", "CARD": "测得", "WAVE": "测得", "CYAN": "测得", "GREEN": "测得", "RED": "测得", "WHITE": "—", "PILL": "设计值"}
use = {"BG": "深色功能页背景（设置/列表）", "SHELL": "脸部屏背景（毛发白，与白色外壳融合）", "CARD": "卡片/列表行（概念板深蓝灰面板）", "CARD2": "按钮/开关关闭态/未选中芯片", "TRACK": "滑块轨道",
       "DIM": "次要文字", "CYAN": "科技强调色（光点、滑块）", "WAVE": "聆听波形", "BLUE2": "开关/选中态填充", "GREEN": "已就绪/成功",
       "AMBER": "警告/错误提示图标", "RED": "未读角标", "WHITE": "主文字", "PILL": "提示条半透明黑底"}
for k, v in spec["palette"].items():
    w("| %s | %s | %s | %s |" % (k, v, use.get(k, ""), src.get(k, "估算")))
w("\n语音状态色（概念板状态机，供运行时着色参考，工程内未直接使用）：待机 `#9CD1FD` / 唤醒 `#88C33E` / 聆听 `#31DA38` / 思考 `#8E9AFC` / 回复 `#D081F8`  `[测得]`\n")

w("## 2. 屏幕清单（%d 屏）\n" % len(nav))
w("| # | 屏 | 类别 | 脸部帧 | 说明 |\n|---|---|---|---|---|")
for i, n in enumerate(nav, 1):
    w("| %d | `%s` | %s | %s | %s |" % (i, n["name"], KIND[n["kind"]], n["face"] or "—", n["desc"]))
w("\n初始屏：`home`。**不使用 `order` 滑动环**（`order=[home]`），所有导航由 §4 显式事件定义。\n")

w("## 3. 对象清单（逐屏）\n")
w("`rect=[x,y,w,h]` 屏幕绝对坐标。对象名在屏内唯一，导出后 C 变量为 `ui_<屏>_<对象>`（运行时按此名取对象）。\n")
for s in spec["screens"]:
    w("### 3.%d 屏 `%s`\n" % (spec["screens"].index(s) + 1, s["name"]))
    w("| 对象 | 类型 | rect | 说明 |\n|---|---|---|---|")
    for d, o in walk(s["children"]):
        w("| %s`%s` | %s | %s | %s |" % ("↳ " * d, o["name"], o["type"], o["rect"], desc(o)))
    w("")

w("## 4. 交互定义\n")
w("工程内接线的事件只用编辑器已验证的集合：`CLICKED / GESTURE_LEFT|RIGHT|UP|DOWN / SCREEN_LOAD_START`。\n")
w("| 屏 | 触发 | 事件 | 动作 |\n|---|---|---|---|")
for s in spec["screens"]:
    for _, o in walk(s["children"]):
        for e in o.get("events", []) or []:
            w("| %s | 对象 `%s` | %s | %s |" % (s["name"], o["name"], e["on"], "；".join(action_str(a) for a in e["actions"])))
    for e in spec["screen_events"].get(s["name"], []) or []:
        w("| %s | 屏幕 | %s | %s |" % (s["name"], e["on"], "；".join(action_str(a) for a in e["actions"])))
w("""
### 4.1 需求书手势 ↔ 工程接线

| 需求书手势 | 工程内 | 说明 |
|---|---|---|
| 首页 单击 → 聆听 | ✅ `home/face` CLICKED → `listening` | 演示接线；真实流程由 Voice FSM 事件驱动 |
| 首页 上滑/下滑/左滑/右滑 | ✅ → notification / quick_settings / time_weather / personality | 见 `home` 屏事件 |
| 首页 **双击** → 开心反馈 | ❌ **未接线（引擎限制）** | `DOUBLE_CLICKED` 不在编辑器已验证事件集内；写进去有让 SquareLine 打不开工程的风险。请在 `panda_ui` 中对 `ui_home_face` 注册 `LV_EVENT_DOUBLE_CLICKED` → 播放 `anim_happy`，并处理与单击的去抖 |
| 首页 **长按** → 持续聆听，松开提交 | ❌ **未接线（引擎限制）** | 同上，`LONG_PRESSED` 未验证。用 `LV_EVENT_LONG_PRESSED` + `LV_EVENT_RELEASED` 在 C 层实现 |
| Listening 单击=提交，长按=取消 | ✅ 单击 → thinking；长按 ❌ C 层 | 下滑 → home 作为临时取消手势 |
| Speaking 单击=打断 | ✅ 单击 → home | 真实打断=停止 TTS 后回 Idle |
| Error 单击=重试 | ✅ asr_failed→listening；llm_error→thinking；tts_error→home | |
| Thinking 单击=取消 | 〔可选，工程内单击 → speaking 仅为演示〕 | 取消请求在 C 层实现 |
| 所有触摸有即时视觉反馈（需求 R019） | ✅ 每个可点击对象 `PRESSED → SET_OPACITY 190`、`RELEASED → 255` | `scripts/gen_spec.py` 里 `touch_feedback=190`；真机可在 C 层改成更精致的按压样式 |

**所有状态切换在真机上由业务事件驱动（`UI_EVT_*`），不依赖固定时长**；工程内的"点击进入下一状态"只是让设计师在模拟器里能走通流程。
""")

w("## 5. 动画\n")
w("| 名称 | 目标 | 属性 | 周期 | 触发 |\n|---|---|---|---|---|")
for a in spec["animations"]:
    scr = a["target"].split("/")[0]
    w("| %s | `%s` | opacity | %d ms 循环 | `%s` SCREEN_LOAD_START |" % (a["name"], a["target"], a["duration"], scr))
w("""
- 页面切换：`FADE_ON` 150 ms 淡入（需求书 §5.3：轻量淡入，不做复杂转场）
- 脸部帧动画（Idle 呼吸/眨眼/说话口型等）**不在工程里**：由 `panda_animation` 从 SD 卡逐帧读取并替换 `face` 对象的图源
- 聆听波形：`wave_1..9` 为真对象，运行时按音量调整高度/透明度；工程内是静态示意
""")

w("## 6. 字体\n")
w("| codename | 字重 | 字号 | kind | 用途 |\n|---|---|---|---|---|")
fuse = {"Big60": "时间 14:30（仅数字与冒号）", "Title22": "页面标题", "Body18": "正文/行标题/日期", "Small16": "次要文字/提示条/标签"}
for f in spec["fonts"]:
    wt = "700" if "-700" in f["ttf"] else ("500" if "-500" in f["ttf"] else "400")
    w("| %s | %s | %d | %s | %s |" % (f["codename"], wt, f["size"], f["kind"], fuse[f["codename"]]))
w("\nNoto Sans SC（随包）。设计板的字体无法复刻，只匹配字重与字号。\n")
w("### 6.1 文案字符集（glyph headroom）★\n")
w("> 构建时本文档的全部字符会进入字体子集；这里同时列出界面现有文案与将来可能出现的词。\n")
w("- **界面现有文案**：`%s`" % " ".join(texts))
w("- **备用词（headroom）**：`%s`" % HEADROOM)
w("- **数字字体 `Big60`** = `symbols[number]`（`0123456789:`）∪ `ranges_num`（`0x30-0x3A`），只含数字和冒号；该字体的 LABEL 里只能出现这些字符（`slx.py check` 会拦 E-GLYPH）\n")

w("## 7. 资产清单\n")
w("### 7.1 脸部帧（设计期占位，来自用户设计板）\n")
w("| 文件 | 尺寸 | 来源 | 备注 |\n|---|---|---|---|")
w("| `face_01_idle` … `face_20_celebrate`（19 张，缺 06） | 360×360（**满铺白毛，无黑边**） | `board_face_ui_20.png` 单元 01–20 | ① 以**逐格量出的头部轮廓中心**为中心裁 188 px（不是毛发包围盒——耳根深色会让它偏 8 px）；② 头部椭圆（半轴 104×90，上半 80）以外的黑底/耳根/光晕，用椭圆内侧**毛发白**沿径向延伸填满（只采样毛发白像素，五官/眼泪/爱心不会被拖出）；③ 从 45% 半径起把**亮色像素**连续提亮到壳白（强度 0.92），暗色五官不动，以消除照片与延伸毛发的接缝及 3D 边缘暗部；④ Lanczos 放大约 1.9× + 轻锐化 |")
w("| `face_mini_idle` | 170×170 | 同 01 | 时间天气页小脸（深色页），边缘羽化 |")
w("| `thumb_*`（19 张） | 60×60 | 同上 | 角色预览缩略图 |")
w("""
> ⚠️ **这些是占位帧，不是生产资源。** 板上单张人脸约 220 px，放大后偏软。生产帧由 3D 管线按需求书 §6 导出 256×256 RGB565 序列放进 SD 卡 `panda/expressions|animations/`，运行时替换 `face` 对象。
> **板上"思考"（06）带手部**，违反需求书 §3.1/§6.1（不得出现手），**已排除**；工程里 `thinking` 暂用 03「好奇」帧，请在 3D 母版里重做不带手的思考帧。
""")
w("### 7.2 图标（Lucide，ISC 许可，无需署名）\n")
w("| 文件 | 尺寸 | Lucide 图标 | 色 |\n|---|---|---|---|")
for it in manifest["icons"]:
    w("| `%s` | %d | `%s` | %s |" % (it["name"], it["size"], it["icon"], it["color"]))

w("""
## 7.3 需求追溯

`requirements.json` / `需求追溯矩阵.md`：需求书拆成 73 条带编号的原子需求，**每条都有处置**（完成 / 偏差 / 超出本工程范围 / 信息），其中 8 条带自动验证规则。
**偏差必读**：R006/R050/R067（黑底融合 → 用户后来指定白壳白毛）、R028（占位帧 360×360）、R053（双击/长按在 C 层）等。

## 8. 对照需求书 §11 验收

### 8.1 视觉
- [ ] 屏幕中只出现熊猫脸部 —— 脸部屏均为满铺脸部帧；`time_weather` 的小脸是唯一不铺满屏幕的页（需给时间文字留位，版式取自概念板）
- [ ] **白毛铺满整屏并与白壳融为一体** —— 圆屏最外圈（r∈[0.95,1.0]）平均亮度：实测 19 帧最低 237、中位数 249（255=纯白）；见 `preview/shell_merge_simulation.png`
- [ ] 无耳朵 / 无头部外轮廓 / 无身体与手 —— 头部椭圆外已用毛发白填充；带手的 06 帧已排除
- [ ] 无表盘边框、圆形装饰框、边缘光效 —— 工程内无任何环形对象；**已删除**唤醒/重连的边缘光晕（会给白毛边缘染色，见 §9 R3）
- [ ] 信息叠加不遮挡五官 —— 叠加层仅在额头（光点）/下巴（波形、提示条）/右上（角标）
- [ ] 所有表情脸部比例/位置/光照一致 —— 同一裁切边长

### 8.2 交互
- [ ] 手势 —— 见 §4.1（双击/长按为 C 层）
- [ ] 状态由业务事件驱动 —— 工程仅提供屏幕与对象，驱动在 `panda_ui`
- [ ] 错误反馈 —— asr_failed / llm_error / tts_error / network_lost / reconnecting / battery_low 均有屏

### 8.3 工程
- [ ] validator：`OK - project validated, no problems found`
- [ ] 构建无缺字形告警；改文案前先改 §6.1

## 9. 运行时契约与风险

### 9.1 `panda_ui` 需要知道的
- 脸部对象：每个脸部屏的 `ui_<屏>_face`（IMAGE，360×360，位于最底层）。运行时 `lv_image_set_src()` 指向 SD 帧解码缓冲，或用 `lv_animimg`；资源缺失 → 回退 `face_01_idle`
- 叠加层对象名稳定：`wave_1..9`、`dot_1..3`、`tip`/`tip_text`/`tip_icon`、`badge`/`badge_n`（`home`，初始隐藏）
- 事件回调名全局唯一：`<屏>_<对象>_<事件>`
- 所有 LVGL 对象只在 UI Task 操作（需求书 §8）

### 9.2 已知偏差与风险
| # | 内容 | 处理 |
|---|---|---|
| R1 | 双击/长按不在已验证事件集 | C 层实现（§4.1） |
| R2 | 板上"思考"帧带手 | 已排除；需 3D 重做 |
| R3 | 唤醒/重连原有的边缘青色光晕与"白毛融入白壳"冲突 | **已删除**。唤醒提示改由脸部帧（睁眼）+ 状态逻辑表达，不在边缘加任何色彩 |
| R4 | 设计板脸部分辨率低（~220 px），且毛发延伸为合成 | 仅作设计期占位；少数帧（困惑、异常）边缘残留极小深色点，生产帧不会有 |
| R9 | 白毛满屏后，深色功能页（设置/列表）与脸部屏反差大 | 如需统一，可把功能页背景改为壳白并反相文字色（待确认） |
| R5 | `Sleepy/Confused/Angry` 等板上带小图标（Zzz、?、怒气）的帧，图标在圆形裁切后被切掉 | 如需保留，作为独立叠加图标对象加回，不要烘焙进脸部帧 |
| R6 | 通知列表只有 3 条静态卡片，无滚动容器 | 运行时用 LVGL 滚动或分页实现 |
| R7 | 滑块/开关为静态示意，值由运行时驱动 | `*_fill`、`*_knob` 为真对象，可改宽度/位置 |
| R8 | 错误→表情映射为设计假设：ASR/LLM=困惑，TTS=难过，断网=异常，低电=疲惫 | 在 §2 可调整 |
""")
open(os.path.join(PROJ, "%sDesign" % NAME + ".tmp"), "w").close()
os.remove(os.path.join(PROJ, "%sDesign" % NAME + ".tmp"))
open(os.path.join(PROJ, "%s设计规格文档.md" % NAME), "w", encoding="utf-8", newline="\n").write("\n".join(D))

# ------------------------------------------------------------------- requirement --
R = []
r = R.append
r("# Panda AI Pendant UI 需求清单\n")
r("## 1. 基本信息\n")
r("- 产品：AI 熊猫挂坠（语音交互 + 情绪陪伴）　来源：需求规格说明书 V2.0 + 两张设计板")
r("- 面板：**360×360 圆形**（微雪 1.85\" 触摸屏，UI 画布）；ESP32-S3；LVGL 9；资源在 SD 卡")
r("- 视觉：**只显示熊猫脸部，白色毛发铺满整张 360×360 屏幕并与白色外壳浑然一体**（无黑边/耳朵/头部轮廓/身体/手/边框/表盘/边缘光效）；默认无状态栏")
r("- 交付：SquareLine 工程（.spj）+ 预览图 + 规格文档\n")
r("## 2. 屏幕清单与切换逻辑（%d 屏）\n" % len(nav))
r("| 类别 | 屏 |\n|---|---|")
for k in ("face", "emotion", "aux"):
    r("| %s | %s |" % (KIND[k], "、".join("`%s`" % n["name"] for n in nav if n["kind"] == k)))
r("""
首页手势：单击→聆听；上滑→通知；下滑→快捷设置；左滑→时间天气；右滑→个性化；双击→开心；长按→持续聆听（双击/长按在 C 层，见规格文档 §4.1）。
返回：时间天气右滑；个性化左滑；通知右滑；快捷设置上滑；其余设置页右滑。

## 3. 每块屏上有什么
见《设计规格文档》§3（逐屏对象表）。要点：
- 脸部状态屏 = 全屏脸部 + 轻量叠加（聆听波形 / 思考光点 / 底部提示条 / 未读角标）
- 时间天气 = 时间 + 日期 + 小脸 + 天气图标与温度
- 设置类 = 深色卡片/芯片/开关/滑块，圆屏安全区内排布

## 4. 交互与动画效果
- 页面切换：150 ms 淡入；脸部动画为 SD 卡帧序列（运行时）；工程内仅有光点/光晕的透明度循环
- 语音状态由业务事件驱动，工程内点击仅用于设计期演示

## 5. 文案与语言
简体中文 + 数字。完整文案与备用词见规格文档 §6.1。

## 6. 资产需求
脸部帧 19 张（设计板裁切占位）+ 小脸/缩略图/光晕；Lucide 线性图标 19 枚。详见规格文档 §7。

## 7. 字体
Noto Sans SC：时间 Big60（700，数字）、标题 Title22（500）、正文 Body18、次要 Small16。

## 8. 验收偏好
对照需求书 §11（规格文档 §8）；位置/比例以设计板为准。

## 9. 迭代记录
| # | 日期 | 用户原话 | 状态 | 改动章节 |
|---|---|---|---|---|
| 1 | 2026-11-07 | 「根据这个需求设计我的AI熊猫挂坠的UI工程文件」 | 首版 | 全部 |

### 待用户确认的假设
1. 错误→表情映射（规格文档 R8）；2. 脸部帧为占位，生产帧走 3D 管线；3. "思考"帧需重做（板上带手）；4. 双击/长按在 C 层实现；5. 脸部屏白毛满屏后，深色功能页是否改成壳白底（R9）。
""")
open(os.path.join(PROJ, "UI需求清单.md"), "w", encoding="utf-8", newline="\n").write("\n".join(R))
print("docs written | texts: %d | doc chars: %d" % (len(texts), len("\n".join(D))))
