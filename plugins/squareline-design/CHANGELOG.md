# Changelog

## 0.2.0 - lessons from two full concept-to-project runs (a 2-screen watch face, a 37-screen pendant)

Each item says what went wrong and what now prevents it.

| What went wrong | What changed |
|---|---|
| **The reverse-render preview put text ~11% of the font size too low** (clock baseline 189 vs 181 on the real LVGL); every coordinate in both projects had been tuned to it | `preview_from_project` now lays text out with the font's real `line_height`/`base_line` (CSS ascent/descent overrides): <= 2 px from real LVGL 9.2.2. New `slx.py truth` renders every label with the real LVGL and compares with the design intent (113/113 labels within 1.5 px in the Pendant project) |
| Font size and label y were guessed, built, measured, adjusted (78->76, 70->62) | `slx.py fit-font` solves them from a measured ink box using the real lv_font_conv metrics (reproduces 76 and 62) |
| Concept measured by eye / by hand-written scripts | `slx.py scan` lists a board's screens and a screen's elements in panel px with colours, kind hints, font estimates and a numbered overlay (limits stated: text printed on a big shape is merged into it) |
| Clauses of a 400-line requirements document nearly lost ("no hands" vs a concept frame with a paw; "black background" vs a white shell) | `slx.py reqs`: extract numbered atomic requirements, force a disposition for each (done+evidence / deviation / out_of_scope / blocked / info), 14 auto-verify rule types, `需求追溯矩阵.md`. Dogfooding found one unmet MUST (touch feedback) which was then implemented |
| Builder crashed with a Python traceback (`KeyError: 'number'`), invalid events (`LONG_PRESSED`) could make the project unopenable, chip labels got negative x, 4 screens unreachable in the simulator, 8 dead-end screens in the upstream sample | `slx.py check` (pre-build lint, 40+ coded findings with fixes; `build` refuses on errors), `slx.py explain` error catalog |
| A weaker model would skip steps / gates | `slx.py next` workflow driver + `slx.py gate` approvals recorded in `.slx/state.json`; portable `AGENTS.md` and `docs/UNIVERSAL_PROMPT.md` (no dependency on Claude-specific features) |
| Every project re-implemented chips, switches, sliders, pills ... | `tools/specbuilder.py` widget library; text placed by ink centre; optional touch feedback on every clickable object |
| A custom script was needed to cut a bitmap out of a concept board | manifest source `raster` (crop/size/circle mask/feather) with mandatory provenance |
| Wrong beliefs in my own docs ("a number font holds only the digits", "gradient rings can be baked") | corrected: non-text font = `symbols` U `ranges_num`; progress rings must be live single-colour ARCs |
| Stale files kept shipping inside the project (old fonts, a deleted glow overlay) | `slx build` prunes unreferenced fonts and pictures |
| `verify` moved the preview HTML and fonts silently fell back to a serif face | font paths re-pointed; whole-page screenshot skipped for very tall pages (per-screen shots are the reference) |
| `numpy` was a hidden dependency | `slx.py doctor` checks it |
| No tests | `tests/run_tests.py` (15 tests; byte-identical rebuild of the upstream golden project, lint negative controls, fit-font/scan ground truth, traceability round trip, real-LVGL check when gcc is present) |

Known limits: `scan` is heuristic; `reqs extract` is heuristic (skim and fix); `truth` needs gcc and a one-time LVGL download; no run inside SquareLine Studio itself.

## 0.1.0
First plugin from the upstream `squareline-design-skills` project: commands, three skills, reviewer agent, `slx.py` front door.
