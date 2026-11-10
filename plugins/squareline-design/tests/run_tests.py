#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the squareline-design toolkit.   python3 tests/run_tests.py [-k substring] [-v]

Every test here guards something that actually went wrong in a real project (see CHANGELOG.md).
Optional tests (need gcc / LVGL source) report SKIP rather than failing.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
TK = os.path.dirname(HERE)
SLX = [sys.executable, os.path.join(TK, "tools", "slx.py")]
TMP = tempfile.mkdtemp(prefix="slxtest_")
TESTS = []


class Skip(Exception):
    pass


def test(fn):
    TESTS.append(fn)
    return fn


def sh(*args, cwd=None, inp=None, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run(list(SLX) + [str(a) for a in args], cwd=cwd, capture_output=True, text=True, input=inp, env=e, timeout=900)
    return r.returncode, r.stdout + r.stderr


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def new_project(name="Demo", w=360, h=360, shape="CIRCLE"):
    d = os.path.join(TMP, name + "_" + hashlib.md5(os.urandom(8)).hexdigest()[:6])
    rc, out = sh("init", name, "--width", w, "--height", h, "--shape", shape, "--dir", d)
    need(rc == 0, "init failed: " + out)
    return os.path.join(d, name)


def load_spec(proj):
    p = [f for f in os.listdir(proj) if f.endswith(".spec.json")][0]
    return os.path.join(proj, p), json.load(open(os.path.join(proj, p), encoding="utf-8"))


def save_spec(path, spec):
    json.dump(spec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# --------------------------------------------------------------------------------------------
@test
def doctor():
    rc, out = sh("doctor")
    need(rc == 0 and "all good" in out, out)


@test
def skeleton_builds_and_validates():
    p = new_project()
    rc, out = sh("build", p)
    need(rc == 0 and "OK - project validated" in out, out)


@test
def lint_catches_known_failure_modes():
    """One mutation per lint code; each must be reported with that code."""
    base = new_project()
    spec_path, spec = load_spec(base)
    home = spec["screens"][0]
    lbl = home["children"][0]

    def m_event(s):
        s["screen_events"] = {"home": [{"on": "LONG_PRESSED", "name": None, "actions": [{"type": "CHANGE_SCREEN", "target": "home"}]}]}

    def m_kind(s):
        s["fonts"][0]["kind"] = "number"
        s["symbols"] = {}

    def m_rect(s):
        s["screens"][0]["children"][0]["rect"][0] = -10

    def m_color(s):
        s["screens"][0]["children"][0]["color"] = "NOPE"

    def m_dup(s):
        s["screens"][0]["children"].append(copy.deepcopy(s["screens"][0]["children"][0]))

    def m_imgpath(s):
        s["screens"][0]["children"].append({"type": "IMAGE", "name": "pic", "rect": [10, 10, 20, 20], "asset": "assets/images/x.png"})

    def m_target(s):
        s["screens"][0]["children"][0]["events"] = [{"on": "CLICKED", "name": None, "actions": [{"type": "CHANGE_SCREEN", "target": "nowhere"}]}]

    def m_dead(s):
        s["screens"].append({"name": "island", "bg": "BG", "children": []})
        s["screens"][0]["children"][0]["events"] = [{"on": "CLICKED", "name": None, "actions": [{"type": "CHANGE_SCREEN", "target": "island"}]}]

    def m_lblh(s):
        r = s["screens"][0]["children"][0]["rect"]
        r[3] = s["fonts"][0]["size"]

    def m_circle(s):
        s["screens"][0]["children"].append({"type": "PANEL", "name": "corner", "rect": [300, 300, 50, 50], "bg": "CARD", "radius": 0})

    def m_tap(s):
        s["screens"][0]["children"].append({"type": "PANEL", "name": "tiny", "rect": [150, 150, 20, 20], "bg": "CARD", "radius": 0,
                                            "events": [{"on": "CLICKED", "name": None, "actions": [{"type": "CHANGE_SCREEN", "target": "home"}]}]})

    cases = [("E-EVENT-KIND", m_event), ("E-FONT-KIND", m_kind), ("E-RECT-CANVAS", m_rect), ("E-COLOR", m_color), ("E-OBJ-DUP", m_dup),
             ("E-IMG-PATH", m_imgpath), ("E-ACT-SCREEN", m_target), ("E-NAV-DEAD", m_dead), ("E-LABEL-H", m_lblh),
             ("E-CIRCLE", m_circle), ("W-TAP", m_tap)]
    missed = []
    for code, mut in cases:
        d = os.path.join(TMP, "lint_" + code)
        shutil.copytree(base, d)
        sp, s = load_spec(d)
        mut(s)
        save_spec(sp, s)
        rc, out = sh("check", d, "--json")
        try:
            j = json.loads(out[out.index("{"):])
        except Exception:
            missed.append("%s (no json: %s)" % (code, out[:120]))
            continue
        codes = {f["code"] for f in j["errors"] + j["warnings"]}
        if code not in codes:
            missed.append("%s (got %s)" % (code, sorted(codes)))
    need(not missed, "lint did not report: " + "; ".join(missed))


@test
def lint_does_not_cry_wolf_on_valid_things():
    """False positives that were found and fixed: the upstream golden example is a valid project (apart from its real dead ends)."""
    d = os.path.join(TMP, "nova_lint")
    shutil.copytree(os.path.join(TK, "examples", "NovaWatchS12"), d, ignore=shutil.ignore_patterns("squareline"))
    os.makedirs(os.path.join(d, "assets", "images"), exist_ok=True)
    rc, out = sh("assets", d)
    rc, out = sh("check", d, "--json")
    j = json.loads(out[out.index("{"):])
    bad = [f for f in j["errors"] if f["code"] not in ("E-NAV-DEAD",)]
    need(not bad, "unexpected lint errors on the golden example: %s" % [(f["code"], f["where"]) for f in bad])
    need(sum(f["code"] == "E-NAV-DEAD" for f in j["errors"]) == 8, "the golden example has exactly 8 real dead-end screens")


@test
def build_refuses_when_lint_has_errors():
    p = new_project()
    sp, s = load_spec(p)
    s["screen_events"] = {"home": [{"on": "DOUBLE_CLICKED", "name": None, "actions": [{"type": "CHANGE_SCREEN", "target": "home"}]}]}
    save_spec(sp, s)
    rc, out = sh("build", p)
    need(rc == 3 and "build refused" in out, "expected refusal, got rc=%s: %s" % (rc, out[-300:]))


@test
def upstream_golden_project_rebuilds_byte_identical():
    d = os.path.join(TMP, "nova_build")
    shutil.copytree(os.path.join(TK, "examples", "NovaWatchS12"), d, ignore=shutil.ignore_patterns("squareline"))
    for sub in ("assets/images", "downloads", "preview"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    need(sh("assets", d)[0] == 0, "assets failed")
    rc, out = sh("build", d, "--force")             # --force: the example really has dead-end screens (E-NAV-DEAD)
    need(rc == 0, out[-400:])
    got = hashlib.sha256(open(os.path.join(d, "squareline", "NovaWatchS12", "NovaWatchS12.spj"), "rb").read()).hexdigest()
    want = open(os.path.join(TK, "examples", "NovaWatchS12", "NovaWatchS12.spj.sha256")).read().strip()
    need(got == want, "spj differs from the golden file: %s != %s" % (got[:12], want[:12]))


@test
def specbuilder_regenerates_the_reference_example():
    d = os.path.join(TMP, "panda_regen")
    shutil.copytree(os.path.join(TK, "examples", "PandaPendant"), d)
    r = subprocess.run([sys.executable, os.path.join(d, "scripts", "gen_spec.py")], capture_output=True, text=True,
                       env=dict(os.environ, SLX_TOOLS=os.path.join(TK, "tools")))
    need(r.returncode == 0, r.stdout + r.stderr)
    a = json.load(open(os.path.join(TK, "examples", "PandaPendant", "PandaPendant.spec.json"), encoding="utf-8"))
    b = json.load(open(os.path.join(d, "PandaPendant.spec.json"), encoding="utf-8"))
    need(a == b, "regenerated spec differs from the stored one (font-metric probe or specbuilder changed)")


@test
def fit_font_reproduces_known_answers():
    """Ground truth from a real project: the concept clock (ink 193.5x55) needs 76 px, the timer (162.5x46) 62 px."""
    rc, out = sh("fit-font", "10:42", "--w", 193.5, "--h", 55, "--weight", 700, "--cy", 161.5)
    need(rc == 0 and "recommended size 76 px" in out, out)
    rc, out = sh("fit-font", "05:00", "--w", 162.5, "--h", 46, "--weight", 700)
    need("recommended size 62 px" in out, out)
    # the y it prints must be consistent with the REAL font metrics (line_height 93, baseline 71 below the box top for 76 px, ASCII range)
    rc, out = sh("fit-font", "10:42", "--w", 193.5, "--h", 55, "--weight", 700, "--cy", 161.5, "--ranges", "0x20-0x7E,0x00B0")
    need("line_height 93" in out and "rect y = 119" in out, out)


@test
def scan_finds_screens_and_elements_in_the_fixture():
    img = os.path.join(HERE, "fixtures", "focusring_concept.png")
    rc, out = sh("scan", img, "--find-screens")
    j = json.loads(out)
    need(len(j["screens"]) == 2, "expected 2 screens, got %s" % j["screens"])
    b = j["screens"][0]["bbox"]
    need(all(abs(x - y) <= 3 for x, y in zip(b, [100, 80, 700, 680])), "screen 1 bbox %s" % b)
    o = os.path.join(TMP, "scan_out")
    rc, out = sh("scan", img, "--screen", 100, 80, 700, 680, "--panel", 360, "--shape", "circle", "--out", o)
    need(rc == 0, out)
    res = json.load(open([os.path.join(o, f) for f in os.listdir(o) if f.endswith(".json")][0], encoding="utf-8"))
    el = res["elements"]
    ring = [e for e in el if e["kind_hint"] == "ring/arc"]
    need(ring, "no ring found: %s" % [e["kind_hint"] for e in el])
    need(all(abs(a - c) <= 6 for a, c in zip(ring[0]["rect_panel"], [20, 20, 320, 320])), "ring rect %s (true [20,20,320,320])" % ring[0]["rect_panel"])
    clock = [e for e in el if e["kind_hint"] == "text-like" and 185 <= e["rect_panel"][2] <= 205]
    need(clock, "clock text (about 193 px wide) not detected: %s" % [(e["kind_hint"], e["rect_panel"]) for e in el])
    need(abs(clock[0]["rect_panel"][0] - 84) <= 3 and abs(clock[0]["rect_panel"][1] - 134) <= 3, "clock rect %s (true x 84, y 134)" % clock[0]["rect_panel"])
    need(any(e["kind_hint"] == "icon-like" and e["color"].upper().startswith("#FF37") for e in el), "heart icon (#FF375F) not detected")
    need(res.get("notes"), "a big element must produce the 'text printed on it is merged' note")


@test
def requirements_traceability_round_trip():
    p = new_project()
    md = os.path.join(p, "concept", "req.md")
    open(md, "w", encoding="utf-8").write("# 约束\n\n- 屏幕必须显示时间。\n- 不得出现手或耳朵。\n- 建议使用圆角卡片。\n\n| 项 | 要求 |\n|---|---|\n| 画布 | 360 × 360 px |\n")
    rc, out = sh("reqs", "extract", md, "--proj", p)
    need(rc == 0, out)
    rq = json.load(open(os.path.join(p, "requirements.json"), encoding="utf-8"))
    st = {i["text"][:6]: i["strength"] for i in rq["items"]}
    need(any(i["strength"] == "MUST_NOT" for i in rq["items"]), "MUST_NOT clause not detected: %s" % st)
    need(not any("项 ｜ 要求" in i["text"] for i in rq["items"]), "a table header was taken as a requirement")
    need(sh("reqs", "check", p)[0] == 1, "undisposed hard requirements must fail the check")
    ids = [i["id"] for i in rq["items"] if i["strength"] in ("MUST", "MUST_NOT")]
    sh("reqs", "set", p, *ids, "done")                                   # no evidence -> error
    need(sh("reqs", "check", p)[0] == 1, "'done' without evidence must fail")
    sh("reqs", "set", p, *ids, "done", "--evidence", "x", "--verify", '{"type":"screen_exists","screen":"nope"}')
    rc, out = sh("reqs", "check", p)
    need(rc == 1 and "auto-verify" in out, "a failing verify rule must fail the check: " + out)
    sh("reqs", "set", p, *ids, "done", "--evidence", "x", "--verify", '{"type":"canvas","width":360,"height":360,"shape":"CIRCLE"}')
    need(sh("reqs", "check", p)[0] == 0, "should be green now")
    rc, out = sh("reqs", "report", p)
    need(os.path.exists(os.path.join(p, "需求追溯矩阵.md")), out)


@test
def next_walks_the_stages():
    p = new_project()
    j = json.loads(sh("next", p, "--json")[1])
    need(j["next"] == "intake", j["next"])
    shutil.copy(os.path.join(HERE, "fixtures", "focusring_concept.png"), os.path.join(p, "concept", "c.png"))
    j = json.loads(sh("next", p, "--json")[1])
    need(j["next"] == "analysis", "after adding a concept the next stage must be the analysis, got " + str(j["next"]))
    need(sh("gate", p, 1, "--note", "test")[0] == 0, "gate")
    out = sh("next", p)[1]
    need("NEXT" in out, out)
    need(sh("next", os.path.join(TMP, "does_not_exist"))[0] == 0, "next on a missing folder should explain `init`, not crash")


@test
def raster_source_needs_provenance_and_cuts_exact_size():
    p = new_project()
    shutil.copy(os.path.join(HERE, "fixtures", "focusring_concept.png"), os.path.join(p, "concept", "c.png"))
    man = os.path.join(p, "assets.manifest.json")
    entry = {"name": "img_cut", "source": "raster", "file": "concept/c.png", "crop": [100, 80, 700, 680], "size": [120, 120], "mask": "circle"}
    json.dump({"defaults": {}, "icons": [entry]}, open(man, "w"))
    rc, out = sh("assets", p)
    need(rc != 0 and "provenance" in out, "missing provenance must be an error: " + out)
    entry["provenance"] = "test fixture"
    json.dump({"defaults": {}, "icons": [entry]}, open(man, "w"))
    rc, out = sh("assets", p)
    need(rc == 0, out)
    from PIL import Image
    need(Image.open(os.path.join(p, "assets", "images", "img_cut.png")).size == (120, 120), "wrong size")
    need(os.path.exists(os.path.join(p, "assets.provenance.json")), "provenance not recorded")


@test
def explain_knows_the_famous_failures():
    rc, out = sh("explain", "E-FONT-KIND")
    need(rc == 0 and "symbols" in out, out)
    rc, out = sh("explain", "KeyError")
    need(rc == 0, out)


@test
def preview_fonts_load_and_text_follows_lvgl_metrics():
    """The reverse-render must carry LVGL's line_height/base_line into CSS (ascent/descent overrides)."""
    p = new_project()
    rc, out = sh("build", p)
    need(rc == 0, out)
    rc, out = sh("verify", p)
    html = open(os.path.join(p, "preview", "project_preview.html"), encoding="utf-8").read()
    need("ascent-override" in html and "descent-override" in html, "preview does not use the LVGL font metrics")
    need("../squareline/" in html or "assets/fonts/" in html, "font path missing")


@test
def truth_matches_design_intent_optional():
    """OPTIONAL (gcc + LVGL source): ink positions in the REAL LVGL equal the design intent within 2.5 px."""
    import shutil as _sh
    if not _sh.which("gcc"):
        raise Skip("no gcc")
    src = os.environ.get("SLX_LVGL_SRC") or os.path.join(os.path.expanduser("~"), ".cache", "slx", "lvgl-9.2.2")
    if not os.path.isdir(os.path.join(src, "src")):
        raise Skip("no LVGL source (set SLX_LVGL_SRC or run `slx.py truth` once with network)")
    sys.path.insert(0, os.path.join(TK, "tools"))
    from specbuilder import Project
    d = os.path.join(TMP, "truth_proj")
    rc, out = sh("init", "TruthDemo", "--width", 360, "--height", 360, "--shape", "CIRCLE", "--dir", d)
    p = os.path.join(d, "TruthDemo")
    T = "noto-sans-sc-v40-chinese-simplified-%s.ttf"
    P = Project("TruthDemo", 360, 360, "CIRCLE", {"BG": "#000000", "WHITE": "#FFFFFF"},
                [{"codename": "Big60", "ttf": T % "700", "size": 60, "kind": "number"}, {"codename": "Body18", "ttf": T % "regular", "size": 18, "kind": "text"}],
                ranges_num=["0x30-0x3A"])
    P.screen("home", [P.label("clock", 180, 120, 220, "10:42", "Big60"), P.label("date", 180, 200, 200, "周六 11月7日", "Body18")])
    P.write(os.path.join(p, "TruthDemo.spec.json"))
    need(sh("build", p)[0] == 0, "build")
    rc, out = sh("truth", p, "--lvgl", src)
    need(rc == 0 and "off: 0" in out, out)


# --------------------------------------------------------------------------------------------
def main():
    pat = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
    verbose = "-v" in sys.argv
    res = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for t in TESTS:
        if pat and pat not in t.__name__:
            continue
        try:
            t()
            res["PASS"] += 1
            print("PASS  %s" % t.__name__)
        except Skip as s:
            res["SKIP"] += 1
            print("SKIP  %s (%s)" % (t.__name__, s))
        except Exception as e:                       # noqa: BLE001
            res["FAIL"] += 1
            print("FAIL  %s\n      %s" % (t.__name__, str(e).strip().replace("\n", "\n      ")[:900]))
            if verbose:
                traceback.print_exc()
    print("\n%(PASS)d passed, %(FAIL)d failed, %(SKIP)d skipped" % res)
    shutil.rmtree(TMP, ignore_errors=True)
    return 1 if res["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
