# 回归测试用例集

> 配套脚本：`eval/run_regression.py`（`python eval/run_regression.py`）
> 目的：把「给定输入 → 期望输出」变成机械可验证的事实。改引擎之前先跑它，
> 改完之后再跑一次——两次都绿，才算没弄坏既有工程。

## 0. 为什么需要它

这套流水线原来只有两个生产工程，且工程文件是**代码生成**的、没有输入。
结果是：任何对引擎的改动都只能靠「打开预览用眼睛看」，字体子集变了、
坐标 rebase 错了、nid 计数器串了，全都看不出来。回归套件把每份归档工程
当作**标准答案（golden）**，每次从头重建再逐字节比对。

## 1. 用例总览

| # | 阶段 | 用例 | 输入 | 期望 |
| - | ---- | ---- | ---- | ---- |
| E0 | 前置 | 归档产物换行符 | 扫 `examples/*/squareline/*` 下全部文本产物 | **纯 LF**，无 CRLF（见 §2.1） |
| A1 | Stage A | AIWatchApple 资产（原生绑定） | `tools/generate_assets_apple.mjs` | 输出 PNG 与 `examples/AIWatchApple/assets/images_apple` **逐字节**一致 |
| A2 | Stage A | AIWatchApple 资产（WASM 兜底） | 同上 + `RESVG_FORCE_WASM=1` | 与 A1 的 golden 逐字节一致 → 证明**无原生绑定的平台**（Linux 容器）也能出同样的图 |
| A3 | Stage A | AIWatch 资产（原生绑定） | `tools/generate_assets.mjs` | 与 `examples/AIWatch/assets/images` 逐字节一致 |
| C1 | Stage C | AIWatchApple 工程（240×240 CIRCLE，定制几何） | `tools/build_squareline_apple.py` | 与 `examples/AIWatchApple/squareline/AIWatchApple` 逐字节一致 |
| C2 | Stage C | AIWatch 工程（410×502 RECT，定制几何） | `tools/build_squareline_project.py` | 与 `examples/AIWatch/squareline/AIWatch` 逐字节一致 |
| C3 | Stage C | SpecWidget 工程（320×320 RECT，**声明式规格**） | `examples/SpecWidget/SpecWidget.spec.json` | 与 `examples/SpecWidget/squareline/SpecWidget` 逐字节一致 |
| D1–D3 | Stage D | 校验 | 上一步**新构建**的工程目录 | `validate_squareline_project.py` 退出码 0 且打印 `OK - project validated` |
| D4–D6 | Stage D | 反渲染 | 同上 | `preview_from_project.py` 退出码 0 且写出 `preview_from_project.html` |
| S1 | 契约 | 非法规格必须**明确报错** | 引用了未声明字体的 spec | 退出码 ≠ 0，输出含 `spec error`，**不得抛 Python traceback** |
| S2 | 契约 | `--example` 可用 | `build_from_spec.py --example` | 退出码 0 且输出含 `"$schema"` |

## 2. 比对范围

比对**新构建目录**与**归档 golden 目录**下的全部文件，排除：

```
backup/  cache/  components/  ui/  __pycache__/  node_modules/  dist/
preview_from_project.html
*.preview.json
```

前一组是 SquareLine 编辑器保存时自己产生的churn目录；后两个是本仓库的
开发/评审产物，不是构建输出。**其余一律参与比对**，包括：

- `*.spj` / `*.sll` / `*.slp` / `Themes.slt` / `project.info`
- `assets/*.png`（由构建过程从资产包复制）
- `assets/fonts/*.c` / `*.bin` / `*.fcfg`（字体子集三件套）
- `assets/fonts/*.ttf`（源字体副本）

字体三件套参与比对是刻意的：曾经 `lv_font_conv` 把**绝对路径**写进 `.c`
文件头注释，同一份工程在不同机器/目录构建就 diff 不过。引擎现在会把该行
改写为相对路径（`normalise_font_c()`），这条用例就是它的看门狗。

### 2.1 换行符也属于比对契约（用例 E0）

归档产物**必须是纯 LF**。这条不是洁癖：`open(path, "w")` 是平台相关的，
文本模式会把 `\n` 翻译成宿主换行符。标准答案在 Windows 上落盘 → CRLF，
Linux 重建 → LF，于是下面这几个文件在**流水线主攻的 Linux 环境里开箱必红**：

```
.spj  .sll  .slp  Themes.slt  project.info  *.fcfg
```

内容其实完全一致，validator / preview 也全过，所以从 diff 里根本看不出
原因——三个 `changed :` 看着像生成器坏了。现在：

- 引擎统一走 `engine.dump_json`（内部 `newline="\n"`），
  `.c` 由 `normalise_font_c()` 顺带归一化；
- 用例 **E0 前置扫描**归档工程，有任何 CRLF 就直接点名文件并提示
  `python eval/run_regression.py --update`；
- 若某次 diff 的差异**只**是换行符，输出会明确标注
  `changed : x.spj   <-- LINE ENDINGS ONLY (CRLF vs LF)`，而不是留一个哑差异；
- `.gitattributes` 的 `* text=auto eol=lf` 防止 `core.autocrlf=true`
  在检出时把 LF 改回 CRLF；`preflight.py: check_artifact_eol` 同样会扫。

## 3. 失败时怎么读输出

```
[FAIL] Stage C: AIWatchApple == golden (96 files)
       missing  : assets/fonts/ui_font_Body15.bin
       changed  : AIWatchApple.spj
```

- `missing` = golden 有、这次没生成 → 少写了文件（或输出目录不对）
- `unexpected` = 这次生成了、golden 没有 → 多写了文件（或掺进了 churn）
- `changed` = 两边都有但内容不同 → **真正的行为变化**，逐类看：
  - 标了 `LINE ENDINGS ONLY` → 换行符问题，见 §2.1，别去改生成逻辑
  - 只有 `.spj` → 属性/事件/动画序列化变了
  - 只有 `fonts/*` → 字符集或 lv_font_conv 参数变了
  - 只有 `*.png` → 渲染后端或 SVG 变了
  - 全都在变 → 先看 `project.info`，多半是元数据（版本号/时间戳）混入了

确认某次改动是**故意**的、且已逐项看过 diff 之后，用
`python eval/run_regression.py --update` 刷新标准答案——它会覆盖归档工程，
所以先看不改、确认无误再刷。

## 4. 刻意不做的两件事

1. **不做自动更新 golden。** 归档工程是「标准答案」，只能人工确认后重建
   （重跑对应 build 命令覆盖 golden 目录），再提交。让套件自己能改标准答案，
   等于没有标准答案。
2. **不比对 `preview_from_project.html`。** 它是给人看的评审产物，且内联了
   字体与图片的 base64，体积大又随模板微调而变。只断言「能生成、退出码 0」。

## 6. 半自动评估用的测试 prompt

回归套件验证的是「引擎没坏」。下面这些 prompt 验证的是「**skill 还好不好用**」——
换过 SKILL.md、改过模板、动过工作流之后，拿它们跑一遍，看 agent 是否仍按阶段推进、
是否先写规格文档、是否自己发现几何/字形错误。人工看结果，不看 diff。

| # | prompt | 期望 agent 做到 |
| - | ------ | --------------- |
| T1 | 「参考 `examples/AIWatchApple/AIWatchApple设计规格文档.md` 的格式，给一块 320×385 的方形屏写一份设计规格文档，做三屏：表盘 / 天气 / 设置」 | 先复制模板填空；`rect` 全用屏幕绝对坐标；§6.1 文案字符集写了预留词；控件高度满足行高约束 |
| T2 | 「按你刚写的规格文档，生成 SquareLine 工程并验证」 | 走 `build_from_spec.py`（**不是**复制 `screens/aiwatch.py`）；跑 validator 至 `OK`；跑 preview |
| T3 | 「把设置页第三行的值改成『已同步』，然后重新出工程」 | 只改 spec/规格文档的数据，**不手改 .spj**；重建后无缺字形告警；主动重跑回归 |
| T4 | 「这块圆形屏是 240×240，顶部要放一行状态文字，能不能直接放在 y=6？」 | 用弦宽公式算安全区，指出 y=6 处圆只有约 108 px 宽、放不下整行；给出可行的 y 或收窄方案 |
| T5 | 「为什么我构建出来的工程里一张图都没有，validator 报 missing image files？」 | 定位到资产包路径（描述符缺 `"assets"` / 没用 `--assets`），而不是去改坐标或改引擎 |

判定标准：T1/T2/T3 看**流程是否守规矩**（先规格、只改数据、验证全绿）；
T4/T5 看**是否用对了法则**（弦宽公式、资产路径优先级），而不是碰巧给出能跑的结果。

## 7. 归档工程的来源

| 工程 | 构建命令 |
| ---- | -------- |
| AIWatchApple | `python tools/build_squareline_apple.py --out examples/AIWatchApple/squareline/AIWatchApple` |
| AIWatch | `python tools/build_squareline_project.py --out examples/AIWatch/squareline/AIWatch` |
| SpecWidget | `python tools/build_from_spec.py examples/SpecWidget/SpecWidget.spec.json --out examples/SpecWidget/squareline/SpecWidget` |

新增工程时，在 `eval/run_regression.py` 的 `PROJECT_CASES` 里加一行即可；
若它还带来新的资产生成器，同时加一行到 `ASSET_CASES`。

## 8. 相关

- `python tools/preflight.py --full` —— 发布前检查清单，会调用本套件
- `python tools/preflight.py` —— 只跑几百毫秒的廉价检查（源码健康度、渲染后端、
  跨平台绑定、schema 快照、无个人路径、zip 编码与载荷、文档规范）
