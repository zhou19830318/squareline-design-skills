# Third-party components

**Distributed inside this repository**
- Noto Sans SC (`fonts/*.ttf`) - SIL Open Font License 1.1, full text in `fonts/OFL.txt`. The fonts may be bundled and used freely, but not sold on their own.

**Installed on your machine by `python3 tools/slx.py setup` (npm ci) - not redistributed here**
- lucide-static (icons) - ISC
- lv_font_conv (LVGL font converter) - MIT
- @resvg/resvg-js and @resvg/resvg-wasm (SVG rasteriser) - MPL-2.0 (used unmodified)
Their licence files are inside `tools/node_modules/<package>/` after installation. Pinned versions: `tools/package-lock.json`.

**Optionally downloaded at run time**
- LVGL 9.2.2 source (MIT), only by `slx.py truth`, into `~/.cache/slx`, compiled locally.

**Own code**
- Everything else (the toolkit, skills, commands, templates, tests, examples) is by the repository owner and released under the MIT licence in `LICENSE`.

"SquareLine" / "SquareLine Studio" are names of a third-party product. This project is not affiliated with or endorsed by its makers.
