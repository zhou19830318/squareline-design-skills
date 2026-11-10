---
description: 收集/生成工程所需的图标、烘焙图与字体配置（PNG，原生尺寸，含许可证记录）
argument-hint: [工程目录] [补充要求，如"换成 Phosphor 风格"]
---

处理资产：$ARGUMENTS

加载技能 `squareline-assets`。盘点 spec 里的 IMAGE → 选源（Lucide 离线优先）→ 写/改 `assets.manifest.json`
→ `$SLX assets <proj>` → `$SLX preview <proj> --strict` 确认无缺图。站外图标网络受限时如实告诉用户，不要悄悄替代。
结束时汇报来源分布与需署名项。
