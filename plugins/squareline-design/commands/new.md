---
description: 从概念图一路做出 SquareLine 工程（分析→规格→资产→构建→校验→预览），带两个确认闸门
argument-hint: <概念图路径> [工程名] [宽x高] [RECT|CIRCLE]
---

用户想从概念图做一个 SquareLine / LVGL 工程。参数：$ARGUMENTS

**主循环**：每做完一步就运行 `python3 $TK/tools/slx.py next <proj>`，它会告诉你下一步（也会拦住你跳过闸门）。
以下是各阶段的要点。先加载技能 `squareline-ui-pipeline`（工具位置 `$TK`、命令 `$SLX`、闸门规则都在里面）：

1. **环境**：`$SLX doctor`，有 FAIL 先修。
2. **立项**：确定工程名（英文）、面板尺寸与形状；缺的在**一轮**里问清（带推荐默认值）。
   在用户工作区执行 `$SLX init <Name> --width W --height H --shape …`，把概念图复制进 `<proj>/concept/`。
3. **Stage 0**：按技能 `concept-to-spec` 分析概念图，写 `UI需求清单.md`、`<Name>设计规格文档.md`、
   `<Name>.spec.json`、`assets.manifest.json`。
   **闸门 1**：给用户一张确认表（面板、屏幕、配色、字阶、[测得]/[估算]/[假设]、待决问题）。**确认前不要继续**。
4. **Stage A**：按技能 `squareline-assets` 生成资产 `$SLX assets <proj>`。
5. **预览**：`$SLX preview <proj> --strict`，修到无红框无报警。
   **闸门 2**：把 `preview/spec_preview.png` 与概念图并排（`$SLX sidebyside`）给用户看，确认后再构建。
6. **构建与验收**：`$SLX build <proj>` → `$SLX verify <proj>`；调用 `design-reviewer` 子代理对照概念图，
   把差异逐条修掉（改 spec/manifest 后重建，不手改 .spj）。
7. **交付**：按 `squareline-ui-pipeline` §10 说明 .spj 路径、预览图、资产来源/许可、与概念图的已知差异。
