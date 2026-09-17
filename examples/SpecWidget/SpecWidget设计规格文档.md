# SpecWidget 设计规格文档

> 示例：一份**可被 `build_from_spec.py` 直接消费**的设计规格文档。
> 本文档同时是 Stage 0 的输入契约样例（见 `templates/设计规格文档模板.md`），
> 也是构建时字体子集的 **glyph headroom 来源**——引擎会收录本文所有字符，
> 这样以后改文案时不会缺字形。

## 1. 设备

| 项 | 值 |
| --- | --- |
| 产品名 | SpecWidget |
| 屏幕尺寸 | 320 × 320 |
| 形状 | RECT |
| 主题 | 深色 |
| LVGL | 9.2.2 |
| 位图资产 | 无（纯几何 + 文字） |

## 2. 屏幕清单

| # | 屏幕 | 中文名 | 说明 |
| - | ---- | ------ | ---- |
| 1 | home | 首页 | 步数环，左右滑动切换 |
| 2 | settings | 设置 | 两张卡片 + 关于浮层 |

## 3. 交互定义

| 触发 | 对象 | 动作 |
| ---- | ---- | ---- |
| GESTURE_LEFT | home | 切到 settings |
| GESTURE_RIGHT | settings | 回到 home |
| CLICKED | ring | 播放 `ring pulse` 动画 |
| CLICKED | card_display | 隐藏「自动」、显示「手动」 |
| CLICKED | cd_value_manual | 隐藏「手动」、显示「自动」 |
| CLICKED | card_about | 显示「关于本机」浮层 |
| CLICKED | panel_about | 关闭浮层 |

## 4. 字体

| codename | 字重 | 字号 | 用途 |
| -------- | ---- | ---- | ---- |
| Big48 | 700 | 48 | 步数大数字 |
| Title20 | 500 | 20 | 标题、设置项名 |
| Body16 | 400 | 16 | 正文、说明、单位 |

### 4.1 文案字符集（glyph headroom）

以下为界面可能出现的全部文案，构建时会全部打进字体：

首页：步数 8642 步 左滑进入设置 右滑返回
设置：显示 自动 手动 关于本机 版本 v1.0 SpecWidget
浮层：320x320 声明式规格示例 关闭
未来文案（预留 headroom）：心率 血氧 睡眠 卡路里 距离 分钟 小时 天气 温度 湿度 电量 充电 同步 通知 免打扰 亮度 音量 语言 中文 英文 重置 恢复出厂 保存 取消 确定 返回

## 5. 坐标系约定

所有 `rect` 一律为**屏幕绝对坐标**（左上角原点）；引擎在写 `.spj` 前会
`rebase()` 成「相对父容器中心」的偏移，与 SquareLine 编辑器保存的形态一致。

## 6. 验收

- `validate_squareline_project.py` 10 项检查全通过
- `preview_from_project.py` 能反渲染出全部屏幕
- `eval/run_regression.py` 与标准答案逐字节一致
