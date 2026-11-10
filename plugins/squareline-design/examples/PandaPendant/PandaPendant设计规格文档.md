# Panda AI Pendant UI 设计规格文档（PandaPendant 工程）

> 本文档是 `PandaPendant.spec.json` 的**源真相**：先改本文档，再重新生成/构建。§3–§5、§7 的表格由 `scripts/gen_docs.py` 从 spec 自动生成。

来源：`concept/Panda_AI_Pendant_UI_需求规格说明书_V2_0.md`（需求）＋ `concept/board_face_ui_20.png`（20 表情）＋ `concept/board_emotion_pages.png`（功能页/状态机概念）。

## 1. 设备与画布

- 面板：微雪 1.85" 圆形触摸屏，**UI 画布 360×360 px，圆形**（圆心 (180,180)，r=180）；LVGL 9.2.2；SquareLine Studio 1.6.2；深色主题 `[来源：需求书 §2]`
- 坐标：屏幕绝对坐标，左上角原点。实际 LCD 驱动分辨率/有效区域以最终硬件为准（需求书 §2 说明）
- 混合方案：**脸部 = 全屏 `face` 图片对象**（运行时由 SD 卡帧序列替换，RGB565、12–15 FPS）＋ **叠加层 = 真 LVGL 对象**（波形、光点、提示条、文字、开关）。不做不可交互的全屏静态页（需求书附录 A-5）
- 视觉硬约束（需求书 §3.1 + 产品补充）：**熊猫脸部的白色毛发铺满整张 360×360 屏幕，与白色外壳浑然一体**——屏幕边缘不得出现黑底、头部轮廓、耳朵、深色边或任何环形装饰；无身体/手；默认无状态栏。脸部屏背景色 `SHELL`，脸部帧边缘向壳白连续过渡

### 1.1 调色板

| 键 | 色值 | 用途 | 来源 |
|---|---|---|---|
| BG | #000000 | 深色功能页背景（设置/列表） | 测得 |
| SHELL | #F7F5F9 | 脸部屏背景（毛发白，与白色外壳融合） | 估算 |
| CARD | #0F1729 | 卡片/列表行（概念板深蓝灰面板） | 测得 |
| CARD2 | #1B2538 | 按钮/开关关闭态/未选中芯片 | 估算 |
| TRACK | #24304A | 滑块轨道 | 估算 |
| WHITE | #FFFFFF | 主文字 | — |
| DIM | #8E9AB5 | 次要文字 | 估算 |
| CYAN | #40CAFB | 科技强调色（光点、滑块） | 测得 |
| WAVE | #15C7FD | 聆听波形 | 测得 |
| BLUE2 | #1F7AE0 | 开关/选中态填充 | 估算 |
| GREEN | #31DA38 | 已就绪/成功 | 测得 |
| AMBER | #FFB020 | 警告/错误提示图标 | 估算 |
| RED | #F85C7A | 未读角标 | 测得 |
| PILL | #000000B3 | 提示条半透明黑底 | 设计值 |

语音状态色（概念板状态机，供运行时着色参考，工程内未直接使用）：待机 `#9CD1FD` / 唤醒 `#88C33E` / 聆听 `#31DA38` / 思考 `#8E9AFC` / 回复 `#D081F8`  `[测得]`

## 2. 屏幕清单（37 屏）

| # | 屏 | 类别 | 脸部帧 | 说明 |
|---|---|---|---|---|
| 1 | `home` | 脸部状态 | idle | Idle / default home. Hosts all home gestures. Hidden unread badge (UI_EVT_NOTIFICATION). |
| 2 | `wakeup` | 脸部状态 | idle | Wakeup: eyes open (runtime frame sequence). Hand-over to listening is event-driven (tap = demo). |
| 3 | `listening` | 脸部状态 | listen | Listening: focused face + volume waveform (bars resized/opacity by audio level). |
| 4 | `thinking` | 脸部状态 | curious | Thinking: face + 3 pulsing cyan dots on the forehead. |
| 5 | `speaking` | 脸部状态 | speak | Speaking: mouth frames follow TTS (runtime); tap = interrupt. |
| 6 | `asr_failed` | 脸部状态 | confused | ASR failed: confused face + 没听清; tap = retry. |
| 7 | `llm_error` | 脸部状态 | confused | LLM request failed: confused face + 暂时无法回答; tap = retry. |
| 8 | `tts_error` | 脸部状态 | sad | TTS playback failed: mouth stopped (sad frame) + 播放失败; tap = back to idle. |
| 9 | `network_lost` | 脸部状态 | abnormal | Network lost: worried face + 网络已断开. |
| 10 | `reconnecting` | 脸部状态 | curious | Reconnecting: expectant face + 重新连接中 prompt. |
| 11 | `battery_low` | 脸部状态 | tired | Low battery: tired face + 电量低 15% (reduce animation FPS in runtime). |
| 12 | `face_happy` | 情绪帧 | happy | Happy emotion frame. Tap = home; swipe right = character preview. |
| 13 | `face_laugh` | 情绪帧 | laugh | Laugh emotion frame. Tap = home; swipe right = character preview. |
| 14 | `face_excited` | 情绪帧 | celebrate | Excited emotion frame. Tap = home; swipe right = character preview. |
| 15 | `face_curious` | 情绪帧 | curious | Curious emotion frame. Tap = home; swipe right = character preview. |
| 16 | `face_surprised` | 情绪帧 | surprised | Surprised emotion frame. Tap = home; swipe right = character preview. |
| 17 | `face_shy` | 情绪帧 | shy | Shy emotion frame. Tap = home; swipe right = character preview. |
| 18 | `face_sad` | 情绪帧 | sad | Sad emotion frame. Tap = home; swipe right = character preview. |
| 19 | `face_confused` | 情绪帧 | confused | Confused emotion frame. Tap = home; swipe right = character preview. |
| 20 | `face_angry` | 情绪帧 | angry | Angry emotion frame. Tap = home; swipe right = character preview. |
| 21 | `face_love` | 情绪帧 | love | Love emotion frame. Tap = home; swipe right = character preview. |
| 22 | `face_sleepy` | 情绪帧 | sleepy | Sleepy emotion frame. Tap = home; swipe right = character preview. |
| 23 | `face_sleep` | 情绪帧 | sleep | Sleep emotion frame. Tap = home; swipe right = character preview. |
| 24 | `face_confident` | 情绪帧 | confident | Confident (board only) emotion frame. Tap = home; swipe right = character preview. |
| 25 | `face_cried` | 情绪帧 | cried | Cried (board only) emotion frame. Tap = home; swipe right = character preview. |
| 26 | `time_weather` | 辅助页 | idle | Time, date, weather. Face stays small and un-covered. Swipe right = home. |
| 27 | `notification` | 辅助页 | — | Notification list: source, title, short body. Vertical scroll in runtime; swipe right = home. |
| 28 | `quick_settings` | 辅助页 | — | Quick settings: Wi-Fi/BT/DND toggles, brightness+volume -> system settings, sleep. Swipe up = home. |
| 29 | `personality` | 辅助页 | — | Personality: character, feedback strength, animation activity. Swipe left = home. |
| 30 | `sleep_settings` | 辅助页 | — | Sleep settings: auto-sleep timeout, wake method, sleep animation. Swipe right = personality. |
| 31 | `system_settings` | 辅助页 | — | System settings: brightness, volume, network, time sync. Swipe right = quick settings. |
| 32 | `system_info` | 辅助页 | — | Storage + version, entry points to dev/preview pages. Swipe right = system settings. |
| 33 | `character_preview_1` | 辅助页 | — | Character preview page 1/3: tap a thumbnail to open that expression. Swipe left/right = page. |
| 34 | `character_preview_2` | 辅助页 | — | Character preview page 2/3: tap a thumbnail to open that expression. Swipe left/right = page. |
| 35 | `state_preview` | 辅助页 | — | State preview page 3/3: jump to every voice/error state (they are event-driven on device). Swipe right = page 2. |
| 36 | `expression_manager` | 辅助页 | — | Expression resource list (name, frames, status). Missing resource shows the fallback state. Swipe right = system info. |
| 37 | `animation_manager` | 辅助页 | — | Animation resource list (frames, FPS, load state). Swipe right = system info. |

初始屏：`home`。**不使用 `order` 滑动环**（`order=[home]`），所有导航由 §4 显式事件定义。

## 3. 对象清单（逐屏）

`rect=[x,y,w,h]` 屏幕绝对坐标。对象名在屏内唯一，导出后 C 变量为 `ui_<屏>_<对象>`（运行时按此名取对象）。

### 3.1 屏 `home`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_01_idle.png |
| `badge` | PANEL | [257, 47, 26, 26] | bg RED r13 〔初始隐藏〕 |
| ↳ `badge_n` | LABEL | [257, 51, 26, 22] | 「1」Small16 WHITE |

### 3.2 屏 `wakeup`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_01_idle.png |

### 3.3 屏 `listening`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_07_listen.png |
| `wave_1` | PANEL | [133, 317, 6, 10] | bg WAVE r3 |
| `wave_2` | PANEL | [144, 313, 6, 18] | bg WAVE r3 |
| `wave_3` | PANEL | [155, 308, 6, 28] | bg WAVE r3 |
| `wave_4` | PANEL | [166, 314, 6, 16] | bg WAVE r3 |
| `wave_5` | PANEL | [177, 305, 6, 34] | bg WAVE r3 |
| `wave_6` | PANEL | [188, 312, 6, 20] | bg WAVE r3 |
| `wave_7` | PANEL | [199, 307, 6, 30] | bg WAVE r3 |
| `wave_8` | PANEL | [210, 315, 6, 14] | bg WAVE r3 |
| `wave_9` | PANEL | [221, 318, 6, 8] | bg WAVE r3 |

### 3.4 屏 `thinking`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_03_curious.png |
| `dot_1` | PANEL | [144, 34, 12, 12] | bg CYAN r6 |
| `dot_2` | PANEL | [174, 34, 12, 12] | bg CYAN r6 |
| `dot_3` | PANEL | [204, 34, 12, 12] | bg CYAN r6 |

### 3.5 屏 `speaking`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_08_speak.png |

### 3.6 屏 `asr_failed`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_12_confused.png |
| `tip` | PANEL | [95, 298, 170, 34] | bg PILL r17 |
| ↳ `tip_icon` | IMAGE | [109, 307, 16, 16] | icon_mic_off.png |
| ↳ `tip_text` | LABEL | [130, 306, 120, 22] | 「没听清」Small16 WHITE |

### 3.7 屏 `llm_error`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_12_confused.png |
| `tip` | PANEL | [95, 298, 170, 34] | bg PILL r17 |
| ↳ `tip_icon` | IMAGE | [109, 307, 16, 16] | icon_cloud_off.png |
| ↳ `tip_text` | LABEL | [130, 306, 120, 22] | 「暂时无法回答」Small16 WHITE |

### 3.8 屏 `tts_error`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_11_sad.png |
| `tip` | PANEL | [95, 298, 170, 34] | bg PILL r17 |
| ↳ `tip_icon` | IMAGE | [109, 307, 16, 16] | icon_volume_x.png |
| ↳ `tip_text` | LABEL | [130, 306, 120, 22] | 「播放失败」Small16 WHITE |

### 3.9 屏 `network_lost`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_19_abnormal.png |
| `tip` | PANEL | [95, 298, 170, 34] | bg PILL r17 |
| ↳ `tip_icon` | IMAGE | [109, 307, 16, 16] | icon_wifi_off.png |
| ↳ `tip_text` | LABEL | [130, 306, 120, 22] | 「网络已断开」Small16 WHITE |

### 3.10 屏 `reconnecting`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_03_curious.png |
| `tip` | PANEL | [95, 298, 170, 34] | bg PILL r17 |
| ↳ `tip_icon` | IMAGE | [109, 307, 16, 16] | icon_refresh_cw.png |
| ↳ `tip_text` | LABEL | [130, 306, 120, 22] | 「重新连接中」Small16 WHITE |

### 3.11 屏 `battery_low`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_18_tired.png |
| `tip` | PANEL | [95, 298, 170, 34] | bg PILL r17 |
| ↳ `tip_icon` | IMAGE | [109, 307, 16, 16] | icon_battery_low.png |
| ↳ `tip_text` | LABEL | [130, 306, 120, 22] | 「电量低 15%」Small16 WHITE |

### 3.12 屏 `face_happy`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_02_happy_wink.png |

### 3.13 屏 `face_laugh`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_05_laugh.png |

### 3.14 屏 `face_excited`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_20_celebrate.png |

### 3.15 屏 `face_curious`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_03_curious.png |

### 3.16 屏 `face_surprised`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_04_surprised.png |

### 3.17 屏 `face_shy`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_14_shy.png |

### 3.18 屏 `face_sad`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_11_sad.png |

### 3.19 屏 `face_confused`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_12_confused.png |

### 3.20 屏 `face_angry`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_13_angry.png |

### 3.21 屏 `face_love`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_17_love.png |

### 3.22 屏 `face_sleepy`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_09_sleepy.png |

### 3.23 屏 `face_sleep`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_10_sleep.png |

### 3.24 屏 `face_confident`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_15_confident.png |

### 3.25 屏 `face_cried`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `face` | IMAGE | [0, 0, 360, 360] | face_16_cried.png |

### 3.26 屏 `time_weather`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `clock` | LABEL | [95, 46, 170, 81] | 「14:30」Big60 WHITE |
| `date` | LABEL | [80, 109, 200, 25] | 「11月7日 周五」Body18 DIM |
| `face_mini` | IMAGE | [95, 137, 170, 170] | face_mini_idle.png |
| `wx_icon` | IMAGE | [143, 312, 24, 24] | icon_cloud_sun.png |
| `wx_temp` | LABEL | [173, 314, 60, 25] | 「26°C」Body18 WHITE |

### 3.27 屏 `notification`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 23, 160, 30] | 「通知」Title22 WHITE |
| `n1` | PANEL | [58, 62, 244, 82] | bg CARD r18 |
| ↳ `n1_ic` | IMAGE | [72, 74, 20, 20] | icon_message_circle.png |
| ↳ `n1_src` | LABEL | [98, 75, 90, 22] | 「消息」Small16 DIM |
| ↳ `n1_time` | LABEL | [232, 75, 60, 22] | 「14:28」Small16 DIM |
| ↳ `n1_title` | LABEL | [72, 99, 216, 25] | 「小李」Body18 WHITE |
| ↳ `n1_body` | LABEL | [72, 121, 216, 22] | 「晚上一起吃饭吗？」Small16 DIM |
| `n2` | PANEL | [58, 152, 244, 82] | bg CARD r18 |
| ↳ `n2_ic` | IMAGE | [72, 164, 20, 20] | icon_calendar.png |
| ↳ `n2_src` | LABEL | [98, 165, 90, 22] | 「日程」Small16 DIM |
| ↳ `n2_time` | LABEL | [232, 165, 60, 22] | 「14:00」Small16 DIM |
| ↳ `n2_title` | LABEL | [72, 189, 216, 25] | 「团队周会」Body18 WHITE |
| ↳ `n2_body` | LABEL | [72, 211, 216, 22] | 「15:00 · 会议室 B」Small16 DIM |
| `n3` | PANEL | [58, 242, 244, 56] | bg CARD r18 |
| ↳ `n3_ic` | IMAGE | [72, 254, 20, 20] | icon_bell.png |
| ↳ `n3_src` | LABEL | [98, 255, 90, 22] | 「提醒」Small16 DIM |
| ↳ `n3_time` | LABEL | [232, 255, 60, 22] | 「13:45」Small16 DIM |
| ↳ `n3_title` | LABEL | [72, 279, 216, 25] | 「记得喝水」Body18 WHITE |

### 3.28 屏 `quick_settings`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 25, 160, 30] | 「快捷设置」Title22 WHITE |
| `wifi_off` | PANEL | [56, 82, 76, 76] | bg CARD2 r38 可点击 |
| `wifi_on` | PANEL | [56, 82, 76, 76] | bg BLUE2 r38 可点击 |
| `wifi_ic` | IMAGE | [79, 105, 30, 30] | icon_wifi.png |
| `wifi_lbl` | LABEL | [54, 164, 80, 22] | 「Wi-Fi」Small16 WHITE |
| `bt_off` | PANEL | [142, 82, 76, 76] | bg CARD2 r38 可点击 |
| `bt_on` | PANEL | [142, 82, 76, 76] | bg BLUE2 r38 可点击 |
| `bt_ic` | IMAGE | [165, 105, 30, 30] | icon_bluetooth.png |
| `bt_lbl` | LABEL | [140, 165, 80, 22] | 「蓝牙」Small16 WHITE |
| `bright_btn` | PANEL | [228, 82, 76, 76] | bg CARD2 r38 可点击 |
| `bright_ic` | IMAGE | [251, 105, 30, 30] | icon_sun.png |
| `bright_lbl` | LABEL | [226, 165, 80, 22] | 「亮度」Small16 WHITE |
| `vol_btn` | PANEL | [56, 198, 76, 76] | bg CARD2 r38 可点击 |
| `vol_ic` | IMAGE | [79, 221, 30, 30] | icon_volume_2.png |
| `vol_lbl` | LABEL | [54, 281, 80, 22] | 「音量」Small16 WHITE |
| `dnd_off` | PANEL | [142, 198, 76, 76] | bg CARD2 r38 可点击 |
| `dnd_on` | PANEL | [142, 198, 76, 76] | bg BLUE2 r38 〔初始隐藏〕 可点击 |
| `dnd_ic` | IMAGE | [165, 221, 30, 30] | icon_bell_off.png |
| `dnd_lbl` | LABEL | [140, 281, 80, 22] | 「勿扰」Small16 WHITE |
| `sleep_btn` | PANEL | [228, 198, 76, 76] | bg CARD2 r38 可点击 |
| `sleep_ic` | IMAGE | [251, 221, 30, 30] | icon_moon.png |
| `sleep_lbl` | LABEL | [226, 281, 80, 22] | 「睡眠」Small16 WHITE |

### 3.29 屏 `personality`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 23, 160, 30] | 「个性化」Title22 WHITE |
| `pers_lbl` | LABEL | [56, 73, 200, 22] | 「性格」Small16 DIM |
| `pers_0_off` | PANEL | [52, 96, 80, 34] | bg CARD2 r17 可点击 |
| `pers_1_off` | PANEL | [140, 96, 80, 34] | bg CARD2 r17 可点击 |
| `pers_2_off` | PANEL | [228, 96, 80, 34] | bg CARD2 r17 可点击 |
| `pers_0_on` | PANEL | [52, 96, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `pers_1_on` | PANEL | [140, 96, 80, 34] | bg BLUE2 r17 |
| `pers_2_on` | PANEL | [228, 96, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `pers_0_t` | LABEL | [52, 104, 80, 22] | 「活泼」Small16 WHITE |
| `pers_1_t` | LABEL | [140, 104, 80, 22] | 「温柔」Small16 WHITE |
| `pers_2_t` | LABEL | [228, 104, 80, 22] | 「安静」Small16 WHITE |
| `fb_lbl` | LABEL | [56, 145, 200, 22] | 「反馈强度」Small16 DIM |
| `fb_0_off` | PANEL | [52, 168, 80, 34] | bg CARD2 r17 可点击 |
| `fb_1_off` | PANEL | [140, 168, 80, 34] | bg CARD2 r17 可点击 |
| `fb_2_off` | PANEL | [228, 168, 80, 34] | bg CARD2 r17 可点击 |
| `fb_0_on` | PANEL | [52, 168, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `fb_1_on` | PANEL | [140, 168, 80, 34] | bg BLUE2 r17 |
| `fb_2_on` | PANEL | [228, 168, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `fb_0_t` | LABEL | [52, 176, 80, 22] | 「弱」Small16 WHITE |
| `fb_1_t` | LABEL | [140, 176, 80, 22] | 「中」Small16 WHITE |
| `fb_2_t` | LABEL | [228, 176, 80, 22] | 「强」Small16 WHITE |
| `act_lbl` | LABEL | [56, 217, 200, 22] | 「动画活跃度」Small16 DIM |
| `act_0_off` | PANEL | [52, 240, 80, 34] | bg CARD2 r17 可点击 |
| `act_1_off` | PANEL | [140, 240, 80, 34] | bg CARD2 r17 可点击 |
| `act_2_off` | PANEL | [228, 240, 80, 34] | bg CARD2 r17 可点击 |
| `act_0_on` | PANEL | [52, 240, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `act_1_on` | PANEL | [140, 240, 80, 34] | bg BLUE2 r17 |
| `act_2_on` | PANEL | [228, 240, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `act_0_t` | LABEL | [52, 248, 80, 22] | 「低」Small16 WHITE |
| `act_1_t` | LABEL | [140, 248, 80, 22] | 「中」Small16 WHITE |
| `act_2_t` | LABEL | [228, 248, 80, 22] | 「高」Small16 WHITE |
| `link_sleep` | PANEL | [110, 292, 140, 32] | bg CARD2 r16 可点击 |
| ↳ `link_sleep_t` | LABEL | [124, 299, 96, 22] | 「睡眠设置」Small16 WHITE |
| ↳ `link_sleep_i` | IMAGE | [222, 300, 16, 16] | icon_chevron_right.png |

### 3.30 屏 `sleep_settings`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 23, 160, 30] | 「睡眠设置」Title22 WHITE |
| `auto_lbl` | LABEL | [51, 73, 200, 22] | 「自动休眠」Small16 DIM |
| `auto_0_off` | PANEL | [47, 96, 62, 34] | bg CARD2 r17 可点击 |
| `auto_1_off` | PANEL | [115, 96, 62, 34] | bg CARD2 r17 可点击 |
| `auto_2_off` | PANEL | [183, 96, 62, 34] | bg CARD2 r17 可点击 |
| `auto_3_off` | PANEL | [251, 96, 62, 34] | bg CARD2 r17 可点击 |
| `auto_0_on` | PANEL | [47, 96, 62, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `auto_1_on` | PANEL | [115, 96, 62, 34] | bg BLUE2 r17 |
| `auto_2_on` | PANEL | [183, 96, 62, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `auto_3_on` | PANEL | [251, 96, 62, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `auto_0_t` | LABEL | [47, 104, 62, 22] | 「1分钟」Small16 WHITE |
| `auto_1_t` | LABEL | [115, 104, 62, 22] | 「5分钟」Small16 WHITE |
| `auto_2_t` | LABEL | [183, 104, 62, 22] | 「10分钟」Small16 WHITE |
| `auto_3_t` | LABEL | [251, 104, 62, 22] | 「从不」Small16 WHITE |
| `wake_lbl` | LABEL | [56, 145, 200, 22] | 「唤醒方式」Small16 DIM |
| `wake_0_off` | PANEL | [52, 168, 80, 34] | bg CARD2 r17 可点击 |
| `wake_1_off` | PANEL | [140, 168, 80, 34] | bg CARD2 r17 可点击 |
| `wake_2_off` | PANEL | [228, 168, 80, 34] | bg CARD2 r17 可点击 |
| `wake_0_on` | PANEL | [52, 168, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `wake_1_on` | PANEL | [140, 168, 80, 34] | bg BLUE2 r17 〔初始隐藏〕 |
| `wake_2_on` | PANEL | [228, 168, 80, 34] | bg BLUE2 r17 |
| `wake_0_t` | LABEL | [52, 176, 80, 22] | 「触摸」Small16 WHITE |
| `wake_1_t` | LABEL | [140, 176, 80, 22] | 「语音」Small16 WHITE |
| `wake_2_t` | LABEL | [228, 176, 80, 22] | 「都可以」Small16 WHITE |
| `anim_lbl` | LABEL | [64, 249, 120, 25] | 「睡眠动画」Body18 WHITE |
| `sw_anim_off` | PANEL | [226, 244, 52, 28] | bg CARD2 r14 可点击 |
| `sw_anim_knob_off` | PANEL | [229, 247, 22, 22] | bg WHITE r11 |
| `sw_anim_on` | PANEL | [226, 244, 52, 28] | bg BLUE2 r14 可点击 |
| `sw_anim_knob_on` | PANEL | [253, 247, 22, 22] | bg WHITE r11 |

### 3.31 屏 `system_settings`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 23, 160, 30] | 「系统设置」Title22 WHITE |
| `bri_k` | LABEL | [62, 75, 110, 25] | 「亮度」Body18 WHITE |
| `bri_v` | LABEL | [168, 75, 130, 22] | 「80%」Small16 DIM |
| `bri_s_track` | PANEL | [62, 104, 236, 8] | bg TRACK r4 |
| `bri_s_fill` | PANEL | [62, 104, 189, 8] | bg CYAN r4 |
| `bri_s_knob` | PANEL | [242, 99, 18, 18] | bg WHITE r9 |
| `volm_k` | LABEL | [62, 133, 110, 25] | 「音量」Body18 WHITE |
| `volm_v` | LABEL | [168, 133, 130, 22] | 「60%」Small16 DIM |
| `volm_s_track` | PANEL | [62, 162, 236, 8] | bg TRACK r4 |
| `volm_s_fill` | PANEL | [62, 162, 142, 8] | bg CYAN r4 |
| `volm_s_knob` | PANEL | [195, 157, 18, 18] | bg WHITE r9 |
| `net_k` | LABEL | [62, 195, 110, 25] | 「网络」Body18 WHITE |
| `net_v` | LABEL | [168, 195, 130, 22] | 「Wi-Fi 已连接」Small16 DIM |
| `tsync_k` | LABEL | [62, 231, 110, 25] | 「时间同步」Body18 WHITE |
| `tsync_v` | LABEL | [168, 231, 130, 22] | 「自动」Small16 DIM |
| `link_info` | PANEL | [100, 280, 160, 32] | bg CARD2 r16 可点击 |
| ↳ `link_info_t` | LABEL | [114, 287, 116, 22] | 「存储与版本」Small16 WHITE |
| ↳ `link_info_i` | IMAGE | [232, 288, 16, 16] | icon_chevron_right.png |

### 3.32 屏 `system_info`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 23, 160, 30] | 「存储与版本」Title22 WHITE |
| `sd_k` | LABEL | [62, 75, 110, 25] | 「SD 卡」Body18 WHITE |
| `sd_v` | LABEL | [148, 75, 150, 22] | 「12.3 / 29.8 GB」Small16 DIM |
| `sd_s_track` | PANEL | [62, 104, 236, 8] | bg TRACK r4 |
| `sd_s_fill` | PANEL | [62, 104, 97, 8] | bg CYAN r4 |
| `ver_k` | LABEL | [62, 133, 110, 25] | 「版本」Body18 WHITE |
| `ver_v` | LABEL | [168, 133, 130, 22] | 「v2.0.0」Small16 DIM |
| `link_prev` | PANEL | [86, 176, 188, 36] | bg CARD2 r18 可点击 |
| ↳ `link_prev_t` | LABEL | [100, 185, 144, 22] | 「角色预览」Small16 WHITE |
| ↳ `link_prev_i` | IMAGE | [246, 186, 16, 16] | icon_chevron_right.png |
| `link_exp` | PANEL | [86, 218, 188, 36] | bg CARD2 r18 可点击 |
| ↳ `link_exp_t` | LABEL | [100, 227, 144, 22] | 「表情管理」Small16 WHITE |
| ↳ `link_exp_i` | IMAGE | [246, 228, 16, 16] | icon_chevron_right.png |
| `link_anim` | PANEL | [86, 260, 188, 36] | bg CARD2 r18 可点击 |
| ↳ `link_anim_t` | LABEL | [100, 269, 144, 22] | 「动画管理」Small16 WHITE |
| ↳ `link_anim_i` | IMAGE | [246, 270, 16, 16] | icon_chevron_right.png |

### 3.33 屏 `character_preview_1`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 25, 160, 30] | 「角色预览」Title22 WHITE |
| `th_01` | IMAGE | [82, 66, 60, 60] | thumb_01_idle.png |
| `th_02` | IMAGE | [150, 66, 60, 60] | thumb_02_happy_wink.png |
| `th_03` | IMAGE | [218, 66, 60, 60] | thumb_03_curious.png |
| `th_04` | IMAGE | [48, 134, 60, 60] | thumb_04_surprised.png |
| `th_05` | IMAGE | [116, 134, 60, 60] | thumb_05_laugh.png |
| `th_06` | IMAGE | [184, 134, 60, 60] | thumb_07_listen.png |
| `th_07` | IMAGE | [252, 134, 60, 60] | thumb_08_speak.png |
| `th_08` | IMAGE | [82, 202, 60, 60] | thumb_09_sleepy.png |
| `th_09` | IMAGE | [150, 202, 60, 60] | thumb_10_sleep.png |
| `th_10` | IMAGE | [218, 202, 60, 60] | thumb_11_sad.png |
| `page` | LABEL | [140, 287, 80, 22] | 「1 / 3」Small16 DIM |

### 3.34 屏 `character_preview_2`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 25, 160, 30] | 「角色预览」Title22 WHITE |
| `th_01` | IMAGE | [82, 66, 60, 60] | thumb_12_confused.png |
| `th_02` | IMAGE | [150, 66, 60, 60] | thumb_13_angry.png |
| `th_03` | IMAGE | [218, 66, 60, 60] | thumb_14_shy.png |
| `th_04` | IMAGE | [48, 134, 60, 60] | thumb_15_confident.png |
| `th_05` | IMAGE | [116, 134, 60, 60] | thumb_16_cried.png |
| `th_06` | IMAGE | [184, 134, 60, 60] | thumb_17_love.png |
| `th_07` | IMAGE | [252, 134, 60, 60] | thumb_18_tired.png |
| `th_08` | IMAGE | [82, 202, 60, 60] | thumb_19_abnormal.png |
| `th_09` | IMAGE | [150, 202, 60, 60] | thumb_20_celebrate.png |
| `page` | LABEL | [140, 287, 80, 22] | 「2 / 3」Small16 DIM |

### 3.35 屏 `state_preview`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 25, 160, 30] | 「状态预览」Title22 WHITE |
| `st_1` | PANEL | [66, 70, 108, 32] | bg CARD2 r16 可点击 |
| `st_1_t` | LABEL | [66, 77, 108, 22] | 「唤醒」Small16 WHITE |
| `st_2` | PANEL | [186, 70, 108, 32] | bg CARD2 r16 可点击 |
| `st_2_t` | LABEL | [186, 77, 108, 22] | 「聆听」Small16 WHITE |
| `st_3` | PANEL | [66, 112, 108, 32] | bg CARD2 r16 可点击 |
| `st_3_t` | LABEL | [66, 119, 108, 22] | 「思考」Small16 WHITE |
| `st_4` | PANEL | [186, 112, 108, 32] | bg CARD2 r16 可点击 |
| `st_4_t` | LABEL | [186, 119, 108, 22] | 「说话」Small16 WHITE |
| `st_5` | PANEL | [66, 154, 108, 32] | bg CARD2 r16 可点击 |
| `st_5_t` | LABEL | [66, 161, 108, 22] | 「没听清」Small16 WHITE |
| `st_6` | PANEL | [186, 154, 108, 32] | bg CARD2 r16 可点击 |
| `st_6_t` | LABEL | [186, 161, 108, 22] | 「无法回答」Small16 WHITE |
| `st_7` | PANEL | [66, 196, 108, 32] | bg CARD2 r16 可点击 |
| `st_7_t` | LABEL | [66, 203, 108, 22] | 「播放失败」Small16 WHITE |
| `st_8` | PANEL | [186, 196, 108, 32] | bg CARD2 r16 可点击 |
| `st_8_t` | LABEL | [186, 203, 108, 22] | 「网络断开」Small16 WHITE |
| `st_9` | PANEL | [66, 238, 108, 32] | bg CARD2 r16 可点击 |
| `st_9_t` | LABEL | [66, 245, 108, 22] | 「重连中」Small16 WHITE |
| `st_10` | PANEL | [186, 238, 108, 32] | bg CARD2 r16 可点击 |
| `st_10_t` | LABEL | [186, 245, 108, 22] | 「低电量」Small16 WHITE |
| `page` | LABEL | [140, 287, 80, 22] | 「3 / 3」Small16 DIM |

### 3.36 屏 `expression_manager`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 21, 160, 30] | 「表情管理」Title22 WHITE |
| `sum` | LABEL | [70, 57, 220, 22] | 「19 个表情 · 已就绪 18」Small16 DIM |
| `r1` | PANEL | [58, 86, 244, 36] | bg CARD r18 |
| ↳ `r1_n` | LABEL | [76, 95, 120, 25] | 「首页陪伴」Body18 WHITE |
| ↳ `r1_m` | LABEL | [190, 95, 70, 22] | 「24 帧」Small16 DIM |
| ↳ `r1_s` | IMAGE | [276, 94, 20, 20] | icon_circle_check.png |
| `r2` | PANEL | [58, 130, 244, 36] | bg CARD r18 |
| ↳ `r2_n` | LABEL | [76, 139, 120, 25] | 「开心」Body18 WHITE |
| ↳ `r2_m` | LABEL | [190, 139, 70, 22] | 「20 帧」Small16 DIM |
| ↳ `r2_s` | IMAGE | [276, 138, 20, 20] | icon_circle_check.png |
| `r3` | PANEL | [58, 174, 244, 36] | bg CARD r18 |
| ↳ `r3_n` | LABEL | [76, 183, 120, 25] | 「好奇」Body18 WHITE |
| ↳ `r3_m` | LABEL | [190, 183, 70, 22] | 「18 帧」Small16 DIM |
| ↳ `r3_s` | IMAGE | [276, 182, 20, 20] | icon_circle_check.png |
| `r4` | PANEL | [58, 218, 244, 36] | bg CARD r18 |
| ↳ `r4_n` | LABEL | [76, 227, 120, 25] | 「聆听」Body18 WHITE |
| ↳ `r4_m` | LABEL | [190, 227, 70, 22] | 「22 帧」Small16 DIM |
| ↳ `r4_s` | IMAGE | [276, 226, 20, 20] | icon_circle_check.png |
| `r5` | PANEL | [58, 262, 244, 36] | bg CARD r18 |
| ↳ `r5_n` | LABEL | [76, 271, 120, 25] | 「疲惫」Body18 WHITE |
| ↳ `r5_m` | LABEL | [190, 271, 70, 22] | 「缺失」Small16 DIM |
| ↳ `r5_s` | IMAGE | [276, 270, 20, 20] | icon_triangle_alert.png |

### 3.37 屏 `animation_manager`

| 对象 | 类型 | rect | 说明 |
|---|---|---|---|
| `title` | LABEL | [100, 21, 160, 30] | 「动画管理」Title22 WHITE |
| `a1` | PANEL | [58, 62, 244, 50] | bg CARD r18 |
| ↳ `a1_n` | LABEL | [76, 66, 150, 25] | 「anim_idle」Body18 WHITE |
| ↳ `a1_s` | LABEL | [222, 68, 70, 22] | 「已加载」Small16 GREEN |
| ↳ `a1_m` | LABEL | [76, 89, 190, 22] | 「24 帧 · 12 FPS」Small16 DIM |
| `a2` | PANEL | [58, 120, 244, 50] | bg CARD r18 |
| ↳ `a2_n` | LABEL | [76, 124, 150, 25] | 「anim_listening」Body18 WHITE |
| ↳ `a2_s` | LABEL | [222, 126, 70, 22] | 「已加载」Small16 GREEN |
| ↳ `a2_m` | LABEL | [76, 147, 190, 22] | 「22 帧 · 15 FPS」Small16 DIM |
| `a3` | PANEL | [58, 178, 244, 50] | bg CARD r18 |
| ↳ `a3_n` | LABEL | [76, 182, 150, 25] | 「anim_speaking」Body18 WHITE |
| ↳ `a3_s` | LABEL | [222, 184, 70, 22] | 「加载中」Small16 CYAN |
| ↳ `a3_m` | LABEL | [76, 205, 190, 22] | 「20 帧 · 15 FPS」Small16 DIM |
| `a4` | PANEL | [58, 236, 244, 50] | bg CARD r18 |
| ↳ `a4_n` | LABEL | [76, 240, 150, 25] | 「anim_sleep」Body18 WHITE |
| ↳ `a4_s` | LABEL | [222, 242, 70, 22] | 「待加载」Small16 DIM |
| ↳ `a4_m` | LABEL | [76, 263, 190, 22] | 「16 帧 · 12 FPS」Small16 DIM |

## 4. 交互定义

工程内接线的事件只用编辑器已验证的集合：`CLICKED / GESTURE_LEFT|RIGHT|UP|DOWN / SCREEN_LOAD_START`。

| 屏 | 触发 | 事件 | 动作 |
|---|---|---|---|
| home | 对象 `face` | CLICKED | → listening |
| home | 对象 `face` | PRESSED | SET_OPACITY |
| home | 对象 `face` | RELEASED | SET_OPACITY |
| home | 屏幕 | GESTURE_DOWN | → quick_settings |
| home | 屏幕 | GESTURE_UP | → notification |
| home | 屏幕 | GESTURE_LEFT | → time_weather |
| home | 屏幕 | GESTURE_RIGHT | → personality |
| wakeup | 对象 `face` | CLICKED | → listening |
| wakeup | 对象 `face` | PRESSED | SET_OPACITY |
| wakeup | 对象 `face` | RELEASED | SET_OPACITY |
| listening | 对象 `face` | CLICKED | → thinking |
| listening | 对象 `face` | PRESSED | SET_OPACITY |
| listening | 对象 `face` | RELEASED | SET_OPACITY |
| listening | 屏幕 | GESTURE_DOWN | → home |
| thinking | 对象 `face` | CLICKED | → speaking |
| thinking | 对象 `face` | PRESSED | SET_OPACITY |
| thinking | 对象 `face` | RELEASED | SET_OPACITY |
| thinking | 屏幕 | SCREEN_LOAD_START | 动画「think dot 1」；动画「think dot 2」；动画「think dot 3」 |
| speaking | 对象 `face` | CLICKED | → home |
| speaking | 对象 `face` | PRESSED | SET_OPACITY |
| speaking | 对象 `face` | RELEASED | SET_OPACITY |
| speaking | 屏幕 | GESTURE_DOWN | → home |
| asr_failed | 对象 `face` | CLICKED | → listening |
| asr_failed | 对象 `face` | PRESSED | SET_OPACITY |
| asr_failed | 对象 `face` | RELEASED | SET_OPACITY |
| llm_error | 对象 `face` | CLICKED | → thinking |
| llm_error | 对象 `face` | PRESSED | SET_OPACITY |
| llm_error | 对象 `face` | RELEASED | SET_OPACITY |
| tts_error | 对象 `face` | CLICKED | → home |
| tts_error | 对象 `face` | PRESSED | SET_OPACITY |
| tts_error | 对象 `face` | RELEASED | SET_OPACITY |
| network_lost | 对象 `face` | CLICKED | → reconnecting |
| network_lost | 对象 `face` | PRESSED | SET_OPACITY |
| network_lost | 对象 `face` | RELEASED | SET_OPACITY |
| reconnecting | 对象 `face` | CLICKED | → home |
| reconnecting | 对象 `face` | PRESSED | SET_OPACITY |
| reconnecting | 对象 `face` | RELEASED | SET_OPACITY |
| battery_low | 对象 `face` | CLICKED | → home |
| battery_low | 对象 `face` | PRESSED | SET_OPACITY |
| battery_low | 对象 `face` | RELEASED | SET_OPACITY |
| face_happy | 对象 `face` | CLICKED | → home |
| face_happy | 对象 `face` | PRESSED | SET_OPACITY |
| face_happy | 对象 `face` | RELEASED | SET_OPACITY |
| face_happy | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_laugh | 对象 `face` | CLICKED | → home |
| face_laugh | 对象 `face` | PRESSED | SET_OPACITY |
| face_laugh | 对象 `face` | RELEASED | SET_OPACITY |
| face_laugh | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_excited | 对象 `face` | CLICKED | → home |
| face_excited | 对象 `face` | PRESSED | SET_OPACITY |
| face_excited | 对象 `face` | RELEASED | SET_OPACITY |
| face_excited | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_curious | 对象 `face` | CLICKED | → home |
| face_curious | 对象 `face` | PRESSED | SET_OPACITY |
| face_curious | 对象 `face` | RELEASED | SET_OPACITY |
| face_curious | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_surprised | 对象 `face` | CLICKED | → home |
| face_surprised | 对象 `face` | PRESSED | SET_OPACITY |
| face_surprised | 对象 `face` | RELEASED | SET_OPACITY |
| face_surprised | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_shy | 对象 `face` | CLICKED | → home |
| face_shy | 对象 `face` | PRESSED | SET_OPACITY |
| face_shy | 对象 `face` | RELEASED | SET_OPACITY |
| face_shy | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_sad | 对象 `face` | CLICKED | → home |
| face_sad | 对象 `face` | PRESSED | SET_OPACITY |
| face_sad | 对象 `face` | RELEASED | SET_OPACITY |
| face_sad | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_confused | 对象 `face` | CLICKED | → home |
| face_confused | 对象 `face` | PRESSED | SET_OPACITY |
| face_confused | 对象 `face` | RELEASED | SET_OPACITY |
| face_confused | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_angry | 对象 `face` | CLICKED | → home |
| face_angry | 对象 `face` | PRESSED | SET_OPACITY |
| face_angry | 对象 `face` | RELEASED | SET_OPACITY |
| face_angry | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_love | 对象 `face` | CLICKED | → home |
| face_love | 对象 `face` | PRESSED | SET_OPACITY |
| face_love | 对象 `face` | RELEASED | SET_OPACITY |
| face_love | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_sleepy | 对象 `face` | CLICKED | → home |
| face_sleepy | 对象 `face` | PRESSED | SET_OPACITY |
| face_sleepy | 对象 `face` | RELEASED | SET_OPACITY |
| face_sleepy | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_sleep | 对象 `face` | CLICKED | → home |
| face_sleep | 对象 `face` | PRESSED | SET_OPACITY |
| face_sleep | 对象 `face` | RELEASED | SET_OPACITY |
| face_sleep | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_confident | 对象 `face` | CLICKED | → home |
| face_confident | 对象 `face` | PRESSED | SET_OPACITY |
| face_confident | 对象 `face` | RELEASED | SET_OPACITY |
| face_confident | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| face_cried | 对象 `face` | CLICKED | → home |
| face_cried | 对象 `face` | PRESSED | SET_OPACITY |
| face_cried | 对象 `face` | RELEASED | SET_OPACITY |
| face_cried | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| time_weather | 屏幕 | GESTURE_RIGHT | → home |
| notification | 屏幕 | GESTURE_RIGHT | → home |
| quick_settings | 对象 `wifi_off` | CLICKED | SHOW wifi_on |
| quick_settings | 对象 `wifi_off` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `wifi_off` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `wifi_on` | CLICKED | HIDE wifi_on |
| quick_settings | 对象 `wifi_on` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `wifi_on` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `bt_off` | CLICKED | SHOW bt_on |
| quick_settings | 对象 `bt_off` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `bt_off` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `bt_on` | CLICKED | HIDE bt_on |
| quick_settings | 对象 `bt_on` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `bt_on` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `bright_btn` | CLICKED | → system_settings |
| quick_settings | 对象 `bright_btn` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `bright_btn` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `vol_btn` | CLICKED | → system_settings |
| quick_settings | 对象 `vol_btn` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `vol_btn` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `dnd_off` | CLICKED | SHOW dnd_on |
| quick_settings | 对象 `dnd_off` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `dnd_off` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `dnd_on` | CLICKED | HIDE dnd_on |
| quick_settings | 对象 `dnd_on` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `dnd_on` | RELEASED | SET_OPACITY |
| quick_settings | 对象 `sleep_btn` | CLICKED | → face_sleep |
| quick_settings | 对象 `sleep_btn` | PRESSED | SET_OPACITY |
| quick_settings | 对象 `sleep_btn` | RELEASED | SET_OPACITY |
| quick_settings | 屏幕 | GESTURE_UP | → home |
| personality | 对象 `pers_0_off` | CLICKED | SHOW pers_0_on；HIDE pers_1_on；HIDE pers_2_on |
| personality | 对象 `pers_0_off` | PRESSED | SET_OPACITY |
| personality | 对象 `pers_0_off` | RELEASED | SET_OPACITY |
| personality | 对象 `pers_1_off` | CLICKED | SHOW pers_1_on；HIDE pers_0_on；HIDE pers_2_on |
| personality | 对象 `pers_1_off` | PRESSED | SET_OPACITY |
| personality | 对象 `pers_1_off` | RELEASED | SET_OPACITY |
| personality | 对象 `pers_2_off` | CLICKED | SHOW pers_2_on；HIDE pers_0_on；HIDE pers_1_on |
| personality | 对象 `pers_2_off` | PRESSED | SET_OPACITY |
| personality | 对象 `pers_2_off` | RELEASED | SET_OPACITY |
| personality | 对象 `fb_0_off` | CLICKED | SHOW fb_0_on；HIDE fb_1_on；HIDE fb_2_on |
| personality | 对象 `fb_0_off` | PRESSED | SET_OPACITY |
| personality | 对象 `fb_0_off` | RELEASED | SET_OPACITY |
| personality | 对象 `fb_1_off` | CLICKED | SHOW fb_1_on；HIDE fb_0_on；HIDE fb_2_on |
| personality | 对象 `fb_1_off` | PRESSED | SET_OPACITY |
| personality | 对象 `fb_1_off` | RELEASED | SET_OPACITY |
| personality | 对象 `fb_2_off` | CLICKED | SHOW fb_2_on；HIDE fb_0_on；HIDE fb_1_on |
| personality | 对象 `fb_2_off` | PRESSED | SET_OPACITY |
| personality | 对象 `fb_2_off` | RELEASED | SET_OPACITY |
| personality | 对象 `act_0_off` | CLICKED | SHOW act_0_on；HIDE act_1_on；HIDE act_2_on |
| personality | 对象 `act_0_off` | PRESSED | SET_OPACITY |
| personality | 对象 `act_0_off` | RELEASED | SET_OPACITY |
| personality | 对象 `act_1_off` | CLICKED | SHOW act_1_on；HIDE act_0_on；HIDE act_2_on |
| personality | 对象 `act_1_off` | PRESSED | SET_OPACITY |
| personality | 对象 `act_1_off` | RELEASED | SET_OPACITY |
| personality | 对象 `act_2_off` | CLICKED | SHOW act_2_on；HIDE act_0_on；HIDE act_1_on |
| personality | 对象 `act_2_off` | PRESSED | SET_OPACITY |
| personality | 对象 `act_2_off` | RELEASED | SET_OPACITY |
| personality | 对象 `link_sleep` | CLICKED | → sleep_settings |
| personality | 对象 `link_sleep` | PRESSED | SET_OPACITY |
| personality | 对象 `link_sleep` | RELEASED | SET_OPACITY |
| personality | 屏幕 | GESTURE_LEFT | → home |
| sleep_settings | 对象 `auto_0_off` | CLICKED | SHOW auto_0_on；HIDE auto_1_on；HIDE auto_2_on；HIDE auto_3_on |
| sleep_settings | 对象 `auto_0_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `auto_0_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `auto_1_off` | CLICKED | SHOW auto_1_on；HIDE auto_0_on；HIDE auto_2_on；HIDE auto_3_on |
| sleep_settings | 对象 `auto_1_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `auto_1_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `auto_2_off` | CLICKED | SHOW auto_2_on；HIDE auto_0_on；HIDE auto_1_on；HIDE auto_3_on |
| sleep_settings | 对象 `auto_2_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `auto_2_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `auto_3_off` | CLICKED | SHOW auto_3_on；HIDE auto_0_on；HIDE auto_1_on；HIDE auto_2_on |
| sleep_settings | 对象 `auto_3_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `auto_3_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `wake_0_off` | CLICKED | SHOW wake_0_on；HIDE wake_1_on；HIDE wake_2_on |
| sleep_settings | 对象 `wake_0_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `wake_0_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `wake_1_off` | CLICKED | SHOW wake_1_on；HIDE wake_0_on；HIDE wake_2_on |
| sleep_settings | 对象 `wake_1_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `wake_1_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `wake_2_off` | CLICKED | SHOW wake_2_on；HIDE wake_0_on；HIDE wake_1_on |
| sleep_settings | 对象 `wake_2_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `wake_2_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `sw_anim_off` | CLICKED | SHOW sw_anim_on；SHOW sw_anim_knob_on |
| sleep_settings | 对象 `sw_anim_off` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `sw_anim_off` | RELEASED | SET_OPACITY |
| sleep_settings | 对象 `sw_anim_on` | CLICKED | HIDE sw_anim_on；HIDE sw_anim_knob_on |
| sleep_settings | 对象 `sw_anim_on` | PRESSED | SET_OPACITY |
| sleep_settings | 对象 `sw_anim_on` | RELEASED | SET_OPACITY |
| sleep_settings | 屏幕 | GESTURE_RIGHT | → personality |
| system_settings | 对象 `link_info` | CLICKED | → system_info |
| system_settings | 对象 `link_info` | PRESSED | SET_OPACITY |
| system_settings | 对象 `link_info` | RELEASED | SET_OPACITY |
| system_settings | 屏幕 | GESTURE_RIGHT | → quick_settings |
| system_info | 对象 `link_prev` | CLICKED | → character_preview_1 |
| system_info | 对象 `link_prev` | PRESSED | SET_OPACITY |
| system_info | 对象 `link_prev` | RELEASED | SET_OPACITY |
| system_info | 对象 `link_exp` | CLICKED | → expression_manager |
| system_info | 对象 `link_exp` | PRESSED | SET_OPACITY |
| system_info | 对象 `link_exp` | RELEASED | SET_OPACITY |
| system_info | 对象 `link_anim` | CLICKED | → animation_manager |
| system_info | 对象 `link_anim` | PRESSED | SET_OPACITY |
| system_info | 对象 `link_anim` | RELEASED | SET_OPACITY |
| system_info | 屏幕 | GESTURE_RIGHT | → system_settings |
| character_preview_1 | 对象 `th_01` | CLICKED | → home |
| character_preview_1 | 对象 `th_01` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_01` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_02` | CLICKED | → face_happy |
| character_preview_1 | 对象 `th_02` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_02` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_03` | CLICKED | → face_curious |
| character_preview_1 | 对象 `th_03` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_03` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_04` | CLICKED | → face_surprised |
| character_preview_1 | 对象 `th_04` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_04` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_05` | CLICKED | → face_laugh |
| character_preview_1 | 对象 `th_05` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_05` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_06` | CLICKED | → listening |
| character_preview_1 | 对象 `th_06` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_06` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_07` | CLICKED | → speaking |
| character_preview_1 | 对象 `th_07` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_07` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_08` | CLICKED | → face_sleepy |
| character_preview_1 | 对象 `th_08` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_08` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_09` | CLICKED | → face_sleep |
| character_preview_1 | 对象 `th_09` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_09` | RELEASED | SET_OPACITY |
| character_preview_1 | 对象 `th_10` | CLICKED | → face_sad |
| character_preview_1 | 对象 `th_10` | PRESSED | SET_OPACITY |
| character_preview_1 | 对象 `th_10` | RELEASED | SET_OPACITY |
| character_preview_1 | 屏幕 | GESTURE_LEFT | → character_preview_2 |
| character_preview_1 | 屏幕 | GESTURE_RIGHT | → system_info |
| character_preview_2 | 对象 `th_01` | CLICKED | → face_confused |
| character_preview_2 | 对象 `th_01` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_01` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_02` | CLICKED | → face_angry |
| character_preview_2 | 对象 `th_02` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_02` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_03` | CLICKED | → face_shy |
| character_preview_2 | 对象 `th_03` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_03` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_04` | CLICKED | → face_confident |
| character_preview_2 | 对象 `th_04` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_04` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_05` | CLICKED | → face_cried |
| character_preview_2 | 对象 `th_05` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_05` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_06` | CLICKED | → face_love |
| character_preview_2 | 对象 `th_06` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_06` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_07` | CLICKED | → battery_low |
| character_preview_2 | 对象 `th_07` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_07` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_08` | CLICKED | → network_lost |
| character_preview_2 | 对象 `th_08` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_08` | RELEASED | SET_OPACITY |
| character_preview_2 | 对象 `th_09` | CLICKED | → face_excited |
| character_preview_2 | 对象 `th_09` | PRESSED | SET_OPACITY |
| character_preview_2 | 对象 `th_09` | RELEASED | SET_OPACITY |
| character_preview_2 | 屏幕 | GESTURE_RIGHT | → character_preview_1 |
| character_preview_2 | 屏幕 | GESTURE_LEFT | → state_preview |
| state_preview | 对象 `st_1` | CLICKED | → wakeup |
| state_preview | 对象 `st_1` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_1` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_2` | CLICKED | → listening |
| state_preview | 对象 `st_2` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_2` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_3` | CLICKED | → thinking |
| state_preview | 对象 `st_3` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_3` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_4` | CLICKED | → speaking |
| state_preview | 对象 `st_4` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_4` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_5` | CLICKED | → asr_failed |
| state_preview | 对象 `st_5` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_5` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_6` | CLICKED | → llm_error |
| state_preview | 对象 `st_6` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_6` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_7` | CLICKED | → tts_error |
| state_preview | 对象 `st_7` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_7` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_8` | CLICKED | → network_lost |
| state_preview | 对象 `st_8` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_8` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_9` | CLICKED | → reconnecting |
| state_preview | 对象 `st_9` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_9` | RELEASED | SET_OPACITY |
| state_preview | 对象 `st_10` | CLICKED | → battery_low |
| state_preview | 对象 `st_10` | PRESSED | SET_OPACITY |
| state_preview | 对象 `st_10` | RELEASED | SET_OPACITY |
| state_preview | 屏幕 | GESTURE_RIGHT | → character_preview_2 |
| expression_manager | 屏幕 | GESTURE_RIGHT | → system_info |
| animation_manager | 屏幕 | GESTURE_RIGHT | → system_info |

### 4.1 需求书手势 ↔ 工程接线

| 需求书手势 | 工程内 | 说明 |
|---|---|---|
| 首页 单击 → 聆听 | ✅ `home/face` CLICKED → `listening` | 演示接线；真实流程由 Voice FSM 事件驱动 |
| 首页 上滑/下滑/左滑/右滑 | ✅ → notification / quick_settings / time_weather / personality | 见 `home` 屏事件 |
| 首页 **双击** → 开心反馈 | ❌ **未接线（引擎限制）** | `DOUBLE_CLICKED` 不在编辑器已验证事件集内；写进去有让 SquareLine 打不开工程的风险。请在 `panda_ui` 中对 `ui_home_face` 注册 `LV_EVENT_DOUBLE_CLICKED` → 播放 `anim_happy`，并处理与单击的去抖 |
| 首页 **长按** → 持续聆听，松开提交 | ❌ **未接线（引擎限制）** | 同上，`LONG_PRESSED` 未验证。用 `LV_EVENT_LONG_PRESSED` + `LV_EVENT_RELEASED` 在 C 层实现 |
| Listening 单击=提交，长按=取消 | ✅ 单击 → thinking；长按 ❌ C 层 | 下滑 → home 作为临时取消手势 |
| Speaking 单击=打断 | ✅ 单击 → home | 真实打断=停止 TTS 后回 Idle |
| Error 单击=重试 | ✅ asr_failed→listening；llm_error→thinking；tts_error→home | |
| Thinking 单击=取消 | 〔可选，工程内单击 → speaking 仅为演示〕 | 取消请求在 C 层实现 |
| 所有触摸有即时视觉反馈（需求 R019） | ✅ 每个可点击对象 `PRESSED → SET_OPACITY 190`、`RELEASED → 255` | `scripts/gen_spec.py` 里 `touch_feedback=190`；真机可在 C 层改成更精致的按压样式 |

**所有状态切换在真机上由业务事件驱动（`UI_EVT_*`），不依赖固定时长**；工程内的"点击进入下一状态"只是让设计师在模拟器里能走通流程。

## 5. 动画

| 名称 | 目标 | 属性 | 周期 | 触发 |
|---|---|---|---|---|
| think dot 1 | `thinking/dot_1` | opacity | 900 ms 循环 | `thinking` SCREEN_LOAD_START |
| think dot 2 | `thinking/dot_2` | opacity | 900 ms 循环 | `thinking` SCREEN_LOAD_START |
| think dot 3 | `thinking/dot_3` | opacity | 1200 ms 循环 | `thinking` SCREEN_LOAD_START |

- 页面切换：`FADE_ON` 150 ms 淡入（需求书 §5.3：轻量淡入，不做复杂转场）
- 脸部帧动画（Idle 呼吸/眨眼/说话口型等）**不在工程里**：由 `panda_animation` 从 SD 卡逐帧读取并替换 `face` 对象的图源
- 聆听波形：`wave_1..9` 为真对象，运行时按音量调整高度/透明度；工程内是静态示意

## 6. 字体

| codename | 字重 | 字号 | kind | 用途 |
|---|---|---|---|---|
| Big60 | 700 | 60 | number | 时间 14:30（仅数字与冒号） |
| Title22 | 500 | 22 | text | 页面标题 |
| Body18 | 400 | 18 | text | 正文/行标题/日期 |
| Small16 | 400 | 16 | text | 次要文字/提示条/标签 |

Noto Sans SC（随包）。设计板的字体无法复刻，只匹配字重与字号。

### 6.1 文案字符集（glyph headroom）★

> 构建时本文档的全部字符会进入字体子集；这里同时列出界面现有文案与将来可能出现的词。

- **界面现有文案**：`1 没听清 暂时无法回答 播放失败 网络已断开 重新连接中 电量低 15% 14:30 11月7日 周五 26°C 通知 消息 14:28 小李 晚上一起吃饭吗？ 日程 14:00 团队周会 15:00 · 会议室 B 提醒 13:45 记得喝水 快捷设置 Wi-Fi 蓝牙 亮度 音量 勿扰 睡眠 个性化 性格 活泼 温柔 安静 反馈强度 弱 中 强 动画活跃度 低 高 睡眠设置 自动休眠 1分钟 5分钟 10分钟 从不 唤醒方式 触摸 语音 都可以 睡眠动画 系统设置 80% 60% 网络 Wi-Fi 已连接 时间同步 自动 存储与版本 SD 卡 12.3 / 29.8 GB 版本 v2.0.0 角色预览 表情管理 动画管理 1 / 3 2 / 3 状态预览 唤醒 聆听 思考 说话 无法回答 网络断开 重连中 低电量 3 / 3 19 个表情 · 已就绪 18 首页陪伴 24 帧 开心 20 帧 好奇 18 帧 22 帧 疲惫 缺失 anim_idle 已加载 24 帧 · 12 FPS anim_listening 22 帧 · 15 FPS anim_speaking 加载中 20 帧 · 15 FPS anim_sleep 待加载 16 帧 · 12 FPS`
- **备用词（headroom）**：`周一 周二 周三 周四 周五 周六 周日 星期 上午 下午 晴 多云 阴 小雨 大雨 雷阵雨 雪 雾 风 没听清 请再说一遍 暂时无法回答 稍后再试 播放失败 网络已断开 网络恢复 已连接 未连接 重新连接中 重试 取消 电量低 正在充电 已充满 请充电 亮度 音量 勿扰 睡眠 蓝牙 开启 关闭 确定 返回 设置 活泼 温柔 安静 活跃 反馈 强度 性格 互动 偏好 通知 消息 日程 提醒 邮件 来电 1分钟 5分钟 10分钟 30分钟 从不 触摸 语音 唤醒 自动休眠 睡眠动画 存储 版本 时间同步 固件 缺失 已加载 加载中 待加载 帧 角色预览 表情管理 动画管理`
- **数字字体 `Big60`** = `symbols[number]`（`0123456789:`）∪ `ranges_num`（`0x30-0x3A`），只含数字和冒号；该字体的 LABEL 里只能出现这些字符（`slx.py check` 会拦 E-GLYPH）

## 7. 资产清单

### 7.1 脸部帧（设计期占位，来自用户设计板）

| 文件 | 尺寸 | 来源 | 备注 |
|---|---|---|---|
| `face_01_idle` … `face_20_celebrate`（19 张，缺 06） | 360×360（**满铺白毛，无黑边**） | `board_face_ui_20.png` 单元 01–20 | ① 以**逐格量出的头部轮廓中心**为中心裁 188 px（不是毛发包围盒——耳根深色会让它偏 8 px）；② 头部椭圆（半轴 104×90，上半 80）以外的黑底/耳根/光晕，用椭圆内侧**毛发白**沿径向延伸填满（只采样毛发白像素，五官/眼泪/爱心不会被拖出）；③ 从 45% 半径起把**亮色像素**连续提亮到壳白（强度 0.92），暗色五官不动，以消除照片与延伸毛发的接缝及 3D 边缘暗部；④ Lanczos 放大约 1.9× + 轻锐化 |
| `face_mini_idle` | 170×170 | 同 01 | 时间天气页小脸（深色页），边缘羽化 |
| `thumb_*`（19 张） | 60×60 | 同上 | 角色预览缩略图 |

> ⚠️ **这些是占位帧，不是生产资源。** 板上单张人脸约 220 px，放大后偏软。生产帧由 3D 管线按需求书 §6 导出 256×256 RGB565 序列放进 SD 卡 `panda/expressions|animations/`，运行时替换 `face` 对象。
> **板上"思考"（06）带手部**，违反需求书 §3.1/§6.1（不得出现手），**已排除**；工程里 `thinking` 暂用 03「好奇」帧，请在 3D 母版里重做不带手的思考帧。

### 7.2 图标（Lucide，ISC 许可，无需署名）

| 文件 | 尺寸 | Lucide 图标 | 色 |
|---|---|---|---|
| `icon_wifi` | 30 | `wifi` | #FFFFFF |
| `icon_bluetooth` | 30 | `bluetooth` | #FFFFFF |
| `icon_sun` | 30 | `sun` | #FFFFFF |
| `icon_volume_2` | 30 | `volume-2` | #FFFFFF |
| `icon_bell_off` | 30 | `bell-off` | #FFFFFF |
| `icon_moon` | 30 | `moon` | #FFFFFF |
| `icon_mic_off` | 16 | `mic-off` | #FFB020 |
| `icon_cloud_off` | 16 | `cloud-off` | #FFB020 |
| `icon_volume_x` | 16 | `volume-x` | #FFB020 |
| `icon_wifi_off` | 16 | `wifi-off` | #FFB020 |
| `icon_refresh_cw` | 16 | `refresh-cw` | #40CAFB |
| `icon_battery_low` | 16 | `battery-low` | #FFB020 |
| `icon_cloud_sun` | 24 | `cloud-sun` | #FFC857 |
| `icon_message_circle` | 20 | `message-circle` | #7BDBFB |
| `icon_calendar` | 20 | `calendar` | #8E9AFC |
| `icon_bell` | 20 | `bell` | #FFB020 |
| `icon_chevron_right` | 16 | `chevron-right` | #8E9AB5 |
| `icon_circle_check` | 20 | `circle-check` | #31DA38 |
| `icon_triangle_alert` | 20 | `triangle-alert` | #FFB020 |

## 7.3 需求追溯

`requirements.json` / `需求追溯矩阵.md`：需求书拆成 73 条带编号的原子需求，**每条都有处置**（完成 / 偏差 / 超出本工程范围 / 信息），其中 8 条带自动验证规则。
**偏差必读**：R006/R050/R067（黑底融合 → 用户后来指定白壳白毛）、R028（占位帧 360×360）、R053（双击/长按在 C 层）等。

## 8. 对照需求书 §11 验收

### 8.1 视觉
- [ ] 屏幕中只出现熊猫脸部 —— 脸部屏均为满铺脸部帧；`time_weather` 的小脸是唯一不铺满屏幕的页（需给时间文字留位，版式取自概念板）
- [ ] **白毛铺满整屏并与白壳融为一体** —— 圆屏最外圈（r∈[0.95,1.0]）平均亮度：实测 19 帧最低 237、中位数 249（255=纯白）；见 `preview/shell_merge_simulation.png`
- [ ] 无耳朵 / 无头部外轮廓 / 无身体与手 —— 头部椭圆外已用毛发白填充；带手的 06 帧已排除
- [ ] 无表盘边框、圆形装饰框、边缘光效 —— 工程内无任何环形对象；**已删除**唤醒/重连的边缘光晕（会给白毛边缘染色，见 §9 R3）
- [ ] 信息叠加不遮挡五官 —— 叠加层仅在额头（光点）/下巴（波形、提示条）/右上（角标）
- [ ] 所有表情脸部比例/位置/光照一致 —— 同一裁切边长

### 8.2 交互
- [ ] 手势 —— 见 §4.1（双击/长按为 C 层）
- [ ] 状态由业务事件驱动 —— 工程仅提供屏幕与对象，驱动在 `panda_ui`
- [ ] 错误反馈 —— asr_failed / llm_error / tts_error / network_lost / reconnecting / battery_low 均有屏

### 8.3 工程
- [ ] validator：`OK - project validated, no problems found`
- [ ] 构建无缺字形告警；改文案前先改 §6.1

## 9. 运行时契约与风险

### 9.1 `panda_ui` 需要知道的
- 脸部对象：每个脸部屏的 `ui_<屏>_face`（IMAGE，360×360，位于最底层）。运行时 `lv_image_set_src()` 指向 SD 帧解码缓冲，或用 `lv_animimg`；资源缺失 → 回退 `face_01_idle`
- 叠加层对象名稳定：`wave_1..9`、`dot_1..3`、`tip`/`tip_text`/`tip_icon`、`badge`/`badge_n`（`home`，初始隐藏）
- 事件回调名全局唯一：`<屏>_<对象>_<事件>`
- 所有 LVGL 对象只在 UI Task 操作（需求书 §8）

### 9.2 已知偏差与风险
| # | 内容 | 处理 |
|---|---|---|
| R1 | 双击/长按不在已验证事件集 | C 层实现（§4.1） |
| R2 | 板上"思考"帧带手 | 已排除；需 3D 重做 |
| R3 | 唤醒/重连原有的边缘青色光晕与"白毛融入白壳"冲突 | **已删除**。唤醒提示改由脸部帧（睁眼）+ 状态逻辑表达，不在边缘加任何色彩 |
| R4 | 设计板脸部分辨率低（~220 px），且毛发延伸为合成 | 仅作设计期占位；少数帧（困惑、异常）边缘残留极小深色点，生产帧不会有 |
| R9 | 白毛满屏后，深色功能页（设置/列表）与脸部屏反差大 | 如需统一，可把功能页背景改为壳白并反相文字色（待确认） |
| R5 | `Sleepy/Confused/Angry` 等板上带小图标（Zzz、?、怒气）的帧，图标在圆形裁切后被切掉 | 如需保留，作为独立叠加图标对象加回，不要烘焙进脸部帧 |
| R6 | 通知列表只有 3 条静态卡片，无滚动容器 | 运行时用 LVGL 滚动或分页实现 |
| R7 | 滑块/开关为静态示意，值由运行时驱动 | `*_fill`、`*_knob` 为真对象，可改宽度/位置 |
| R8 | 错误→表情映射为设计假设：ASR/LLM=困惑，TTS=难过，断网=异常，低电=疲惫 | 在 §2 可调整 |
