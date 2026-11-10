---
name: squareline-assets
description: >-
  Collects and generates every asset a SquareLine/LVGL project needs: icons (Lucide offline, icon sites
  such as Iconify / SVG Repo / Tabler / Bootstrap / Material / Phosphor, hand-drawn SVG), baked
  decorations (watch dials, waveforms, gradient rings), and the LVGL font subsets — all as native-size
  PNGs with licence tracking. Use when the user asks for 图标 / 图片 / 资产 / icon sources / "找图标" /
  "生成 PNG" / "字体子集" / "换个图标风格", or when a spec lists IMAGE objects whose PNGs do not exist yet
  (preview shows red boxes, validator says "missing image files"). Run after concept-to-spec's
  gate 1, before building.
---

# SquareLine 资产：图标 / 烘焙图 / 字体

输出统一是 **PNG，按目标 `rect` 的原生像素尺寸渲染**，放进 `<proj>/assets/images/`。
工具约定（`$TK`、`$SLX`、工程目录）见 `squareline-ui-pipeline`。

## 1. 先盘点，再选源

从规格文档 §7 / spec JSON 里把所有 `IMAGE` 对象列成表：`文件名 | 目标尺寸 | 用途 | 颜色 | 来源`。
文件名必须 `img_<屏>_<含义>[_<状态>][_<尺寸>]`（如 `img_weather_icon_rain_72`），**不沿用站点原文件名**。
一枚图标一个 PNG；要两个尺寸就写两条（后缀区分）。

每个条目选三种来源之一：

| 来源 | 清单写法 | 何时用 |
|---|---|---|
| **Lucide**（默认，**离线**，~1500 枚线性图标，ISC） | `{"name":…,"source":"lucide","icon":"clock","size":44,"color":"#FFFFFF","stroke_width":2}` | 线性风格、通用图形。先在 `$TK/tools/node_modules/lucide-static/icons/` 里 `ls | grep` 找名字 |
| **站外 SVG**（Iconify / SVG Repo / Tabler / Bootstrap / Feather / Material / Phosphor…） | 先下载到 `<proj>/downloads/<站>_<名>.svg`，再 `{"source":"svg","file":"downloads/xxx.svg",…}` | Lucide 没有的图形、要彩色/填充/双色风格、用户点名某站 |
| **自绘 builtin SVG** | `{"source":"builtin","svg":"<svg viewBox=…>…</svg>","size":N}` | 表盘、刻度、波形、渐变环、满宽字形、品牌无关的自制 logo |

`file` 相对**清单所在目录**解析（本插件已补丁），所以写 `downloads/…` 即可。

## 2. 站外图标的取得（重要：网络可能受限）

站点目录、许可证与风格对比见 **`../squareline-ui-pipeline/ICON_SOURCES.md`**。取得顺序：

1. 先看 Lucide 能不能满足——能就不出网，最稳。
2. 需要站外图标：用 `web_search` 找到图标页 → `web_fetch` 取 SVG 文本 → 写进 `downloads/`。
   Iconify 单图标直链形如 `https://api.iconify.design/<集>--<名>.svg?color=%23FFFFFF`
   （`web_fetch` 只能打开"用户给过/搜索结果里出现过"的 URL，**不能自己拼**；拼不出来就搜到集合页再取）。
3. 沙箱里 `curl` 访问图标站可能被网络白名单拦（`x-deny-reason`）。遇到就**直接告诉用户**：
   可以在设置里放开网络，或者请用户把 SVG 拖进 `<proj>/downloads/`。**不要**悄悄用别的风格顶替。
4. 下载后检查 SVG：去掉 `<metadata>`；确认**没有内嵌位图** `<image href="data:…">`；
   响应式 SVG（无宽高）转换器会按 `size`/viewBox 重定视口，没有 viewBox 的先手工补。

## 3. 许可证纪律（写进工程，不是口头说说）

- 默认只用 **MIT / ISC / Apache-2.0 / CC0**；用户要求商用时尤其如此。
- **CC BY / CC BY-SA** 图标必须在交付说明里署名；许可不明的**不要用**，换 Lucide 或自绘。
- 每个下载的 SVG 在规格文档 §7 资产清单写：`站点 | 集合 | 许可证 | 原链接`。
- 反面清单：参考产品的官方图/固件截图抠图；无许可声明的"免费图标站"；AI 位图放大当图标。

## 3.5 `raster` 源：从用户给的位图里裁一块

默认**重绘**（Lucide/SVG/builtin）。只有"这块是用户自己的作品、且用户明确要复用"时才裁位图：

```jsonc
{ "name":"img_face_idle", "source":"raster", "file":"concept/board.png", "crop":[x0,y0,x1,y1], "size":[360,360],
  "mask":"circle", "feather":0.12, "sharpen":true,
  "provenance":"用户设计板第 1 格（用户确认可用）" }          // provenance 必填，缺了 assets 命令直接报错
```
输出到 `assets/images/<name>.png`，出处写入 `assets.provenance.json`。更复杂的处理（补白、提亮）才需要写自己的脚本。

## 4. 写清单并生成

```jsonc
// <proj>/assets.manifest.json
{ "defaults": { "size": 44, "color": "#FFFFFF", "stroke_width": 2 },
  "icons": [
    { "name":"img_home_icon_clock", "source":"lucide", "icon":"clock" },
    { "name":"img_weather_icon_sun_112", "source":"lucide", "icon":"sun", "size":112, "color":"#FF9F0A" },
    { "name":"img_settings_icon_brightness", "source":"svg", "file":"downloads/tabler_brightness.svg", "size":44 },
    { "name":"img_face_dial", "source":"builtin", "size":456, "svg":"<svg viewBox=\"0 0 456 456\">…</svg>" }
  ] }
```

```bash
$SLX assets <proj>        # 每行 ok <name> WxH；末行 failures: 0
```

- **`"out"` 不要写**（`slx` 传 `--out`）。
- 任何 `failures` ≠ 0 / `WARN header … !=` 都要修，不要带着进构建。
- 单枚临时转换：`node $TK/tools/svg_to_png.mjs <x.svg> --out <proj>/assets/images --size 44 --name img_x`。
- 渲染引擎是 `@resvg/resvg-js`（原生）+ WASM 兜底；输出 backend 行会写 `native` 或 `wasm`，两者产出相同 PNG。

## 5. 质量规则

- **原生尺寸渲染**：PNG 宽高 = spec 里该 IMAGE 的 `rect` 宽高，不靠运行时拉伸（拉伸导致模糊，翻过车）。
- 线性图标放大后描边显细：≥44 px 建议显式 `stroke_width`（Lucide 源走清单字段）。
- 颜色：线性图标统一一个色（通常 `#FFFFFF`），状态色用单独条目（`_on/_off`）而不是运行时染色。
- 满宽/不规则图形自写 path；24×24 网格会 letterbox。
- 指针/刻度：**预烘焙**成单张 PNG（10:09:35 姿态），不要依赖 LVGL 旋转。
- 对照审计：`ls assets/images` 对 spec 里的 `asset` 引用——**缺的补，多的不是删掉而是接进某个真实状态**
  （没被引用的图不会进工程）。`$SLX preview <proj> --strict` 缺图会画红框并非零退出。

## 6. 字体

字体由构建阶段自动生成（`lv_font_conv`，输出 `.c/.bin/.fcfg` 三件套，缺一不可），你只需要在 spec 里把它**配对**：

- 只有随包的 Noto Sans SC：`…-700.ttf`（大数字）/ `…-500.ttf`（标题）/ `…-regular.ttf`（正文）。
- `fonts[]`：`codename`（如 `Title28`）+ `ttf` + `size` + `kind`。**非 text 字体收 `symbols[kind]` ∪ `ranges_num`**，要让纯数字字体小就把 `ranges_num` 设成 `["0x30-0x3A"]`。`text` 是内置的（收录全部 UI 文案 + 规格文档余量）；**任何其它 kind 必须在 spec 的 `symbols` 里声明字符集**，
  例如 `"symbols": {"number": "0123456789:.%"}`，否则构建报 `KeyError: 'number'`。
- `ranges_text` 含 CJK 所需区段与标点；`ranges_num` 只含 `0x20-0x7E`、`0x00B0`。
  **用 `0x20-0x7E`，不要 `0x20-0x7F`**（DEL 任何字体都没有，会永远告警）。
- 字符集来自规格文档（`spec_docs`）+ spec 里所有 LABEL 文本。构建会打印
  `charset: ui-text N, doc-headroom M`——`M` 就是日后改文案的余量。
- 需要别的字体（品牌字/日文/阿拉伯文）：把 TTF 放进 `<proj>/assets/fonts/`（引擎优先读工程自己的），
  `ttf` 字段写文件名，并核对字体许可（OFL/Apache 可嵌入；商用字体先问用户）。
- 彩色 emoji **不进字体**，渲染成 PNG 图片对象。

## 7. 交付给用户的资产摘要

生成完后汇报：PNG 总数与尺寸分布；来源分布（Lucide N / 站外 N / 自绘 N）；**需署名的许可项**；
任何用了近似或替代的图标（"概念图里是实心心形，Lucide 只有线性，已改线性并保持同尺寸"）。
