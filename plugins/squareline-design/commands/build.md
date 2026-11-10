---
description: 预览并构建 SquareLine 工程，随后校验 + 反渲染，输出 .spj 路径与预览图
argument-hint: [工程目录]
---

构建工程：$ARGUMENTS

加载技能 `squareline-ui-pipeline`：`$SLX preview <proj> --strict` → 修到干净 → `$SLX build <proj>` →
`$SLX verify <proj>`。validator 必须输出 `OK - project validated, no problems found`。
若有概念图，对关键文字用 `$SLX bbox` / `$SLX diff` 复量校准（`squareline-ui-pipeline` §5.6）。把 `preview/project_preview.png` 展示给用户，并说明 `.spj` 路径。失败时按技能 §8 速查表定位，
修 spec/manifest 后重建，不手改 .spj。
