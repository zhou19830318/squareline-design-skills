# PandaPendant - reference example (text only)

A real 37-screen, 360x360 round project built with this toolkit from a 400-line requirements document and two concept boards.
Pictures (face frames cut from the user's board, 23 MB) are NOT included, so this folder cannot be built; it shows the *shape of a finished project*:

- `scripts/gen_spec.py` - the whole spec written with `tools/specbuilder.py` (widgets, ink-centred text, touch feedback, gesture wiring)
- `requirements.json` + `需求追溯矩阵.md` - 73 numbered requirements, each decided (done / deviation / out_of_scope / info), 8 auto-verified
- `PandaPendant设计规格文档.md`, `UI需求清单.md` - the filled templates (tables generated from the spec by `scripts/gen_docs.py`)
- `PandaPendant.layout.intent.json` - where each label's ink should land; `slx.py truth` checks it against the real LVGL
- `scripts/make_faces.py` - the bespoke asset step (full-bleed fur fill); a generic crop would use the manifest's `raster` source instead

Regression: `tests/run_tests.py` regenerates the spec from `gen_spec.py` and compares it with `PandaPendant.spec.json`.
