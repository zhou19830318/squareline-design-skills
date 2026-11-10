# Panda AI Pendant UI 需求清单

## 1. 基本信息

- 产品：AI 熊猫挂坠（语音交互 + 情绪陪伴）　来源：需求规格说明书 V2.0 + 两张设计板
- 面板：**360×360 圆形**（微雪 1.85" 触摸屏，UI 画布）；ESP32-S3；LVGL 9；资源在 SD 卡
- 视觉：**只显示熊猫脸部，白色毛发铺满整张 360×360 屏幕并与白色外壳浑然一体**（无黑边/耳朵/头部轮廓/身体/手/边框/表盘/边缘光效）；默认无状态栏
- 交付：SquareLine 工程（.spj）+ 预览图 + 规格文档

## 2. 屏幕清单与切换逻辑（37 屏）

| 类别 | 屏 |
|---|---|
| 脸部状态 | `home`、`wakeup`、`listening`、`thinking`、`speaking`、`asr_failed`、`llm_error`、`tts_error`、`network_lost`、`reconnecting`、`battery_low` |
| 情绪帧 | `face_happy`、`face_laugh`、`face_excited`、`face_curious`、`face_surprised`、`face_shy`、`face_sad`、`face_confused`、`face_angry`、`face_love`、`face_sleepy`、`face_sleep`、`face_confident`、`face_cried` |
| 辅助页 | `time_weather`、`notification`、`quick_settings`、`personality`、`sleep_settings`、`system_settings`、`system_info`、`character_preview_1`、`character_preview_2`、`state_preview`、`expression_manager`、`animation_manager` |

首页手势：单击→聆听；上滑→通知；下滑→快捷设置；左滑→时间天气；右滑→个性化；双击→开心；长按→持续聆听（双击/长按在 C 层，见规格文档 §4.1）。
返回：时间天气右滑；个性化左滑；通知右滑；快捷设置上滑；其余设置页右滑。

## 3. 每块屏上有什么
见《设计规格文档》§3（逐屏对象表）。要点：
- 脸部状态屏 = 全屏脸部 + 轻量叠加（聆听波形 / 思考光点 / 底部提示条 / 未读角标）
- 时间天气 = 时间 + 日期 + 小脸 + 天气图标与温度
- 设置类 = 深色卡片/芯片/开关/滑块，圆屏安全区内排布

## 4. 交互与动画效果
- 页面切换：150 ms 淡入；脸部动画为 SD 卡帧序列（运行时）；工程内仅有光点/光晕的透明度循环
- 语音状态由业务事件驱动，工程内点击仅用于设计期演示

## 5. 文案与语言
简体中文 + 数字。完整文案与备用词见规格文档 §6.1。

## 6. 资产需求
脸部帧 19 张（设计板裁切占位）+ 小脸/缩略图/光晕；Lucide 线性图标 19 枚。详见规格文档 §7。

## 7. 字体
Noto Sans SC：时间 Big60（700，数字）、标题 Title22（500）、正文 Body18、次要 Small16。

## 8. 验收偏好
对照需求书 §11（规格文档 §8）；位置/比例以设计板为准。

## 9. 迭代记录
| # | 日期 | 用户原话 | 状态 | 改动章节 |
|---|---|---|---|---|
| 1 | 2026-11-07 | 「根据这个需求设计我的AI熊猫挂坠的UI工程文件」 | 首版 | 全部 |

### 待用户确认的假设
1. 错误→表情映射（规格文档 R8）；2. 脸部帧为占位，生产帧走 3D 管线；3. "思考"帧需重做（板上带手）；4. 双击/长按在 C 层实现；5. 脸部屏白毛满屏后，深色功能页是否改成壳白底（R9）。
