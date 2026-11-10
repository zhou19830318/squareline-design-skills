# squareline-design（Cowork 插件）

**从概念图设计 SquareLine Studio / LVGL 工程及各项资产。**
流程：需求追溯 → 概念图量测 → 规格与资产 → 构建前体检 → 构建 / 反渲染 → 真 LVGL 真值审计 → 多轮优化。
含 `slx next` 工作流驱动，适配任何能跑 shell 的大模型。当前版本 0.2.0，改动见 `CHANGELOG.md`。

## What this plugin runs, fetches and sends (disclosure) / 运行、联网与数据说明

**English.** This plugin has no hooks, no MCP servers and does not touch Claude / Cowork settings. It only gives Claude instructions (skills, slash commands, a reviewer agent)
and a command-line toolkit (`tools/slx.py`, Python + Node.js) that Claude runs through the shell **inside your project folder**.
Network use is limited to: (1) first use only - `npm ci` downloads four pinned packages and their dependencies (lv_font_conv, lucide-static, @resvg/resvg-js, @resvg/resvg-wasm; about 75 MB on disk, 63 MB of it the Lucide icon set) from registry.npmjs.org
(`python3 tools/slx.py setup` does the same by hand); (2) optional, only if you run `slx.py truth` - downloads the LVGL 9.2.2 source tarball from codeload.github.com once into `~/.cache/slx`
and compiles it locally with gcc; (3) if you ask for an icon that is not in the bundled Lucide set, the host's web tools may fetch an SVG from an icon site that you approve.
**Nothing about you, your files or your designs is uploaded anywhere by this plugin: no telemetry, no analytics, no credentials.** It reads concept images and documents from your project folder
and writes the generated project (`.spj`, PNG, fonts, previews, reports) next to them; the optional LVGL cache is the only place outside the project it writes to.

**中文。** 本插件没有 hooks、没有 MCP 服务，也不修改 Claude / Cowork 的设置；它只提供给 Claude 的指令（技能、斜杠命令、审查代理）和一套命令行工具（`tools/slx.py`，Python + Node.js），
由 Claude 通过 shell 在**你的工程目录内**运行。联网仅限三处：① 首次使用时 `npm ci` 从 registry.npmjs.org 下载 4 个版本固定的依赖包及其依赖（lv_font_conv、lucide-static、@resvg 两个包，磁盘约 75 MB，其中 Lucide 图标集占 63 MB；也可手动 `python3 tools/slx.py setup`）；
② 仅当你运行 `slx.py truth` 时，从 codeload.github.com 一次性下载 LVGL 9.2.2 源码到 `~/.cache/slx` 并在本地用 gcc 编译；③ 你要求的图标不在随包 Lucide 图标集里时，宿主的网页工具可能从你认可的图标站获取 SVG。
**插件本身不会上传你的任何信息、文件或设计，没有遥测、统计或凭据。**

## 目录

1. [准备（一次性）](#一准备一次性)
2. [你要准备的输入](#二你要准备的输入)
3. [方式 A：在 Cowork 里对话](#三方式-a在-cowork-里对话最省事)
4. [方式 B：命令行主循环](#四方式-b命令行主循环)
5. [拿到结果](#五拿到结果)
6. [改需求](#六改需求)
7. [出错怎么办](#七出错怎么办)
8. [让结果更准的几点](#八让结果更准的几点)
9. [工程目录结构](#九工程目录结构)
10. [工具链一览](#十工具链一览)
11. [包含内容](#十一包含内容)
12. [已验证 / 未验证](#十二已验证--未验证)
13. [能力边界](#十三能力边界)
14. [自检](#十四自检)
15. [许可](#十五许可)

---

## 一、准备（一次性）

**环境**（运行 `python3 tools/slx.py doctor` 一次检查全部）：

| 类别 | 内容 |
|---|---|
| 必需 | Python ≥ 3.8；`pip install pillow numpy`；Node.js（字体与 SVG→PNG） |
| 可选 | playwright + chromium（生成截图）；gcc（真值审计 `slx.py truth`） |

**安装**：
- **Claude Code / Cowork（从 GitHub）**：
  ```
  /plugin marketplace add YOUR_GITHUB_USERNAME/squareline-design-skills
  /plugin install squareline-design@squareline-design-marketplace
  ```
  具体入口以你的版本界面为准。Node 依赖在首次使用时自动安装（需要 Node.js 和网络）。
- **其它大模型 / 终端**：解压后直接用命令行，把 `AGENTS.md`（或 `docs/UNIVERSAL_PROMPT.md`）交给它即可，工具都是命令行，能跑 shell 就能用。

下文命令里的 `slx.py` 即 `python3 <插件目录>/tools/slx.py`。

## 二、你要准备的输入

| 输入 | 说明 |
|---|---|
| 概念图 | 一张或多张。尽量用正面平面图，不要带透视的实拍图 |
| 需求文档 | 可选，md / txt。里面的"必须 / 不得 / 禁止"会被逐条追溯 |
| 面板信息 | **分辨率和形状**（如 360×360 圆形）。图里读不出来就要告诉它，否则会被当作"假设" |
| 补充说明 | 比如"外壳是白色""不要手"。口头指示和文档冲突时，会被记为偏差并告诉你 |

## 三、方式 A：在 Cowork 里对话（最省事）

把概念图和需求文档放进工作区文件夹，然后：

```
/squareline-design:new <概念图路径> MyWatch 360x360 CIRCLE
```

或者直接说"帮我把这张图做成 SquareLine 工程"，技能会自动触发，并且全程用 `slx.py next` 驱动。

**你会被问两次**：

1. **闸门 1**：一张确认表（面板、屏幕与跳转、配色、字号、哪些是"测得 / 估算 / 假设"、≤5 个待决问题）。你确认后才会生成资产。
2. **闸门 2**：构建前给你看预览图。

全部命令：

| 命令 | 用途 |
|---|---|
| `/squareline-design:new <概念图> [工程名] [宽x高] [RECT\|CIRCLE]` | 全流程，含两个确认闸门 |
| `/squareline-design:analyze <概念图>` | 只做分析：需求追溯、量测、规格 |
| `/squareline-design:assets [工程]` | 只处理图标、烘焙图、raster 裁切、字体配置 |
| `/squareline-design:build [工程]` | 体检 → 构建 → 校验 → 反渲染 |
| `/squareline-design:iterate <修改意见>` | 应用一轮修改并登记迭代表（一次只改一条） |

## 四、方式 B：命令行主循环

```bash
python3 tools/slx.py init MyWatch --width 360 --height 360 --shape CIRCLE --dir ~/work
cp 概念图.png 需求.md ~/work/MyWatch/concept/
python3 tools/slx.py next ~/work/MyWatch      # 之后每做完一步都跑它
```

`next` 只告诉你**下一步**：做什么、为什么、怎么做、做到什么算完成。典型阶段：

```
需求追溯 → 分析 → 闸门1 → 资产 → 体检 → 构建 → 反渲染 → 真值审计 → 对照概念图 → 追溯终检
```

> 工程名 `<Name>` 只能用英文字母 / 数字 / 下划线，且以字母开头。不要把工程建在插件目录里。

**各阶段常用命令**

```bash
# 1. 需求追溯
slx.py reqs extract concept/需求.md --proj .      # 拆成带编号的需求
slx.py reqs todo .                                 # 分批列出待处置项
slx.py reqs set . R012 done --evidence "home/face"
slx.py reqs set . R053 deviation --reason "双击/长按在 C 层实现"
slx.py reqs check .  &&  slx.py reqs report .      # 检查并生成追溯矩阵

# 2. 量概念图
slx.py scan 图.png --find-screens                  # 设计板上有哪几块屏
slx.py scan 图.png --screen x0 y0 x1 y1 --panel 360 --shape circle   # 一块屏里的元素
slx.py palette 图.png ;  slx.py grid 图.png --step 50 ;  slx.py crop 图.png x0 y0 x1 y1 --zoom 3
slx.py bbox 图.png x0 y0 x1 y1 --scale 0.6         # 量某元素的位置/尺寸（面板 px）
slx.py fit-font "10:42" --w 193 --h 55 --weight 700 --cy 161     # 由实测文字框反算字号和 y

# 3. 记录你的确认（闸门）
slx.py gate . 1 --note "用户确认了面板、屏幕、配色"
#   用户说"别问了直接做"时加 --assume，并在最终报告里列出所有假设

# 4. 生成与检查
slx.py assets .       # 生成图标 / 图片（lucide / svg / builtin / raster）
slx.py check .        # 构建前体检（带编号和修法）
slx.py preview .      # 免构建的版面预览
slx.py build .        # 有体检错误时会拒绝构建
slx.py verify .       # 反渲染，看 preview/screens/*.png
slx.py truth .        # 用真 LVGL 审计文字位置（需 gcc，首次下载 LVGL）
slx.py diff 概念裁剪.png preview/screens/home.png     # 概念图 | 渲染 | 差分
```

**用 Python 写 spec（推荐，少出坐标错误）**：`tools/specbuilder.py` 提供芯片 / 开关 / 滑块 / 提示条 / 卡片 / 进度环等控件，
文字按"墨迹中心"定位，参考 `examples/PandaPendant/scripts/gen_spec.py`。

**从概念图里裁一块素材**（仅限用户自己的作品且明确要复用；默认是重绘）：在 `assets.manifest.json` 里写 `raster` 条目，必须带 `provenance`：

```jsonc
{ "name":"img_face_idle", "source":"raster", "file":"concept/board.png", "crop":[x0,y0,x1,y1],
  "size":[360,360], "mask":"circle", "feather":0.12,
  "provenance":"用户设计板第 1 格（用户确认可用）" }
```

## 五、拿到结果

| 文件 | 说明 |
|---|---|
| `squareline/<Name>/<Name>.spj` | **工程文件**。用 SquareLine Studio 1.6.2 的 Open Project 打开 |
| `preview/screens/*.png` | 逐屏预览（大工程以它为准） |
| `需求追溯矩阵.md` | 每条需求的处置与证据；**请重点看"偏差 / 无法实现"那几段** |
| `<Name>设计规格文档.md` | 源真相：画布、配色、逐屏对象表、交互、字体与字符集、资产、验收、风险 |

## 六、改需求

**不要手改 `.spj`**（编辑器一保存就会重写它）。改法：

1. 让 Claude 或你自己改规格文档、`<Name>.spec.json`、`assets.manifest.json`。
2. 重新 `build` → `verify`。

一次只改一条，出问题才好定位。在 Cowork 里用 `/squareline-design:iterate "把时间改大一点"`。

## 七、出错怎么办

| 现象 | 做法 |
|---|---|
| 任何报错 | `slx.py explain "报错片段"` 或 `slx.py explain E-XXX` |
| `build refused` | 先修 `check` 列出的 ERROR（每条附修法）。不建议 `--force` |
| 图片缺失（missing） | 检查 manifest 后跑 `slx.py assets`；`IMAGE.asset` 必须是扁平路径 `assets/<名>.png` |
| 双击 / 长按没反应 | 这两个事件在编辑器里没验证过，工程里故意没接，要在 C 层实现，并在追溯矩阵记为偏差 |
| 站外图标下载失败 | 沙箱网络受限：把 SVG 放进 `downloads/`，或放开网络 |
| `scan` 漏了元素 | 压在大图形上的文字会被合并（会提示）：裁出该区域单独再扫，或试 `--tol 80` |
| 文字位置和概念图差几个 px | 用 `fit-font` 重算字号和 y；要绝对准用 `truth` |
| 想看某个错误码的含义 | `slx.py explain --all` 列出全部 |

## 八、让结果更准的几点

1. 一开始就给出**分辨率和形状**。
2. 需求文档里写清"必须 / 不得"，它们会被逐条验证。
3. 概念图和文档冲突时，直接告诉它以谁为准。
4. 想要"绝对准"的文字位置，装 gcc 跑 `truth`。预览只是近似（约 ±2 px）。
5. 引擎只有 `PANEL / LABEL / IMAGE / ARC`：渐变、阴影、发光会被烘焙成图或舍弃，进度环是单色。
6. 概念图里的字体无法复刻，只匹配字重与字号（随包字体是 Noto Sans SC）。

## 九、工程目录结构

```
<Name>/
├── concept/                概念图、需求文档（输入）
├── UI需求清单.md   <Name>设计规格文档.md          ← 源真相
├── <Name>.spec.json   assets.manifest.json        ← 声明式规格与资产清单
├── requirements.json   需求追溯矩阵.md             ← 需求追溯
├── downloads/              从图标站取来的 SVG
├── assets/images/          生成的 PNG
├── squareline/<Name>/      ← .spj 工程（交付物）
├── preview/                预览图、diff、truth 报告
└── .slx/state.json         闸门记录（用户批准）
```

## 十、工具链一览

| 作用 | 命令 |
|---|---|
| 工作流驱动 / 记录用户批准 | `next`、`gate` |
| 量概念图 | `scan`、`palette`、`grid`、`crop`、`bbox`、`fit-font` |
| 需求追溯 | `reqs extract / todo / set / add / check / report` |
| 资产 | `assets`（lucide / svg / builtin / raster） |
| 体检与排错 | `check`、`explain` |
| 构建与验证 | `build`（先体检）、`preview`、`verify`、`diff`、`sidebyside`、`shot` |
| 真值 | `truth`：用真正的 LVGL 渲染每个文字标签并与设计意图比对（需 gcc） |
| 环境 | `doctor`、`init` |
| 写 spec | `tools/specbuilder.py`（控件库，文字按墨迹中心定位） |

`python3 tools/slx.py`（不带参数）会打印全部命令与参数。

## 十一、包含内容

- **技能**：`concept-to-spec`（读图、需求追溯）、`squareline-assets`（图标 / raster / 字体 / 许可）、`squareline-ui-pipeline`（总控、规则、迭代）
- **子代理**：`design-reviewer`（对照概念图审查，给出可落到 spec 的差异清单）
- **工具链**：`tools/slx.py` + `tools/slxlib/`（lint、reqs、scan、fontfit、truth、nextstep…）+ 上游构建引擎 / 校验器 / 反渲染 + Lucide 图标库 + Noto Sans SC
- **示例**：`examples/NovaWatchS12`（上游黄金样例）、`examples/PandaPendant`（37 屏、73 条需求追溯的完整项目，纯文本不含图片）
- **可移植指令**：`AGENTS.md`、`docs/UNIVERSAL_PROMPT.md`
- **测试**：`tests/run_tests.py`（15 项）

## 十二、已验证 / 未验证

已验证：
- 上游 NovaWatchS12（456×456 圆屏、10 屏）重建的 `.spj` 与上游黄金文件**逐字节一致**。
- 37 屏的 PandaPendant 通过校验器、体检 0 错误、真 LVGL 文字审计 113/113 在 1.5 px 内。
- 反渲染预览与真 LVGL 的文字位置差 ≤ 2 px（`tests` 与 `truth` 可复现）。

**未验证 / 需要你注意**：
- **没有在真实的 SquareLine Studio 里打开过任何生成的工程。** 第一次拿到 `.spj` 请先打开确认，有问题把现象告诉我们。
- `scan` 与 `reqs extract` 是启发式：`scan` 会漏掉压在大图形上的文字（会提示）；`reqs extract` 抽出的清单要人工略读修正。
- 站外图标站需要网络；受限时插件会告知而不是悄悄替代。
- 命令和技能在 Cowork 中的触发效果未做过实机验证。

## 十三、能力边界

- 引擎只有 `PANEL / LABEL / IMAGE / ARC` 四种原语：渐变、阴影、模糊、复杂图形要烘焙成 PNG；进度环必须是单色活 ARC；字体只能匹配 Noto Sans SC。
- `LONG_PRESSED` / `DOUBLE_CLICKED` 不在编辑器已验证事件集内，工程里不接线，由 C 层实现并在追溯矩阵里记为偏差。
- 上游自带的 Nova 样例有 8 个没有返回手势的子页面，现在 `build` 会拦下，需 `build --force`。

详见 `skills/concept-to-spec/references/expressibility.md` 与 `CHANGELOG.md`。

## 十四、自检

```bash
python3 tests/run_tests.py          # 15 项回归测试
SLX_LVGL_SRC=<LVGL 源码目录> python3 tests/run_tests.py   # 有 gcc 和 LVGL 源码时多跑一项真值测试，否则跳过
```

## 十五、许可

见 `NOTICE.md`。上游项目的许可证在所给压缩包中未找到，分发前请确认。
