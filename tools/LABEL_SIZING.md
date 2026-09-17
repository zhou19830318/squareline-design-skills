# LABEL 高度 vs 字体行高（速查表）

> 本文件由 `tools/label_sizing.py` 从**已构建工程的字体 `.c`** 自动生成，
> 请勿手改。`python tools/preflight.py` 会校验它与工程是否同步。

## 为什么需要这张表

`run_build()` 会拒绝 `height < line_height` 的 LABEL —— 这是对的，
但**报错太晚**：字体是构建期生成的，`line_height` 只能靠正则解析产物 `.c` 才拿得到，
所以在写 spec 坐标的那一刻没有任何东西可查，只能反复试错。

关键点（反直觉）：**`line_height` 一定大于 `size`**。
因为行高包含 ascender + descender 的整体高度，而不是 em 字号本身。
按 `height >= size` 留尺寸必然被裁切。

## ⚠️ 行高不是常量：同一个字体在不同工程里会不一样

`line_height = max(该字体实际包含字形的 ascent) + max(descent)`，
所以**它取决于工程收进了哪些字形**，而不是只取决于字号。实测：

| 字体 | size | 字形数 | line_height | 工程 |
|---|---|---|---|---|
| `Body16` | 16 | 820 | **21** | `examples/AIWatch` |
| `Body16` | 16 | 293 | **20** | `examples/SpecWidget` |
| `Title20` | 20 | 346 | **24** | `examples/AIWatchApple` |
| `Title20` | 20 | 293 | **23** | `examples/SpecWidget` |

结论：**下表只能当起始估计，不能当权威值。**
权威值永远是你自己那次构建输出里的 `lineheight:` 一行。
把下表取**最大值**、或直接按经验公式留余量，才是安全做法。

## 经验公式（推荐）

```
height >= ceil(size * 1.35)     # 单行中文的安全下界（含跨工程余量）
```

实测 `line_height / size` 落在 **1.19 ~ 1.31**（小字号比例更大，因为
hinting/取整对小字号影响更重）。取 **1.35** 可覆盖上表所有行并留出余量；
宁可稍高也不要压线，压线在不同工程/不同字形集下会翻车。
多行文案再乘以行数。

## 实测对照表（按字体名+字号去重，取各工程最大值）

| font | size | line_height | 安全 height (≥) | 比例 | base_line | 来源工程 |
|---|---|---|---|---|---|---|
| `Big48` ⚠️ | 48 | 60 | 60 | 1.25 | 14 | `squareline/SpecWidget/assets/fonts/ui_font_Big48.c` |
| `Body15` | 15 | 19 | 19 | 1.27 | 4 | `examples/AIWatchApple/squareline/AIWatchApple/assets/fonts/ui_font_Body15.c` |
| `Body16` ⚠️ | 16 | 21 | 21 | 1.31 | 5 | `examples/AIWatch/squareline/AIWatch/assets/fonts/ui_font_Body16.c` |
| `Caption12` | 12 | 15 | 15 | 1.25 | 3 | `examples/AIWatch/squareline/AIWatch/assets/fonts/ui_font_Caption12.c` |
| `Caption13` | 13 | 17 | 17 | 1.31 | 4 | `examples/AIWatchApple/squareline/AIWatchApple/assets/fonts/ui_font_Caption13.c` |
| `Number36` | 36 | 44 | 44 | 1.22 | 10 | `examples/AIWatchApple/squareline/AIWatchApple/assets/fonts/ui_font_Number36.c` |
| `NumberBold48` | 48 | 60 | 60 | 1.25 | 14 | `examples/AIWatch/squareline/AIWatch/assets/fonts/ui_font_NumberBold48.c` |
| `TimeBig44` | 44 | 53 | 53 | 1.20 | 12 | `examples/AIWatchApple/squareline/AIWatchApple/assets/fonts/ui_font_TimeBig44.c` |
| `TimeDisplay72` | 72 | 86 | 86 | 1.19 | 20 | `examples/AIWatch/squareline/AIWatch/assets/fonts/ui_font_TimeDisplay72.c` |
| `Title20` ⚠️ | 20 | 24 | 24 | 1.20 | 5 | `examples/AIWatchApple/squareline/AIWatchApple/assets/fonts/ui_font_Title20.c` |
| `Title22` | 22 | 27 | 27 | 1.23 | 6 | `examples/AIWatch/squareline/AIWatch/assets/fonts/ui_font_Title22.c` |

⚠️ = 同一个字体+字号在不同工程里行高不一致（见上一节），此时取的是最大值。

## 怎么用

1. 先按经验公式 `ceil(size * 1.35)` 定 LABEL 高度，别凭字号猜。
2. 想精确核对，跑一次 `python tools/build_from_spec.py <spec.json>`，
   构建输出里的 `lineheight:` 一行列出**你这个工程**的真实行高：
   ```
   lineheight: {'Title20': 23, 'Body16': 20}
   ```
3. 多行文案（`text` 里含 `\n`）把安全高度乘以行数。
4. 仍然 `height < line_height` 会被报成 `ERROR`（构建返回非 0），
   文案换行后超出控件高度会报成 `WARN`。

## 构建输出的相关几行

```
fonts     : [('Big48', 48, 13), ('Title20', 20, 293), ('Body16', 16, 293)]
charset   : ui-text 46, doc-headroom 291 (+246 usable)     # 字形来源与余量
lineheight: {'Big48': 60, 'Title20': 23, 'Body16': 20}     # 本工程真实行高
```
