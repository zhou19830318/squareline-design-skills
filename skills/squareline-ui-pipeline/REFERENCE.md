# REFERENCE.md — SquareLine/LVGL UI 管道技术参考

> 供 agent 深改工具链时查阅。SKILL.md 是工作流与教训，本文是底层机制。
> 经验来自 AIWatch（410×502 方形）与 AIWatchApple（240×240 圆形）两个完整项目。

---

## 1. .spj 文件格式（SquareLine 1.6.2）

`.spj` 是 UTF-8 JSON，顶层键：`root / animations / info / selected_screen / selected_theme`。

### 1.1 几何信息

```
spj["info"] = {
  "name": "<Name>.spj", "depth": 1,
  "width": 240, "height": 240,        ← 面板尺寸在这里
  "shape": "CIRCLE",                   ← RECT(默认) / CIRCLE
  "board": "CMake/Eclipse/VScode with SDL for development on PC",
  "board_version": "v2.0.2", "editor_version": "1.6.2", ...
}
```

**SCREEN 节点不带 OBJECT/Size**（验证过：屏节点属性只有 Name/Layout/Flags/
Scroll* 等）。想拿面板尺寸只能读 `spj["info"]`。`.sll`/`.slp` 是 info 的副本。

### 1.2 对象树

```
root.children[] = SCREEN 节点数组（按切换顺序）
node = { guid, saved_objtypeKey, properties[], children[] }
saved_objtypeKey ∈ SCREEN | PANEL | CONTAINER | LABEL | IMAGE | ARC | BAR |
                    SLIDER | DROPDOWN | ... （ELOANIMATION 是动画节点）
```

属性项（property）形如：

```json
{ "nid": 123, "strtype": "OBJECT/Position", "intarray": [24, 30], "InheritedType": 7 }
{ "nid": 124, "strtype": "LABEL/Text", "strval": "10:09", "InheritedType": 5 }
{ "nid": 125, "strtype": "_style/Text_Font", "strval": "Title20" }
{ "nid": 126, "strtype": "OBJECT/Hidden", "strval": "True" }
```

关键 strtype 速查：

| strtype | 值形 | 备注 |
|---|---|---|
| OBJECT/Name / Position / Size | strval / intarray | **Position 是父中心相对偏移**（见 1.4） |
| OBJECT/Hidden / Clickable | "True"/"False" | State_trickle 见 1.5 |
| OBJECT/Flags | 事件挂载 | |
| LABEL/Text | strval | `\n` 以字面反斜杠存储；禁止真实换行/裸引号 |
| IMAGE/Asset | "assets/img_x.png" | 相对工程目录 |
| IMAGE/Rotation | integer | 单位 0.1°，不可靠（预烘焙替代） |
| ARC/Value / Range / Bg_angles | intarray | 角度：LVGL 0° = 3 点钟 |
| _style/Bg_Color / Text_Color | intarray [r,g,b,a] | |
| _style/Bg_Radius / Arc_Width | integer | |
| _style/Text_Align | LEFT/CENTER/RIGHT | |
| _style/Text_Font | 字体 codename | 必须有对应 .fcfg |
| _event/EventHandler | strval = 事件类型 | 挂在对象 properties 里 |
| _event/action | strval = 动作类型 | EventHandler.childs 里 |

样式挂在 `part` 上：`lv.PART.MAIN` / `lv.PART.INDICATOR` / `lv.PART.SCROLLBAR`，
part.childs[].childs[] 里才是 strtype 项（预览器 main_style_of/part_style 的解析方式）。

### 1.3 事件动作 schema（REF_ACTION_FIELDS）

```
CHANGE SCREEN : Screen_to(屏guid) Fade_mode("FADE_ON") Speed Delay
MODIFY FLAG   : Object(对象guid) Flag("HIDDEN"...) Action("ADD/REMOVE/TOGGLE")
MODIFY STATE  : Object State Action
SET OPACITY   : Target Value
PLAY ANIMATION: FunctionName Target Delay
CALL FUNCTION : Function_name Dont_export_function
```

事件类型：CLICKED / PRESSED / RELEASED / PRESS_LOST / VALUE_CHANGED /
SCREEN_LOAD(ED|_START) / SCREEN_UNLOAD(ED|_START) /
GESTURE_LEFT|RIGHT|UP|DOWN(GESTURE) / CHECKED|UNCHECKED(VALUE_CHANGED)。

EventHandler 必备子项：`_custom/name`、`_custom/condition_C`、`_custom/condition_P`、
至少一个 `_event/action`。动画 setter/getter 白名单见 validator 的 FUNC_OK
（anim_callback_set_opacity/x/y/width/height/image_angle/image_zoom/image_frame）。
动作路径 Path: linear=0 ease_in=1 ease_out=2 overshoot=4。

### 1.4 坐标系（最重要的一个坑）

SquareLine 存 **父对象中心相对偏移**：`child.x = parentW/2 + ox − w/2`。
builder 的做法：全部用**屏幕绝对坐标（左上角）**书写 → 最后一遍 `rebase()`
自顶向下换算。两条铁律：
- 不要混入容器相对坐标（weather 屏曾因此整体偏移一个容器原点）；
- rebase 必须是生成 .spj 前的最后一步。

### 1.5 Clickable 的编辑器演化

官方 examples（旧格式）：无事件对象写 `OBJECT/Clickable:"False"`，有事件的对
象省略 Clickable（隐式可点）。
编辑器当前保存格式：**事件对象可省 `Clickable:True`**，事件少对象用
`OBJECT/State_trickle:"True"`（editor backup zip 中 296 处 State_trickle、
0 处 Clickable:True 为证）。
validator 的对策：`SAVED_FORM_ONLY = {"OBJECT/State_trickle"}` 允许清单 +
handler 存在即视为可点击。

### 1.6 nid / guid

- `nid`：全工程唯一、单调递增（builder 一个计数器发到底）。重复 nid 会让
  编辑器静默损坏工程。
- `guid`：对象唯一标识（"GUID…" 字符串），事件动作按 guid 引用对象/屏。

---

## 2. 字体子集化（lv_font_conv）

三件套产物：`<name>.c / <name>.bin / <name>.fcfg`（fcfg 记 codename/size/range，
validator 校验三件齐全）。

```bash
node tools/node_modules/lv_font_conv/lv_font_conv.js \
  --font assets/fonts/<ttf> --size 20 --bpp 4 --format bin \
  --range 0x20-0x7E --symbols "你好" --no-compress -o out.bin
```

经验法则：
- **按用途建字体**（时间/大数字/标题/正文/小字），不要一个大字库——
  240 屏一个全量 CJK 字体 ≈ 数 MB。
- 字符集从**设计规格文档**全文收集（给未来改文案留余量），再减去
  Noto Sans SC v40 缺字表（emoji/box-drawing/VS16 → tofu）。
- 数字字体**不要**包含全角区 0xFF01-0xFF5E（体积×3）。
- `--range/--symbols` 会说谎：cmap Format-4 的 segment 可把整段映射到
  glyph 0。U+00B0 等符号要**走 cmap 表逐码点验证**（builder 里有现成 walker）。

## 3. 资产生成（resvg + lucide-static）

- 图标：读 lucide-static 的 SVG → 换 stroke 色 → resvg 指定尺寸渲染 PNG。
- 自绘 SVG：满宽字形（表盘刻度、电池、Gemini 星、心电波形）必须自写 path，
  24×24 的 renderExact 会 letterbox。
- **指针/刻度预烘焙**：以 10:09:35 姿态画进单张 PNG（含表圈、刻度环、三针
  +轴心），运行时零旋转。LVGL 的 pivot 旋转在 .spj 序列化里不可靠。
- 校验 PNG 实际尺寸：读 IHDR（offset 16/20 的 u32）。
- 2 px ≈ 1 dp：设计 dp × 2 = px，保证高 ppi 小屏清晰。

## 4. 交互模型（零自定义 C）

| HTML 机制 | LVGL/.spj 等价物 |
|---|---|
| opacity 切换多态图 | 每态一个 IMAGE 对象叠放 + MODIFY FLAG(HIDDEN)/SET OPACITY |
| 页面切换 | 屏级 GESTURE_* 事件 + CHANGE SCREEN(FADE_ON) |
| 点击跳转 | CLICKED + CHANGE SCREEN |
| 动画 | PLAY ANIMATION → ELOANIMATION（setter/getter/KeyFrames） |
| 弹层 | 常驻 hidden PANEL + MODIFY FLAG |

状态链检查法（mic 三态事故的教训）：枚举每个状态的可见对象清单，逐一核对
hidden 初值与所有进入路径的切换动作，而不是读代码"看起来对"。

## 5. 验证器（validate_squareline_project.py，10 项）

1. .spj 解析 + 对象三要素（guid/properties/saved_objtypeKey）
2. strtype ⊆ 官方 examples（+ SAVED_FORM_ONLY 允许清单）
3. nid 全工程唯一
4. CHANGE SCREEN 目标屏 guid 存在
5. IMAGE/Asset 磁盘存在
6. Text_Font ⊆ 已声明字体
7. 字体三件套齐全
8. 事件图 schema + guid 引用闭合
9. 动画名解析 + track 结构
10. CLICKED 挂在可点击对象上
加检：遮挡嫌疑（后绘制 IMAGE/不透明 PANEL 压 LABEL ≥35%）、
`set_text` 语法编译（防换行/引号截断）。

参数化：`python validate_squareline_project.py [dir|.spj]`，无参取
`<root>/squareline/` 第一个工程。

**check 2 的 schema 来源（不依赖本机安装）**：按以下顺序取 strtype 白名单——
1. `tools/schema_snapshot.json`（随仓库发货，由 1.6.2 示例工程生成，
   464 strtypes / 20 object types / editor_version 1.5.4）★ 默认走这条；
2. `tools/extra_reference/*.spj`（放自定义参照工程）；
3. `$SQUARELINE_STUDIO/examples`（**仅作交叉校验**，本机有装才用）。

三条都取不到时 **check 2 明确 FAIL**（不再静默跳过）——早期版本在无安装的
机器上会悄悄弱化校验，这是 P0 级隐患，已修。重新生成快照：
`python tools/sq_catalog.py --snapshot tools/schema_snapshot.json`。

同理，`info.width/height` 缺失时**硬报错**，不再默认 410×502——否则 240×240
工程会被按 410×502 做遮挡检查，静默放水。

## 6. 反渲染预览（preview_from_project.py，已项目无关）

解析 .spj → 每屏一张卡 + 交互态卡（force_show/force_hide 集合）→ HTML。
- 面板几何读 spj["info"]，CIRCLE 时 .screen 圆角 = 半径；缺失硬报错。
- LABEL 的 `\n` 渲染为 `<br>`。
- 嵌套容器子元素坐标按父 rect 累进换算（绝对坐标书写时天然正确）。
- 屏幕顺序**从 .spj 自身的 `root.children` 推导**，不再硬编码 ORDER。
- 字体表从 `assets/fonts/*.fcfg` 自动构建，不再硬编码 FONT_SRC。
- **交互态卡与屏标题走侧车文件** `<Name>.preview.json`（可选）：
  `{"titles": {...}, "states": [{"screen":…, "label":…, "force_show":[…],
  "force_hide":[…]}]}`。没有侧车就只有初始态卡，不再依赖脚本内的表。
  stacked 对象（如波形帧）要写进 force_show，否则显示的是 hidden 帧内容。

## 7. 环境与硬编码路径

- SquareLine Studio 1.6.2：**可选**。装了可做 schema 交叉校验与深校验；
  没装也能跑完整主流程（快照 + resvg 已自足）。
- Python：Pillow（预览/资产后处理）。
- Node：tools/node_modules 内联依赖（@resvg/resvg-js + 各平台原生绑定 +
  resvg-wasm 兜底、lucide-static 裁剪版、lv_font_conv）。
- **可覆盖的环境变量 / 参数**（无一处硬编码开发者本机路径）：
  | 用途 | 环境变量 | 命令行 |
  |---|---|---|
  | Studio 安装目录 | `SQUARELINE_STUDIO` | `sq_catalog.py --studio` |
  | node 可执行 | `SQUARELINE_NODE_BIN` | — |
  | 资产包目录 | `SQUARELINE_ASSETS` | `--assets <dir>` |
  | 工程输出目录 | `SQUARELINE_OUT` | `--out <dir>` |
  | 设计规格文档 | `SQUARELINE_SPEC` | `--spec <md>` |
  | 强制 WASM 渲染 | `RESVG_FORCE_WASM=1` | — |

## 8. 官方示例工程（schema 对照）

`<SquareLine>/examples/` 下 **Smart Watch (392×392 CIRCLE)** 是圆形屏参照；
`.spj` 顶层含 width/height/shape。新 strtype 用 `sq_catalog.py` 从 examples
导出属性目录比对。

## 9. 声明式编译（build_from_spec.py）

不想写 Python 时，把屏写成 spec JSON 交给编译器（引擎/内容分离的落地）：

```bash
python tools/build_from_spec.py examples/<Name>/<Name>.spec.json \
       --assets examples/<Name>/assets --out examples/<Name>/squareline/<Name>
python tools/build_from_spec.py --example     # 打印带注释的骨架
```

spec 顶层：`$schema/name/width/height/shape/palette/fonts/ranges_*/symbols/
skip/screens/animations`；对象类型工厂 `PANEL/LABEL/IMAGE/ARC`；颜色支持
`#rrggbb[aa]` / 数组 / 调色板名；动作支持 `CHANGE_SCREEN/HIDE/SHOW/
SET_OPACITY/PLAY_ANIMATION`。`examples/SpecWidget/` 是完整最小示例
（320×320、无位图资产）。**spec 出错必须报友好消息并非零退出，不能吐栈。**

## 10. 可选：离线深校验与发布工具

- **深校验（可选、不在主流程）**：`python tools/probe_headless_render.py
  [squareline/<Name>]` —— micropython + lvgl 真渲染，能抓反渲染看不见的
  运行时问题。需要本机有可用 lvgl 树，环境不具备时自动跳过即可；按
  `info.lvgl_version` 选匹配的 lvgl（避免 v8 的 `lv.screen_load` 报错）。
- **回归套件**：`python eval/run_regression.py` —— 全流程重跑 + 与标准答案
  逐字节 diff + validator 必须 OK；`--no-assets` 跳过 Stage A，`--keep`
  保留 scratch 供排查，`--update` 在人工确认后刷新标准答案。
- **发布前检查**：`python tools/preflight.py`（数百毫秒廉价检查：渲染后端、
  跨平台绑定、schema 快照、无个人路径、无孤代理转义、**归档产物换行符**、
  **打包器白名单**、**交付物点名**、zip 编码与内容、文档规范）；
  `--full` 额外跑回归套件。
- **打包**：`python tools/package_release.py` —— 用 Python `zipfile` 打包
  （非 ASCII 名自动置 UTF-8 flag bit 11）并**重开校验**。注意：源码里若在
  非 raw 字符串写了 `\udcXX` 之类孤代理转义，Python 解析该文件即抛
  UnicodeEncodeError，表现为"打包莫名失败"——preflight 有专门 check 拦这类。

## 11. 字节可复现性：换行符与交付纪律

这两条不是风格问题，是"产物是否可信"的问题，各自都真实踩过一次。

### 11.1 换行符必须由代码固定，而不是由宿主平台决定

`open(path, "w")` 是**平台相关**的：文本模式会把 `\n` 翻译成宿主平台换行符。
后果是同一份 spec 在 Windows 上产出 CRLF、在 Linux 上产出 LF——而标准答案是
在 Windows 上落盘的，于是每次 Linux 重建都在这几个文件上 diff 失败：
`.spj / .sll / .slp / Themes.slt / project.info / *.fcfg`。

**约定**：

| 产物 | 写法 |
| --- | --- |
| 所有 JSON 工程文件 | `engine.dump_json(path, obj, indent)`（内部 `newline="\n"`） |
| lv_font_conv 产出的 `.c` | `normalise_font_c()` 改写头注释 + 固定 LF（顺带把绝对路径改成相对路径） |
| 其它文本产物 | 显式 `open(..., "w", encoding="utf-8", newline="\n")` |

三道防线：`preflight.py: check_artifact_eol` 扫归档工程残留 CRLF；
`eval/run_regression.py` 把"仅换行符不同"单独标成
`LINE ENDINGS ONLY (CRLF vs LF)`；`.gitattributes` 的 `* text=auto eol=lf`
防 `core.autocrlf=true` 在检出时改回去。

### 11.2 交付物只有一个文件，且必须由打包器产出

`dist/squareline-design-skills.zip`。打包器的归档根目录是**白名单**
（`package_release.py` → `SHIP_TOP`），不是黑名单——黑名单只能挡住作者记得
写的那些目录，白名单让"新冒出来的临时目录"永远进不去，并且会把跳过的条目
打印出来，漏掉是可见的。

事故复盘：曾经把整个工作目录直接压缩交付，包里因此带上了 `.workbuddy/`
（agent 工作记忆，含本机绝对路径）、一个套在里面的 61 MB `dist/*.zip`、
以及评审建议文档；并且因为用资源管理器压缩，中文文件名全部退化成 GBK
乱码——**已经修好的编码问题被原样复现，而真正修好的那个包就混在它里面
没被发出去**。教训练成三条检查：`check_zip_contents`（内容断言，含"整包
带目录前缀"即压了整个目录的识别）、`check_packer_allowlist`（白名单真的
生效）、`check_deliverable`（点名唯一交付物 + 列出仓库旁边的"目录形状"zip
及其中泄漏路径）。

