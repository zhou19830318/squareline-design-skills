# AGENTS.md - SquareLine design toolkit (works with any LLM agent that can run a shell)

Goal: turn a concept image + requirements document into a **SquareLine Studio (.spj) / LVGL project** that opens without
errors, looks like the concept, and provably follows the user's requirements.

You do NOT need to remember the pipeline. **Run `python3 tools/slx.py next <project>` after every step**; it inspects
the project folder and tells you the one next step, why, how, and when it is done. (`tools/` is relative to this toolkit.)

## Start
```bash
python3 tools/slx.py doctor                       # python, Pillow, numpy, node, bundled fonts/icons
python3 tools/slx.py init <Name> --width W --height H --shape CIRCLE|RECT --dir <workspace>
python3 tools/slx.py next <workspace>/<Name>      # <- the loop
```
Never write the project inside the toolkit folder. `<Name>` = ASCII letters/digits/_, starts with a letter.

## Ten rules (each one was learned from a real failure)
1. **Ask before designing** if the panel size/shape, screens or flow are not in the inputs; do not invent them.
2. **Gate 1**: show the user one confirmation table (panel, screens, palette, type scale, every measured/estimated/assumed item, <=5 questions
   with defaults) and wait; then `slx.py gate <proj> 1 --note "..."`. If told "don't ask", use `--assume` and report the assumptions.
3. **Every requirement gets a decision**: `slx.py reqs extract <doc> --proj <proj>`, then `reqs todo` / `reqs set`. A requirement that
   contradicts the concept image is NOT silently resolved - record it (deviation + reason) and tell the user.
4. **Measure, do not eyeball**: `slx.py scan` (elements in panel px), `bbox`, `palette`, `fit-font` (font size from a measured text box).
5. **Never hand-edit the .spj**. Change the spec / manifest / spec doc and rebuild. `build` refuses to run with lint errors.
6. **Run `slx.py check` before `build`**; every finding has a code: `slx.py explain <CODE>`.
7. Only these events are verified to open in SquareLine: CLICKED, PRESSED, RELEASED, PRESS_LOST, VALUE_CHANGED, SCREEN_LOAD_START/LOADED/UNLOAD_START/UNLOADED,
   GESTURE_LEFT/RIGHT/UP/DOWN. **LONG_PRESSED and DOUBLE_CLICKED are NOT** - leave them to C code and record a deviation.
8. All rects are screen-absolute. IMAGE assets are flat paths `assets/<name>.png`. Text is placed by its **ink** centre (use `tools/specbuilder.py`).
9. **The HTML preview is an approximation.** Text/geometry truth is real LVGL: `slx.py truth <proj>` (needs gcc; downloads LVGL once).
   Judge "does it look right" on `verify` screenshots + `diff` against the concept, never on the validator alone.
10. Default is to **redraw** assets. Cropping the concept is allowed only for art the user supplied and wants reused (`raster` source, provenance required).

## Command cheat sheet
| need | command |
|---|---|
| next step | `slx.py next <proj>` |
| find screens on a board / elements on a screen | `slx.py scan <img> --find-screens` / `scan <img> --screen x0 y0 x1 y1 --panel W` |
| colours / coordinates / zoom / text box | `slx.py palette`, `grid`, `crop`, `bbox` |
| font size + label y for a measured text | `slx.py fit-font "<text>" --w W --h H --weight 700 --cy Y` |
| write the spec in Python (widgets, ink-centred text) | `tools/specbuilder.py` (see its docstring) |
| pictures | `slx.py assets <proj>`   (manifest sources: lucide, svg, builtin, raster) |
| lint | `slx.py check <proj>` ; `slx.py explain <CODE>` |
| build / look | `slx.py build <proj>` ; `slx.py verify <proj>` ; `slx.py preview <proj>` |
| compare with concept | `slx.py diff <concept-crop> preview/screens/<s>.png` |
| real-LVGL audit | `slx.py truth <proj>` |
| requirements | `slx.py reqs extract|todo|set|add|check|report` |

## Where the details are
`skills/squareline-ui-pipeline/SKILL.md` (rules, spec essentials), `skills/concept-to-spec/SKILL.md` (reading a concept image),
`skills/squareline-assets/SKILL.md` (icons, rasters, fonts, licences), `skills/squareline-ui-pipeline/references/` (upstream handbook, pitfalls).
Read them only when `slx.py next` points at a stage that needs them.

## Deliver
`.spj` path (+ how to open: SquareLine Studio 1.6.2 -> Open Project; say honestly if you never opened it in Studio), preview images,
`需求追溯矩阵.md` (read the deviations aloud), unconfirmed assumptions, asset licences, known differences from the concept.
