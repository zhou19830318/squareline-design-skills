---
name: squareline-ui-pipeline
description: >-
  Orchestrates the whole "concept image → SquareLine Studio / LVGL project" pipeline and
  owns its toolchain: project folder convention, the slx.py command set, spec JSON rules,
  build, validation, reverse-render preview, multi-round iteration. Use for ANY SquareLine
  Studio / LVGL / .spj task on rectangular or round panels. Triggers: "概念图做 SquareLine
  工程", "参考图 → .spj", "需求清单", "设计规格文档", "新增一个屏幕", "圆形屏 / 圆屏表盘",
  "验证 .spj", "反渲染预览", "改需求再出一版", "SquareLine", "LVGL UI", "spec.json",
  "build_from_spec", "validate_squareline_project". For reading a concept image use
  concept-to-spec; for icons/fonts/PNG use squareline-assets.
---

# SquareLine UI Pipeline（插件版总控）

把**一张/多张概念图 + 需求清单**变成一个**能被 SquareLine Studio 1.6.2 打开且不报错**的
LVGL 工程。已用 456×456 圆形、10 屏的 NovaWatchS12 做过**逐字节重建**验证。

三个技能分工：

| 技能 | 管什么 |
|---|---|
| `concept-to-spec` | **Stage 0**：看概念图 → 需求清单 + 设计规格文档 + 初版 spec JSON |
| `squareline-assets` | **Stage A**：图标/图片/字体资产（Lucide 离线、图标站、自绘 SVG）→ PNG |
| **本技能** | 工程约定、命令、spec 规则、构建/校验/预览、迭代回路、验收 |

## 00. 主循环（先读这一节，其余按需查）

**不要凭记忆走流程。每做完一步就运行 `$SLX next <proj>`**：它读工程目录，只告诉你下一步做什么、为什么、怎么做、做到什么算完成
（需求追溯 → 分析 → 闸门1 → 资产 → 体检 → 构建 → 反渲染 → 真值审计 → 对照概念图 → 追溯终检）。
用户的批准写不进文件，用 `$SLX gate <proj> 1|2 --note "…"` 记录（用户说"别问了直接做"时加 `--assume`，并在最终报告里列出所有假设）。
报错先查：`$SLX explain "<报错片段或 E-XXX 编号>"`。

## 0. 先确定工具包位置（每次会话一次）

`$TK` = **插件根目录**，即包含 `tools/ fonts/ templates/ skills/` 的那一层
（本文件往上两级；若环境变量 `CLAUDE_PLUGIN_ROOT` 已设置就用它）。

```bash
TK="${CLAUDE_PLUGIN_ROOT:-<本 SKILL.md 所在目录>/../..}"     # 解析成绝对路径再用
SLX="python3 $TK/tools/slx.py"
$SLX doctor        # 检查 node / Pillow / lv_font_conv / resvg / 字体，一次看全
```

`doctor` 有 FAIL 就先修（缺 Pillow：`pip install pillow --break-system-packages`；缺
node：装 Node.js 或设 `SQUARELINE_NODE_BIN`），不要硬跑后面的阶段。**工具包目录是只读
资源，永远不要把工程写进去**——工程放用户工作区。

## 1. 工程目录约定

`$SLX init <Name> --width W --height H --shape RECT|CIRCLE [--dir <工作区>]` 创建：

```
<proj>/                         <Name> = 英文字母/数字/下划线，字母开头
├── concept/                    概念图（输入）
├── UI需求清单.md                 ← 模板 templates/UI需求清单模板.md（要什么）
├── <Name>设计规格文档.md          ← 模板 templates/设计规格文档模板.md（怎么做 = 源真相）
├── assets.manifest.json        资产清单（Stage A 输入）
├── downloads/                  从图标站取来的 SVG（Stage A）
├── <Name>.spec.json            声明式屏幕规格（Stage C 输入）
├── assets/images/              生成的 PNG（Stage A 输出）
├── squareline/<Name>/<Name>.spj    ← 交付物：用 SquareLine「Open Project」打开
└── preview/                    spec_preview / project_preview 的 .html 与 .png
```

## 2. 命令（工程目录外也能跑，路径显式传）

| 命令 | 作用 |
|---|---|
| `$SLX init <Name> …` | 脚手架：目录 + 两份模板 + 空清单 + 能直接构建的 1 屏骨架 spec |
| `$SLX assets <proj>` | `assets.manifest.json` → `assets/images/*.png`（并核对 PNG 实际尺寸） |
| `$SLX preview <proj> [--scale S] [--strict]` | spec → HTML 接触表 + PNG，**免构建**，亚秒级；缺图画红框、LABEL 高度不足报警 |
| `$SLX check <proj>` | **构建前的设计体检**（校验器查不到的版面逻辑）：对象是否落在画布/圆屏内（按绘制范围，文字按估算墨迹宽）；导航图里每个屏能否从初始屏进入、能否走回去（死胡同报错；仅事件驱动的屏报警告） |
| `$SLX build <proj>` | spec → `.spj` 工程，**随后自动 validate** |
| `$SLX verify <proj>` | validate + 把 `.spj` 反渲染回 HTML/PNG（逐屏 + 交互态） |
| `$SLX palette <img> [--n 8]` | 概念图主色（先 `crop` 到小块再取，才是某元素的真实色） |
| `$SLX grid <img> --step 50` | 叠像素网格，量坐标用 |
| `$SLX crop <img> x0 y0 x1 y1 --zoom 3` | 裁剪放大，核对细节 |
| `$SLX sidebyside <概念图.png> <渲染.png>` | 概念图 vs 成品并排对照 |
| `$SLX bbox <img> x0 y0 x1 y1 [--color #hex] [--scale 0.6]` | 量某元素（默认近白色像素）的包围盒；`--scale` 把图像素换成面板 px。**量字号/位置的标准办法** |
| `$SLX diff <概念图> <渲染>` | 概念 \| 渲染 \| 3×差分 三联图 + 平均误差；`verify` 会生成 `preview/screens/<屏>.png` 供它用 |
| `$SLX next <proj>` | **主循环**：只打印下一步 |
| `$SLX gate <proj> 1\|2 [--note ..] [--assume]` | 记录用户批准（1=分析确认，2=预览确认） |
| `$SLX scan <img> --find-screens` / `scan <img> --screen x0 y0 x1 y1 --panel W` | 识别设计板上的屏幕 / 一块屏里的元素：面板 px 坐标、颜色、类型提示、字号估计 + 编号叠加图 |
| `$SLX fit-font "<文字>" --w W --h H --weight 700 --cy Y` | 由**实测文字框**反算字号和 LABEL 的 y（用真正的 lv_font_conv 度量，不是经验系数） |
| `$SLX check <proj>` | 构建前体检（schema、引用、字体/符号、事件白名单、图片路径与尺寸、圆屏版面、导航）；`build` 会自动先跑，有错就拒绝 |
| `$SLX explain <编号\|片段>` | 错误目录：含义 + 修法 |
| `$SLX reqs extract\|todo\|set\|add\|check\|report` | 需求追溯（见 concept-to-spec 步骤 0） |
| `$SLX truth <proj>` | **真值审计（可选，需 gcc）**：用真正的 LVGL 渲染每个文字标签，与设计意图比对 |
| `tools/specbuilder.py` | 用 Python 写 spec：芯片/开关/滑块/提示条/卡片…一行一个控件，文字按**墨迹中心**定位，自动记录意图 |
| `$SLX shot <x.html>` | HTML → PNG（需 playwright+chromium；没有就让用户在浏览器打开 HTML） |

其它底层工具（需要时再用）：`node $TK/tools/svg_to_png.mjs`（单枚 SVG→PNG）、
`python3 $TK/tools/build_from_spec.py --example`（打印带注释的 spec 骨架）、
`$TK/tools/layout.py`（网格/行/图标+文字布局函数）、`$TK/tools/LABEL_SIZING.md`（行高速查）。

## 3. 铁律（每条都踩过坑）

1. **重新生成，绝不手改 `.spj`**。编辑器首次保存就会重写它；所有修复进 spec / manifest / 规格文档，
   然后整体重建。
2. **所有 `rect` 写屏幕绝对坐标**（左上角原点）。引擎最后统一转成 SquareLine 的"相对父中心"。
   混用容器相对坐标 = 整屏平移（唯一一次整屏偏移事故的根因）。
3. **需求要逐条处置**：有需求文档就必须 `reqs extract` → 每条 MUST/MUST_NOT 都有 done(+证据/自动验证) / deviation / out_of_scope / blocked(+原因)。
   需求文档与概念图、与用户后来的口头指示冲突时，**不要默默选边**：标 deviation，写明原因，告诉用户。
3. **交互只用内置动作**：`CHANGE_SCREEN / HIDE / SHOW / SET_OPACITY / PLAY_ANIMATION`（另有
   `CALL_FUNCTION` 业务回调）。这样模拟器零自定义 C 代码就能跑。概念图里写不进白名单的效果，
   给出最接近的替代并告诉用户。
4. **规格文档先于一切**。文案字符集（§6.1）必须写全，**含将来可能用的词**：构建时引擎把它收进字体子集，
   这是日后改文案不缺字的唯一保障。要改文案 → 先改规格文档，再重建。
5. **验收两道缺一不可**：validator 打印 `OK - project validated, no problems found`；
   且反渲染预览逐屏对着概念图看过。validator 管"工程有没有问题"，反渲染管"长得对不对"。
6. **不要改 `tools/engine/`**。加屏 = 改 spec 数据（C-1）；极少数几何（径向图标环、弦宽算术）才在
   **工程目录里**写 Python 模块调引擎（逃生舱，见手册 Stage C-2）。

## 3.5 两种预览，别混用

| | `preview`（spec_preview） | `verify`（反渲染 .spj） |
|---|---|---|
| 何时 | 构建前，亚秒级 | 构建后 |
| 可信度 | **只保证几何与文案**：文字垂直居中、无字重、系统字体 | 用工程里的真字体，并按 LVGL 的 `line_height`/`base_line` 排版；与真 LVGL 渲染相比，文字位置误差 ≤2 px（实测） |
| 已知偏差 | — | 画不出弧线圆头（工程里 `Arc_Rounded=True`，真机是圆头）；不画渐变/阴影 |

所以：**坐标/缺图问题在 `preview` 阶段修；字号、字重、文字位置到 `verify` 之后用 `bbox`/`diff` 校准；要"绝对准"用 `truth`。**

> **血的教训**：早期的反渲染把文字基线算在 `框顶 + size×1.22 的 CSS 行高` 上，比真 LVGL（`框顶 + line_height − base_line`）低了约 **11% 字号**
> （时钟基线 189 vs 真机 181），两个工程的文字坐标因此全部偏了。已修，并用真正的 LVGL 9.2.2 渲染验证。
> **验收依据本身也要被验证**：任何"预览/校验器说没问题"的结论，在关键尺寸上用 `truth` 复核一次。

## 4. 阶段与闸门

```
Stage 0  concept-to-spec   → 需求清单 + 设计规格文档 + 初版 spec/manifest
   ▼ 【闸门 1】向用户确认：面板尺寸/形状、屏幕清单与切换、配色、文案、所有"估算/假设"项
Stage A  squareline-assets → assets/images/*.png
Stage B  （可选）交互式 HTML mockup —— 只有用户明确要 HTML 原型才做；日常用 `preview` 即可
Stage C  preview + check → 调整 → build
   ▼ 【闸门 2】把 preview PNG 给用户看（对照概念图），确认再构建；坐标问题在这里改，别等构建后
验收    verify → sidebyside / design-reviewer 对照概念图 → 修 → 重建 → 直到全绿
交付    告知 .spj 路径 + 预览图 + 资产来源与许可 + 已知差异
```

闸门不是形式：Stage 0 的几何一旦错，后面每个阶段都在错的基础上叠加。**用户没点头前不要进入 Stage A**。
用户明确说"别问了直接做"时，把假设项列在最终说明里，不要沉默地吞掉。

## 4.5 `check` 抓得到、`validate` 抓不到的

`validate` 只管 .spj 文件形状；它不知道一个按钮在圆屏外，也不知道某屏进去了出不来。真实案例：
- 试跑里"选项芯片文字 x 坐标算成负数"→ 文字漏到屏幕左边缘（`check` 报 `rect outside canvas`）；
- 一个 36 屏的工程里 4 个"事件驱动"状态屏在模拟器里点不到（`check` 报 warn，加了状态预览页解决）；
- 上游 NovaWatchS12 样例里 8 个子页面没有返回手势（`check` 报 dead end）。

**多屏、多页的工程一定要在 `build` 前跑一遍 `check`。** 设计里"事件驱动才进入"的屏（唤醒、错误态）会报 warn：
真机上没问题，但设计师在 SquareLine 模拟器里走不到——建议加一个"状态预览"页，让每个屏都能点到。

## 5. spec JSON 要点

完整字段见 `python3 $TK/tools/build_from_spec.py --example` 与手册。常用骨架：

```jsonc
{ "name":"Demo","width":456,"height":456,"shape":"CIRCLE","assets_subdir":"images",
  "spec_docs":["Demo设计规格文档.md"],                 // 文案字符集从这里收
  "palette":{"BG":"#000000","CARD":"#1C1C1E","WHITE":"#FFFFFF","ACCENT":"#30D158"},
  "fonts":[{"codename":"Title28","ttf":"noto-sans-sc-v40-chinese-simplified-500.ttf","size":28,"kind":"text"}],
  "ranges_text":["0x20-0x7E","0x00B0","0x3001","0x3002"], "ranges_num":["0x20-0x7E","0x00B0"],
  "screens":[{"name":"home","bg":"BG","children":[
      {"type":"LABEL","name":"t","rect":[60,120,336,38],"text":"10:09","font":"Title28","color":"WHITE","align":"CENTER"},
      {"type":"IMAGE","name":"ic","rect":[196,46,64,64],"asset":"assets/img_home_icon_x.png",
       "events":[{"on":"CLICKED","actions":[{"type":"CHANGE_SCREEN","target":"settings"}]}]}]}],
  "order":["home","settings"], "initial_screen":"home" }
```

- **不要**在 spec 里写 `"assets": "..."`（那是上游"工程在仓库里"的约定）；`slx` 会传 `--assets`。
- **重建会自动清理陈旧产物**：`slx build` 会删掉工程里不再被 spec 引用的字体三件套和图片（构建器本身只增不删），避免已删除的图层继续随工程交付。
- **`order` 要小心**：不写或写空数组 = 所有屏幕自动连成一条左右滑动环。屏幕多且导航不是线性的，写 `"order":["<首屏>"]`
  关掉滑动环，所有跳转用 `screen_events`（屏事件）和对象 `events` 显式接线。
- **事件名要全局唯一**（会变成 C 函数名）：建议 `<屏>_<对象>_<事件>`。
- **可用事件白名单**：`CLICKED / PRESSED / RELEASED / PRESS_LOST / VALUE_CHANGED / SCREEN_LOAD_START|LOADED|UNLOAD_START|UNLOADED / GESTURE_LEFT|RIGHT|UP|DOWN`。
  **`LONG_PRESSED`、`DOUBLE_CLICKED` 不在编辑器已验证集合内**——写进去有让 SquareLine 打不开工程的风险。
  需求里有双击/长按时，工程里接单击/滑动，双击/长按在 C 层挂 `LV_EVENT_*`，并写进规格文档。
- **PANEL 没有 `clickable` 字段**：可点击性由是否带 `events` 自动推导。
- **选项芯片/开关这类"二选一/多选一"控件**：每个选项一个 OFF 底板（带点击事件）+ 一个 ON 底板（只有默认的可见），
  **文字做成独立 LABEL 画在两层底板之上**（否则 ON 底板会盖住 OFF 底板里的字，校验器会报遮挡）。
- **非 text 字体 = `symbols[kind]` ∪ `ranges_num`**（`ranges_num` 对所有非 text 字体共用）。想让纯数字字体小，把 `ranges_num` 收到 `["0x30-0x3A"]`；
  默认的 `0x20-0x7E` 会把整段 ASCII 都带进去（体积大、行高被撑高，数字在行框里偏上）。
- **文字定位用墨迹中心**：`LABEL` 的 `rect.y` 不等于文字视觉位置——文字基线在 `y + line_height − base_line`，
  数字字体的行框里常含着不用的下伸部分。用 `specbuilder.label(cy=墨迹中心)` 或 `fit-font --cy` 算，不要按行框中心估。
- **IMAGE 的 `asset` 永远是扁平路径** `assets/img_x.png`。写成 `assets/images/img_x.png` → 全部 `missing`。
  `assets_subdir` 只决定从哪读源 PNG，**不进引用**。
- **LABEL 高度 ≥ 字体行高**，且行高 > 字号。安全写法：`h ≥ ceil(size × 1.35)`；
  权威值看构建输出的 `lineheight:` 行。可用 `layout.label_sized()` 自动算。
- 颜色写调色板键或 `#rrggbb` / `#rrggbbaa`。
- 事件：`CLICKED / PRESSED / RELEASED / SCREEN_LOAD_START / SCREEN_LOADED / GESTURE_LEFT/RIGHT/UP/DOWN` 等；
  `order` 中相邻屏会自动生成左右滑动。
- 叠层状态（天气图标、麦克风三态）：**一个状态一个对象**，每个都要显式 `hidden` 初值并接线切换
  （LVGL 没有换图）。写完后逐态列出"此时可见哪些对象"来核对，别只读代码。
- 控件能画的只有 `PANEL / LABEL / IMAGE / ARC`。渐变、阴影、模糊、发光、不规则形状、照片、复杂图表
  → **烘焙成 PNG**（builtin SVG），文字和要交互的东西保持活对象。细则见 `concept-to-spec`。

坐标别手算：`tools/layout.py` 提供 `grid / stack / card_row / icon_text / label_sized`，
间距放不下会抛错而不是输出负宽度（用法见手册）。

## 5.5 进度环（ARC）要点

- LVGL 弧线默认 **0° 在 3 点钟**。想从 **12 点钟**顺时针开始，写 `"angles":[270,269]`（背景弧 270°→269°，约 359°；写 `[270,270]` 会退化成 0°）。
  不写 `angles` = 从 3 点钟开始，反渲染里会看到环"转歪了"。
- `rect` 是弧的**外接框**：外径 = `2×(环中心半径 + 环宽/2)`；`width` 是环宽。
- 值会变的环必须是**活 ARC**（单色）；渐变/发光无法保留，色取渐变中点并标 `[估算]`。

## 5.6 字号校准（首版必然偏差）

字高 → 字号 `size ≈ 大写/数字高 ÷ 0.72` 只是**初值**。目测更不可靠：试跑里两个大数字目测偏大 6–12%。
正确做法：构建 → `verify` → 对同一元素分别在概念图和 `preview/screens/*.png` 上跑 `bbox`，
按 **宽、高比例的折中**改字号（Noto 与概念图字体宽度不同，通常以宽度对齐、高度容忍 1–2 px），再按新字号的
基线偏移（≈1.05×size）重算 `rect.y`，重建一次即收敛。验收线：文字包围盒位置/尺寸误差 ≤ 2 px（面板）。

## 6. 圆形屏法则（法则通用，具体数字每个面板重算）

- 圆在 y 处的弦宽 `chord(y) = 2·sqrt(r² − (y − r)²)`，`r = 面板直径/2`。靠近上下缘的元素按弦宽收窄。
- 每个**可见**元素外接框四角到圆心的距离 ≤ r（透明命中区、全宽居中文本框、指针画布允许探出，审计时区别对待）。
  留 ~5% 的呼吸边距。
- 径向布局（图标环）比方格更适合圆屏；每行宽度取该行上下缘弦宽的较小值。
- 模拟指针：**预烘焙成单张 PNG**（固定 10:09:35 姿态，轴心在屏幕中心）。LVGL 的 pivot 旋转在 `.spj`
  里序列化不可靠。
- 字号起点：正文 ≈ 屏幕短边/15，再按行高约束收敛。大环 + 细数字读起来精致，反过来像玩具。

## 7. 多轮优化回路（需求变更的固定走法）

用户的每条意见**登记进 `UI需求清单.md` §9 迭代表**（原话、日期、状态），然后：

```
① 改源真相（设计规格文档；必要时同步需求清单 §3/§4）
② 资产类 → 改 assets.manifest.json 并 `assets`；布局/文案类 → 改 spec JSON
③ `preview` 快速确认 → `build`（全量重建）
④ `verify` 全绿 → 在迭代表登记"已应用 + 改了哪几节"
```

- **一轮一验收**：别攒五条意见一起改；逐条改、逐条验，出问题才能二分定位。
- 文案变了先查字符集：新词必须出现在规格文档里，否则字体缺字。
- 坐标大改先用 `layout.py`，不要手算一批新魔法数。
- 规格文档、spec JSON、（如有）mockup 由**同一轮改动**保证一致。

## 8. 高频坑速查（完整 32 条见手册）

| 症状 | 原因 / 对策 |
|---|---|
| 全部图片 `missing` | `asset` 写成了 `assets/images/...`；改成扁平 `assets/img_x.png`；或没传 `--assets`（用 `slx` 就不会） |
| `ERROR: 控件高度 < 行高` | LABEL 高度小于字体行高；用 `ceil(size×1.35)` 起步，看 `lineheight:` |
| 整屏偏移 | 某容器的子元素写成了容器相对坐标；全部改屏幕绝对坐标 |
| 字体缺字 | 新文案没进规格文档 §6.1；补进去重建。`0x20-0x7F` 要写成 `0x20-0x7E` |
| `strtype not in official examples` | 先看是不是编辑器存盘形态变化（手册 pitfall 11），别急着改 builder |
| 预览里圆环不见 | 别用 CSS conic-gradient 画弧（旧 WebKit 静默失败）；预览已用 SVG 描边 |
| 构建出的文本含换行/引号报语法错 | 用 spj 里字面 `\n`；validator 会编译所有 set_text 来抓 |
| 一张图被拉伸模糊 | 资产必须按目标 rect 的**原生尺寸**渲染，不要小图放大 |

## 9. 品牌/原创自查（引用真实产品或概念图时必过）

- [ ] 资产全部由本流水线生成或自绘；**不来自**参考产品的固件/截图/官宣图。
- [ ] 无商标 logo、字标、原样复制的特征 UI chrome；用通用类比件替代。
- [ ] 只借"设计语言"（节奏、间距、圆角、字阶、色彩**角色**），字形/图标集/品牌色必须是自己的。
- [ ] 工程/屏幕命名不暗示隶属关系。
- [ ] 每个 IMAGE 的 `asset` 来源可说清；说不清来源的扁平路径就是警报。
- [ ] 预览来自我们自己的 `.spj`，不是参考设备截图——评审看到的就是真实成品。

用户自己的概念图例外条款见 `concept-to-spec`（只有用户明确要求才可裁切其作品）。

## 10. 交付说明模板

交付时告诉用户：① `.spj` 路径与打开方式（SquareLine Studio 1.6.2 → Open Project；**未装 Studio 也已通过
校验器 + 反渲染**，但没在编辑器里实机打开过——如实说）；② 预览 PNG 路径；③ 资产来源与许可（含需署名的）；
④ 与概念图的已知差异与原因（字体近似、渐变烘焙、被替换的动效…）；⑤ 迭代表里还剩什么。

深度参考：`references/pipeline-handbook.md`（上游完整手册，含 32 条踩坑与圆形屏细则）、
`REFERENCE.md`（.spj 格式与引擎机制）、`ICON_SOURCES.md`（图标站目录与许可证）。
