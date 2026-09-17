# squareline-design-skills

**把一张参考图变成可打开、可验证的 SquareLine Studio / LVGL 工程**的完整技能包。
由 AIWatch（410×502 方形屏）与 AIWatchApple（240×240 圆形屏）两个实战项目沉淀而成，
可整体拷贝到任何位置、供任何 agent 工具加载使用——Claude Code、WorkBuddy、
DeepSeek harness / Codex、豆包、Freebuff / Codebuff、Cursor 等，
各家的接入方式见「[接入 agent 工具](#接入-agent-工具)」。

---

## 使用方法

### 1. 这个技能做什么

一条「输入 → 输出」的确定性流水线：给一张 UI 参考图 + 几句需求，产出一个**能直接用
SquareLine Studio 打开、且编辑器不报错**的完整工程。

| | 内容 |
|---|---|
| **输入** | ① UI 参考图（概念图 / 设计稿 / 截图）② UI 需求的文字说明 ③ 可选：图标、字体素材 |
| **输出** | ① `<Name>设计规格文档.md`（可复现的**源真相**）② 全套 PNG 资产 ③ `mockup.html`（含单文件 standalone 版）④ **完整 SquareLine 工程**（`.spj/.sll/.slp/Themes.slt/project.info` + `assets/`，含子集化字体三件套）⑤ 校验与反渲染预览结果 |

### 2. 前置条件

| 需要 | 说明 |
|---|---|
| **Node.js** | 渲染 PNG、字体子集化、mockup 内联。依赖已内联在 `tools/node_modules`，**无需 npm install** |
| **Python 3** | 构建工程、校验、预览（本机在 3.13 实测通过）。`Pillow` 仅截图辅助脚本需要 |
| **SquareLine Studio** | **不需要**。校验器用 `tools/schema_snapshot.json` 做 schema 对照；装了也只是多一层交叉校验 |

### 3. 两种用法

**用法一：交给 agent 自动跑（推荐）**

把整个 `squareline-design-skills/` 拷进你的项目，按下文「接入 agent 工具」配置一次。
之后用自然语言下指令即可——SKILL.md 的 front-matter 已声明触发词，agent 会自己按
Stage 0 → A → B → C 走完，并在每个阶段跑对应的机械校验。

```
用户：这是手表首页的参考图 [图]，做一个 SquareLine 工程，240×240 圆形屏。

agent：1. 先写 examples/<Name>/<Name>设计规格文档.md（源真相），与你确认几何/文案
       2. Stage A 生成资产 PNG
       3. Stage B 出 HTML mockup 给你看
       4. Stage C 编译成 .spj 工程
       5. validator + 反渲染预览，全绿后交付
```

**交付时必须卡住两条**：validator 打印 `OK - project validated, no problems found`；
反渲染预览逐屏与你给的参考图一致。

**用法二：自己敲命令**

见下文「命令速查」。五个阶段各有一条命令，每阶段都有独立校验，可随时中断检查。

### 4. 五个阶段

| 阶段 | 干什么 | 产出 | 怎么校验 |
|---|---|---|---|
| **Stage 0**<br>输入契约 | 复制 `templates/设计规格文档模板.md`，逐节填成 `<Name>设计规格文档.md` | 设计规格文档——**后续每个阶段都拿它当基准** | 人工三条：`rect` 全用屏幕绝对坐标；§6.1 文案字符集写全；控件高 ≥ 字体行高 |
| **Stage A**<br>资产 | `generate_assets*.mjs` 用 resvg 把 Lucide 图标 / 自绘 SVG 渲成 PNG（2 px ≈ 1 dp） | `assets/images_*/` | 读 PNG 头核对真实尺寸；与 mockup 引用比对 missing / unused |
| **Stage B**<br>Mockup | 出静态网格 `mockup.html` + 交互态版；`inline_mockup.mjs` 压成单文件 | `mockup.html` / `*_standalone.html` | 未缩放重叠审计（用 `offsetTop+offsetHeight`，别用 rect） |
| **Stage C**<br>编译工程 | 常规屏走 spec JSON → `build_from_spec.py`；径向布局等定制几何 → `tools/screens/<name>.py` | `squareline/<Name>/` 完整工程 | `validate_squareline_project.py` + `preview_from_project.py` |
| **回归 / 发布** | 重建归档工程逐字节比对；发布前体检与打包 | 全绿报告 / `dist/*.zip` | `eval/run_regression.py`、`tools/preflight.py --full` |

> **为什么一定要先有 Stage 0**：规格文档是唯一的「源真相」。而且引擎构建时会
> **收录文档里出现的每一个字符**进字体子集——所以想改文案，必须先把新词写进 §6.1，
> 否则字体会缺字。

### 5. 常见任务 → 这样说就行

| 你想做的事 | 直接说 |
|---|---|
| 从参考图做新工程 | 「参考图 [图] 做一个 SquareLine 工程，`<宽×高>` `<RECT/CIRCLE>`」 |
| 加一个屏幕 | 「加一个设置屏，包含 X / Y / Z」 |
| 布局对不齐 | 「首页图标环与参考图对不齐，按图调整」 |
| 只要 HTML 效果 | 「先出个 HTML mockup 看看，不用生成工程」 |
| 只要图标和字体 | 「把图标渲成 assets/images，字体做子集」 |
| 校验已有工程 | 「验证一下 `<路径>.spj`」 |
| 不开编辑器看效果 | 「反渲染预览这个工程」 |
| 换成圆形屏 | 「改成 240×240 圆形屏」 |

### 6. 交付物长什么样

```
examples/<Name>/
├── <Name>设计规格文档.md            # 源真相 —— 改需求先改这里
├── assets/images_*/                 # Stage A 产出的 PNG
├── mockup.html / *_standalone.html  # Stage B 的 HTML 预览
└── squareline/<Name>/               # Stage C 的 SquareLine 工程
    ├── <Name>.spj                   # ← 用 SquareLine「Open Project」打开这个
    ├── <Name>.sll / .slp / Themes.slt / project.info
    └── assets/                      # 图片 + 字体三件套（.c / .bin / .fcfg）
```

`backup/ cache/ components/ ui/` 是编辑器运行时产生的垃圾，**不要提交**。

### 7. 出问题先跑什么

```bash
python tools/validate_squareline_project.py <工程>   # 工程本身有没有问题
python tools/preview_from_project.py <工程>          # 不开编辑器看效果
python eval/run_regression.py                        # 改过 tools/engine/ 之后必跑
python tools/preflight.py                            # 包是否还健康（秒级）
```

---

## 目录结构

```
squareline-design-skills/
├── skills/squareline-ui-pipeline/
│   ├── SKILL.md          # 技能定义（工作流 + 全部踩坑教训）—— agent 接入入口
│   └── REFERENCE.md      # .spj 格式 / 事件 schema / 字体子集 / 资产 深度技术参考
├── templates/
│   └── 设计规格文档模板.md          # Stage 0 输入契约：复制它填，就是「源真相」
├── tools/                # 全套工具链（node + python，见下表；node_modules 已内联，离线可用）
│   ├── engine/squareline_engine.py  # 引擎层：序列化/事件/动画/字体/rebase（项目无关）
│   ├── screens/*.py                 # 内容层：定制几何的屏幕定义（AIWatch / AIWatchApple）
│   ├── lib/resvg.mjs                # SVG→PNG 统一入口（原生绑定 + WASM 兜底）
│   ├── schema_snapshot.json         # 官方 strtype 快照（无本地 Studio 也能校验）
│   └── ...                          # 构建/校验/预览/打包/preflight 脚本
├── fonts/                # 源字体（Noto Sans SC 400/500/700 TTF，供子集化）
├── eval/                 # 回归套件：重建每个归档工程并逐字节比对标准答案
├── examples/
│   ├── AIWatchApple/     # 240×240 圆形屏：规格文档 + mockup + **完整生成的 SquareLine 工程**
│   │   └── squareline/AIWatchApple/
│   ├── AIWatch/          # 410×502 方形屏：规格文档 + 静态/交互 mockup + 生成工程
│   └── SpecWidget/       # 320×320 最小示例：SpecWidget.spec.json（**声明式规格**，无位图资产）
```

> `tools/node_modules`（约 64MB，已 prune lucide-static 冗余）随包内联：拷贝后
> **无需 npm install** 即可运行全部 node 工具；也可删除后用 `cd tools && npm install` 重建
> （依赖声明在 tools/package.json）。
>
> `@resvg/resvg-js` 是**原生模块**（每个 OS/CPU 一个 `.node`）。包里已 vendoring
> Linux(x64/arm64, gnu/musl)、macOS(arm64/x64)、Windows(x64) 绑定，外加
> `@resvg/resvg-wasm` 兜底，所以 **Linux 容器里不装任何东西也能跑 Stage A**。
> 需要补/platform 时用 `python tools/vendor_prepare.py --platforms`。

### tools/ 一览

| 文件 | 作用 | 依赖 |
|---|---|---|
| `build_from_spec.py` | **声明式规格 JSON → 工程**（常规屏首选路径） | python |
| `build_squareline_project.py` | 入口：410×502 方形工程（定制几何） | python |
| `build_squareline_apple.py` | 入口：240×240 圆形工程（定制几何） | python |
| `engine/squareline_engine.py` | 引擎层：属性 plumbing / nid·guid / 事件动画 / rebase / 字体子集 | python |
| `generate_assets*.mjs` | Lucide/自绘 SVG → PNG（resvg），2px≈1dp | node |
| `generate_fonts.mjs` | TTF → LVGL 子集字体（lv_font_conv 三件套） | node |
| `inline_mockup.mjs` | HTML mockup 图片/字体 base64 内联 → standalone | node |
| `validate_squareline_project.py` | 10 项校验（schema/nid/资源/事件图/遮挡/语法） | python |
| `preview_from_project.py` | .spj → HTML 反渲染预览（工程无关，自动识别尺寸/形状） | python |
| `sq_catalog.py` | 从官方 examples 提取 schema 快照 | python |
| `schema_snapshot.json` | 固化后的官方 strtype 快照（校验器的对照源） | 数据 |
| `preflight.py` | 发布前检查清单（`--full` 含回归套件） | python + node |
| `package_release.py` | 打包 dist/*.zip，强制 UTF-8 文件名 | python |
| `vendor_prepare.py` | 侧载各平台 resvg 绑定 / prune lucide-static | python |
| `probe_headless_render.py` | **可选**深校验：用 LVGL 真渲染一帧 | python + lvgl |
| `crop_zoom.py` / `grab_window.py` | 截图裁剪/窗口抓取辅助 | python + Pillow |

## 命令速查（新项目）

> 流程图与各阶段说明见上文「使用方法 → 五个阶段」。这里只给可直接复制的命令。

```bash
# 0) 一次性准备：复制规格文档模板，填成你的设计规格（= source of truth）
#    模板已经把引擎需要的都列全了：面板几何 / 屏幕清单 / 对象表 / 交互 / 字体 / 文案字符集

# 1) 生成资产 + mockup
node tools/generate_assets_apple.mjs --out examples/<Name>/assets/images_apple
node tools/inline_mockup.mjs examples/<Name>/mockup.html examples/<Name>/mockup_standalone.html

# 2) 生成工程 —— 常规屏走声明式规格（推荐）
python tools/build_from_spec.py  examples/<Name>/<Name>.spec.json --out examples/<Name>/squareline/<Name>
python tools/build_from_spec.py  --example     # 打印带注释的 spec 骨架
#    只有径向布局/弦宽算术/预烘焙指针这类几何才需要写代码，见 tools/screens/*.py

# 3) 验证 + 反渲染预览（工程无关，可传任意 squareline/<Name>）
python tools/validate_squareline_project.py examples/<Name>/squareline/<Name>
python tools/preview_from_project.py        examples/<Name>/squareline/<Name>

# 4) 改动之后先跑回归，再动手提交
python eval/run_regression.py       # 重建全部归档工程，与标准答案逐字节比对
python tools/preflight.py --full    # 发布前检查清单
```

验收标准：validator 输出 `OK - project validated, no problems found`；
预览逐屏与 mockup 一致；SquareLine Studio 1.6.2 打开 .spj 无报错。

## 接入 agent 工具

这个包里**没有任何绑定某一家的代码**——`skills/` + `tools/` 就是全部接口。任何能读写
文件、能跑 shell 命令的 agent harness 都能驱动它，区别只在「技能怎么被加载」这一层。

| Agent | 加载方式 | 一句话配置 |
|---|---|---|
| **Claude Code** | `CLAUDE.md` + 目录内自动发现 | 根目录放 `CLAUDE.md` 指路（见 A），或把技能目录拷进 `.claude/skills/` |
| **WorkBuddy** | `~/.workbuddy/skills/` 或项目 `.workbuddy/skills/` | 把 `squareline-ui-pipeline` 整个拷进去，front-matter 触发词自动生效（见 B） |
| **DeepSeek harness / Codex / Cline / Roo** | `AGENTS.md` / 自定义 system prompt | `AGENTS.md` 一段指路（见 C），无技能自动加载机制 |
| **豆包 / 通用对话式 agent** | 系统提示词 | 把 SKILL.md 全文粘进「角色设定」，或上传为知识库文件（见 D） |
| **Freebuff / Codebuff** | `.codebuff/skills/` 自动发现 | 拷贝目录即可，靠 front-matter 触发（见 E） |
| **Cursor / Windsurf / 通义灵码 等** | `.cursorrules` / 规则文件 | 规则文件里指路（见 F） |

> **通用原则**：不管哪家，**只需要保证 agent 能读到 `skills/squareline-ui-pipeline/SKILL.md`
> 并且 `tools/`、`fonts/`、`templates/` 在仓库里同构存在**。SKILL.md 里的命令全部是
> 仓库相对路径（`python tools/...`），所以拷贝后零改动即可跑。

### 能力分级：你的 agent 属于哪一档

流水线对 harness 的要求是有阶梯的，**先确认你的 agent 在哪一档，再决定给它多少活**：

| 档位 | 具备能力 | 能跑到的阶段 | 典型代表 |
|---|---|---|---|
| **L1 纯对话** | 只输出文本，不能执行命令、不能写文件 | 只能帮你**起草 Stage 0 设计规格文档**（你手动落盘） | 网页版豆包、纯聊天窗口 |
| **L2 能读写文件** | 能改仓库文件，但不能执行 shell | Stage 0 + 手写 spec JSON；**Stage A/C 必须你自己敲命令** | 部分 IDE 补全类插件 |
| **L3 能执行命令** | 读写文件 + 跑 `node` / `python` | **全流程闭环**：Stage 0→A→B→C + validator + 回归 | Claude Code、WorkBuddy、Codex CLI、Freebuff |

**怎么判断**：直接问它一句「你能执行 `python tools/preflight.py` 并把输出贴给我吗」。
能跑就是 L3。**L3 才是这个技能的完整体验**——因为每个阶段都靠机械校验闭环，
L1/L2 会把「改完立刻验证」这个最重要的环节丢掉。

### A. Claude Code

Claude Code 会在会话里自动发现工作目录下的 `CLAUDE.md`，用它当项目级指令。

**A-1 最小接入（推荐）** — 在仓库根建 `CLAUDE.md`：

```markdown
# 项目：SquareLine UI Pipeline

本项目是一套把 UI 参考图转成 SquareLine Studio / LVGL 工程的技能包。

处理任何 SquareLine / LVGL UI 任务前，**必须先完整读**
`skills/squareline-ui-pipeline/SKILL.md`，并严格按它的阶段执行：

1. **Stage 0** 先写 `examples/<Name>/<Name>设计规格文档.md`（模板在 `templates/`），
   写完向用户确认几何与文案，再往下走。
2. **Stage A** `node tools/generate_assets*.mjs` 产出 PNG。
3. **Stage B** 出 `mockup.html`，让用户确认视觉。
4. **Stage C** 常规屏走 `python tools/build_from_spec.py <spec.json> --out <dir>`；
   径向/弦宽等定制几何才写 `tools/screens/<name>.py`。
5. **验证** `python tools/validate_squareline_project.py <工程>` +
   `python tools/preview_from_project.py <工程>`，全绿才算完成。

深度技术细节（.spj 字段、事件 schema、字体子集、资产规范）查
`skills/squareline-ui-pipeline/REFERENCE.md`。

**铁律**：只改 builder / spec 后重新生成，**绝不手改 `.spj`**；交互只用内置动作白名单；
改动 `tools/engine/` 之前先跑 `python eval/run_regression.py`。
```

**A-2 技能化接入（Claude Code 的 skills 机制）**

如果版本支持 `/skills` 目录发现，把技能整个拷进去：

```bash
mkdir -p .claude/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline .claude/skills/
cp -r squareline-design-skills/tools squareline-design-skills/fonts \
      squareline-design-skills/templates squareline-design-skills/eval \
      .claude/skills/squareline-ui-pipeline/
```

之后 `SKILL.md` front-matter 里的 `description` 就是触发条件，Claude 会在匹配到
「做一个 SquareLine 工程 / 圆形屏幕 / 验证 .spj」等说法时自动加载。

**Claude Code 注意事项**

- 它默认会在改文件前征询许可。全流程涉及几十次写文件，**建议开
  `--dangerously-skip-permissions` 或至少预先批准 `Bash(node:*)`、`Bash(python:*)`**，
  否则每个阶段都会被卡住。
- 长命令（`generate_assets.mjs` 渲 70+ 张 PNG、`run_regression.py` 全量重建）**要提前
  告诉它加大 timeout**，不然容易被当成卡死而中断。
- 它习惯「读完整个文件再改」。`tools/engine/squareline_engine.py` 有 1200+ 行，
  提醒它**只读要改的区段**，避免上下文爆掉。

### B. WorkBuddy

WorkBuddy 有原生技能目录，是本技能包**体验最完整**的宿主之一。

**B-1 用户级安装（所有项目可用）**

```bash
mkdir -p ~/.workbuddy/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline ~/.workbuddy/skills/
```

**B-2 项目级安装（随仓库走，推荐给团队）**

```bash
mkdir -p .workbuddy/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline .workbuddy/skills/
cp -r squareline-design-skills/tools squareline-design-skills/fonts \
      squareline-design-skills/templates squareline-design-skills/eval \
      .workbuddy/skills/squareline-ui-pipeline/
```

⚠️ **`.workbuddy/` 既是技能目录也是工作记忆目录**。本技能包自己的 `.gitignore`、
`.workbuddy/.gitignore` 和打包器白名单（`SHIP_TOP`）三重的就是**这个包自己的工作记忆**，
不是你要拷进去的 `.workbuddy/skills/`。在**目标项目**里，`.workbuddy/skills/` 应该提交；
在**本技能包仓库**里，`.workbuddy/` 整个不提交。两个语义不要混。

**B-3 触发方式**

`SKILL.md` 的 front-matter 已声明触发词，直接自然语言下指令即可：

```
用户：这是手表首页的参考图 [图]，做一个 SquareLine 工程，240×240 圆形屏。

WorkBuddy：先写设计规格文档 → 与你确认 → 生成资产 → 出 mockup →
           编译工程 → validator + 反渲染预览 → 全绿交付
```

**WorkBuddy 注意事项**

- 本技能包在 WorkBuddy 里实测过：`tools/node_modules` 已内联，**不需要 npm install**；
  Windows 上跑 node 工具若报 `node` 找不到，设 `SQUARELINE_NODE_BIN`。
- WorkBuddy 的 bash shim 在某些 Windows 环境下不完整（`dirname: command not found`）。
  遇到时**改用 PowerShell 或让 agent 直接调 python.exe 绝对路径**：
  ```powershell
  & "C:\Users\<you>\.workbuddy\binaries\python\versions\3.13.12\python.exe" tools\preflight.py
  ```
- 中文输出在 PowerShell 控制台可能显示成乱码（GBK 解码），但**写进文件的日志是好的**
  ——让它重定向到文件再读，不要以控制台显示判断成败。
- 多阶段长任务会被自动后台化，**不要让它去轮询**；跑完会收到通知。

### C. DeepSeek harness / Codex CLI / Cline / Roo Code

这一类没有技能自动加载机制，靠**仓库根的 `AGENTS.md`** 或 harness 自己的指令文件。
在项目根建 `AGENTS.md`：

```markdown
## SquareLine UI 技能

任何 SquareLine / LVGL UI 任务，先读 `skills/squareline-ui-pipeline/SKILL.md` 并严格
按其阶段执行：

设计规格文档（Stage 0，模板见 `templates/设计规格文档模板.md`）→ 资产 → HTML mockup →
`python tools/build_from_spec.py`（或 `build_squareline_*.py`）→
`validate_squareline_project.py` + `preview_from_project.py`。

技术细节查 `skills/squareline-ui-pipeline/REFERENCE.md`。

铁律：
- 只改 builder / spec 后重新生成，不手改 `.spj`；
- 交互只用内置动作白名单；
- 验证必须全绿（validator 输出 `OK - project validated, no problems found`）；
- 动 `tools/engine/` 之前先跑 `python eval/run_regression.py`。
```

**DeepSeek harness 注意事项**

- 上下文窗口较小时（如 64K），**不要让它一次读 SKILL.md + REFERENCE.md +
  engine 源码**。建议让它**先只读 SKILL.md**，需要时再按需读 REFERENCE.md 的对应章节
  （REFERENCE.md 是按 §1–§11 分节的，可以只读一节）。
- 它对超长命令输出的处理较保守，跑 `run_regression.py` 时**让它加
  `--no-assets`**（跳过慢的 Stage A），先确认 Stage C 的字节比对，最后再跑全量。
- 这一档**最需要 Stage 0 的纪律**：没有钩子帮你把住流程，模型容易跳步直接生成工程，
  结果就是字体缺字、坐标漂移。**务必让它先把设计规格文档写出来并跟你确认**。

**Codex CLI / Cline 补充**

- Codex CLI 自动读 `AGENTS.md`，同样配置即可。它的沙箱默认禁止网络，本技能**全离线**，
  不受影响；但**文件写入需在 workspace 内**，把技能包拷进项目目录再跑。
- Cline / Roo Code 用「Custom Instructions」字段，粘贴 `AGENTS.md` 那段内容即可。
  它们的 diff 编辑对 `tools/engine/squareline_engine.py` 这种大文件较吃力，
  建议只让它们改 `tools/screens/*.py` 和 spec JSON。

### D. 豆包 / 通用对话式 agent

豆包这类**没有仓库概念**，跑不了命令（L1 档）。**不要让它直接写 `.spj`——它做不到**，
写了也是错的。让它承担它真正擅长的部分：

**D-1 当「设计规格文档生成器」用（这是最有价值的用法）**

把 `templates/设计规格文档模板.md` 全文贴给它，加上参考图和需求：

```
你是 SquareLine Studio UI 设计规格文档的撰写者。
下面是文档模板 [模板全文]。
下面是我的 UI 参考图 [图] 和需求 [需求]。
请把模板逐节填成完整的设计规格文档，特别注意：
- §几何：所有 rect 用「屏幕绝对坐标」写全 x/y/w/h，不要写相对/居中描述；
- §对象表：每个控件给出类型、坐标、颜色、字号、对齐；
- §6.1 文案：把界面上会出现的**每一个字符**都列进去（含标题、按钮、单位、数字），
  这会决定字体子集要收录哪些字；
- §控件高度 ≥ 字体行高。
不确定的地方标注「待确认」，不要编造。
```

它产出的文档你手动存成 `examples/<Name>/<Name>设计规格文档.md`，**这就是源真相**，
后面交给 L3 的 agent 往下跑。

**D-2 当「素材文案助手」用**

- 让它在 mockup 出图后做**视觉走查**（贴 mockup 截图问「哪里对齐有问题」）。
- 让它核对参考图与反渲染预览的差异（两张图贴一起对比）。

**D-3 注意**

- 豆包**不能执行 `python` / `node`**，所以 Stage A/C 必须由你或 L3 agent 执行。
- 它有可能「幻觉」出并不存在的 LVGL API 或 `.spj` 字段。**所有技术判断以 REFERENCE.md 为准**，
  它的输出只当文案和几何草案。

### E. Freebuff / Codebuff

这是本技能包的**原始宿主**——两个实战工程（AIWatch / AIWatchApple）都是在它上面跑出来的。

```bash
mkdir -p .codebuff/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline .codebuff/skills/
cp -r squareline-design-skills/tools squareline-design-skills/fonts \
      squareline-design-skills/templates squareline-design-skills/eval \
      .codebuff/skills/squareline-ui-pipeline/
```

SKILL.md 的 front-matter 已含触发词，agent 会按 SKILL.md 的阶段流程走。

**Freebuff / Codebuff 注意事项**（来自实战踩坑）

- **重启会杀掉预览和后台服务**，需要重新注册；**文件本身不丢**。
- 预标签页是**一次性**的，用「替换」而不是叠加，否则会堆一地。
- `write_file` / `str_replace` 必须给全必填字段，`oldString` 要**字节精确**
  （先读区段再改）。
- 长任务（渲 70+ PNG）要留意它的超时，必要时拆成两条命令。

### F. Cursor / Windsurf / 通义灵码 / 其它 IDE 插件

没有技能发现机制，用「规则文件」指路：

```bash
# Cursor
cp AGENTS.md .cursorrules        # 或建 .cursor/rules/squareline.mdc

# Windsurf
# 把同一段内容粘进 .windsurfrules 或全局 Rules
```

规则文件内容与 C 节的 `AGENTS.md` 相同。`tools/`、`fonts/`、`templates/` 保持同目录结构即可。

> **提示**：把整个 `squareline-design-skills/` 拷进目标项目后，A–F 所有方式都指向
> 同一份 `SKILL.md`，迁移零改动。**改技能只需要改这一处。**


## 移植到新面板尺寸/形状

1. 面板几何写在描述符里（`width/height/shape`：`RECT` | `RECTANGLE` | `CIRCLE`）；
   validator / preview 自动从 `spj["info"]` 读取，无需改工具。
2. 圆形屏：遵守 SKILL.md「Round-screen design laws」（弦宽公式、径向布局、
   指针预烘焙、圆内安全区）。注意那里标 `[实例]` 的数值是 AIWatchApple 的实测值，
   **换面板要重算**——SKILL.md 开头专门有一节讲这个区别。
3. 字体：`fonts/` 放源 TTF，描述符的 `fonts` 表按用途列子集；
   字符集自动取自设计规格文档（也可用 `--spec <file>` 指定）。
4. 资产包：描述符里写 `"assets": "examples/<Name>/assets"`（仓库相对），
   裸命令即可重建；否则用 `--assets <dir>` 或 `SQUARELINE_ASSETS`。

## 包自检

```bash
python tools/preflight.py            # 廉价检查（秒级）：渲染后端 / 跨平台绑定 /
                                     # schema 快照 / 无个人路径 / 全树换行符 /
                                     # 打包器允许清单 / zip 编码与内容 /
                                     # README 文档与工具表一致性 / 无悬空引用
python tools/preflight.py --full     # 追加 eval/run_regression.py
python eval/run_regression.py        # 重建 3 个归档工程 + 6 个 Stage A 用例，
                                     # 逐字节比对 + 校验 + 预览（用例说明见 eval/test_cases.md）
python eval/run_regression.py --update   # 故意改动后刷新标准答案（先看 diff 再刷）
```

当前状态（本机实测）：`preflight.py` **16 项检查：15 通过 / 0 失败 / 1 提示**。

当前状态（本机实测）：

```
Stage A: AIWatchApple assets (native)         74 PNG 与标准答案逐字节一致
Stage A: AIWatchApple assets (wasm fallback)  74 PNG 与标准答案逐字节一致
Stage A: AIWatch assets (native)              71 PNG 与标准答案逐字节一致
Stage C: AIWatchApple / AIWatch / SpecWidget  工程树逐字节一致
Stage D: 三个工程 validate + preview 全通过
```

**归档产物不绑定宿主平台。** 引擎写文件一律固定 LF（`engine.dump_json`），
标准答案（`examples/**/squareline/`）因此是纯 LF。`preflight.py` 会扫描归档工程里
残留的 CRLF，`eval/run_regression.py` 也会把"仅换行符不同"单独标出来——历史上正是
这个差异让三个比对在 Linux 上**开箱必红**：标准答案是在 Windows 上落盘的，Python
的 `open(..., "w")` 会把 `\n` 翻成 CRLF，而 Linux 重建产出 LF。`.gitattributes` 的
`* text=auto eol=lf` 从 git 层再兜一层，防 `core.autocrlf=true` 在检出时改回去。

## 离线 / 容器环境

- **不需要** SquareLine Studio 安装：校验器的 strtype 对照源是
  `tools/schema_snapshot.json`。装了 Studio 也只是多一层交叉校验
  （`SQUARELINE_STUDIO=<install dir>`）。
- **不需要** npm install：`tools/node_modules` 已内联且含全平台 resvg 绑定。
- node 不在 PATH 时设 `SQUARELINE_NODE_BIN=/path/to/node`。

## 已知约束

- Python 侧需要 Pillow（仅截图辅助脚本用）；node 侧依赖已声明在 tools/package.json。
- `.spj` 由 builder 生成，编辑器保存后会加 `State_trickle` 等新字段——属正常，
  不要往回改引擎的序列化（validator 已含允许清单）。
- `probe_headless_render.py` 是可选深校验，需要本机有 lvgl 树；**不在主流程里**，
  环境不具备时跳过即可。
- `.workbuddy/` 是本项目的工作记忆（给 agent 用，`.workbuddy/memory/*.md`），
  **不是**交付内容。`.gitignore`、`.workbuddy/.gitignore` 与打包器的顶层白名单
  三重排除它。

## 发布：只发 `dist/squareline-design-skills.zip` 这一个文件

```bash
python tools/preflight.py --full        # 必须全绿
python tools/package_release.py         # 产出 dist/squareline-design-skills.zip 并自查
```

交付时只给这一个文件。这条规则是有代价换来的：曾经有一次交付是把**整个工作目录**
直接压缩，包里因此带上了 `.workbuddy/`（agent 工作笔记，含本机绝对路径）、一个
61 MB 的 `dist/*.zip`（自己套自己）、以及评审用的建议文档；又因为用的是资源管理器
"压缩文件夹"，中文文件名全部退化成 GBK 乱码——**把已经修好的编码问题原样复现了一遍，
而真正修好的那个包就混在它里面**。

现在有三道防线，任何一道都能独立拦住这类事故：

| 防线 | 位置 | 挡住什么 |
| --- | --- | --- |
| **顶层白名单** | `package_release.py` → `SHIP_TOP` | 根目录只发白名单条目，其余不打包**并把清单打印出来**。用白名单而非黑名单，是因为"新冒出来的临时目录"永远不会被漏掉——黑名单只能挡住作者记得写的那些 |
| **归档内容断言** | `preflight.py: check_zip_contents` | 包里出现 `dist/`、`.workbuddy/`、`__pycache__`、嵌套 `*.zip`、或整包带 `squareline-design-skills/` 前缀（= 压了整个目录）即判定失败 |
| **交付物点名 + 外部告警** | `preflight.py: check_deliverable` | 明确打印唯一交付物；若仓库旁边躺着"目录形状"的 zip，直接列出来并标注其中的泄漏路径 |

**永远不要**手动压缩整个 `squareline-design-skills/` 目录当交付物。
