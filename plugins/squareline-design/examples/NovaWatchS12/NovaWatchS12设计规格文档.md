# NovaWatchS12 设计规格文档

> **源真相**。本工程由 `tools/build_from_spec.py` 从 `NovaWatchS12.spec.json`
> 构建；本规格文档是其人类可读形式 + 字体字符集来源。几何全部为
> **屏幕绝对坐标**（左上角原点），面板 456×456 CIRCLE，r=228，
> 可见元素外接框四角到圆心距离 ≤ 216（安全区）。

---

## 1. 设备与画布

| 项 | 值 |
| --- | --- |
| 项目名 | `NovaWatchS12` |
| 面板尺寸 | `456 × 456` px |
| 形状 | `CIRCLE` |
| 主题 | 深色 |
| LVGL 版本 | `9.2.2` |
| 缩放约定 | px = design dp × 2（456px ≈ 228dp，46mm 表壳级） |
| 位图资产目录 | `examples/NovaWatchS12/assets/images` |

## 2. 屏幕清单

顺序 = 滑动环顺序（`order`）：watchface ↔ apps 双屏环，其余屏经 apps 点击进出。

| # | 屏幕名 | 中文名 | 一句话说明 |
| - | ------ | ------ | ---------- |
| 1 | `watchface` | 表盘 | 模拟表盘 + 数字时间 + 3 个 complication |
| 2 | `apps` | 应用 | 8 图标径向网格 + Nova 星徽标 |
| 3 | `health` | 健身 | 三活动环 + 步数/心率/卡路里 |
| 4 | `weather` | 天气 | 24° 大字 + 4 个逐时段 |
| 5 | `alarms` | 闹钟 | 3 行闹钟开关卡 |
| 6 | `workout` | 训练 | 户外跑步启动页 |
| 7 | `stopwatch` | 秒表 | 大数字秒表 |
| 8 | `breathe` | 正念 | 呼吸圆环 |
| 9 | `voice` | 语音 | AI 助手三态 |

- 初始屏：`watchface`

## 3. 对象清单（逐屏）

> `rect` = `[x, y, w, h]` 屏幕绝对坐标。`type` ∈ PANEL/LABEL/IMAGE/ARC。
> 完整逐对象坐标以 `NovaWatchS12.spec.json` 为准（同一数据的机器形式），
> 本表列出每屏的对象组与关键值。

### 3.1 `watchface`
| name | type | 关键内容 |
| ---- | ---- | -------- |
| `face_dial` | IMAGE | 预烘焙表盘 PNG `assets/img_face_dial.png`（表圈+刻度+三针 10:09:30） |
| `time_digital` | LABEL | `10:09` Big72，[118,66,220,96] |
| `date_line` | LABEL | `周二 9月28日` Title28 |
| `comp_hr` / `hr_value` | IMAGE+LABEL | 心率 32px 图标 @ [212,190] + `72` Small16 |
| `comp_temp` / `temp_value` | IMAGE+LABEL | `24°` 左下 |
| `comp_batt` / `batt_value` | IMAGE+LABEL | `82%` 右下 |
| `swipe_hint` | LABEL | `左滑 ›` Body20 |

### 3.2 `apps`
| name | type | 关键内容 |
| ---- | ---- | -------- |
| `nova_core` | IMAGE | 自绘星徽标 96px 居中 [180,180] |
| `app_health` … `app_voice` | IMAGE ×8 | 64px 图标 @ r=150 环上 8 点（0°=顶部起，偏 22.5° 避开状态区） |

环上坐标（圆心 228,228，r=150，图标 64×64，左上 = cx+R·cosθ−32, cy+R·sinθ−32）：

| 角度 | 图标 | 左上坐标 |
| ---- | ---- | -------- |
| 270°（顶） | health | [196, 46] |
| 315° | weather | [298, 84] |
| 0°（右） | alarms | [346, 196] |
| 45° | workout | [298, 308] |
| 90°（底） | stopwatch | [196, 346] |
| 135° | breathe | [94, 308] |
| 180°（左） | voice | [46, 196] |
| 225° | settings | [94, 84] |

### 3.3–3.9 应用屏
- `health`：三活动环（红/绿/蓝 ARC，[148,60,160,160] 同心，宽度 14）+
  步数 `8642` Big72 + 心率/卡路里两行小卡。
- `weather`：`24°` Big72 @ [128,84] + `晴` Title28 + 4 列逐时（图标 48 + 温度）。
- `alarms`：3 张 card_row（`06:30 工作日` / `07:30 每天` / `22:30 就寝`），
  开关值为「开/关」标签对，点击切换（SHOW/HIDE 对）。
- `workout`：跑步图标 120px + `户外跑步` Title28 + `开始` 绿色按钮卡（点击
  隐自身、显示 `进行中` 卡）。
- `stopwatch`：`00:00.00` Big72 @ [88,150] + `开始`/`重置` 两个按钮卡。
- `breathe`：呼吸环（蓝 ARC + 呼吸动画）+ `呼吸` Body20。
- `voice`：麦克风图标 96px + 波形三态（`wave_idle`/`wave_listening`/`wave_
  speaking` 三张叠层，显式 hidden + 互斥 SHOW/HIDE）+ 三态文案。

## 4. 交互定义

> 动作白名单：CHANGE_SCREEN / HIDE / SHOW / SET_OPACITY / PLAY_ANIMATION /
> CALL_FUNCTION。

| # | 触发对象 | 事件 | 动作 |
| - | -------- | ---- | ---- |
| 1 | 8 个 app 图标 | CLICKED | CHANGE_SCREEN 对应屏 |
| 2 | 各应用屏（手势） | GESTURE_RIGHT | CHANGE_SCREEN `apps` |
| 3 | watchface↔apps | GESTURE_LEFT/RIGHT | 滑动环自动接线 |
| 4 | alarms 开关 | CLICKED | SHOW/HIDE 对 |
| 5 | workout 开始 | CLICKED | SHOW 进行中卡 / HIDE 开始卡 |
| 6 | voice 麦克风 | CLICKED | 三态轮转 SHOW/HIDE |
| 7 | health 环 | SCREEN_LOAD_START | PLAY_ANIMATION 环脉冲 |
| 8 | breathe 环 | SCREEN_LOAD_START | PLAY_ANIMATION 呼吸（loop） |

## 5. 动画

| name | target | property | frames (value, ms) | duration | path | loop |
| ---- | ------ | -------- | ------------------ | -------- | ---- | ---- |
| `health pulse` | health/ring_move | opacity | (120,0)(255,420)(160,840) | 840 | ease_out | 否 |
| `breathe cycle` | breathe/ring | opacity | (90,0)(255,1600)(90,3200) | 3200 | ease_in_out→ease_out | 是 |
| `sw pulse` | stopwatch/time_big | opacity | (140,0)(255,300) | 300 | ease_out | 否 |

## 6. 字体

| codename | 字重 | 字号 px | 用途 | ranges |
| -------- | ---- | ------- | ---- | ------ |
| `Big72` | 700 | 72 | 大数字/大温度 | `0x20-0x7E` |
| `Title28` | 500 | 28 | 标题/日期 | `0x20-0x7E`, `0x3001`, `0x3002`, CJK 常用 |
| `Body20` | 400 | 20 | 正文 | 同上 |
| `Small16` | 400 | 16 | complication 数值 | 同上 |

### 6.1 文案字符集（glyph headroom）★ 必填

- 表盘：`10:09 周二 9月28日 24° 72 82% 左滑`
- 应用：`应用 健康 天气 闹钟 训练 秒表 正念 语音 设置 呼吸`
- 健康：`步数 心率 卡路里 千卡 8642 12848`
- 天气：`晴 多云 小雨 转 24° 19° 26° 28° 21° 现在`
- 闹钟：`06:30 07:30 22:30 工作日 每天 就寝 开 关 闹钟`
- 训练：`户外跑步 开始 进行中 暂停 结束 体能训练`
- 秒表：`00:00.00 00:05.24 01:12.88 开始 重置 秒表`
- 正念：`呼吸 跟随圆环 吸气 呼气 正念`
- 语音：`你好 今天有什么安排 在听… 正在播报 点击说话`
- 预留：`电量 蓝牙 静音 月 日 年 温度 湿度 风速 睡眠 血氧 压力 确定 取消 完成 已连接 未连接 定时 提醒`

**skip**（Noto Sans SC v40 缺字 / LVGL 不适用）：`℃≈├📍⚠💡⏸→←🔋▶─️`

## 7. 资产清单

全部由 `assets.manifest.json` 声明式生成（`generate_assets_from_manifest.mjs`），
无外部下载，许可全部 MIT/ISC：

| 文件 | 尺寸 | 用途 | 来源 |
| ---- | ---- | ---- | ---- |
| `img_face_dial.png` | 456×456 | 预烘焙模拟表盘（表圈/刻度/三针） | builtin |
| `img_nova_core.png` | 96×96 | Nova 星徽标 | builtin |
| `img_app_health.png` 等 ×8 | 64×64 | 应用图标 | Lucide |
| `img_comp_hr.png` / `img_comp_temp.png` / `img_comp_batt.png` | 32×32 | complication | Lucide |
| `img_weather_now.png` 等 ×6 | 96/48 | 天气 | Lucide |
| `img_workout_run.png` | 120×120 | 训练 | Lucide |
| `img_wave_idle/listening/speaking.png` | 120×120 | 语音三态 | builtin |

## 8. 验收标准

- [x] `python tools/validate_squareline_project.py` 输出 `OK - project validated`
- [x] `python tools/preview_from_project.py` 9 屏全部反渲染
- [x] 无位图缺失、字体三件套齐全
- [x] 圆形屏可见元素全部落安全区（r≤216）
- [x] `eval/run_regression.py` 全绿（本工程为基准答案）
