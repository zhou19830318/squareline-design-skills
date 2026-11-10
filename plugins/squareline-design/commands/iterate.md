---
description: 应用一轮修改意见（改需求→改规格→预览→重建→验收），并登记迭代记录
argument-hint: <修改意见> [工程目录]
---

用户的修改意见：$ARGUMENTS

按 `squareline-ui-pipeline` §7 的回路：先把意见**原话**登记进 `UI需求清单.md` §9 迭代表 →
改设计规格文档 → 资产类改 manifest 并 `$SLX assets`，布局/文案类改 spec → `$SLX preview` →
`$SLX build` → `$SLX verify`。一次只处理一条意见（多条就逐条做，逐条验）。文案变化先确认新词已写入规格 §6.1。
最后在迭代表登记"已应用 + 改了哪几节"，并展示新旧预览对比。
