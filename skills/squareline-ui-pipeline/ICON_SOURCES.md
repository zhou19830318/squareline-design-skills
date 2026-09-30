# ICON_SOURCES.md — 图标/素材网站目录与下载→PNG 工作流

> **用途**：Stage A 收集图标时的**站点目录**。用户需求没点名来源时，按本表
> 顺序挑站；用户点名了站/风格，就在该站检索后走统一下载→转换流程。
> **铁律**：只取**可再分发的开源许可**图标；下载的 SVG 一律存进
> `examples/<Name>/downloads/` 并记许可证，然后转 PNG——**绝不把截图直接抠图
> 当资产**（见 SKILL.md 的品牌自查清单）。

---

## 1. 站点目录（按使用优先级）

### ① Lucide — `https://lucide.dev/icons`　★默认，离线可用

- **许可证**：ISC（可商用、可再分发，无需署名）。
- **风格**：线性图标，24×24 网格、2px 圆头描边——与本流水线已有的
  `generate_assets*.mjs` 完全同源，视觉上无缝。
- **怎么用**：**已随包内联**（`tools/node_modules/lucide-static/icons/`，
  ~1500 个），离线直接用清单生成器，不需要下载：

  ```jsonc
  // assets.manifest.json 里
  { "name": "img_home_icon_clock", "source": "lucide", "icon": "clock", "size": 44 }
  ```

- 找不到想要的图形再往下找其它站。

### ② Iconify 全集 — `https://icon-sets.iconify.design/`

- **许可证**：**逐集确认**（集合页右上角有 License 标签；常用：
  Tabler=MIT、Bootstrap=MIT、Feather=MIT、Material Symbols=Apache-2.0、
  Phosphor=MIT、Solar=CC BY 4.0（需署名））。**CC BY / OFL 集要记出处**。
- **风格**：聚合 **200+ 套**开源图标集，20 万+ 图标，可按风格过滤
  （线性/填充/双色/emoji），支持换色预览。
- **怎么用**：单图标 SVG 直链形如
  `https://api.iconify.design/<集合>--<图标名>.svg?color=%23FFFFFF`，
  下载到 `examples/<Name>/downloads/` 后：

  ```bash
  node tools/svg_to_png.mjs examples/<Name>/downloads/<名>.svg \
       --out examples/<Name>/assets/images --size 44 --name img_<屏>_<含义>
  ```

  （或把 `source: "svg", "file": "..."` 写进清单，走清单生成器。）

### ③ SVG Repo — `https://www.svgrepo.com/`

- **许可证**：站内按 **CC0 / Public Domain / MIT / Apache** 过滤；
  也有 CC BY 集合——**下载页明示每枚图标许可**，逐枚确认。
- **风格**：50 万+ 图标与插画，含**彩色填充风格**（线性图标站补不齐的
  彩色插画、品牌类图形常在这里找）。
- **怎么用**：页面直接下载 SVG → 同 Iconify 的转换流程。注意部分图标
  内嵌大量 path 与元数据，转换前可手工清掉 `<metadata>`。

### ④ Tabler Icons — `https://tabler.io/icons`

- **许可证**：MIT。
- **风格**：约 6000 枚线性图标，24×24、2px 描边，与 Lucide 风格接近，
  适合做补充（个别图形 Lucide 缺失时）。

### ⑤ Bootstrap Icons — `https://icons.getbootstrap.com/`

- **许可证**：MIT。
- **风格**：约 2000 枚，线性 + 少量填充，命名贴近通用 UI 词汇。

### ⑥ Feather — `https://feathericons.com/`

- **许可证**：MIT。
- **风格**：约 280 枚极简线性，24×24。胜在极简克制，缺现代题材。

### ⑦ Material Symbols — `https://fonts.google.com/icons`

- **许可证**：Apache-2.0。
- **风格**：Google 全家桶题材（支付、家居、车辆、健康），线性/填充/圆角/
  尖角四种变体。下载 SVG 时在页面右侧选 "SVG" 且关掉 ligature（直接
  引用 `icon_name.svg` 形式），或用 Iconify 的 `material-symbols` 集。

### ⑧ Phosphor Icons — `https://phosphoricons.com/`

- **许可证**：MIT。
- **风格**：约 9000 枚 × 6 种粗细（线性/填充/双色等），同一图形多档
  字重，做「同图标多状态」很方便。

### ⑨ Minecraft/游戏/设备类特殊素材

低频需求走 SVG Repo 或 OpenMoji（`https://openmoji.org/`，CC BY-SA 4.0，
emoji 全集线性+彩色）。emoji 类在 LVGL 里注意：**彩色 emoji 不适合打进
字体**，应渲染成 PNG 图片对象。

### 反面清单（不要当资产来源）

- 参考产品的官方宣传图/固件截图抠图——品牌自查直接不过。
- 来路不明的「免费图标」站（无许可声明、要求回链才能商用的）。
- AI 生成的位图截图放大当图标（锯齿 + 许可不明）；要 AI 生成请生成
  SVG 描述再走本流程。

## 2. 许可证纪律（写进工程）

1. 每个下载的 SVG 存 `examples/<Name>/downloads/<站>_<名>.svg`；
2. 逐枚把「站点 + 许可证 + 原链接」记进设计规格文档 §7 资产清单的
   「来源」列（与 Lucide/自绘同表）；
3. CC BY 4.0 / CC BY-SA 的图标**必须**在交付说明里署名；不确定许可
   的**不要用**，换 Lucide 或自绘；
4. 商用交付默认只选 MIT / ISC / Apache-2.0 / CC0。

## 3. 下载 → PNG 的统一工作流

```bash
# 1) 下载（浏览器或 curl），存进项目的 downloads/
curl -o examples/<Name>/downloads/tabler_brightness.svg \
     "https://api.iconify.design/tabler--brightness.svg?color=%23FFFFFF"

# 2) 单枚转换：SVG → PNG（尺寸 = 规格 rect 的实际像素）
node tools/svg_to_png.mjs examples/<Name>/downloads/tabler_brightness.svg \
     --out examples/<Name>/assets/images --size 44 \
     --name img_settings_icon_brightness

# 3) 批量：写进 assets.manifest.json（推荐，构建可复现）
node tools/generate_assets_from_manifest.mjs examples/<Name>/assets.manifest.json

# 4) 审计：PNG 头核对真实尺寸（与 curated 生成器同一招）
node -e "const b=require('fs').readFileSync('examples/<Name>/assets/images/img_settings_icon_brightness.png');console.log(b.readUInt32BE(16)+'x'+b.readUInt32BE(20))"
```

## 4. LVGL 侧注意事项（转换后）

- **渲染到目标 rect 的原生尺寸**（本流水线 2px ≈ 1dp 时即 rect 尺寸），
  不要渲染小图靠拉伸——已经因为「stretched assets」翻过车。
- 站点下载的 SVG 若是**响应式**（`width="100%"` 或无宽高），转换器会按
  `--size`/viewBox 重定视口；若源连 viewBox 都没有，先手工补一个再转。
- 线性图标的描边粗细在放大后会显细：44px 以上建议在转换时显式
  `--stroke 2`（lucide 源用清单里的 `stroke_width`）。
- 彩色图标（SVG Repo 的插画类）确认**没有内嵌位图**（`<image href="data:...">`），
  有的话 resvg 会渲染但体积暴涨，且缩放发糊。
- 图标语义按用途命名（`img_<屏>_<含义>[_<状态>].png`），**不要沿用站点的
  文件名**——将来换图标源时引用不用动。
