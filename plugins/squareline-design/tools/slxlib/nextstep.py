# -*- coding: utf-8 -*-
"""`slx.py next <proj>`: a workflow driver.

A strong model can keep the whole pipeline in its head; a weaker one (or one with a short context)
skips steps and forgets the gates.  This inspects the PROJECT FOLDER, decides which stage is the first
unfinished one and prints a short, concrete instruction for that stage only.  Call it after every step.

State that cannot be inferred from files (the user's approvals) lives in <proj>/.slx/state.json,
written by `slx.py gate`.
"""
import glob
import json
import os
import sys

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def _newest(paths):
    return max([_mtime(p) for p in paths] or [0.0])


def load_state(proj):
    p = os.path.join(proj, ".slx", "state.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def save_state(proj, st):
    os.makedirs(os.path.join(proj, ".slx"), exist_ok=True)
    with open(os.path.join(proj, ".slx", "state.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def record_gate(proj, n, note, assume):
    import time
    st = load_state(proj)
    st["gate%d" % n] = {"at": time.strftime("%Y-%m-%d %H:%M"), "note": note, "assumed_without_asking": bool(assume)}
    save_state(proj, st)
    print("gate %d recorded%s." % (n, " (ASSUMED - list the assumptions in the final report)" if assume else ""))
    return 0


def _walk(ch):
    for o in ch or []:
        yield o
        for c in _walk(o.get("children")):
            yield c


def inspect(proj, tk):
    """Return (name, stages) where stage = dict(id, title, done, detail, why, do, done_when, optional)."""
    S = []
    def add(**k):
        d = {"optional": False, "detail": ""}
        d.update(k)
        S.append(d)
    specs = sorted(glob.glob(os.path.join(proj, "*.spec.json")))
    if not specs:
        add(id="init", title="create the project", done=False,
            why="there is no <Name>.spec.json here",
            do="python3 tools/slx.py init <Name> --width W --height H --shape CIRCLE|RECT --dir <workspace>   "
               "(<Name>: ASCII letters/digits/_, starts with a letter). Ask the user for the panel size/shape if the concept does not say.",
            done_when="the project folder exists with a *.spec.json")
        return None, S
    spec = json.load(open(specs[0], encoding="utf-8"))
    name = spec["name"]
    st = load_state(proj)
    add(id="init", title="create the project", done=True, detail="%dx%d %s" % (spec["width"], spec["height"], spec["shape"]))

    # ---- intake -------------------------------------------------------------
    cdir = os.path.join(proj, "concept")
    cfiles = os.listdir(cdir) if os.path.isdir(cdir) else []
    imgs = [f for f in cfiles if f.lower().endswith(IMG_EXT)]
    docs = [f for f in cfiles if f.lower().endswith((".md", ".txt", ".docx"))]
    add(id="intake", title="collect the concept images and requirement documents", done=bool(imgs or docs),
        detail="%d image(s), %d document(s) in concept/" % (len(imgs), len(docs)),
        why="nothing to design from yet",
        do="Copy the user's concept image(s) and any requirements document into <proj>/concept/. If the user gave none, ASK; never invent a design.",
        done_when="concept/ has at least one image or document")

    # ---- requirements -------------------------------------------------------
    from . import reqs
    rq = reqs.load(proj)
    if docs and not rq:
        add(id="reqs", title="turn the requirements document into numbered requirements", done=False,
            why="a document was provided but nothing is traced yet; clauses like \"must not show hands\" get lost otherwise",
            do="python3 tools/slx.py reqs extract concept/<doc>.md --proj <proj>   then   python3 tools/slx.py reqs todo <proj>   "
               "and decide each item in batches with `reqs set` (done+evidence / deviation / out_of_scope / blocked / info). "
               "Add anything it missed with `reqs add`.",
            done_when="`slx.py reqs check <proj>` reports no undisposed MUST / MUST_NOT item")
    elif rq:
        todo = [i for i in rq["items"] if i["status"] == "todo" and i["strength"] in ("MUST", "MUST_NOT")]
        add(id="reqs", title="dispose every hard requirement", done=not todo,
            detail="%d requirement(s), %d hard still undecided" % (len(rq["items"]), len(todo)),
            why="every MUST / MUST_NOT needs a decision, otherwise it may silently be missing from the design",
            do="python3 tools/slx.py reqs todo <proj>   then   reqs set <proj> <ids> done --evidence \"screen/object\" | deviation|out_of_scope|blocked --reason \"...\" | info",
            done_when="no undisposed MUST / MUST_NOT item (final check happens again after the build)")

    # ---- analysis docs -------------------------------------------------------
    sd = os.path.join(proj, "%s设计规格文档.md" % name)
    rd = os.path.join(proj, "UI需求清单.md")

    def is_template(p):
        if not os.path.exists(p):
            return True
        t = open(p, encoding="utf-8", errors="ignore").read()
        return ("模板" in t.split("\n", 1)[0]) or t.count("<...>") + t.count("`<") > 3 or len(t) < 800
    skeleton = len(spec["screens"]) <= 1 and any(o.get("text") == "replace me" for sc in spec["screens"] for o in _walk(sc["children"]))
    add(id="analysis", title="analyse the concept: fill the requirement list, the design spec doc and the spec", done=not (is_template(sd) or is_template(rd) or skeleton),
        detail="spec doc %s, requirement list %s, spec %s" % ("TEMPLATE" if is_template(sd) else "filled", "TEMPLATE" if is_template(rd) else "filled",
                                                              "starter skeleton" if skeleton else "%d screen(s)" % len(spec["screens"])),
        why="the design spec doc is the source of truth; the spec must contain the real screens",
        do="Follow the concept-to-spec skill: `slx.py scan <image> --find-screens`, then `scan --screen ...` per screen, `palette`, `fit-font`; "
           "write UI需求清单.md, %s设计规格文档.md, %s.spec.json (use specbuilder.py for widgets) and assets.manifest.json." % (name, name),
        done_when="both docs are filled (no template text) and the spec holds the real screens")

    # ---- gate 1 --------------------------------------------------------------
    g1 = st.get("gate1")
    add(id="gate1", title="GATE 1 - user confirms the analysis", done=bool(g1),
        detail=("approved " + g1["at"] + (" (assumed)" if g1.get("assumed_without_asking") else "")) if g1 else "not recorded",
        why="geometry/palette/screen mistakes here poison every later stage",
        do="Show the user ONE confirmation table: panel, screens + navigation, palette, type scale, every [测得]/[估算]/[假设] item with its effect, "
           "and <=5 open questions with defaults. Wait for the answer, then: python3 tools/slx.py gate <proj> 1 --note \"<what was approved>\". "
           "If the user said 'just do it / don't ask', run it with --assume and put the assumptions in the final report.",
        done_when="`slx.py gate <proj> 1` has been run AFTER the user answered")

    # ---- assets -------------------------------------------------------------
    img_dir = os.path.join(proj, "assets", "images")
    on_disk = set(os.listdir(img_dir)) if os.path.isdir(img_dir) else set()
    used = sorted({os.path.basename(o["asset"])[:-4] for sc in spec["screens"] for o in _walk(sc["children"]) if o.get("type") == "IMAGE" and o.get("asset")})
    mp = os.path.join(proj, "assets.manifest.json")
    manifest = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"icons": []}
    in_manifest = {i["name"] for i in manifest.get("icons", [])}
    missing_files = [u for u in used if (u + ".png") not in on_disk]
    unplanned = [u for u in missing_files if u not in in_manifest]
    add(id="assets", title="generate the pictures", done=not missing_files,
        detail="%d picture(s) used, %d missing%s" % (len(used), len(missing_files), (" (%d not even in the manifest: %s)" % (len(unplanned), ", ".join(unplanned[:4]))) if unplanned else ""),
        why="the spec references pictures that do not exist yet",
        do=("Add the %d unplanned name(s) to assets.manifest.json (source lucide|svg|builtin|raster; icon sites need downloads/*.svg; raster needs a provenance), then " % len(unplanned) if unplanned else "")
           + "python3 tools/slx.py assets <proj>",
        done_when="every IMAGE in the spec has its PNG in assets/images/")
    raster_no_prov = [i["name"] for i in manifest.get("icons", []) if i.get("source") == "raster" and not i.get("provenance")]
    if raster_no_prov:
        add(id="provenance", title="state where raster assets come from", done=False, detail=", ".join(raster_no_prov[:5]),
            why="cropped / user-supplied bitmaps need a recorded origin (licence, ownership)",
            do="Add \"provenance\": \"user concept art (user-provided) / <licence>\" to each raster entry in assets.manifest.json",
            done_when="all raster entries have a provenance")

    # ---- lint ---------------------------------------------------------------
    from . import lint
    f = lint.run(proj, spec, tk)
    errs = [x for x in f if x.level == "ERROR"]
    add(id="lint", title="pre-build check passes", done=not errs, detail="%d error(s), %d warning(s)" % (len(errs), len(f) - len(errs)),
        why="errors here become tracebacks or an unopenable project later",
        do="python3 tools/slx.py check <proj>   - fix every ERROR (each line says how; `slx.py explain <CODE>` for more). Warnings are advice.",
        done_when="`slx.py check` reports 0 errors")

    # ---- gate 2 + build -------------------------------------------------------
    g2 = st.get("gate2")
    add(id="gate2", title="GATE 2 - user has seen the preview", done=bool(g2), optional=True,
        detail=("approved " + g2["at"]) if g2 else "not recorded",
        why="coordinates are cheapest to change before the build",
        do="python3 tools/slx.py preview <proj>, show preview/spec_preview.png next to the concept (slx.py sidebyside), then `slx.py gate <proj> 2` once the user agrees.",
        done_when="recorded (optional for tiny projects)")
    spj = os.path.join(proj, "squareline", name, "%s.spj" % name)
    inputs = [specs[0], mp, sd] + glob.glob(os.path.join(img_dir, "*"))
    add(id="build", title="build the project", done=os.path.exists(spj) and _mtime(spj) >= _newest(inputs),
        detail="up to date" if (os.path.exists(spj) and _mtime(spj) >= _newest(inputs)) else ("not built" if not os.path.exists(spj) else "inputs changed after the last build"),
        why="the .spj is generated from spec + manifest + docs; never hand-edit it",
        do="python3 tools/slx.py build <proj>", done_when="the validator prints `OK - project validated, no problems found`")
    shots = glob.glob(os.path.join(proj, "preview", "screens", "*.png")) + [os.path.join(proj, "preview", "project_preview.png")]
    vfresh = _newest(shots) >= _mtime(spj) and os.path.exists(spj)        # big projects only get per-screen shots (page too tall)
    add(id="verify", title="reverse-render and look at every screen", done=vfresh,
        detail="preview/screens/*.png %s" % ("current" if vfresh else "missing or stale"),
        why="the validator proves the file is sound, not that it looks right",
        do="python3 tools/slx.py verify <proj>   then look at preview/screens/*.png",
        done_when="every screen has been looked at")
    th = os.path.join(proj, "preview", "truth_labels.json")
    add(id="truth", title="audit text positions with the real LVGL (recommended)", done=os.path.exists(th) and _mtime(th) >= _mtime(spj), optional=True,
        detail="needs gcc; downloads LVGL once", why="the HTML preview approximates LVGL; this is ground truth for text placement",
        do="python3 tools/slx.py truth <proj>   (add --lvgl <path> if LVGL source is already on disk)", done_when="0 labels off / blank")
    diffs = [p for p in glob.glob(os.path.join(proj, "preview", "diff*.png"))]
    add(id="compare", title="compare the result with the concept image", done=(not imgs) or (bool(diffs) and _newest(diffs) >= _mtime(spj)), optional=True,
        detail="%d comparison image(s)" % len(diffs), why="catches wrong sizes/colours/positions the checks cannot know",
        do="for each screen: python3 tools/slx.py diff <concept-crop> preview/screens/<screen>.png --out preview/diff_<screen>.png ; measure text with `slx.py bbox` on both; "
           "or hand the screens to the design-reviewer agent. Fix with spec edits, rebuild.",
        done_when="no unexplained difference larger than ~3 px / a clear colour")

    # ---- requirements final ---------------------------------------------------
    if rq:
        fails, todo = 0, 0
        for it in rq["items"]:
            if it.get("verify"):
                ok, _m = reqs.verify(it["verify"], spec, proj, tk)
                fails += (ok is False)
            todo += (it["status"] == "todo" and it["strength"] in ("MUST", "MUST_NOT"))
        add(id="reqs_final", title="requirement traceability is green", done=(fails == 0 and todo == 0),
            detail="%d auto-verify failure(s), %d undisposed hard requirement(s)" % (fails, todo),
            why="the matrix is what proves the delivered project follows the user's document",
            do="python3 tools/slx.py reqs check <proj> ; fix failures in the spec (or change the disposition honestly) ; python3 tools/slx.py reqs report <proj>",
            done_when="`reqs check` exits 0 and 需求追溯矩阵.md is written")
    return name, S


DELIVER = """\
ALL STAGES DONE. Deliver:
  1. the .spj path and how to open it (SquareLine Studio 1.6.2 -> Open Project); say honestly if you never opened it in Studio
  2. preview images (preview/*.png)
  3. 需求追溯矩阵.md - and say out loud every deviation / out_of_scope / blocked item
  4. assumptions that the user did not confirm (gate notes) and open questions
  5. asset sources and licences (attribution items!)
  6. known differences from the concept (font, gradients, effects the engine cannot draw) and why"""


def run(proj, tk, as_json=False):
    name, stages = inspect(proj, tk)
    first = next((s for s in stages if not s["done"] and not s["optional"]), None)
    if as_json:
        print(json.dumps({"project": name, "next": first and first["id"], "stages": stages}, ensure_ascii=False, indent=1))
        return 0
    print("SquareLine project: %s   (%s)" % (name or "<not created>", proj))
    for i, s in enumerate(stages, 1):
        mark = "x" if s["done"] else ("~" if s["optional"] else " ")
        print(" [%s] %-9s %s%s" % (mark, s["id"], s["title"], ("  - " + s["detail"]) if s["detail"] else ""))
    print("     ([x] done  [ ] to do  [~] optional / recommended)")
    if first is None:
        opt = next((s for s in stages if not s["done"]), None)
        if opt:
            print("\nOptional but recommended: %s\n  do: %s" % (opt["title"], opt["do"]))
        print("\n" + DELIVER)
        return 0
    print("\nNEXT -> %s: %s\n  why : %s\n  do  : %s\n  done: %s" % (first["id"], first["title"], first["why"], first["do"], first["done_when"]))
    print("\nAfter this step run `python3 tools/slx.py next %s` again." % proj)
    return 0
