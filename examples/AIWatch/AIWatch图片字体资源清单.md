# AIWatch 图片 & 字体资源清单
适用于：SquareLine Studio 导出 + LVGL v8.x + ESP32-S3 (410×502 AMOLED)
目标仓库：zhou19830318/AIWatch（ESP-IDF + LVGL + WebSocket接OpenClaw网关）

> ⚠️ 说明：我暂时无法直接抓取你GitHub仓库里 `main/`、`components/`、`ui/` 的现有文件命名（该仓库搜索引擎未收录具体目录），下面按 **LVGL/SquareLine 通用规范** 命名。导入前建议先看一眼你仓库里 `main/gui/`、`main/ui/` 或 `spiffs_image/` 文件夹里现有资源的命名习惯（比如是否已有 `img_` 前缀、下划线还是驼峰），保持风格统一即可，改名不影响逻辑。

---

## 一、SquareLine Studio 工程设置

新建/打开工程时：
- Resolution: **410 × 502**
- Color depth: **16-bit (RGB565)**（AMOLED面板常用，若面板是RGB666/RGB888需与驱动一致，具体看你仓库里 `lv_conf.h` 的 `LV_COLOR_DEPTH`）
- Project Export Root：导出到你仓库的 `main/ui/` 或 `main/gui/`（与仓库原结构对齐）
- Image assets 导出格式：勾选 **"C array"**（不要用 raw bin，除非你仓库已用 LittleFS/SPIFFS 加载图片再另说）

---

## 二、图片资源清单（按界面分组）

### 命名规则
`img_[模块]_[内容]_[尺寸].c/.png`
例：`img_home_icon_clock_64.png`

### 1. 状态栏 / 通用图标
| 文件名 | 尺寸(px) | 格式 | 用途 | 颜色要求 |
|---|---|---|---|---|
| `img_status_battery_frame.png` | 18×10 | PNG-32(含透明) | 电池外框 | 白色线条 |
| `img_status_battery_charging.png` | 12×10 | PNG-32 | 充电闪电图标（叠加态） | 黄色 |
| `img_status_wifi.png` | 16×16 | PNG-32 | WiFi连接图标 | 白色 |
| `img_status_wifi_off.png` | 16×16 | PNG-32 | WiFi未连接 | 灰色 |
| `img_status_mic_active.png` | 16×16 | PNG-32 | 麦克风录音中指示 | 红色/粉色高亮 |
| `img_nav_back_arrow.png` | 12×20 | PNG-32 | 通用返回箭头/列表右箭头 ">" | 灰白 `#999999` |

### 2. 总览预览（App Grid 主页）
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_home_icon_clock.png` | 32×32 | PNG-32 | 时间入口图标（线条白色，放入蓝色圆底） |
| `img_home_icon_weather.png` | 32×32 | PNG-32 | 天气入口图标（晴+云） |
| `img_home_icon_ai.png` | 32×32 | PNG-32 | AI对话机器人图标 |
| `img_home_icon_pomodoro.png` | 32×32 | PNG-32 | 番茄钟图标 |
| `img_home_icon_steps.png` | 32×32 | PNG-32 | 计步跑步人图标 |
| `img_home_icon_music.png` | 32×32 | PNG-32 | MP3音符图标 |
| `img_home_icon_settings.png` | 32×32 | PNG-32 | 设置齿轮图标 |
| `img_home_circle_bg_blue.png`(可选) | 64×64 | PNG-32 | 若不用LVGL纯色圆而用图片圆底 |
| `img_home_circle_bg_purple.png` | 64×64 | PNG-32 | 同上，紫色 |
| `img_home_circle_bg_red.png` | 64×64 | PNG-32 | 同上，红橙色 |
| `img_home_circle_bg_green.png` | 64×64 | PNG-32 | 同上，绿色 |

> 💡 建议：圆形彩色底优先用 LVGL `lv_obj` 设置 `radius=LV_RADIUS_CIRCLE` + `bg_color` 实现，**不需要额外切图**，只需准备透明底的白色线条图标（32×32）叠加在上面即可，能省一半图片资源和Flash空间。

### 3. 时间（表盘）
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_watchface_bg_01.png` | **410×502** | JPG(若无透明需求，体积更小) 或 PNG | 默认表盘壁纸（日落山景），需完整铺满屏幕 |
| `img_watchface_bg_02.png` ~ `_0N.png` | 410×502 | JPG | 可选：多套表盘壁纸供切换 |
| `img_watchface_icon_location.png` | 12×14 | PNG-32 | 定位小图标 |
| `img_watchface_icon_weather_mini.png` | 40×40 | PNG-32 | 底部卡片天气小图标（与天气页图标集共用） |

> ⚠️ 壁纸图**体积控制**：410×502全彩JPG若不压缩，转成LVGL C数组后可能占用 400KB~800KB Flash/PSRAM，多套壁纸会很快吃满8MB PSRAM。建议：
> - 用 `LV_IMG_CF_TRUE_COLOR` 而不是 `_ALPHA`（背景图不需要透明通道）
> - 或转 RGB565 (2字节/像素) 而非 ARGB8888 (4字节/像素)，能省一半体积
> - 或改用 JPG/PNG 解码方案（LVGL支持 `lv_png`/`lv_sjpg` 解码器）从 SD卡/Flash文件系统实时加载，而不是编译进固件，这样切换壁纸更灵活

### 4. 天气
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_weather_icon_sunny_72.png` | 72×72 | PNG-32 | 主区大图标-晴 |
| `img_weather_icon_cloudy_72.png` | 72×72 | PNG-32 | 多云 |
| `img_weather_icon_overcast_72.png` | 72×72 | PNG-32 | 阴 |
| `img_weather_icon_rain_72.png` | 72×72 | PNG-32 | 小/中雨 |
| `img_weather_icon_heavyrain_72.png` | 72×72 | PNG-32 | 大雨 |
| `img_weather_icon_thunder_72.png` | 72×72 | PNG-32 | 雷阵雨 |
| `img_weather_icon_snow_72.png` | 72×72 | PNG-32 | 雪 |
| `img_weather_icon_fog_72.png` | 72×72 | PNG-32 | 雾/霾 |
| 以上每个再切一套 | **28×28** | PNG-32 | 命名后缀改 `_28`，用于逐时预报小图标 |
| `img_weather_icon_location_pin.png` | 16×16 | PNG-32 | 顶部定位图标 |
| `img_weather_drag_handle.png`(可选) | 36×4 | PNG-32 | 底部拖拽指示条，也可直接用 `lv_obj` 圆角矩形绘制无需切图 |

> 图标代码映射建议：和风天气(QWeather)返回的 `icon` 字段是数字代码（如100=晴、101=多云...），在固件里做一个 `icon_code -> 本地图片资源` 的映射表（枚举或 switch-case），避免依赖网络实时拉取图片。

### 5. AI对话
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_ai_avatar_bot.png` | 44×44 | PNG-32(圆形裁切) | AI消息头像 |
| `img_ai_avatar_user.png` | 44×44 | PNG-32(圆形裁切) | 用户消息头像（若需展示用户发言气泡） |
| `img_ai_icon_history_bubble.png` | 28×28 | PNG-32 | 历史列表每条前的小图标 |
| `img_ai_icon_mic_idle.png` | 48×48 | PNG-32 | 麦克风按钮-待机态 |
| `img_ai_icon_mic_listening.png` | 48×48 | PNG-32 | 麦克风按钮-聆听态（可做呼吸动画，多帧） |
| `img_ai_icon_mic_speaking.png` | 48×48 | PNG-32 | 播放AI语音回复时的状态图标 |
| `img_ai_waveform_frame01~05.png`(可选) | 200×40 | PNG-32 | 语音波形动画帧，用于录音/播放时的动效，5帧循环播放 |

> 语音状态动画建议用 LVGL 的 `lv_anim` + 多帧图片切换，或更省资源的方式：用 `lv_arc`/`lv_led` 做呼吸灯效果代替真实波形图。

### 6. 番茄时钟
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_pomodoro_icon_tomato.png` | 22×22 及 32×32(主页复用) | PNG-32 | 番茄图标 |
| `img_pomodoro_icon_list.png` | 24×24 | PNG-32 | 左下角列表/历史按钮图标 |
| `img_pomodoro_icon_play.png` | 24×24 | PNG-32 | 播放三角 |
| `img_pomodoro_icon_pause.png` | 24×24 | PNG-32 | 暂停双杠 |
| `img_pomodoro_icon_settings.png` | 24×24 | PNG-32 | 右下角齿轮 |

> 中间的圆环进度条**不需要切图**，用 `lv_arc` 控件配合渐变色实现（LVGL 8.x的arc不直接支持渐变，可用两层arc叠加或自定义色阶模拟，或者简单用纯色 `#FF5A3C`）。

### 7. 计步
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_steps_icon_running.png` | 22×22 | PNG-32 | 顶部标题图标 |
| `img_steps_icon_shoe.png` | 28×28 | PNG-32 | 圆环内鞋子图标 |
| `img_steps_icon_fire.png` | 20×20 | PNG-32 | 卡路里火焰图标 |
| `img_steps_icon_location.png` | 20×20 | PNG-32 | 公里数定位图标 |
| `img_steps_icon_chart.png` | 24×24 | PNG-32 | 底部统计柱状图图标 |

### 8. MP3播放
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_music_icon_note.png` | 20×20 | PNG-32 | 顶部标题音符图标 |
| `img_music_album_placeholder.png` | 90×90 | PNG-32(圆角需提前在图片里切好，或用LVGL的 `lv_obj_set_style_radius` 裁切容器) | 无封面时默认专辑图 |
| `img_music_icon_prev.png` | 28×28 | PNG-32 | 上一曲 |
| `img_music_icon_next.png` | 28×28 | PNG-32 | 下一曲 |
| `img_music_icon_play.png` | 32×32 | PNG-32 | 播放态 |
| `img_music_icon_pause.png` | 32×32 | PNG-32 | 暂停态 |
| `img_music_icon_shuffle.png` | 22×22 | PNG-32 | 随机播放 |
| `img_music_icon_shuffle_active.png` | 22×22 | PNG-32 | 随机播放-开启高亮态 |
| `img_music_icon_volume.png` | 22×22 | PNG-32 | 音量图标 |

> 若要显示SD卡MP3的真实ID3内嵌封面，需在固件里解析ID3v2的APIC帧并动态解码JPEG（用 `lv_img_dsc_t` 动态构造 + `lv_sjpg` 解码器），比预置占位图复杂很多，建议先做占位图版本，封面功能后续再加。

### 9. 系统设置
| 文件名 | 尺寸 | 格式 | 说明 |
|---|---|---|---|
| `img_settings_icon_gear.png` | 20×20 | PNG-32 | 标题齿轮图标 |
| `img_settings_icon_bluetooth.png` | 16×16 | PNG-32 | 蓝牙符号(白色，放蓝色圆底) |
| `img_settings_icon_brightness.png` | 16×16 | PNG-32 | 太阳符号(放黄色圆底) |
| `img_settings_icon_volume.png` | 16×16 | PNG-32 | 喇叭符号(放紫色圆底) |
| `img_settings_icon_language.png` | 16×16 | PNG-32 | 地球符号(放蓝色圆底) |
| `img_settings_icon_about.png` | 16×16 | PNG-32 | "i"信息符号(放灰色圆底) |

---

## 三、字体文件清单

### 中文字体推荐
- **思源黑体 (Source Han Sans / 思源黑体 CN)** Regular/Medium/Bold —— 开源免费商用，字形清晰适合小屏
- 或 **阿里巴巴普惠体 (Alibaba PuHuiTi)** —— 开源免费商用，字重丰富
- 备选：**霞鹜文楷/得意黑** 风格更活泼，若想要更有设计感的表盘字体可用于"时间"大数字

> ⚠️ 不要直接把整个TTF字体文件塞进LVGL项目——中文字库全字符集有几万字，转换后会占用几MB到十几MB Flash，ESP32-S3扛不住。**必须做字符子集化**。

### 需要的字号规格（按界面用途分类）

| 用途 | 字号 | 字重 | 建议命名(LVGL字体变量名) |
|---|---|---|---|
| 表盘大数字时间 "10:27" | 64-72px | Bold | `font_time_display_72` |
| 页面大数字（步数"6820"、天气"18°C"） | 44-48px | Bold | `font_number_bold_48` |
| 一级标题（页面标题、歌曲名） | 20-22px | Bold/Medium | `font_title_22` |
| 状态栏时间/常规正文 | 16-18px | Regular | `font_body_16` |
| 次级信息（日期、副标题、艺术家名） | 14-15px | Regular | `font_body_medium_14` |
| 辅助/时间戳/单位文字 | 12-13px | Regular | `font_caption_12` |

### 字符子集化方案（关键步骤）
中文字体不能全量转换，需要用 **LVGL官方字体转换工具** 提取"你的UI实际会用到的汉字"，方法二选一：

**方法A：在线转换工具**
访问 `https://lvgl.io/tools/fontconverter`
- 上传 TTF 字体文件
- Size 填入上表对应字号（如72、48、22、16、14、12，需要几个字号就转几次）
- Bpp（每像素位数）选择 **4 bit-per-pixel**（抗锯齿效果好且体积可控）
- Symbols 一栏**只填入你界面上实际会出现的汉字/符号**，例如：
  ```
  时间天气多云晴阴雨雪雷霜霾风冷热今明后天北京上海10:27冷热
  ℃%步卡路里公里专注时间设置蓝牙亮度声音语言简中文关于本机
  已连接自动番茄钟计步MP3AI对话你好有什么我可以帮助的吗历史
  0123456789.:年月日周一二三四五六星期
  ```
  （实际请把你所有界面文案汇总去重后整体填入，缺字会显示方块）
- 勾选 Basic Latin（0x20-0x7F）保证英文数字标点正常显示
- 生成后下载 `.c` 文件，命名为对应的 `font_xxx_18.c` 放入项目字体目录

**方法B：命令行 `lv_font_conv`（适合CI自动化，字库变化频繁时更方便）**
```bash
npm install -g lv_font_conv
lv_font_conv --font SourceHanSansCN-Bold.ttf -o font_title_22.c \
  --format lvgl --lv-include lvgl.h \
  --bpp 4 --size 22 \
  --symbols "你的界面所有中文字符与符号"
```

### 字体文件命名与存放
```
main/ui/fonts/
├── font_time_display_72.c   (表盘大数字，含: 0-9 : 及少量中文"月周日"等)
├── font_number_bold_48.c    (数字+单位: 0-9 ℃ % 步)
├── font_title_22.c          (各页面标题汉字全集)
├── font_body_16.c           (正文常用字，字符集最大的一个)
├── font_body_medium_14.c
├── font_caption_12.c
```

> 每新增一个界面文案，都要重新生成一次涉及字号的字体（把新字加入symbols重新转换），**不是运行时动态加字**，LVGL的位图字体是编译期固定字符集的。

---

## 四、SquareLine Studio 里导入这些资源的操作步骤

1. 打开工程 → 左侧面板 **Assets → Images** → 右键 `Import` → 依次选中上面清单里的PNG/JPG文件（保持按上面命名批量导入，方便后续代码里通过 `&img_xxx` 直接引用）
2. **Assets → Fonts** → 右键 `Import` → 选择字体转换生成的 `.c` 文件或直接在SquareLine内置的Font Converter里传入TTF+填字号+填symbols（同方法A的参数）
3. 每个Screen里的组件（Image、Label）在右侧属性面板的 `Image` / `Font` 下拉框中选择对应导入的资源
4. 导出（Export → Export UI Files）时，SquareLine会生成 `ui.c/ui.h` 及各资源的 `.c` 文件到指定目录——**导出目录直接设为你仓库里放UI代码的目录**（如 `main/ui/`），这样导出后可直接被ESP-IDF的CMakeLists编译进固件
5. 检查你仓库 `main/CMakeLists.txt` 里的 `SRCS`/`INCLUDE_DIRS` 是否已经把 `ui/` 目录纳入编译范围，若是新增的图片/字体`.c`文件确保被自动glob匹配到，或手动加入源文件列表

---

## 五、Flash/存储空间预算参考

| 资源类型 | 预估单项大小 | 数量估算 | 合计 |
|---|---|---|---|
| 小图标(20-44px, RGB565+透明) | 2-6 KB | 约60个 | ~250 KB |
| 中图标(72px天气图标) | 8-12 KB | 16个(8种×2尺寸) | ~160 KB |
| 表盘壁纸(410×502, RGB565) | ~400 KB/张 | 1-3张 | 400KB-1.2MB |
| 字体文件(6个字号，含常用汉字约300-500字/号) | 30-80 KB/个 | 6个 | ~300 KB |
| **合计** | | | **约1-2MB** |

若你的Flash是32MB（Waveshare该开发板规格），空间完全够用；若壁纸想做多套高清切换，建议壁纸单独存SD卡+运行时JPG解码加载，不编译进固件。

---

## 六、下一步建议

1. 先确认你仓库 `main/` 下现有UI相关目录结构（如果方便，可以把 `main/ui/` 或 `main/gui/` 目录的文件列表贴给我，我可以按你已有命名习惯直接对齐调整上面清单，而不是通用命名）
2. 确认 `lv_conf.h` 里 `LV_COLOR_DEPTH` 设置，决定图片导出色深
3. 确认 UI 渲染是否已挂载 SD卡文件系统（决定壁纸/专辑封面是否走动态加载而非编译进固件）
