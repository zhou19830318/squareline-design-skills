---
name: squareline-ui-pipeline
description: >-
  Use for ANY SquareLine Studio / LVGL watch-or-device UI work — from a concept
  image to a validated, previewable .spj project, on rectangular AND round
  panels. Triggers: "参考图做一个 SquareLine 工程", "HTML mockup / 模拟页面",
  "生成图片/图标/字体资产", "新增一个屏幕", "对齐参考图调整布局", "圆形屏幕 /
  round screen", "验证 .spj 工程", "工程反渲染预览", "不用打开 SquareLine 预览",
  "写设计规格文档", or mentions of generate_assets, inline_mockup,
  build_from_spec, build_squareline, validate_squareline_project,
  preview_from_project, lv_font_conv, SquareLine Studio, LVGL, .spj.
---

# SquareLine UI Pipeline：概念图 → HTML Mockup → SquareLine/LVGL 工程

End-to-end pipeline that turns a reference image into a **validated SquareLine
Studio project** the editor can open without errors. It has been run twice at
production quality: AIWatch (410×502 rectangle) and AIWatchApple (240×240
CIRCLE — the round-panel lessons are marked 🔄 throughout).

**Source of truth**: one design-spec markdown (`*设计规格文档.md`, exact px
coordinates / colors / copy) + the user's concept image. Write the spec FIRST;
every later stage checks against it. Never skip verification — each stage has a
mechanical verifier below.

```
概念图
  → Stage 0  输入契约:  <Name>设计规格文档.md     ← 模板见 templates/设计规格文档模板.md
  → Stage A  assets:   node tools/generate_assets*.mjs      (PNGs, 2 px ≈ 1 dp)
  → Stage B  HTML:     mockup.html (static grid)  [+ interactive variant]
             preview:  node tools/inline_mockup.mjs → *_standalone.html
  → Stage C  LVGL:     spec JSON → python tools/build_from_spec.py      (常规屏)
                                或 python tools/build_squareline_<v>.py (定制几何)
             verify:   python tools/validate_squareline_project.py [squareline/<Name>]
                       python tools/preview_from_project.py      [squareline/<Name>]
```

## 先读：通用法则 与 实例数据

本文档混着两类内容，落笔前必须分清——**照抄实例数据到新项目是本流水线最常见的
翻车方式**。

| 类别 | 标记 | 含义 | 能不能直接抄 |
|---|---|---|---|
| **通用法则** | 无标记 | 坐标系、nid、字体子集化、事件动作白名单、验收方式——**换项目也成立** | 必须遵守 |
| **实例数据** | `[实例]` / 🔄 | AIWatch(410×502)、AIWatchApple(240×240) 这两个具体工程量出来的数值 | **只当参考，必须按新面板重新计算或实测** |

典型陷阱：`r = 120`、`chord(y) = 2·sqrt(r²−(y−r)²)`、`字号 15/16/36/44`、
`margin 12/32`、`64 px 中心件 + 8 个 44 px 图标 @ r=76`——这些全是**特定面板的
实测结果**，不是普适常数。换了屏幕尺寸，它们全部作废。

> **免责声明**：文中出现的所有 px、字号、半径、边距、行高，除显式写成公式的外，
> 均为两个示例工程的**观测值**，用于说明「应该量什么、量到什么精度」，不代表
> 目标值。新项目请以 `设计规格文档.md` 和参考图为准。


**Iron rules** (both projects, repeatedly proven):
1. **Regenerate, never hand-patch** project files. All fixes go into the
   builder; the .spj is disposable output. Hand-editing .spj is a dead end —
   the editor rewrites it on first save.
2. **Author every object in screen-absolute coordinates** (top-left), like the
   HTML. One `rebase()` pass converts to SquareLine's parent-centre-relative
   offsets at the very end. NEVER mix in container-relative coordinates — a
   nested container whose children were written container-relative rendered the
   whole weather screen shifted by the container origin (took a debug cycle to
   find; see pitfall C-6).
3. **nid discipline**: one monotonic counter for ALL properties, project-wide.
   Duplicates corrupt the project silently in the editor.
4. **Interaction graph from built-in actions only** (CHANGE SCREEN, MODIFY FLAG,
   SET OPACITY, PLAY ANIMATION, MODIFY STATE) → the simulator works with zero
   custom C code.
5. Verify with the validator (must print `OK - project validated, no problems
   found`) AND re-render preview screenshots per screen. Screenshots **lag one
   interaction behind** — after a DOM change, re-navigate/reload, and prefer
   DOM metrics (`getBoundingClientRect` at scale 1) over screenshots for audits.

## Stage 0 — 输入契约（先写设计规格文档）

动手前必须有 `<Name>设计规格文档.md`。**整份复制 `templates/设计规格文档模板.md`**
再逐节填实——模板已经把引擎真正需要的东西列全了（面板几何、屏幕清单与顺序、
逐屏对象表、交互表、动画表、字体表、**文案字符集**、资产清单、验收标准）。

三条容易漏的：

- **所有 `rect` 写屏幕绝对坐标**（左上角原点）。相对坐标是唯一一次「整屏偏移」
  事故的来源（见 pitfall C-6）。
- **§6.1 文案字符集必填**，且要写「将来可能用到的词」。构建时引擎会收录
  本文档的每一个字符进字体子集；不写 = 字体只有当前文案的字形，改一句话就缺字。
- **控件 `h` ≥ 字体行高**。行高 ≈ 字号 × 1.25，写小了引擎直接报
  `ERROR: 控件高度 < 行高`（示例工程实测 48 px 字体行高 60、20 px 行高 23）。

规格文档同时是引擎查找「glyph headroom」的地方：默认按
`dirname(assets)/<Name>设计规格文档.md` 搜索，也可用 `--spec <file>` 或
`SQUARELINE_SPEC` 显式指定。找不到会打印
`WARN: spec doc(s) ... not found - fonts get NO glyph headroom`。

## Canvas & sizing

Set px = design dp × 2 for crisp small-watch rendering (2 px ≈ 1 dp)：

| `[实例]` panel | px | dp feel | px sizes that worked |
|---|---|---|---|
| rect (AIWatch) | 410×502 | ~315 ppi | body 32, labels 22–26, display 96, margin 32 |
| round 🔄 (AIWatchApple) | 240×240 | ~326 ppi | body 15–16, labels 12–13, big number 36–44, margin 12 |

> 上表是**两个既有工程的观测值**，用来说明「一个面板该量哪几档字号」，不是目标值。
> 新面板请从「正文 ≈ 屏幕短边/15」起步，再按 §6 行高约束收敛。

🔄 Round-screen design laws（法则通用；括号里的数是 AIWatchApple `[实例]`）：

- **Circular clipping is real**：在 240 面板的 y=14 处，圆只剩 112 px 宽。
  顶部状态元素必须向中心收；安全区由弦宽算：`chord(y) = 2·sqrt(r² − (y−r)²)`，
  `r = 120`（`[实例]`，换面板重算 r）。**公式是法则，120 是数据。**
- **Radial home layout** beats a square grid：一个 64 px 中心件 + 8 个 44 px 图标
  排在 r=76 的环上（偏移 22.5° 避开顶部状态区）（`[实例]` 半径/尺寸）。
- **Row alignment to the round edge**：每行按所处带宽给宽度（取上下边缘弦宽的
  较小值），使行与表圈视觉相接——引擎侧的 `row_geo()` 就干这个（通用做法）。
- **Analog hands**：预烘焙旋转好的 PNG（10:09:35 姿态），轴心在屏幕中心；
  时 ≈ 0.48r、分 ≈ 0.73r、秒 ≈ 0.82r + 尾（`[实例]` 比例）。预烘焙可完全绕开
  LVGL 轴心旋转的序列化问题（通用结论）。
- 每个可见元素外接框须完整落在圆内（四角到圆心距离 ≤ r）；透明命中区 / 全宽居中
  文本框 / 指针画布允许探出——审计时区别对待。
- 96 px 弧环内文字 ≤ 20 px（`[实例]`）；大环 + 细数字读起来像「Apple」，反过来像「玩具」。


## Stage A — Assets (node tools/generate_assets*.mjs)

resvg renders white/coloured Lucide strokes + custom inline SVGs (gemini star,
heart waveform, grid dots, battery, hands/ticks/bezel…). Render at **native UI
size** (HTML uses width/height 1:1 — stretched assets shipped twice before).

- Full-bleed wide glyphs need a custom SVG, not the 24×24 `renderExact` helper
  (which letterboxes).
- 🔄 Pre-rotate clock hands/ticks into single PNGs (10:09:35). LVGL image
  rotation via pivot is not serialized reliably — baked assets dodge it.
- Audit with PNG header read: `node -e "const b=require('fs').readFileSync('assets/images_x/F.png');console.log(b.readUInt32BE(16)+'x'+b.readUInt32BE(20))"`.
- Unused/missing audit: `ls` vs grep of mockup files (comm -23 / -13). Wire
  unused assets into real UI states instead of deleting.

## Stage B — HTML Mockup

- `mockup.html` static grid of all screens; optional interactive variant with
  swipe/tap navigation.
- `tools/inline_mockup.mjs <src> <out>` base64-inlines images+fonts for the
  Freebuff/preview single-file flow. It matches asset paths **as string
  literals** — runtime-concatenated paths (`'assets/img_' + name + '.png'`)
  silently stay external → blank images in standalone only.
- Keep mockup and builder in sync: when a screen changes, change both, or the
  design source drifts from the project (it happened; a sync pass was needed).
- **Unscaled overlap audit** (caught 5+ real bugs): everything inside W×H, no
  sibling collisions >2 px; measure with `offsetTop+offsetHeight`, not rects —
  preview scale (0.75/1.05) masks overflow.

## Stage C — SquareLine/LVGL port

**两条路，先走第一条。**

### C-1 常规屏 → 声明式规格（默认）

把屏写成一份 **spec JSON**，交给编译器出工程：

```bash
python tools/build_from_spec.py examples/<Name>/<Name>.spec.json \
       --out examples/<Name>/squareline/<Name>
python tools/build_from_spec.py --example        # 打印带注释的骨架
```

（资产包路径写在 spec 的 `"assets"` 里就不必加 `--assets`，见下。）

`tools/engine/` 是**引擎层**（属性 plumbing、nid/guid、事件动画序列化、rebase、
字体子集化），`spec JSON` 是**内容层**。加一个屏 = 改数据，**不碰引擎**。
支持 `PANEL / LABEL / IMAGE / ARC`、滑动环、以及 5 个内置动作。

`examples/SpecWidget/` 是完整可跑的最小示例（320×320、无位图资产）。

资产包路径的优先级是 `--assets` > `$SQUARELINE_ASSETS` > 描述符里的
`"assets"` > `<repo>/assets`。**请把 `"assets": "examples/<Name>/assets"`
写进描述符**（仓库相对路径），这样 `python tools/build_from_spec.py <spec>`
裸命令就能重建工程，不用记参数；否则漏掉 `--assets` 的后果是工程里
一张图都不复制、validator 报一屏 `missing image files`（很难一眼看出是路径问题）。

### C-2 定制几何 → `tools/screens/<name>.py`

径向图标环、弦宽算术、预烘焙指针这类**必须写代码**的几何，才落到
`tools/screens/<name>.py`，再由 `tools/build_squareline_<name>.py` 入口调用：

```python
# tools/build_squareline_<name>.py —— 只有入口
from screens.<name> import PROJECT
from engine import squareline_engine as engine
def main(): return engine.build(PROJECT)
```

`tools/screens/aiwatch.py`（矩形）与 `tools/screens/aiwatch_apple.py`（圆形）
是两份样板。**新增工程优先考虑 C-1；只有几何确实无法用数据描述时才走 C-2。**

### 落盘约定

- 项目元数据（.spj 的 `info`）：`width/height/shape`，`"RECT"` 默认、
  `"CIRCLE"` 圆形（官方 392×392 Smartwatch 示例可证）。
- Stacked-image 状态机（天气图标、波形帧、mic 状态）：**一个状态一个 LVGL 对象**，
  靠 MODIFY FLAG / SET OPACITY 切换——LVGL 没有 src-swap。
  **每个叠层对象都必须显式 `hidden` 初值 + 显式接线**：曾有一版 3 个 mic 状态
  既同时可见、又完全没接切换事件的工程发出去（代码评审看不出，第一次点击就露馅）。
- 字体：按用途分子集，`lv_font_conv` 出 `.c/.bin/.fcfg` 三件套，缺一不可（校验器会查）。
  字符集取自**设计规格文档**（见 Stage 0），保证日后改文案不缺字。
  纯数字字体**不要**声明全角 CJK 区段（体积 3 倍）。
  `U+00B0` 要遍历 cmap 确认（Format-4 段可能映射到 glyph 0，`--range`/`--symbols` 会骗你）。
  注意 `0x20-0x7F` 含 `U+007F`(DEL)，任何字体都没有 → 用 `0x20-0x7E`。
- 生成物：`.spj/.sll/.slp/Themes.slt/project.info` + `assets/`。
  `backup/ cache/ components/ ui/` 是编辑器产生的垃圾，**不要提交**。


## Validation & preview（project-agnostic）

```bash
python tools/validate_squareline_project.py [squareline/<Name> | x.spj]
python tools/preview_from_project.py       [squareline/<Name> | x.spj] [--only a,b] [--scale 1.5]
```

不带参数时，两者都取 `<root>/squareline/` 下第一个 `*.spj`。
面板几何读 `spj["info"]`——**不要读 SCREEN 节点**（它们不带 OBJECT/Size；
曾经因为信任它，校验器在 240×240 工程上默认成 410×502，把遮挡检查悄悄废掉了）。

**校验器 10 项**：strtypes 对照官方样例、nid 唯一性、CHANGE SCREEN 目标、
图片存在性、字体 codename + 三件套、事件图 schema、动画合法性、可点击性、
遮挡嫌疑、生成的 `set_text` 语法编译。

`strtypes` 对照源**优先用 `tools/schema_snapshot.json`**（已固化 464 个 strtype，
由本机 74 个官方示例提取）。**没有任何本地 SquareLine 安装也能完整校验**；
快照缺失时校验器**明确报错**，不会静默降级成「弱化版 check 2」。
要交叉核对官方样例时设 `SQUARELINE_STUDIO` 指向安装目录即可。

`preview_from_project` 把 .spj 反渲染成 HTML 接触表——初始态卡片 + 强制展开的
交互态卡片。屏幕顺序、面板尺寸、字体表全部从工程文件自身推导（字体表读
`assets/fonts/*.fcfg`），**不再有 per-project 硬编码**。人类可读的标题与
交互态属于判断信息、推导不出来，放进可选的侧车文件
`squareline/<Name>/<Name>.preview.json`：

```json
{ "titles": {"home": "App 网格"},
  "states": [{"screen": "settings", "show": ["panel_about"],
              "hide": [], "caption": "关于浮层展开"}] }
```

侧车缺失时预览照常生成，只是没有标题和交互态卡片（不会崩）。
标签里的 `\n` 按 `<br>` 渲染（spj 存的是字面反斜杠 n）。

### 可选：离线深校验

需要**真·LVGL 渲染**而不只是反渲染时，另有
`tools/probe_headless_render.py`——它用 micropython + lvgl 把工程跑一遍，
能抓到反渲染看不见的运行时问题。属**可选**深校验，**不在主流程里**，
也不要依赖它出结果：它需要本机有可用的 lvgl 树，环境不具备时自动跳过即可。
如需运行：`python tools/probe_headless_render.py [squareline/<Name>]`。

## 动引擎之前：跑回归

```bash
python eval/run_regression.py        # 全部用例（秒级~分钟级）
python eval/run_regression.py --no-assets   # 跳过较慢的 Stage A
```

它把三个归档工程（AIWatchApple / AIWatch / SpecWidget）**从头重建**，与
`examples/*/squareline/*` 里的标准答案**逐字节比对**，再各自 validate + preview；
另外单独验证 Stage A 的资产生成在**原生绑定**与 **WASM 兜底**两条路径下产出相同 PNG。
用例清单与失败读法见 `eval/test_cases.md`。

规矩：**改了 `tools/engine/` 就必须跑它**。归档工程是标准答案，人工确认改动无误后
才用 `python eval/run_regression.py --update` 刷新它（先看 diff 再刷，不要让套件
"顺手"更新）。加新工程时在 `eval/run_regression.py` 的 `PROJECT_CASES` 加一行即可。

**换行符是契约的一部分。** 归档产物必须是纯 LF：引擎写文件一律固定 LF
（`engine.dump_json`），因为 `open(..., "w")` 会把 `\n` 翻成宿主平台的换行符——
历史上标准答案在 Windows 落盘成 CRLF、Linux 重建出 LF，导致三个逐字节比对在
**流水线主攻的 Linux 环境里开箱必红**，看起来像生成器坏了。所以：

- 归档工程只许 LF；`preflight.py` 与回归套件都会扫，`.gitattributes`
  (`* text=auto eol=lf`) 从 git 层兜底。
- 任何"逐字节比对"失败，先看改动是否**只**差换行符——套件会直接把这种情况
  标成 `LINE ENDINGS ONLY (CRLF vs LF)`。
- 别在文本模式下手写产物文件；一律走 `engine.dump_json` 或显式 `newline="\n"`。

发布前跑 `python tools/preflight.py --full`（含本套件的廉价版检查清单）。

## 发布：只发 `dist/squareline-design-skills.zip`

```bash
python tools/preflight.py --full      # 必须全绿
python tools/package_release.py       # 产出唯一交付物并自查
```

交付时**只给这一个文件**。`package_release.py` 的归档根目录是**白名单**
（`SHIP_TOP`），所以 `.workbuddy/`、`dist/`、临时目录不会被带出去——这不是洁癖：
曾有一次交付是把整个工作目录直接压缩，包里混进了 agent 工作笔记（含本机绝对路径）、
一个套在里面的 61 MB `dist/*.zip`，并且**用资源管理器压缩导致中文文件名全部变
GBK 乱码**——而真正修好的那个包就躺在它里面没被发出去。

永远不要手动压缩整个技能目录当交付物；`preflight.py` 的
`check_zip_contents` / `check_packer_allowlist` / `check_deliverable` 三道检查
专门拦这类事故。


## The recurring pitfalls (each bit at least once)

**A. Assets**
1. Render at native size; full-bleed glyphs need custom SVG.
2. 🔄 Bake pre-rotated hands/ticks; don't trust LVGL image rotation.

**B. HTML**
3. Inliner only rewrites whole string literals; runtime-concatenated paths
   leak through as broken images.
4. `visibility:visible` children escape a `visibility:hidden` ancestor —
   use `opacity` for image-state toggles.
5. Screenshots lag one interaction behind: re-navigate, then measure DOM.

**C. Builder / .spj**
6. One coordinate convention only (screen-absolute); rebase() at the end.
   Nested-container children in container-relative coords = shifted screen.
7. nids unique + monotonic project-wide; duplicates corrupt silently.
8. Every stacked-state object: explicit `hidden`, explicit toggles, on every
   path into the state (check by listing visible objects per state, not by
   reading code).
9. Label text: real newlines/quotes/backslashes break the generated
   `set_text("…")` — validator compiles the collected texts to catch it.
   spj stores `\n` literally; preview renders it as `<br>`.
10. Panel geometry lives in spj["info"]; SCREEN nodes have no size.
11. Editor-save forms evolve: `OBJECT/State_trickle` replaces
    `OBJECT/Clickable:True` on event-less objects. When the validator flags
    "strtype not in official examples", check an editor-saved backup zip
    before "fixing" the builder (allowlist lives in the validator).
12. No machine-specific paths anywhere. Studio install → `SQUARELINE_STUDIO`;
    node binary → `SQUARELINE_NODE_BIN`; asset/output dirs → `--assets` /
    `--out`. Shipped code must contain **zero** absolute paths, or the zip only
    works on the machine that built it.
13. `0x20-0x7F` claims `U+007F` (DEL), which no TTF contains → harmless-looking
    `TTF 里没有 1 个声明字形` warning forever. Use `0x20-0x7E`.
14. SVG→PNG is `@resvg/resvg-js`, a **napi native module**: one `.node` per
    OS/CPU. Vendored bindings for every platform + `@resvg/resvg-wasm` fallback
    live in `tools/lib/resvg.mjs`; import the shim, never `@resvg/resvg-js`
    directly, or Stage A dies on any platform you did not build on.

**D. Round panel** 🔄 `[实例]` 数值均属 AIWatchApple，换面板重算
15. Chord-width math for everything near top/bottom of the circle.
16. Radial home; row width = local chord; hands pivot-centred, lengths in r
    fractions; ring 96–112 px with 8 px stroke, number ≤ 20 px.
17. Audit "inside the circle" by corner distance ≤ r for VISIBLE pixels only —
    transparent canvases and hit-areas legitimately poke out.

**E. Process**
18. Freebuff restarts kill previews/servers — re-register; files survive.
19. write_file/str_replace: all required fields; oldString byte-exact (read
    the region first). Preview tabs are single-use — replace, don't stack.
20. Mockup drifts from project unless changed together; schedule a sync pass
    before delivery.
21. Adding a screen must not mean copying 450 lines of Python. If you find
    yourself editing `tools/engine/`, stop — the change belongs in the spec
    JSON (C-1) or in `tools/screens/<name>.py` (C-2).
22. A descriptor that reads state filled in *later* silently yields empty lists.
    `SpecProject.descriptor()` must derive screen names straight from the spec,
    not from `self.names` (populated only once `build_screens()` runs — i.e.
    after `configure()` already consumed the descriptor) — it caused
    `KeyError: 'home'` at the first line that looked up a screen guid.
23. **`open(path, "w")` is host-dependent.** Text mode translates `\n` to the
    platform's line ending, so artifacts built on Windows carry CRLF and a
    Linux rebuild carries LF. Every byte-comparable output must go through
    `engine.dump_json` (or pass `newline="\n"` explicitly). Symptom: three
    golden comparisons red on Linux with contents that look identical.
    **Applies to hand-written tools too, not just goldens** — widening the
    preflight check from examples/ to the whole shipped tree found two tool
    files still CRLF, which `.gitattributes` then rewrites on commit, so the
    working tree silently diverges from the repository.
24. **Never deliver by zipping the working directory.** A blocklist of
    exclusions only removes what you remembered; use a top-level *allowlist*
    (`package_release.py` → `SHIP_TOP`) so a new scratch dir cannot leak.
    Windows' own zip tools also re-introduce the ANSI-codepage filename
    mojibake that `package_release.py` exists to prevent, so the naive
    archive is broken in two independent ways at once.
25. **A cleanup pass is where dangling references are born.** Delete a doc and
    something still tells you to open it; delete a directory and the packer
    allowlist still lists it (harmless-looking, slowly meaningless). After any
    eviction, grep the shipped docs *and* `SHIP_TOP` for the gone names —
    `preflight.py: check_no_stale_refs` does exactly that, and also asserts
    every allowlist entry exists.
26. **Docs drift because nothing executes them.** The tools table in README.md
    is hand-maintained and never imported, so it is the first thing to rot.
    `check_doc_scripts_linked` cross-checks every `` `x.py` ``/`` `x.mjs` ``
    the README names against the actual files.

