# squareline-design-skills

Turn one UI reference image into a **complete LVGL project that SquareLine Studio
can open without errors**.

Nothing here is tied to a particular agent: `skills/` + `tools/` are the whole
interface. Copy the folder anywhere, and any agent tool that can read/write files
and run commands can drive it (per-agent recipes under
[Plugging into your agent](#plugging-into-your-agent)).

**Languages:** **English** · [中文](README.md)

---

## Usage

The one-minute version: **copy `skills/` + `tools/` somewhere your agent can read
them → hand it a concept image and a requirement file (template at
`templates/UI需求清单模板.md`; the agent asks for whatever is missing) → it walks
the five stages → you run a check at each stage → open the resulting
`squareline/<Name>/<Name>.spj` in SquareLine Studio. Want changes? Send feedback
through the multi-round refinement loop.**

To actually do it, work through the sections below in order.

### 1. Requirements

| Needed | Notes |
|---|---|
| **Node.js** | Renders PNGs, subsets fonts, inlines the mockup. Dependencies are vendored in `tools/node_modules` — **no `npm install`** |
| **Python 3** | Builds, validates and previews projects (tested on 3.13 here) |
| **SquareLine Studio** | **Not required.** The validator checks against `tools/schema_snapshot.json`; installing it only adds a cross-check |

### 2. Run your first project

One finished project ships in the repo: `examples/NovaWatchS12` (456×456 round,
10-screen full-feature watch UI). **Running it is the fastest way in** — you do
not need a reference image yet:

```bash
# Validate the project (should print OK - project validated, no problems found)
python tools/validate_squareline_project.py examples/NovaWatchS12/squareline/NovaWatchS12

# Look at it without opening the editor (writes a single-file preview HTML)
python tools/preview_from_project.py examples/NovaWatchS12/squareline/NovaWatchS12
```

Those two commands are the core loop of this package — **the validator answers
"is the project sound?", the re-render answers "does it look right?"**. You will
run the same two over and over when you build your own.

To rebuild it from scratch (the spec carries its own asset pack, so the bare
command works):

```bash
node tools/generate_assets_from_manifest.mjs examples/NovaWatchS12/assets.manifest.json
python tools/build_from_spec.py examples/NovaWatchS12/NovaWatchS12.spec.json
```

It prints the project summary; success means no `ERROR` at the end:

```
screens   : 10
objects   : 103
images    : 0  missing: []
fonts     : [('Big48', 48, 13), ('Title20', 20, 293), ('Body16', 16, 293)]
charset   : ui-text 46, doc-headroom 291 (+246 usable)
lineheight: {'Big48': 60, 'Title20': 23, 'Body16': 20}
OK - project validated, no problems found
```

### 3. Build your own project

Five stages, **each with its own check, so you can stop and inspect at any point**.

| Stage | What happens | Output | Pass condition |
|---|---|---|---|
| **Stage 0**<br>requirements → spec | Collect requirements from `templates/UI需求清单模板.md` (size/shape/screens/switching/animations/asset preferences), then copy `templates/设计规格文档模板.md` and fill it in section by section as `<Name>设计规格文档.md` | The design spec — **every later stage is measured against it** | Three manual checks: every `rect` uses absolute screen coordinates; the text charset is complete; control height ≥ font line height |
| **Stage A**<br>collect + generate assets | Manifest-driven `node tools/generate_assets_from_manifest.mjs` (three sources: vendored Lucide, downloaded SVGs, inline SVG); one-off conversions with `node tools/svg_to_png.mjs`; icon-site directory and licences in `ICON_SOURCES.md` | `assets/images_*/` | Read the PNG header to confirm real size; compare against mockup references for missing / unused |
| **Stage B**<br>produce the mockup | Emit `mockup.html`, squash it to a single file with `inline_mockup.mjs` | `mockup.html` / `*_standalone.html` | Unscaled overlap audit |
| **Stage C**<br>compile the project | Ordinary screens go spec JSON → `build_from_spec.py`; rare custom geometry via a small project-local Python module (SKILL.md C-2) | A complete project in `squareline/<Name>/` | `validate_squareline_project.py` + `preview_from_project.py` |

> **Why Stage 0 comes first**: the spec is the single source of truth. The engine
> collects every character that appears in the document into the font subset, so
> **to change wording you must first write the new words into the document** —
> otherwise the font is missing glyphs. This is the human confirmation point; if
> the document is not right, nothing downstream will be.

The minimum viable sequence:

```bash
# 0) Fill in the requirement file (size/shape/screens/switching/animations/assets)
cp templates/UI需求清单模板.md examples/<Name>/UI需求清单.md

# 1) The agent copies the spec template and fills in your design spec (= source of truth)
cp templates/设计规格文档模板.md examples/<Name>/<Name>设计规格文档.md

# 2) Generate assets + mockup (icon sites and licences: ICON_SOURCES.md)
node tools/generate_assets_from_manifest.mjs examples/<Name>/assets.manifest.json
node tools/inline_mockup.mjs examples/<Name>/mockup.html examples/<Name>/mockup_standalone.html

# 3) Design-time preview (no build) → compile (declarative spec for ordinary screens)
python tools/spec_preview.py     examples/<Name>/<Name>.spec.json --scale 1
python tools/build_from_spec.py  examples/<Name>/<Name>.spec.json --out examples/<Name>/squareline/<Name>
python tools/build_from_spec.py  --example     # print an annotated spec skeleton

# 4) Validate + re-render
python tools/validate_squareline_project.py examples/<Name>/squareline/<Name>
python tools/preview_from_project.py        examples/<Name>/squareline/<Name>
```

Acceptance: the validator prints `OK - project validated, no problems found`; the
preview matches the mockup screen by screen; SquareLine Studio 1.6.2 opens the
`.spj` without errors.

**That is the whole job** — from here, open the `.spj` in SquareLine Studio and
use it, or let the agent keep adding screens. To change things, send feedback
(recorded in the requirement file's iteration table): the agent updates the
spec/manifest → confirms with `spec_preview.py` → rebuilds → validates green,
one round at a time.

### 4. What you end up with

```
examples/<Name>/
├── <Name>设计规格文档.md            # source of truth — change requirements here first
├── assets/images_*/                 # PNGs from Stage A
├── mockup.html / *_standalone.html  # Stage B HTML preview
└── squareline/<Name>/               # the Stage C SquareLine project
    ├── <Name>.spj                   # ← open THIS with SquareLine "Open Project"
    ├── <Name>.sll / .slp / Themes.slt / project.info
    └── assets/                      # images + the font trio (.c / .bin / .fcfg)
```

`backup/ cache/ components/ ui/` are editor runtime junk — do not commit them.

---

## Walkthrough: NovaWatchS12 (a full-feature Apple-Watch-S12-style watch)

That covers the steps. This section unpacks each one using
`examples/NovaWatchS12` (456×456 round) — a real "Apple Watch S12 style
full-feature UI" project with **10 screens**: watch face (pre-baked analogue
hands), app grid, activity rings, weather, alarms, workout, stopwatch,
mindful breathing, AI voice (three states), and settings.

### ① Input: the requirement file

The requirement file lives at `examples/NovaWatchS12/UI需求清单.md` (filled from
`templates/UI需求清单模板.md`): 456×456 CIRCLE, 10-screen list with switching
logic, per-screen element sketches, interactions and animations, asset
preferences. This project had no external concept image — the requirement is
text-only; yours can ship with concept images.

### ② Stage 0: the design spec

The output is `examples/NovaWatchS12/NovaWatchS12设计规格文档.md`. Canvas
`456×456 / shape CIRCLE` (r=228; every visible element's corners within 216 of
the centre), **absolute screen coordinates** for all 10 screens, an interaction
table plus 3 animations, 4 font tiers, and the **text charset** (with
future-proofing words — the build collects 414 characters into the font subsets
so wording can change later without missing glyphs).

### ③ Stage A: manifest-driven asset generation

```
node tools/generate_assets_from_manifest.mjs examples/NovaWatchS12/assets.manifest.json
```

Produces **22 PNGs**: the 456px **pre-baked analogue dial** (bezel + ticks +
three hands in a 10:09:30 pose, inline-drawn builtin SVG), 8 app icons + 3
complication icons + 5 weather icons (offline Lucide source), and the
three voice waveform states (builtin). Rasterisation goes through
`tools/lib/resvg.mjs` (native binding preferred, WASM fallback), so it runs in
a Linux container with nothing installed.

### ④ Design-time preview + Stage C: compile the project

```
python tools/spec_preview.py examples/NovaWatchS12/NovaWatchS12.spec.json --scale 0.9
python tools/build_from_spec.py examples/NovaWatchS12/NovaWatchS12.spec.json
python tools/validate_squareline_project.py squareline/NovaWatchS12
python tools/preview_from_project.py        squareline/NovaWatchS12
```

The validator's real output:

| Check | Result |
|---|---|
| `screen size / shape` | 456x456 / CIRCLE |
| `nids` | 3058 unique: 3058 duplicates: **0** |
| `screens` / `objects` | 10 / 119 |
| `event handlers` / `actions` | 22 / 35 |
| `images` | 22, missing: **[]** |
| `occlusion suspects` | **0** |
| Verdict | **`OK - project validated, no problems found`** |

### ⑤ Re-render: turn the generated `.spj` back into images

`preview_from_project.py` parses the `.spj` directly and re-renders it (project
agnostic — size and shape detected automatically, images inlined so the sheet
is one self-contained file). The sidecar (`<Name>.preview.json`) supplies
human titles and 4 interaction-state cards (alarm-off, workout-active, voice
listening / speaking).

---

## Common problems and pitfalls

### Asset paths are flat

`assets_subdir` only chooses **which source directory to read assets from** — it is
**never** written into the project's references. The reference recorded in the
project is **always** `assets/<filename>`:

```jsonc
{
  "assets_subdir": "images",              // only picks the source asset pack
  "screens": [{"children": [
    {"type": "IMAGE", "asset": "assets/img_logo.png"}   // ✅ flat path
    //                "asset": "assets/images/img_logo.png"  ❌ always wrong
  ]}]
}
```

Writing `assets/images/...` makes the project point at a file it does not own, so
every image reports `missing`. `build_from_spec.py` stops this at the spec-writing
stage and tells you the correct form.

### LABEL height must be ≥ the font line height

The root cause of vertically clipped Chinese text: `line_height = max(ascent) +
max(descent)`, which is **always larger than the font size**. Sizing a control as
"height = font size" is guaranteed to break. Leave headroom instead:

```
height >= ceil(size * 1.35)        # safe lower bound for one line of CJK (measured ratio 1.19–1.31)
```

**And the line height is not a constant** — it depends on which glyphs that project
actually pulled in, so the same font at the same size differs between projects:

| Font | size | Glyphs | line_height | Project |
|---|---|---|---|---|
| `Big72` | 72 | 13 | **86** | `examples/NovaWatchS12` |
| `Title28` | 28 | 429 | **34** | `examples/NovaWatchS12` |
| `Body20` | 20 | 429 | **24** | `examples/NovaWatchS12` |

To check precisely, run a build and read the `lineheight:` line (it lists this
project's real line heights). There is a lookup table in
[`tools/LABEL_SIZING.md`](tools/LABEL_SIZING.md) (generated by `label_sizing.py`,
and `preflight.py` verifies it is in sync); when generating a spec in code you can
just use `label_sized()` from `tools/layout.py` and the height is computed for you.

### Do not hand-calculate layout arithmetic

Grid tiling, card rows and icon+text recur constantly, and hand-computed `rect` is
where coordinate drift comes from. `tools/layout.py` provides pure functions (they
return plain dicts you can drop straight into `children[]`):

```python
from layout import grid, stack, card_row, icon_text, label_sized

tiles = grid((20, 60, 360, 220), cols=3, rows=2, gap_x=12, gap_y=12,
             factory=lambda x, y, w, h: panel("t", [x, y, w, h], radius=14))
card  = card_row("card_display", [24, 72, 272, 96], "Display", "Auto", "Title20", "Body16")
lbl   = label_sized("hint", (30, 272), 260, "Swipe left for settings", 16, "Body16")
```

`grid()` raises rather than emitting a negative width when the gaps do not fit.
Self-test: `python tools/layout.py`.

### What to run when something is wrong

```bash
python tools/validate_squareline_project.py <project>   # is the project itself sound?
python tools/preview_from_project.py <project>          # look at it without the editor
```

Those two localise most problems. The regression suite is only needed when you
change the skill package itself (see [Self-check](#self-check-after-changing-the-package)).

---

## Command reference

```bash
# Build
python tools/build_from_spec.py <spec.json> --out <dir>   # declarative spec -> project (first choice for ordinary screens)
python tools/build_from_spec.py --example                 # print an annotated spec skeleton

# Assets and mockup
node tools/generate_assets_from_manifest.mjs <manifest.json>  # manifest-driven: lucide + downloaded SVG + inline
node tools/svg_to_png.mjs <x.svg> --size 44 --name img_x      # one-off downloaded SVG -> PNG
node tools/inline_mockup.mjs <in.html> <out.html>         # squash into a standalone single file

# Design-time preview (no build; the fast loop for coordinate/colour/copy tweaks)
python tools/spec_preview.py <spec.json> [--scale S] [--strict]

# Validate and preview
python tools/validate_squareline_project.py <project>
python tools/preview_from_project.py <project>

# Self-check (only when changing the skill package itself)
python tools/preflight.py                                 # few-second health check
python tools/preflight.py --full                          # + the regression suite
python tools/label_sizing.py                              # refresh the LABEL line-height table
python tools/layout.py                                    # layout library self-test
```

---

## Plugging into your agent

Nothing here is bound to one vendor — the only difference is **how the skill gets
loaded**. Whichever you use, the agent just has to be able to read
`skills/squareline-ui-pipeline/SKILL.md`, with `tools/`, `fonts/` and `templates/`
present alongside it: every command in SKILL.md is repo-relative, so it runs
unchanged after copying.

| Agent | How it loads | Key point |
|---|---|---|
| **Freebuff / Codebuff** | `.codebuff/skills/` auto-discovery | Just copy the directory; pick the `GLM-5.3-flash` model (see E) |
| **Claude Code** | `CLAUDE.md` + directory auto-discovery | Drop a `CLAUDE.md` at the repo root (see A) |
| **WorkBuddy** | `~/.workbuddy/skills/` or project `.workbuddy/skills/` | Copy `squareline-ui-pipeline` in (see B) |
| **DeepSeek / Codex / Cline** | `AGENTS.md` | A short pointer is enough; no auto-loading (see C) |
| **豆包 / general chat agents** | system prompt | Paste SKILL.md into the role, or use it as a knowledge base (see D) |
| **Cursor / Windsurf etc.** | `.cursorrules` / rule files | Same as `AGENTS.md` (see F) |

### First work out which tier your agent is in

| Tier | Capability | Can reach | Typical |
|---|---|---|---|
| **L1 chat only** | text output only | Can only **draft the Stage 0 spec** for you (you save it yourself) | web 豆包 |
| **L2 read/write files** | edits files, cannot run commands | Stage 0 + hand-written spec JSON; **you type the Stage A/C commands** | some IDE plugins |
| **L3 runs commands** | read/write + runs node/python | **The whole loop** | Claude Code, WorkBuddy, Codex CLI, Freebuff |

**How to tell**: ask it "can you run `python tools/preflight.py` and paste the
output?". If it can, it is L3. **L3 is the full experience** — every stage closes
its loop with a mechanical check, whereas L1/L2 drop the single most valuable
step, "validate immediately after every change".

### A. Claude Code

**Minimal setup** — create `CLAUDE.md` at the repo root:

```markdown
# Project: SquareLine UI Pipeline

This is a skill package that turns a UI reference image into a SquareLine Studio /
LVGL project.

Before any SquareLine / LVGL UI task, **read
`skills/squareline-ui-pipeline/SKILL.md` in full** and follow its stages exactly:

1. **Stage 0** write `examples/<Name>/<Name>设计规格文档.md` first (template in
   `templates/`), then confirm geometry and wording with the user before going on.
2. **Stage A** `node tools/generate_assets_from_manifest.mjs` (or `svg_to_png.mjs`) to produce PNGs.
3. **Stage B** produce `mockup.html` and let the user confirm the visuals.
4. **Stage C** ordinary screens go through
   `python tools/build_from_spec.py <spec.json> --out <dir>`; only radial/arc-width
   rare custom geometry goes in a project-local Python module (SKILL.md C-2).
5. **Validate** `python tools/validate_squareline_project.py <project>` +
   `python tools/preview_from_project.py <project>`; it is not done until both are green.

Deep technical detail lives in `skills/squareline-ui-pipeline/REFERENCE.md`.

**Hard rules**: only change the builder / spec and regenerate, **never hand-edit
`.spj`**; interactions use only the built-in action allowlist; run
`python eval/run_regression.py` before touching `tools/engine/`.
```

**Notes**

- It asks permission before writing files by default. The full flow involves dozens
  of writes, so consider `--dangerously-skip-permissions`, or at least pre-approve
  `Bash(node:*)` and `Bash(python:*)`.
- Long commands (rendering 70+ PNGs, the full regression) need a raised timeout —
  tell it up front, or it will be mistaken for a hang and interrupted.
- `tools/engine/squareline_engine.py` is 1300+ lines; tell it to **read only the
  section it needs to change**.

### B. WorkBuddy

User-level install (available in all projects):

```bash
mkdir -p ~/.workbuddy/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline ~/.workbuddy/skills/
```

Project-level install (travels with the repo; recommended for teams):

```bash
mkdir -p .workbuddy/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline .workbuddy/skills/
cp -r squareline-design-skills/tools squareline-design-skills/fonts \
      squareline-design-skills/templates squareline-design-skills/eval \
      .workbuddy/skills/squareline-ui-pipeline/
```

After that just give it natural-language instructions; SKILL.md's trigger words
take effect automatically.

> ⚠️ In this skill package's own repo `.workbuddy/` is the **working-memory
> directory** (not committed); in your *target* project `.workbuddy/skills/` is the
> skill directory (which should be committed). Do not confuse the two meanings.

**Notes**

- `tools/node_modules` is vendored — no `npm install` needed. On Windows, if
  `node` is not found, set `SQUARELINE_NODE_BIN`.
- On some Windows setups the bash shim is incomplete
  (`dirname: command not found`). Switch to PowerShell, or call python by absolute
  path:
  ```powershell
  & "C:\Users\<you>\.workbuddy\binaries\python\versions\3.13.12\python.exe" tools\preflight.py
  ```
- Chinese output may look like mojibake in a PowerShell console, but **the log
  written to a file is fine** — redirect to a file and read it rather than judging
  by the console.

### C. DeepSeek harness / Codex CLI / Cline / Roo Code

These have no auto-loading mechanism, so use `AGENTS.md` at the repo root:

```markdown
## SquareLine UI skill

For any SquareLine / LVGL UI task, read
`skills/squareline-ui-pipeline/SKILL.md` first and follow its stages exactly:

design spec (Stage 0, template at `templates/设计规格文档模板.md`) -> assets ->
HTML mockup -> `python tools/build_from_spec.py` (or `build_squareline_*.py`) ->
`validate_squareline_project.py` + `preview_from_project.py`.

Technical detail lives in `skills/squareline-ui-pipeline/REFERENCE.md`.

Hard rules:
- only change the builder / spec and regenerate; never hand-edit `.spj`;
- interactions use only the built-in action allowlist;
- validation must be fully green (validator prints
  `OK - project validated, no problems found`);
- run `python eval/run_regression.py` before touching `tools/engine/`.
```

**Notes**

- With a small context window (e.g. 64K), **do not let it read SKILL.md +
  REFERENCE.md + engine source in one pass**. Read SKILL.md first, then pull in only
  the relevant REFERENCE.md section (§1–§11 are separate, so one section at a time works).
- This tier **needs the Stage 0 discipline most**: with no hooks enforcing the flow,
  the model tends to skip ahead and generate the project directly, which shows up as
  missing glyphs and coordinate drift. **Make it write the spec out and confirm it
  with you.**
- The Codex CLI sandbox blocks network by default; this skill is entirely offline so
  that is fine. File writes must stay inside the workspace, so copy the skill package
  into the project directory before running. With Cline / Roo Code, restrict it to
  editing the spec JSON and the asset manifest.

### D. 豆包 / general chat agents

These have no notion of a repository and cannot run commands (tier L1).
**Do not ask them to write `.spj` — they cannot.**

**Use it as a "spec-document generator" (the most valuable use)**: paste
`templates/设计规格文档模板.md` in full, plus your reference image and requirement:

```
You are the author of a SquareLine Studio UI design spec document.
Below is the document template [full template].
Below is my UI reference image [image] and requirement [requirement].
Fill the template in section by section into a complete design spec, paying
particular attention to:
- Geometry: write every rect as absolute screen coordinates (x/y/w/h), never
  relative or centred descriptions;
- Object table: give type, coordinates, colour, font size and alignment per control;
- §6.1 Text: list every character that will appear on screen (titles, buttons,
  units, digits);
- Control height >= font line height.
Mark anything uncertain as "to be confirmed"; do not invent.
```

Save the result as `examples/<Name>/<Name>设计规格文档.md` — **that is the source of
truth**, and you then hand it to an L3 agent to carry on.

It may also hallucinate LVGL APIs or `.spj` fields that do not exist — **treat
REFERENCE.md as authoritative for anything technical**, and use its output only as
draft wording and geometry.

### E. Freebuff / Codebuff

> **A good way to start**: there is a free daily quota, so it does not consume your
> own tokens; the worked example NovaWatchS12 (456×456 round full-feature watch)
> was built with it, and
> compatibility is best.
> Entry: <https://freebuff.com/?ref=ref-046c65ee-f8d6-4d68-87cd-324439d48da1>
> **Pick the `GLM-5.3-flash` model** — measured as the most stable on multi-turn tool
> use like this ("read SKILL.md, follow the stages, re-run validation commands").

```bash
mkdir -p .codebuff/skills
cp -r squareline-design-skills/skills/squareline-ui-pipeline .codebuff/skills/
cp -r squareline-design-skills/tools squareline-design-skills/fonts \
      squareline-design-skills/templates squareline-design-skills/eval \
      .codebuff/skills/squareline-ui-pipeline/
```

A good first message:

```
Read skills/squareline-ui-pipeline/SKILL.md and follow its stages exactly.
My reference image is at [image]; build a 240×240 round-screen SquareLine project,
and write the design spec first for me to confirm.
```

**Notes** (from real use)

- **A restart kills previews and background services**; re-register them. **Files
  themselves are not lost.**
- Preview tabs are one-shot — use "replace", not "add".
- `write_file` / `str_replace` `oldString` must be byte-exact (read the section first,
  then edit).
- Watch the timeout on long tasks (rendering 70+ PNGs); split into two commands if needed.

### F. Cursor / Windsurf / 通义灵码

No skill-discovery mechanism, so point them at the rules file:

```bash
cp AGENTS.md .cursorrules        # Cursor; or create .cursor/rules/squareline.mdc
```

The rules-file contents are the same as the `AGENTS.md` in section C.

> **Tip**: once you copy the whole `squareline-design-skills/` into your target
> project, every approach A–F points at the same `SKILL.md`, so migrating costs
> nothing. **Changing the skill only ever means changing that one file.**

---

## Directory layout

```
squareline-design-skills/
├── README.md             # this guide (Chinese — the primary doc)
├── README.en.md          # English translation of the same guide
├── skills/squareline-ui-pipeline/
│   ├── SKILL.md          # skill definition (workflow + every pitfall) — the agent entry point
│   ├── ICON_SOURCES.md   # icon/asset site directory (Lucide/Iconify/SVG Repo…) + licences + download→PNG workflow
│   └── REFERENCE.md      # deep reference: .spj format / event schema / font subsetting / assets
├── templates/
│   ├── UI需求清单模板.md            # the user's requirement entry: concept image + this = the agent's input
│   └── 设计规格文档模板.md          # Stage 0 input contract: copy and fill it = the source of truth
├── tools/                # the whole toolchain (node + python; node_modules vendored, offline-capable)
│   ├── engine/squareline_engine.py  # engine layer: serialisation/events/animation/fonts/rebase (project agnostic)
│   ├── lib/resvg.mjs                # unified SVG->PNG entry (native binding + WASM fallback)
│   ├── schema_snapshot.json         # official strtype snapshot (validate without a local Studio)
│   └── LABEL_SIZING.md              # LABEL line-height lookup (generated)
├── fonts/                # source fonts (Noto Sans SC 400/500/700 TTF)
├── eval/                 # regression suite: rebuild archived projects and byte-compare
└── examples/
    └── NovaWatchS12/     # 456×456 round full-feature watch: requirement file +
                          # design spec + asset manifest + spec + full project
                          # (the regression baseline)
```

`tools/node_modules` (~64 MB) is vendored with the package, so every node tool runs
after copying with **no `npm install`**; you can also delete it and rebuild with
`cd tools && npm install`.

`@resvg/resvg-js` is a native module (one `.node` per OS/CPU). Linux (x64/arm64,
gnu/musl), macOS (arm64/x64) and Windows (x64) bindings are vendored, plus a WASM
fallback, so **Stage A runs in a Linux container with nothing installed**.

### `tools/` at a glance

| File | Purpose |
|---|---|
| `build_from_spec.py` | Declarative spec JSON → project (first choice for ordinary screens) |
| `spec_preview.py` | spec JSON → HTML design-time preview (no build; audits missing assets / line heights) |
| `generate_assets_from_manifest.mjs` | Manifest-driven asset generation (lucide / downloaded SVG / inline SVG) |
| `svg_to_png.mjs` | Any downloaded SVG → PNG (the generic entry for icon-site material) |
| `engine/squareline_engine.py` | Engine layer: property plumbing / nid·guid / events & animation / rebase / font subsetting |
| `layout.py` | Layout helpers: grid tiling / card rows / icon+text / safe text height |
| `label_sizing.py` | Generates the `LABEL_SIZING.md` table (line heights derived from real font `.c` files) |
| `generate_assets*.mjs` | Lucide / hand-drawn SVG → PNG (resvg) |
| `generate_fonts.mjs` | TTF → LVGL subset font trio |
| `inline_mockup.mjs` | Base64-inlines mockup images/fonts → standalone |
| `validate_squareline_project.py` | 10 checks (schema / nid / assets / event graph / occlusion / syntax) |
| `preview_from_project.py` | `.spj` → HTML re-render preview (project agnostic) |
| `sq_catalog.py` / `schema_snapshot.json` | Extract and freeze a schema snapshot from the official examples |
| `vendor_prepare.py` | Side-load per-platform resvg bindings / prune lucide-static |
| `probe_headless_render.py` | **Optional** deep check: render one frame with real LVGL |
| `crop_zoom.py` / `grab_window.py` | Screenshot cropping / window capture helpers |

> `tools/` also holds a few **maintainer tools** (release health check, packaging,
> regression suite) that day-to-day use never touches. If you change the engine, or
> want to publish this package, see **[tools/RELEASE.md](tools/RELEASE.md)**.

---

## Porting to a new panel size/shape

1. Panel geometry lives in the descriptor (`width` / `height` / `shape`: `RECT` |
   `RECTANGLE` | `CIRCLE`); the validator and preview read it from `spj["info"]`
   automatically, so no tool changes are needed.
2. Round screens: follow the "Round-screen design laws" in SKILL.md (chord-width
   formula, radial layout, pre-baked hands, safe area inside the circle). Note that
   values marked `[instance]` are per-project measurements — **recompute them
   for a different panel**.
3. Fonts: put source TTFs in `fonts/`, and list subsets per purpose in the
   descriptor's `fonts` table; the charset is taken from the design spec
   automatically (or point at one with `--spec <file>`).
4. Asset pack: write `"assets": "examples/<Name>/assets"` (repo-relative) in the
   descriptor and a bare command rebuilds it; otherwise use `--assets <dir>` or
   `SQUARELINE_ASSETS`.

## Self-check: after changing the package

```bash
python tools/preflight.py                 # few-second health check: renderer backend / cross-platform bindings /
                                          # schema snapshot / docs-vs-tools consistency / dangling refs / whole-tree line endings
python tools/preflight.py --full          # + the regression suite
python eval/run_regression.py             # rebuild archived projects + Stage A cases, byte-compare
```

After changing `tools/engine/` you **must** run the second step — it asserts the
archived projects are **byte-identical** to the reference answers, which is the
only hard evidence that nothing broke.

Current state (measured on this machine): `preflight.py` **19 checks: 19 pass /
0 fail / 0 skipped**; `eval/run_regression.py` **all green**.

## Offline / container environments

- **No** SquareLine Studio required: the validator's strtype source is
  `tools/schema_snapshot.json`. Installing it only adds a cross-check
  (`SQUARELINE_STUDIO=<install dir>`).
- **No** `npm install` required: `tools/node_modules` is vendored with all-platform
  resvg bindings.
- If `node` is not on PATH, set `SQUARELINE_NODE_BIN=/path/to/node`.

## Known constraints

- The Python-side screenshot helper scripts need Pillow; node-side dependencies are
  declared in `tools/package.json`.
- `.spj` is generated by the builder; saving it in the editor adds new fields such as
  `State_trickle` — that is normal. Do not "fix" the engine serialisation to match
  (the validator already has an allowlist for them).
- `probe_headless_render.py` needs a local lvgl tree; it is **not part of the main
  flow**, so skipping it when the environment lacks one is fine.
- `.workbuddy/` is this project's working memory (for the agent), **not** deliverable
  content, and is excluded by `.gitignore`.
