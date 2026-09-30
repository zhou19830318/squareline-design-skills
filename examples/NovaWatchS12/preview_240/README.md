# NovaWatchS12 · 240×240 圆形表盘 UI 图片

仿 Apple Watch Series 12 设计语言的 **240×240 圆形屏**全屏 UI 渲染图（深色主题，圆外透明）。
由 `tools/render_240_watch.py` 生成，源真相为 `UI需求清单.md` + `NovaWatchS12.spec.json`。

## 文件

| 文件 | 内容 |
| --- | --- |
| `overview_240.png` | 10 屏总览（1080×712） |
| `variants_states.png` | 状态变体：voice 三态 / workout 进行中 / 闹钟开关两态 |
| `01_watchface.png` | 表盘：刻度圈 + 三针 10:09:30 + 数字时间 + 日期 + 心率/温度/电量 complication |
| `02_apps.png` | 径向应用网格：8 图标 @ r=80 + Nova 星徽标 |
| `03_health.png` | 三活动环（红 68% / 绿 45% / 蓝 80%）+ 8642 步 + 心率·卡路里 |
| `04_weather.png` | 24° 大字 + 晴 + 4 列逐时（现在/15时/16时/20时） |
| `05_alarms.png` | 3 行闹钟卡（06:30 工作日 / 07:30 每天 / 22:30 就寝）+ 开关 |
| `06_workout.png` | 户外跑步启动页 + 绿色「开始」 |
| `07_stopwatch.png` | 秒表：刻度表圈 + 00:00.00 + 开始/重置 |
| `08_breathe.png` | 呼吸圆环（蓝，内柔光）+ 跟随圆环 / 吸气·呼气 |
| `09_voice.png` | AI 语音待机：麦克风按钮 + 波形 + 点击说话 |
| `10_settings.png` | 设置：蓝牙 已连接 / 电量 82% + 右滑返回 |

## 从 456 → 240 的版式适配

- **等比基准** `s = 240/456 = 0.526`；几何按比例缩放，**文字不按比例**（否则
  Small16 会变成 8.4px 不可读），最小字号抬到 10px，形成 10 / 11.5 / 13 / 15 / 18 / 32 / 38 / 40 的字号阶梯。
- **安全区** `r ≤ 112`（= spec 的 216 @456），脚本内置四角距离自检，本次输出
  `warnings=0`。240 圆下底部可写宽度仅约 100px，故：闹钟行宽 148、按钮成对并排放
  在 y=166~200、健康屏两行小卡合并为一行混排文字。
- 数字时间放在圆心上方 y=56，指针长度收到 29.5/41 以免压到日期行（原 456 版指针更长）。
- 配色、文案、屏幕清单、切换逻辑与 spec 完全一致。

## 渲染管线

4× 超采样（960×960）矢量绘制 + 文字 → LANCZOS 降采样到 240 → 与圆形蒙版**相乘**
（`ImageChops.multiply`，不能用 `putalpha`，否则元素自身透明度会被覆盖成不透明）。

## 注意：源位图资产有缺陷

`assets/images/` 中的 Lucide 位图把**只描边（stroke-only）**的图形栅格化成了实心填充，
导致以下图标不可用，本渲染器已改用自绘矢量（`Pen`，24×24 viewBox，2px 描边）：

| 资产 | 症状 | 现在 |
| --- | --- | --- |
| `img_app_alarms.png` | 实心白圆（指针/铃铛丢失） | 自绘闹钟矢量 |
| `img_app_stopwatch.png` | 实心白圆 | 自绘秒表矢量 |
| `img_app_settings.png` | 花瓣状团块（齿轮齿丢失） | 自绘齿轮矢量 |
| `img_weather_now.png` | 只有一个小圆点（太阳光芒丢失） | 自绘太阳矢量 |
| `img_weather_h3.png` | 云朵无雨滴 | 自绘云+雨滴矢量 |
| `img_comp_batt.png` | 无电极凸起 | 自绘电池矢量 |

其余资产（heart / footprints / mic / flower-2 / cloud / moon / thermometer / wave 三态 /
nova 星）正常，直接复用。**若 SquareLine 工程也要用，需先修 `assets.manifest.json` 的位图生成器。**

## 重新生成

```bash
python tools/render_240_watch.py    # → preview_240/
```
