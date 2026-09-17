# 发布与维护（工程内部文档）

> **这是维护者文档，不是使用说明。** 使用者请读 [README.md](README.md)。
> 本文件只讲「怎么把本技能包发布出去、怎么改动它而不把它改坏」。

## 发布：只发 `dist/squareline-design-skills.zip` 这一个文件

```bash
python tools/preflight.py --full        # 必须全绿
python tools/package_release.py         # 产出 dist/squareline-design-skills.zip 并自查
```

交付时只给这一个文件。

### 这条规则是有代价换来的

曾经有一次交付是把**整个工作目录**直接压缩，包里因此带上了：

- `.workbuddy/`（agent 工作笔记，含本机绝对路径）
- 一个 61 MB 的 `dist/*.zip`（自己套自己）
- 评审用的建议文档
- 又因为用的是资源管理器「压缩文件夹」，中文文件名全部退化成 GBK 乱码——
  **把已经修好的编码问题原样复现了一遍，而真正修好的那个包就混在它里面**

### 三道防线

任何一道都能独立拦住这类事故：

| 防线 | 位置 | 挡住什么 |
|---|---|---|
| **顶层白名单** | `package_release.py` → `SHIP_TOP` | 根目录只发白名单条目，其余不打包**并把清单打印出来**。用白名单而非黑名单，是因为「新冒出来的临时目录」永远不会被漏掉——黑名单只能挡住作者记得写的那些 |
| **归档内容断言** | `preflight.py: check_zip_contents` | 包里出现 `dist/`、`.workbuddy/`、`__pycache__`、嵌套 `*.zip`、或整包带 `squareline-design-skills/` 前缀（= 压了整个目录）即判定失败 |
| **交付物点名 + 外部告警** | `preflight.py: check_deliverable` | 明确打印唯一交付物；若仓库旁边躺着「目录形状」的 zip，直接列出来并标注其中的泄漏路径 |

**永远不要**手动压缩整个 `squareline-design-skills/` 目录当交付物。

当前 `SHIP_TOP`（10 项）与 `dist/` 的实际根目录条目一致：

```
README.md  README.en.md  skills  tools  templates  eval  examples  fonts
.gitignore  .gitattributes
```

`README.en.md` 是 `README.md` 的英文版，**不单独占白名单一项**：打包器认的是
「白名单里已有 `README.md`，所以 `README.<后缀>.md` 一起发」（见
`SHIP_COMPANION_SUFFIXES`）。这样根目录的 `.md` 仍然只有词干被白名单点名过的
才发，白名单性质不变，多语言文档也不会因为漏加一行而静静丢失。

两份 README 之间必须**互相有语言切换链接**、且所有相对链接与截图都要落得到实处——
这条由 `preflight.py: check_readme_languages` 守着。

`.git/`、`.workbuddy/`、`dist/` 一律不发，且打包器会把它们**打印在「not shipped」
清单里**，让省略可见而不是静默发生。

## 包自检

```bash
python tools/preflight.py            # 廉价检查（秒级）：渲染后端 / 跨平台绑定 /
                                     # schema 快照 / 无个人路径 / 全树换行符 /
                                     # 打包器允许清单 / zip 编码与内容 /
                                     # README 文档与工具表一致性 / 中英 README 互链 /
                                     # 无悬空引用
python tools/preflight.py --full     # 追加 eval/run_regression.py
python eval/run_regression.py        # 重建 3 个归档工程 + 6 个 Stage A 用例，
                                     # 逐字节比对 + 校验 + 预览（用例说明见 eval/test_cases.md）
python eval/run_regression.py --update   # 故意改动后刷新标准答案（先看 diff 再刷）
```

当前状态（本机实测）：`preflight.py` **19 项检查：18 通过 / 0 失败 / 1 提示**
（唯一的提示是仓库旁边那个历史遗留的目录形状 zip，见下）。

回归套件（本机实测，18/18 全绿）：

```
Stage A: AIWatchApple assets (native)         74 PNG 与标准答案逐字节一致
Stage A: AIWatchApple assets (wasm fallback)  74 PNG 与标准答案逐字节一致
Stage A: AIWatch assets (native)              71 PNG 与标准答案逐字节一致
Stage C: AIWatchApple / AIWatch / SpecWidget  工程树逐字节一致
Stage D: 三个工程 validate + preview 全通过
```

## 改动的四条纪律

1. **只改 builder / spec 后重新生成，绝不手改 `.spj`。**
   编辑器保存 `AIWatchApple.spj` 时会在里面写 UTF-8 中文。
   任何「用文本工具直接改 `.spj`」的尝试都会踩到编码坑，且下次重建即被覆盖。
2. **交互只用内置动作白名单。** 动作名写错不会报错，只会在 Studio 里静默失效。
3. **改 `tools/engine/` 之前先跑 `python eval/run_regression.py`**，改完再跑一次。
   三个归档工程必须仍然逐字节一致。
4. **改 README / SKILL.md 之后跑 `python tools/preflight.py`**，
   它会交叉核对「README 里点名的脚本是否都存在」与「是否有悬空引用」。

## 换行符契约（跨平台不翻车的关键）

**归档产物不绑定宿主平台。** 引擎写文件一律固定 LF（`engine.dump_json` 里显式
`newline="\n"`），标准答案（`examples/**/squareline/`）因此是纯 LF。

历史上正是这个差异让三个比对在 **Linux 上开箱必红**：标准答案是在 Windows 上落盘的，
Python 的 `open(..., "w")` 会把 `\n` 翻成 CRLF，而 Linux 重建产出 LF。
`.gitattributes` 的 `* text=auto eol=lf` 从 git 层再兜一层，
防 `core.autocrlf=true` 在检出时改回去。

`preflight.py` 的 `check_artifact_eol` 会扫描**整棵交付树里 91 个文本文件**，
`eval/run_regression.py` 也会把「仅换行符不同」单独标出来。

> 注意：这个检查早先只扫 `examples/`，于是 `tools/` 下两个 CRLF 文件长期漏网。
> 现在扫全树，新加的脚本如果带 CRLF 会当场变红。

## 目录结构与发布范围的关系

`README.md` 的「目录结构」一节是**使用者视角**（有哪些能力、在哪）。
发布范围由 `tools/package_release.py` 的 `SHIP_TOP` 决定，两者刻意分开：
README 讲能做什么，`SHIP_TOP` 管发什么。

- `docs/steps/*.png`（README 实战走查的过程截图）挂在 `examples/` 之下，
  随包发布——**README 里嵌的图必须发**，否则读者看到一堆裂图。
- `preview_from_project.html` 是**生成物**（跑一次 preview 就会在归档工程里落一个），
  已在 `EXCLUDE_FILES` 里排除，不随包发。
- `mockup*.html` 是 Stage B 的**交付物**，保留。

## 已知维护项

- `preflight.py: check_deliverable` 会一直在仓库父目录扫 `.zip`。若那里躺着一个
  目录形状的旧包（本次实测 123.2 MB，泄漏 `.workbuddy/`），它会以 SKIP 形式报出来。
  **这不是本仓库的问题**，但删除它可以消除唯一的提示项。
- `probe_headless_render.py` 是可选深校验，需要本机有 lvgl 树；不在主流程里，
  环境不具备时跳过即可。它也**不能被列进 SKILL.md 的主流程代码块**（preflight 会红）。
- `e2e` 的 `dist/*.zip` 是构建产物，不进版本库（`.gitignore` 已排除）。
