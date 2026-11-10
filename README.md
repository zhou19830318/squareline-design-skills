# squareline-design-skills

Turn a **concept image + a requirements document** into a **SquareLine Studio / LVGL project** that opens without errors, looks like the concept,
and provably follows the requirements. 把**概念图 + 需求文档**变成能被 SquareLine Studio 打开、长得像概念图、并且逐条对得上需求的 LVGL 工程。

- requirement tracing (every "must / must not" gets a decision) / 需求追溯
- measuring the concept (`scan`, `fit-font`) instead of eyeballing / 量测概念图
- pre-build lint with coded fixes, real-LVGL text audit (`truth`) / 构建前体检与真 LVGL 真值审计
- a `slx next` workflow driver, so weaker LLMs can follow the pipeline too / 工作流驱动，适配各类大模型

## Install (Claude Code / Cowork)

```
/plugin marketplace add YOUR_GITHUB_USERNAME/squareline-design-skills
/plugin install squareline-design@squareline-design-marketplace
```

Needs Python >= 3.8 (`pip install pillow numpy`) and Node.js; Node packages install themselves on first use. Optional: gcc (for `slx.py truth`), playwright + chromium (screenshots).

## Use with any other LLM agent

Give it [`plugins/squareline-design/AGENTS.md`](plugins/squareline-design/AGENTS.md) (or [`docs/UNIVERSAL_PROMPT.md`](plugins/squareline-design/docs/UNIVERSAL_PROMPT.md)). Everything is a command line:

```bash
python3 plugins/squareline-design/tools/slx.py doctor
python3 plugins/squareline-design/tools/slx.py init MyWatch --width 360 --height 360 --shape CIRCLE --dir ~/work
python3 plugins/squareline-design/tools/slx.py next ~/work/MyWatch      # run after every step
```

Full guide: [`plugins/squareline-design/README.md`](plugins/squareline-design/README.md) - usage, commands, disclosure of what the plugin runs/fetches, verified vs unverified, limits. Changes: [`CHANGELOG.md`](plugins/squareline-design/CHANGELOG.md).

**Status:** the generated `.spj` files have been validated and rendered by the toolkit's own checks, but have **not** been opened in SquareLine Studio itself - please report what you see.

## Licence

MIT, see [LICENSE](LICENSE). Bundled Noto Sans SC is under the SIL OFL ([plugins/squareline-design/fonts/OFL.txt](plugins/squareline-design/fonts/OFL.txt)); other third-party notes in [NOTICE.md](plugins/squareline-design/NOTICE.md).
"SquareLine Studio" is a third-party product name; this project is not affiliated with or endorsed by its makers.
