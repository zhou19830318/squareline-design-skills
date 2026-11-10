#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slx.py - workspace-aware front door for the SquareLine toolkit (plugin edition).

The original tools assume the project lives INSIDE the toolkit tree.  In a plugin the
toolkit is read-only and the project lives in the user's workspace, so every call
needs explicit --assets/--out paths.  This wrapper bakes that in, so an agent runs
one short command instead of assembling flags (and getting them wrong).

Project folder convention  (<proj> = <workspace>/<Name>/)
    concept/                  concept images (input)
    UI需求清单.md              requirement list      (input, from templates/)
    <Name>设计规格文档.md       design spec doc       (source of truth)
    assets.manifest.json      icon/image manifest   (Stage A input)
    downloads/                SVGs fetched from icon sites
    <Name>.spec.json          declarative screen spec (Stage C input)
    assets/images/            generated PNGs        (Stage A output)
    squareline/<Name>/        the SquareLine project (.spj)  (Stage C output)
    preview/                  spec_preview / project preview HTML

Commands
    init     <Name> [--dir PARENT] [--width W] [--height H] [--shape RECT|CIRCLE]
    assets   <proj>                 manifest -> PNGs (lucide/svg/builtin via node; "raster" = crop/resize/mask a user bitmap, provenance required)
    preview  <proj> [--scale S]     spec -> HTML contact sheet (no build)
    build    <proj>                 spec -> .spj, then validate
    verify   <proj> [--scale S]     validate + reverse-render the built .spj
    palette  <image> [--n 8]        dominant colours of a concept image
    grid     <image> [--step 50] [--out f.png]   overlay a labelled pixel grid
    crop     <image> x0 y0 x1 y1 [--zoom 3] [--out f.png]
    shot     <file.html> [--out f.png] [--width 1400]   screenshot a preview (needs playwright+chromium)
    sidebyside <left.png> <right.png> [--out f.png]     concept-vs-render comparison sheet
    bbox     <image> x0 y0 x1 y1 [--color #RRGGBB] [--tol 30] [--scale S]
                                    bounding box of pixels matching a colour (default near-white) inside a region;
                                    --scale converts image px to panel px (e.g. 0.6) -> measure text size/position
    diff     <concept.png> <render.png> [--out f.png]   concept | render | amplified-difference triptych + mean error
    (verify also writes preview/screens/<screen>.png, one exact-size PNG per screen, for `diff`)
    check    <proj> [--json]        pre-build lint: schema, references, fonts/symbols, event whitelist, picture
                                    paths/sizes, round-screen layout, navigation.  `build` runs it and refuses on errors.
    explain  <CODE|text>            what a lint code / common build message means and how to fix it
    scan     <image> --find-screens | --screen x0 y0 x1 y1 --panel W [--shape circle]
                                    detect a board's screens / one screen's elements -> JSON in PANEL px + numbered overlay
    fit-font "<text>" --w W --h H [--weight 700] [--cy Y] [--ranges <spec ranges_num|ranges_text>] [--prefer height]
                                    font size (bundled Noto) that reproduces a measured ink box, + LABEL rect y
    next     <proj> [--json]        WORKFLOW DRIVER: inspects the project, prints only the next step (run it after every step)
    gate     <proj> 1|2 [--note ..] [--assume]   record the user's approval (1 = analysis, 2 = preview)
    truth    <proj> [--lvgl <src>] [--tol 2.5]   OPTIONAL: render every label with the REAL LVGL (gcc + LVGL source, auto-downloaded once)
                                    and compare the ink position with the design intent -- ground truth, the HTML preview is only an approximation
    reqs     extract|todo|set|add|check|report   requirements traceability: turn the user's document into numbered
                                    atomic requirements, force a disposition for each, auto-verify, write the matrix
    setup                           install the Node dependencies for THIS machine (npm ci); other commands do it automatically
    doctor                          check node / python / PIL / bundled deps
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
NODE = os.environ.get("SQUARELINE_NODE_BIN") or "node"


def die(msg, code=2):
    print("slx: " + msg, file=sys.stderr)
    sys.exit(code)


def run(cmd, cwd=None):
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=cwd)


def read_spec(proj):
    proj = os.path.abspath(proj)
    specs = [f for f in os.listdir(proj) if f.endswith(".spec.json")]
    if not specs:
        die("no *.spec.json in %s (run `slx.py init` first or write the spec)" % proj)
    spec = os.path.join(proj, sorted(specs)[0])
    with open(spec, encoding="utf-8") as fh:
        data = json.load(fh)
    return proj, spec, data


def opt(args, flag, default=None, cast=str):
    if flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            die("%s needs a value" % flag)
        return cast(args[i + 1])
    return default


# ------------------------------------------------------------------ init --
def spec_skeleton(name, w, h, shape):
    """Smallest spec that builds clean: 2 screens, a swipe pair, 1 label each."""
    r = min(w, h) // 2
    inset = int(r * 0.30) if shape == "CIRCLE" else 24
    big = max(24, min(w, h) // 9)
    body = max(16, min(w, h) // 22)
    lh = lambda size: -(-size * 135 // 100)   # ceil(size * 1.35)
    return {
        "$schema": "squareline-spec/1",
        "name": name, "width": w, "height": h, "shape": shape,
        "description": "%s - %dx%d %s (concept-image project)" % (name, w, h, shape.lower()),
        "assets_subdir": "images",
        "spec_docs": ["%s设计规格文档.md" % name],
        "theme_dark": True,
        "palette": {"BG": "#000000", "CARD": "#1C1C1E", "DIM": "#98989F",
                    "WHITE": "#FFFFFF", "ACCENT": "#30D158"},
        "fonts": [
            {"codename": "Title%d" % big, "ttf": "noto-sans-sc-v40-chinese-simplified-500.ttf",
             "size": big, "kind": "text"},
            {"codename": "Body%d" % body, "ttf": "noto-sans-sc-v40-chinese-simplified-regular.ttf",
             "size": body, "kind": "text"},
        ],
        "ranges_text": ["0x20-0x7E", "0x00B0", "0x3001", "0x3002"],
        "ranges_num": ["0x20-0x7E", "0x00B0"],
        "symbols": {"number": "0123456789:.%"},
        "screens": [
            {"name": "home", "bg": "BG", "children": [
                {"type": "LABEL", "name": "title", "rect": [inset, h // 2 - lh(big) // 2, w - 2 * inset, lh(big)],
                 "text": "Hello", "font": "Title%d" % big, "color": "WHITE", "align": "CENTER"},
                {"type": "LABEL", "name": "hint", "rect": [inset, h // 2 + lh(big), w - 2 * inset, lh(body)],
                 "text": "replace me", "font": "Body%d" % body, "color": "DIM", "align": "CENTER"}]},
        ],
        "order": ["home"],
        "initial_screen": "home",
    }


def cmd_init(args):
    pos = [a for a in args if not a.startswith("--")]
    # strip option values from positional list
    vals = {opt(args, f) for f in ("--dir", "--width", "--height", "--shape") if f in args}
    pos = [a for a in pos if a not in vals]
    if not pos:
        die("usage: slx.py init <Name> [--dir PARENT] [--width W] [--height H] [--shape RECT|CIRCLE]")
    name = pos[0]
    if not name.replace("_", "").isalnum() or not name[0].isalpha():
        die("project name must be ASCII letters/digits/underscore, starting with a letter: %r" % name)
    parent = os.path.abspath(opt(args, "--dir", os.getcwd()))
    w = opt(args, "--width", 456, int)
    h = opt(args, "--height", 456, int)
    shape = opt(args, "--shape", "CIRCLE" if w == h else "RECT").upper()
    if shape not in ("RECT", "CIRCLE"):
        die("--shape must be RECT or CIRCLE")
    if shape == "CIRCLE" and w != h:
        die("CIRCLE panels must be square (got %dx%d)" % (w, h))
    proj = os.path.join(parent, name)
    if os.path.exists(proj) and os.listdir(proj):
        die("%s already exists and is not empty" % proj)
    for d in ("concept", "downloads", os.path.join("assets", "images"), "preview"):
        os.makedirs(os.path.join(proj, d), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "templates", "UI需求清单模板.md"), os.path.join(proj, "UI需求清单.md"))
    shutil.copy(os.path.join(ROOT, "templates", "设计规格文档模板.md"),
                os.path.join(proj, "%s设计规格文档.md" % name))
    manifest = {"defaults": {"size": 44, "color": "#FFFFFF", "stroke_width": 2}, "icons": []}
    with open(os.path.join(proj, "assets.manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(proj, "%s.spec.json" % name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(spec_skeleton(name, w, h, shape), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("created %s  (%dx%d %s)" % (proj, w, h, shape))
    print("next: put concept image(s) in %s/concept/, then analyse them." % proj)
    return 0


# ------------------------------------------------------- pipeline stages --
def cmd_assets(args):
    """manifest -> PNGs.  lucide / svg / builtin go through the node converter; raster entries are cut with Pillow."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    proj, _, _ = read_spec(args[0])
    ensure_node_deps()
    man = os.path.join(proj, "assets.manifest.json")
    if not os.path.exists(man):
        die("missing " + man)
    data = json.load(open(man, encoding="utf-8"))
    vector = [i for i in data.get("icons", []) if i.get("source") != "raster"]
    raster = [i for i in data.get("icons", []) if i.get("source") == "raster"]
    rc = 0
    out = os.path.join(proj, "assets", "images")
    if vector:
        tmp = os.path.join(proj, ".assets.vector.tmp.json")           # same folder: relative `file` paths keep working
        json.dump(dict(data, icons=vector), open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        try:
            rc = run([NODE, os.path.join(HERE, "generate_assets_from_manifest.mjs"), tmp, "--out", out])
        finally:
            os.remove(tmp)
    if raster:
        from slxlib import raster as rmod
        prov = {}
        for e in raster:
            if not e.get("provenance"):
                print("ERROR raster %s: \"provenance\" is required (where does this bitmap come from? who may use it?)" % e["name"])
                rc = rc or 1
                continue
            try:
                p, sz = rmod.render(e, proj)
                prov[e["name"]] = {"file": e["file"], "crop": e.get("crop"), "provenance": e["provenance"]}
                print("ok  %s.png  %dx%d  (raster <- %s)" % (e["name"], sz[0], sz[1], e["file"]))
            except Exception as ex:                                    # noqa: BLE001 - report, keep going
                print("ERROR raster %s: %s" % (e["name"], ex))
                rc = rc or 1
        if prov:
            json.dump(prov, open(os.path.join(proj, "assets.provenance.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("raster provenance written to assets.provenance.json (%d)" % len(prov))
    return rc


def cmd_preview(args):
    proj, spec, _ = read_spec(args[0])
    out = os.path.join(proj, "preview", "spec_preview.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = [PY, os.path.join(HERE, "spec_preview.py"), spec, "--assets", os.path.join(proj, "assets"),
           "--out", out, "--scale", str(opt(args, "--scale", 1.0, float))]
    if "--strict" in args:
        cmd.append("--strict")
    rc = run(cmd)
    print("preview:", out)
    if rc == 0 and try_shot(out, out[:-5] + ".png"):
        print("preview png:", out[:-5] + ".png")
    return rc


def prune_stale_fonts(out, spec):
    """The builder only adds files. After a font is renamed/resized in the spec its old
    ui_font_* triple stays behind as dead weight in the delivered project: remove those."""
    fdir = os.path.join(out, "assets", "fonts")
    if not os.path.isdir(fdir):
        return
    keep = {"ui_font_%s.%s" % (f["codename"], e) for f in spec.get("fonts", []) for e in ("c", "bin", "fcfg")}
    keep |= {f["ttf"] for f in spec.get("fonts", [])}
    gone = [n for n in sorted(os.listdir(fdir)) if n not in keep]
    for n in gone:
        os.remove(os.path.join(fdir, n))
    if gone:
        print("pruned %d stale font file(s): %s" % (len(gone), ", ".join(gone)))


def prune_stale_images(out, spec):
    """Same story for pictures: an asset dropped from the spec (e.g. a deleted overlay) would
    otherwise keep shipping inside the delivered project."""
    adir = os.path.join(out, "assets")
    if not os.path.isdir(adir):
        return

    def walk(ch):
        for o in ch or []:
            yield o
            yield from walk(o.get("children"))
    used = {os.path.basename(o["asset"]) for sc in spec["screens"] for o in walk(sc["children"])
            if o.get("type") == "IMAGE" and o.get("asset")}
    gone = [n for n in sorted(os.listdir(adir))
            if n.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")) and n not in used]
    for n in gone:
        os.remove(os.path.join(adir, n))
    if gone:
        print("pruned %d unreferenced image(s): %s" % (len(gone), ", ".join(gone)))


def cmd_build(args):
    proj, spec, data = read_spec(args[0])
    ensure_node_deps()
    errs, _w = run_lint(args[0], quiet=("--force" in args))
    if errs and "--force" not in args:
        print("build refused: fix the %d error(s) above first (or `build --force` to try anyway)." % errs)
        return 3
    name = data["name"]
    out = os.path.join(proj, "squareline", name)
    if data.get("assets"):
        print("note: spec has an \"assets\" key; the --assets flag below overrides it.")
    rc = run([PY, os.path.join(HERE, "build_from_spec.py"), spec,
              "--assets", os.path.join(proj, "assets"), "--out", out])
    if rc != 0:
        return rc
    prune_stale_fonts(out, data)
    prune_stale_images(out, data)
    return run([PY, os.path.join(HERE, "validate_squareline_project.py"), out])


def cmd_verify(args):
    proj, _, data = read_spec(args[0])
    out = os.path.join(proj, "squareline", data["name"])
    if not os.path.isdir(out):
        die("not built yet: " + out)
    rc = run([PY, os.path.join(HERE, "validate_squareline_project.py"), out])
    rc2 = run([PY, os.path.join(HERE, "preview_from_project.py"), out,
               "--scale", str(opt(args, "--scale", 1.0, float))])
    html = os.path.join(out, "preview_from_project.html")
    if os.path.exists(html):
        dst = os.path.join(proj, "preview", "project_preview.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # Keep the .spj folder clean, but the page loads its fonts via a relative
        # assets/fonts/ path -- re-point it, or text silently falls back to a serif face.
        with open(html, encoding="utf-8") as fh:
            page = fh.read()
        rel = os.path.relpath(os.path.join(out, "assets", "fonts"), os.path.dirname(dst)).replace(os.sep, "/")
        page = page.replace("url('assets/fonts/", "url('%s/" % rel)
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(page)
        os.remove(html)
        print("preview:", dst)
        if try_shot(dst, dst[:-5] + ".png"):
            print("preview png:", dst[:-5] + ".png")
        elif len(data.get("screens", [])) > 12:
            print("note: the whole-page screenshot is skipped for big projects (page taller than the browser limit); use preview/screens/*.png")
        names = [sc["name"] for sc in data["screens"]]
        sdir = os.path.join(proj, "preview", "screens")
        if shoot_screens(dst, sdir, names):
            print("per-screen:", sdir)
    return rc or rc2


# ------------------------------------------------------ concept-image aids --
def cmd_palette(args):
    from PIL import Image
    img = Image.open(args[0]).convert("RGB")
    img.thumbnail((256, 256))
    n = opt(args, "--n", 8, int)
    q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    print("source size: %dx%d (analysed at thumbnail size)" % Image.open(args[0]).size)
    for c, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        print("#%02X%02X%02X  %5.1f%%" % (r, g, b, 100.0 * c / total))
    return 0


def cmd_grid(args):
    from PIL import Image, ImageDraw
    src = args[0]
    img = Image.open(src).convert("RGB")
    step = opt(args, "--step", 50, int)
    out = opt(args, "--out", os.path.splitext(src)[0] + "_grid.png")
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, img.width, step):
        d.line([(x, 0), (x, img.height)], fill=(255, 0, 255, 90 if x % (step * 2) else 150), width=1)
        d.text((x + 2, 2), str(x), fill=(255, 255, 0, 255))
    for y in range(0, img.height, step):
        d.line([(0, y), (img.width, y)], fill=(0, 255, 255, 90 if y % (step * 2) else 150), width=1)
        d.text((2, y + 2), str(y), fill=(255, 255, 0, 255))
    img.save(out)
    print("saved %s (%dx%d, step %d)" % (out, img.width, img.height, step))
    return 0


def cmd_crop(args):
    from PIL import Image
    pos = [a for a in args if not a.startswith("--")]
    src = pos[0]
    x0, y0, x1, y1 = (int(v) for v in pos[1:5])
    zoom = opt(args, "--zoom", 3, int)
    out = opt(args, "--out", os.path.splitext(src)[0] + "_crop.png")
    img = Image.open(src).crop((x0, y0, x1, y1))
    img = img.resize((img.width * zoom, img.height * zoom), Image.LANCZOS)
    img.save(out)
    print("saved %s (%dx%d)" % (out, img.width, img.height))
    return 0


def cmd_bbox(args):
    import numpy as np
    from PIL import Image
    pos = [a for a in args if not a.startswith("--")]
    vals = {opt(args, f) for f in ("--color", "--tol", "--scale") if f in args}
    pos = [a for a in pos if a not in vals]
    img = np.asarray(Image.open(pos[0]).convert("RGB")).astype(int)
    x0, y0, x1, y1 = (int(v) for v in pos[1:5])
    tol = opt(args, "--tol", 30, int)
    sc = opt(args, "--scale", 1.0, float)
    col = opt(args, "--color", None)
    sub = img[y0:y1, x0:x1]
    if col:
        c = [int(col.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
        m = (abs(sub - c) <= tol).all(axis=2)
    else:
        m = (sub > 255 - tol - 0).all(axis=2) if tol < 100 else (sub > 200).all(axis=2)
    ys, xs = np.where(m)
    if not len(xs):
        print("no matching pixels in region")
        return 1
    bx0, by0, bx1, by1 = xs.min() + x0, ys.min() + y0, xs.max() + x0, ys.max() + y0
    print("image px : x %d..%d  y %d..%d  (w=%d h=%d)" % (bx0, bx1, by0, by1, bx1 - bx0 + 1, by1 - by0 + 1))
    if sc != 1.0:
        f = lambda v: round(v * sc, 1)
        print("panel px : x %s..%s  y %s..%s  (w=%s h=%s)  @scale %g" % (
            f(bx0), f(bx1), f(by0), f(by1), f(bx1 - bx0 + 1), f(by1 - by0 + 1), sc))
    return 0


def cmd_diff(args):
    import numpy as np
    from PIL import Image, ImageChops
    pos = [a for a in args if not a.startswith("--")]
    r = Image.open(pos[1]).convert("RGB")
    a = Image.open(pos[0]).convert("RGB").resize(r.size, Image.LANCZOS)
    d = ImageChops.difference(a, r)
    sheet = Image.new("RGB", (r.width * 3, r.height))
    sheet.paste(a, (0, 0)); sheet.paste(r, (r.width, 0))
    sheet.paste(d.point(lambda v: min(255, v * 3)), (2 * r.width, 0))
    out = opt(args, "--out", "diff.png")
    sheet.save(out)
    print("saved %s | mean abs diff %.2f / 255 (gradients, glow and font shapes always contribute)" % (
        out, float(np.asarray(d.convert("L")).mean())))
    return 0


def shoot_screens(page_html, out_dir, names):
    """One exact-size PNG per .screen element, named after the screens."""
    try:
        from playwright.sync_api import sync_playwright
        os.makedirs(out_dir, exist_ok=True)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1400, "height": 900})
            pg.goto("file://" + os.path.abspath(page_html))
            pg.wait_for_timeout(400)
            els = pg.query_selector_all(".screen")
            for el, n in zip(els, names):
                el.screenshot(path=os.path.join(out_dir, n + ".png"))
            b.close()
        return True
    except Exception as e:
        print("slx: per-screen shots skipped (%s)" % str(e).splitlines()[0][:100])
        return False


def try_shot(html, png, width=1400):
    """Best-effort screenshot; returns True on success, never raises."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": width, "height": 900})
            pg.goto("file://" + os.path.abspath(html))
            pg.wait_for_timeout(300)
            pg.screenshot(path=png, full_page=True)
            b.close()
        return True
    except Exception as e:  # browser binary missing, sandbox limits, ...
        print("slx: screenshot skipped (%s)" % str(e).splitlines()[0][:120])
        return False


def cmd_shot(args):
    pos = [a for a in args if not a.startswith("--")]
    html = pos[0]
    out = opt(args, "--out", os.path.splitext(html)[0] + ".png")
    if not try_shot(html, out, opt(args, "--width", 1400, int)):
        die("cannot screenshot here (playwright/chromium unavailable). Open %s in a browser "
            "instead, or use Claude in Chrome to look at it." % html, 3)
    print("saved", out)
    return 0


def cmd_sidebyside(args):
    from PIL import Image
    pos = [a for a in args if not a.startswith("--")]
    a, b = Image.open(pos[0]).convert("RGB"), Image.open(pos[1]).convert("RGB")
    h = min(max(a.height, b.height), 1400)
    a = a.resize((max(1, a.width * h // a.height), h), Image.LANCZOS)
    b = b.resize((max(1, b.width * h // b.height), h), Image.LANCZOS)
    sheet = Image.new("RGB", (a.width + b.width + 24, h), (40, 40, 48))
    sheet.paste(a, (0, 0))
    sheet.paste(b, (a.width + 24, 0))
    out = opt(args, "--out", "sidebyside.png")
    sheet.save(out)
    print("saved %s (left=%s right=%s)" % (out, os.path.basename(pos[0]), os.path.basename(pos[1])))
    return 0


def ensure_node_deps():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import deps
    if not deps.ensure():
        sys.exit(4)


def cmd_setup(_args):
    """Install the Node dependencies for THIS machine (npm ci from the lock file)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import deps
    ok = deps.ensure()
    print("Node dependencies: %s" % ("ready" if ok else "NOT installed"))
    return 0 if ok else 4


def run_lint(proj_arg, quiet=False, as_json=False):
    """Pre-build lint (slxlib.lint).  Returns (n_errors, n_warnings)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import lint
    proj, _, spec = read_spec(proj_arg)
    findings = lint.run(proj, spec, ROOT)
    errs = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level != "ERROR"]
    if as_json:
        print(json.dumps({"errors": [f.as_dict() for f in errs], "warnings": [f.as_dict() for f in warns]}, ensure_ascii=False, indent=1))
    elif not quiet:
        shown = {}
        for f in errs + warns:                       # collapse floods: same code in the same screen
            key = (f.code, f.where.split("/")[0])
            shown.setdefault(key, []).append(f)
        for key, fs in shown.items():
            print(fs[0].line())
            if len(fs) > 1:
                print("      (+%d more %s in %s: %s)" % (len(fs) - 1, key[0], key[1],
                                                         ", ".join(f.where.split("/")[-1] for f in fs[1:6]) + ("..." if len(fs) > 6 else "")))
        print("check: %d screen(s), %d error(s), %d warning(s)%s" % (
            len(spec.get("screens", [])), len(errs), len(warns), "" if not errs else "   (slx.py explain <CODE> for details)"))
    return len(errs), len(warns)


def cmd_check(args):
    """Design lint the .spj validator cannot do: schema, references, layout on the round screen, navigation."""
    e, _w = run_lint(args[0], as_json="--json" in args)
    return 1 if e else 0


def cmd_explain(args):
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib.catalog import CATALOG, lookup
    q = " ".join(args).strip()
    hits = list(CATALOG.items()) if q in ("", "--all") else lookup(q)
    if not hits:
        print("no catalog entry for %r. Try a message fragment or a code like E-FONT-KIND." % q)
        return 1
    for code, (title, why, fix) in hits:
        print("%s  --  %s\n  why: %s\n  fix: %s\n" % (code, title, why, fix))
    return 0


def cmd_reqs(args):
    """Requirements traceability (slxlib.reqs): extract -> dispose -> auto-verify -> matrix."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import reqs
    if not args:
        print("usage: slx.py reqs extract <file...> --proj <proj> | todo <proj> | set <proj> <ids> <status> [--evidence ..] [--reason ..] "
              "[--verify '{json}'] | add <proj> \"text\" [--strength MUST] | check <proj> | report <proj>")
        return 2
    sub, rest = args[0], args[1:]
    if sub == "extract":
        proj = os.path.abspath(opt(rest, "--proj", os.getcwd()))
        files = [a for a in rest if not a.startswith("--") and a != opt(rest, "--proj")]
        if not files:
            die("reqs extract needs at least one .md/.txt file")
        return reqs.cmd_extract(proj, [os.path.abspath(f) for f in files])
    proj = os.path.abspath(rest[0]) if rest else die("project folder needed")
    if sub == "todo":
        return reqs.cmd_todo(proj, opt(rest, "--n", 15, int))
    if sub == "set":
        vals = {opt(rest, f) for f in ("--evidence", "--reason", "--verify") if f in rest}
        pos = [a for a in rest[1:] if not a.startswith("--") and a not in vals]
        status, ids = pos[-1], pos[:-1]
        if status not in reqs.STATUSES:
            die("status must be one of %s" % ", ".join(reqs.STATUSES))
        return reqs.cmd_set(proj, ids, status, opt(rest, "--evidence", ""), opt(rest, "--reason", ""), opt(rest, "--verify"))
    if sub == "add":
        vals = {opt(rest, f) for f in ("--strength",) if f in rest}
        pos = [a for a in rest[1:] if not a.startswith("--") and a not in vals]
        return reqs.cmd_add(proj, pos[0], opt(rest, "--strength", "MUST"))
    if sub in ("check", "report"):
        _p, _s, spec = read_spec(proj)
        if sub == "check":
            return reqs.cmd_check(proj, spec, ROOT)
        return reqs.cmd_report(proj, spec["name"])
    die("unknown reqs subcommand %r" % sub)


def cmd_scan(args):
    """Detect the screens of a design board / the elements of one screen (numbers + numbered overlay)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import scan
    img = [a for a in args if not a.startswith("--")][0]
    if "--find-screens" in args:
        r = scan.find_screens(img, opt(args, "--tol", 28, int))
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if "--screen" not in args:
        die("scan needs --find-screens or --screen x0 y0 x1 y1 --panel W")
    i = args.index("--screen")
    box = [int(v) for v in args[i + 1:i + 5]]
    out = os.path.abspath(opt(args, "--out", os.path.dirname(os.path.abspath(img))))
    os.makedirs(out, exist_ok=True)
    res, crop = scan.scan(img, box, opt(args, "--panel", 360, int), opt(args, "--shape", "auto"), opt(args, "--tol", 50, int))
    tag = os.path.splitext(os.path.basename(img))[0] + "_%d_%d" % (box[0], box[1])
    jp, op = os.path.join(out, "scan_%s.json" % tag), os.path.join(out, "scan_%s.png" % tag)
    json.dump(res, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    scan.overlay(crop, res, op)
    print("scale image->panel: %s | background %s | %d element(s)" % (res["scale_image_to_panel"], res["background"], len(res["elements"])))
    for e in res["elements"]:
        extra = "  ~%dpx font" % e["est_font_px_from_height"] if "est_font_px_from_height" in e else ""
        print("  #%-2d %-18s rect %-22s centre %-16s %s%s" % (e["id"], e["kind_hint"], e["rect_panel"], e["center_panel"], e["color"], extra))
    for n in res.get("notes", []):
        print("  NOTE:", n)
    print("  (elements missing or merged? try --tol 80 for glow/gradients, or --tol 28 for faint grey-on-black)")
    print("wrote", jp, "and", op, "-> look at the overlay and NAME each numbered box (icon / text / ring ...)")
    return 0


def cmd_fitfont(args):
    """Font size that reproduces a measured ink box of a text."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import fontfit
    ensure_node_deps()
    vals = {opt(args, f) for f in ("--w", "--h", "--weight", "--cy", "--cx", "--box-w", "--ranges", "--prefer") if f in args}
    pos = [a for a in args if not a.startswith("--") and a not in vals]
    if not pos:
        die("usage: slx.py fit-font \"<text>\" --w W --h H [--weight 700|500|400] [--cy Y] [--ranges R] [--prefer width|height]")
    rep, _ = fontfit.report(ROOT, pos[0], opt(args, "--w", None, float), opt(args, "--h", None, float), opt(args, "--weight", "400"),
                            opt(args, "--cy", None, float), opt(args, "--cx", None, float), opt(args, "--box-w", None, int), NODE,
                            opt(args, "--ranges", "0x20-0x7E,0x00B0"), opt(args, "--prefer", "width"))
    print(rep)
    return 0


def cmd_truth(args):
    """Render every LABEL with the REAL LVGL and compare the ink position with the design intent."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import truth
    proj, _sp, spec = read_spec(args[0])
    res = truth.measure(proj, spec, ROOT, opt(args, "--lvgl"))
    bad, ok, blank = truth.report(proj, spec, res, opt(args, "--tol", 2.5, float))
    json.dump(res, open(os.path.join(proj, "preview", "truth_labels.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("real-LVGL label audit: %d label(s) | within tolerance of the design intent: %d | off: %d | rendered blank: %d" % (len(res), ok, len(bad), len(blank)))
    for r in bad[:25]:
        print("  OFF  %s/%s %r: ink centre y=%.1f, intent %.1f (%+.1f px)  -> move rect.y by %+d" % (
            r["screen"], r["object"], r["text"][:14], r["ink_cy"], r["intent_cy"], r["dy"], -round(r["dy"])))
    for r in blank[:10]:
        print("  BLANK %s/%s %r: nothing drawn (missing glyphs? wrong font?)" % (r["screen"], r["object"], r["text"][:14]))
    for r in res:
        for n in r.get("notes", []):
            print("  NOTE %s/%s: %s" % (r["screen"], r["object"], n))
    print("details: preview/truth_labels.json")
    return 1 if (bad or blank) else 0


def cmd_next(args):
    """Workflow driver: inspect the project folder and print only the next step."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import nextstep
    return nextstep.run(os.path.abspath(args[0]), ROOT, "--json" in args)


def cmd_gate(args):
    """Record a user approval (gate 1 = analysis confirmed, gate 2 = preview seen)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from slxlib import nextstep
    pos = [a for a in args if not a.startswith("--")]
    if len(pos) < 2 or pos[1] not in ("1", "2"):
        die("usage: slx.py gate <proj> 1|2 [--note \"what the user approved\"] [--assume]")
    return nextstep.record_gate(os.path.abspath(pos[0]), int(pos[1]), opt(args, "--note", ""), "--assume" in args)


def cmd_doctor(_args):
    ok = True
    def chk(label, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print("%-28s %s %s" % (label, "OK " if good else "FAIL", detail))
    chk("python >= 3.8", sys.version_info >= (3, 8), sys.version.split()[0])
    try:
        import PIL
        chk("Pillow (palette/grid/crop)", True, PIL.__version__)
    except ImportError:
        chk("Pillow (palette/grid/crop)", False, "pip install pillow")
    try:
        import numpy
        chk("numpy (bbox/diff/scan)", True, numpy.__version__)
    except ImportError:
        chk("numpy (bbox/diff/scan)", False, "pip install numpy --break-system-packages")
    try:
        v = subprocess.check_output([NODE, "-v"], text=True).strip()
        chk("node", True, v)
    except Exception as e:
        chk("node", False, "install Node.js or set SQUARELINE_NODE_BIN (%s)" % e)
    nm = os.path.join(HERE, "node_modules")
    if not os.path.isdir(nm):
        print("note: Node dependencies not installed yet -> they install automatically on first use, or run: slx.py setup")
    chk("lv_font_conv (fonts)", os.path.exists(os.path.join(nm, "lv_font_conv", "lv_font_conv.js")))
    chk("lucide-static (icons)", os.path.isdir(os.path.join(nm, "lucide-static", "icons")))
    chk("bundled fonts", os.path.isdir(os.path.join(ROOT, "fonts")) and
        len([f for f in os.listdir(os.path.join(ROOT, "fonts")) if f.endswith(".ttf")]) >= 3)
    chk("schema snapshot", os.path.exists(os.path.join(HERE, "schema_snapshot.json")))
    try:
        r = subprocess.run([NODE, "--input-type=module", "-e",
                            "import {resvgBackend} from './lib/resvg.mjs';console.log(resvgBackend())"],
                           cwd=HERE, capture_output=True, text=True, timeout=60)
        chk("resvg backend", r.returncode == 0, (r.stdout or r.stderr).strip()[:80])
    except Exception as e:
        chk("resvg backend", False, str(e))
    print("optional: gcc %s  (needed only for `slx.py truth`)" % ("found" if shutil.which("gcc") else "not found"))
    print("\nall good" if ok else "\nsome checks failed")
    return 0 if ok else 1


COMMANDS = {"init": cmd_init, "assets": cmd_assets, "preview": cmd_preview, "build": cmd_build,
            "verify": cmd_verify, "palette": cmd_palette, "grid": cmd_grid, "crop": cmd_crop,
            "check": cmd_check, "explain": cmd_explain, "setup": cmd_setup, "reqs": cmd_reqs, "scan": cmd_scan, "truth": cmd_truth, "next": cmd_next, "gate": cmd_gate, "fit-font": cmd_fitfont, "shot": cmd_shot, "sidebyside": cmd_sidebyside, "bbox": cmd_bbox, "diff": cmd_diff, "doctor": cmd_doctor}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help") or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 0 if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help") else 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd in ("assets", "preview", "build", "verify", "palette", "grid", "crop", "shot", "sidebyside", "bbox", "diff", "check", "next", "gate") and not args:
        die("%s needs an argument (project folder or image)" % cmd)
    return COMMANDS[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
