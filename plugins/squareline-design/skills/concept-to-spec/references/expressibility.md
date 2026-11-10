# 概念图元素 → 引擎原语：可表达性与烘焙做法

引擎（`build_from_spec.py`）只有四种原语。判断一个视觉元素怎么落地，先看它能不能被下面这些"活对象"
描述；不能的，**烘焙成 PNG**（用 `assets.manifest.json` 里的 `builtin` 内联 SVG）。
原则：**文字、数字、进度值、要点击/要显隐的东西保持活对象；纯装饰与复杂图形烘焙。**

## 1. 四种原语能做什么

| 原语 | 可控属性 | 典型用途 |
|---|---|---|
| `PANEL` | `bg`、`radius`、`clickable`、`children`、`hidden` | 卡片、按钮底、药丸、开关轨道/旋钮、分割线（高 1–2 px）、圆点、遮罩层 |
| `LABEL` | `text`、`font`、`color`、`align`（LEFT/CENTER/RIGHT） | 一切文字与数字 |
| `IMAGE` | `asset`（扁平路径 `assets/img_x.png`）、`rotation` | 图标、烘焙的装饰、表盘、波形 |
| `ARC` | `value/max`、`indicator`、`track`、`width`、`angles[from,to]` | 进度环、仪表盘、呼吸圈 |

颜色支持 `#rrggbbaa`（带透明度）。例（取自 NovaWatchS12）：

```jsonc
{"type":"ARC","name":"ring_move","rect":[148,60,160,160],"value":68,"max":100,"indicator":"PINK","track":"TRACK","width":14}
{"type":"PANEL","name":"card_hr","rect":[88,360,130,60],"bg":"CARD","radius":16,"children":[ … ]}
{"type":"PANEL","name":"al1_on","rect":[296,118,40,22],"bg":"CARD2","radius":11,"hidden":true,"children":[ … ]}   // 开关"开"态，初始隐藏
```

## 2. 判定表（常见效果）

| 概念图效果 | 能直接画？ | 做法 |
|---|---|---|
| 纯色圆角卡片 | ✅ | `PANEL` + `radius` |
| 圆形 / 药丸 | ✅ | `PANEL`，`radius` ≥ 短边一半 |
| 细分割线 | ✅ | 高 1–2 px 的 `PANEL`，颜色用 `TRACK` |
| 半透明蒙层 | ✅ | `PANEL` + `#rrggbbaa` |
| 描边框（无填充） | ⚠️ | 无描边属性：外 `PANEL`(描边色) + 内 `PANEL`(背景色) 叠成，或烘焙 |
| 渐变背景 | ❌ | 烘焙 `IMAGE`（静态背景才适合烘焙） |
| 渐变进度环 | ❌ | **进度值会变，不能烘焙**：用单色活 `ARC`，色取渐变中点（标 `[估算]`），并告诉用户"渐变/发光无法保留"。只有环是纯装饰（值不变）时才烘焙整环 |
| 投影 / 发光 | ❌ | 烘焙；或用 2–3 层放大的低透明度 `PANEL` 近似（要告知用户是近似） |
| 模糊 / 毛玻璃 | ❌ | 烘焙静态近似；告知"无实时模糊" |
| 非圆角矩形形状（箭头、气泡尾巴、星形） | ❌ | 烘焙为 `IMAGE` |
| 表盘刻度 / 数字环 | ❌ | 预烘焙整盘 PNG（见 NovaWatchS12 的 `img_face_dial`，builtin SVG） |
| 模拟指针 | ❌ | 预烘焙：固定 10:09:35 姿态画进同一张 PNG，轴心在屏幕中心；不用 `rotation` |
| 波形 / 迷你折线图 | ❌ | builtin SVG 烘焙；多状态 = 多张 PNG 叠层显隐 |
| 照片 / 插画 | ❌ | 默认重绘矢量或占位；用户确认可用其作品时才裁位图 |
| 进度值/百分比随数据变 | ✅ | `ARC` + 对应 `LABEL`（运行时由业务代码 `CALL_FUNCTION` 更新） |
| 多状态图标（开/关、三态麦克风） | ✅ | **一个状态一个对象**，初始 `hidden` 明确设置，用 `HIDE/SHOW/SET_OPACITY` 切换 |

## 3. 烘焙（builtin SVG）规范

在 `assets.manifest.json` 里：

```jsonc
{ "name":"img_face_dial", "source":"builtin", "size":456,
  "svg":"<svg viewBox=\"0 0 456 456\"> … </svg>" }
```

- **尺寸 = 对应 `rect` 的像素**（宽高一致，`viewBox` 与之对齐）；不要小图拉伸。
- 满宽/不规则图形必须自写 path；Lucide 的 24×24 网格会 letterbox。
- 命名 `img_<屏>_<含义>[_<状态>][_<尺寸>]`；尺寸差异用后缀，不靠目录区分。
- 烘焙层只放**不会变**的东西；会变的值（时间文字、步数、进度）一律活对象。
- 渐变用 SVG `<linearGradient>/<radialGradient>`；resvg 支持，输出 PNG 即定格。
- 烘焙后在规格文档 §7 记一行：文件 / 尺寸 / 用途 / 生成方式（`builtin 自绘`）。

## 4. 动画能做什么

动画表字段：`name / target(屏/对象) / tracks[{property, frames[[值,毫秒]…], duration}] / duration / path(linear|ease_in|ease_out|overshoot) / loop_infinite`。
实践里稳的属性是 `opacity`（脉冲、呼吸、渐显）。位移/缩放类概念图动效不要承诺；给替代：
透明度脉冲、分帧 PNG 叠层切换、`SCREEN_LOAD_START` 触发的进场动画。写不进的动效要在确认表里告诉用户。

屏幕进场动画的挂法（NovaWatchS12）：

```jsonc
"screen_events": { "health": [ { "on":"SCREEN_LOAD_START", "name":"health_enter",
   "actions":[ { "type":"PLAY_ANIMATION", "animation":"health pulse", "object":"health/ring_move" } ] } ] }
```

## 5. 圆形屏落位检查清单

1. `r = 面板宽 / 2`；圆心 `(r, r)`。
2. 每个可见元素外接框的**四个角**到圆心距离 ≤ `r − 边距`（边距 ≈ 5% × 直径）。
3. 靠上/下缘的元素，用 `chord(y) = 2·sqrt(r² − (y − r)²)` 取该元素上下沿处较小的弦宽作为可用宽度。
4. 允许探出的：透明命中区、全宽居中的文字框（文字本身在内即可）、预烘焙的整盘 PNG。
5. 图标环：N 个图标等角分布，半径取 `r × 0.55–0.7`，起始角偏移半格避开顶部状态区（具体数值每个面板重算）。

## 5.5 进度环起点

LVGL 默认从 3 点钟起。概念图从 12 点钟顺时针 → `ARC` 加 `"angles":[270,269]`。`rect` 是外接框（外径 = 2×(环中心半径 + 环宽/2)）。

## 6. 字体映射

- 只有 Noto Sans SC：700（大数字/强调）、500（标题）、400（正文/小注）。
- 概念图字高 → 字号：**用 `slx.py fit-font "<文字>" --w <实测宽> --h <实测高> --weight <700|500|400>`**（真正的 lv_font_conv 度量；
  宽、高给出的字号相差大说明概念图字体比例和 Noto 不同——数字取宽度保持版面占位，中文取高度）。`h/0.72` 只是无工具时的粗估，会偏大 6–12%。
- 数字专用字体设 `kind: "number"`，在 spec 顶层声明 `"symbols": {"number": "0123456789:"}`，**并把 `ranges_num` 收到 `["0x30-0x3A"]`**。
  非 text 字体收的是 `symbols[kind]` ∪ `ranges_num`：默认的 `0x20-0x7E` 会把整段 ASCII 带进去（体积大，行高被撑高，数字在行框里偏上）。
  `kind` 只有 `text` 是内置的。
- 档位尽量少（3–4 档）：每多一档就多一份字体文件。
