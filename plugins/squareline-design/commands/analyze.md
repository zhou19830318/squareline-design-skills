---
description: 只做 Stage 0：分析概念图，产出需求清单、设计规格文档、初版 spec 与资产清单
argument-hint: <概念图路径> [工程目录]
---

分析概念图：$ARGUMENTS

加载技能 `concept-to-spec` 与 `squareline-ui-pipeline`。有需求文档先 `slx.py reqs extract`；量图用 `slx.py scan` / `fit-font`；每步之后跑 `slx.py next`。若还没有工程目录先 `$SLX init`；
完整执行 concept-to-spec 的步骤 1–9，最后给出**确认表**（闸门 1）。不生成 PNG、不构建。
