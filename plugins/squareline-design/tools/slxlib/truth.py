# -*- coding: utf-8 -*-
"""truth: render every LABEL of a project with the REAL LVGL and report where its ink really lands.

Why this exists: the HTML reverse-render once put text ~11% of the font size lower than the device
(the preview was calibrated against the browser, not LVGL).  This builds the actual LVGL 9.x software
renderer (gcc + the LVGL source, downloaded once to ~/.cache/slx), draws each label at its rect with the
project's own generated font, and measures the ink bounding box -- then compares it with the design
intent recorded by specbuilder (`<Name>.layout.intent.json`).

Optional tool: needs gcc and either --lvgl <path to LVGL source> / $SLX_LVGL_SRC or network access
to codeload.github.com for the one-time download.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor

LVGL_VERSION = "9.2.2"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "slx")
EXCLUDE = re.compile(r"/(drivers|libs|demos|examples)/|/draw/(nxp|renesas|dma2d|sdl|vg_lite|stm32_dma2d|arm2d|opengles|nema_gfx|eve)|"
                     r"/others/(vg_lite_tvg|file_explorer|monkey|ime|snapshot|observer|gridnav|fragment|imgfont|sysmon|test|xml)|/(sdl|gltf)/")

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "lvgl.h"
%(externs)s
typedef struct { const char *name; const lv_font_t *f; } fe_t;
static const fe_t FONTS[] = { %(table)s { NULL, NULL } };
static uint32_t fb[SW*SH], buf1[SW*SH];
static uint32_t tick_cb(void){ static uint32_t t = 0; t += 5; return t; }
static void flush(lv_display_t *d, const lv_area_t *a, uint8_t *px){ memcpy(fb, px, sizeof(fb)); lv_display_flush_ready(d); }
static int hexv(char c){ return c <= '9' ? c - '0' : (c | 32) - 'a' + 10; }
int main(void){
  lv_init(); lv_tick_set_cb(tick_cb);
  lv_display_t *d = lv_display_create(SW, SH);
  lv_display_set_buffers(d, buf1, NULL, sizeof(buf1), LV_DISPLAY_RENDER_MODE_FULL); lv_display_set_flush_cb(d, flush);
  lv_obj_t *scr = lv_screen_active();
  lv_obj_set_style_bg_color(scr, lv_color_hex(0), 0); lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
  char line[8192];
  while (fgets(line, sizeof line, stdin)) {
    int x, y, w, h; char al[16], fn[64], hex[8000];
    if (sscanf(line, "%%d %%d %%d %%d %%15s %%63s %%7999s", &x, &y, &w, &h, al, fn, hex) != 7) continue;
    char text[4000]; int n = (int)strlen(hex) / 2; for (int i = 0; i < n; i++) text[i] = (char)(hexv(hex[2*i]) * 16 + hexv(hex[2*i+1])); text[n] = 0;
    const lv_font_t *f = NULL; for (const fe_t *e = FONTS; e->name; e++) if (!strcmp(e->name, fn)) f = e->f;
    if (!f) { printf("-1 -1 -1 -1\n"); continue; }
    lv_obj_clean(scr);
    lv_obj_t *l = lv_label_create(scr); lv_obj_set_pos(l, x, y); lv_obj_set_size(l, w, h);
    lv_obj_set_style_text_font(l, f, 0); lv_obj_set_style_text_color(l, lv_color_hex(0xFFFFFF), 0); lv_obj_set_style_pad_all(l, 0, 0);
    lv_obj_set_style_text_align(l, !strcmp(al, "CENTER") ? LV_TEXT_ALIGN_CENTER : (!strcmp(al, "RIGHT") ? LV_TEXT_ALIGN_RIGHT : LV_TEXT_ALIGN_LEFT), 0);
    lv_label_set_text(l, text);
    lv_timer_handler(); lv_refr_now(d);
    int x0 = SW, y0 = SH, x1 = -1, y1 = -1;
    for (int yy = 0; yy < SH; yy++) for (int xx = 0; xx < SW; xx++) { uint32_t p = fb[yy*SW+xx];
      if ((((p>>16)&255) + ((p>>8)&255) + (p&255)) / 3 > 96) { if (xx < x0) x0 = xx; if (xx > x1) x1 = xx; if (yy < y0) y0 = yy; if (yy > y1) y1 = yy; } }
    printf("%%d %%d %%d %%d\n", x1 < 0 ? -1 : x0, x1 < 0 ? -1 : y0, x1 < 0 ? -1 : x1 + 1, x1 < 0 ? -1 : y1 + 1);
    fflush(stdout);
  }
  return 0; }
'''


def ensure_lvgl(path=None):
    path = path or os.environ.get("SLX_LVGL_SRC")
    if path and os.path.isdir(os.path.join(path, "src")):
        return path
    dst = os.path.join(CACHE, "lvgl-%s" % LVGL_VERSION)
    if os.path.isdir(os.path.join(dst, "src")):
        return dst
    os.makedirs(CACHE, exist_ok=True)
    url = "https://codeload.github.com/lvgl/lvgl/tar.gz/refs/tags/v%s" % LVGL_VERSION
    tgz = os.path.join(CACHE, "lvgl.tgz")
    print("downloading LVGL %s (one time, ~15 MB) ..." % LVGL_VERSION)
    urllib.request.urlretrieve(url, tgz)
    with tarfile.open(tgz) as t:
        t.extractall(CACHE)
    shutil.move(os.path.join(CACHE, "lvgl-%s" % LVGL_VERSION), dst) if not os.path.isdir(dst) else None
    os.remove(tgz)
    return dst


def _conf(src, out_dir):
    s = open(os.path.join(src, "lv_conf_template.h"), encoding="utf-8").read()
    s = s.replace('#if 0 /*Set it to "1" to enable content*/', "#if 1")
    for name, val in (("LV_COLOR_DEPTH", "32"), ("LV_USE_STDLIB_MALLOC", "LV_STDLIB_CLIB"), ("LV_USE_STDLIB_STRING", "LV_STDLIB_CLIB"),
                      ("LV_USE_STDLIB_SPRINTF", "LV_STDLIB_CLIB"), ("LV_USE_LOG", "0"), ("LV_USE_THEME_DEFAULT", "0")):
        s = re.sub(r"(#define\s+%s\s+)[^\n]*" % name, r"\g<1>%s" % val, s, count=1)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "lv_conf.h"), "w", encoding="utf-8").write(s)


def build_lib(src):
    """Compile LVGL once into object files (cached)."""
    obj_dir = os.path.join(CACHE, "obj-%s" % LVGL_VERSION)
    conf_dir = os.path.join(CACHE, "conf")
    _conf(src, conf_dir)
    files = []
    for root, _d, fs in os.walk(os.path.join(src, "src")):
        for f in fs:
            p = os.path.join(root, f)
            if f.endswith(".c") and not EXCLUDE.search(p.replace(os.sep, "/")):
                files.append(p)
    files += [os.path.join(r, f) for r, _d, fs in os.walk(os.path.join(src, "src", "libs", "bin_decoder")) for f in fs if f.endswith(".c")]
    os.makedirs(obj_dir, exist_ok=True)
    flags = ["-O1", "-w", "-DLV_CONF_INCLUDE_SIMPLE", "-DLV_LVGL_H_INCLUDE_SIMPLE", "-I" + conf_dir, "-I" + src, "-I" + os.path.join(src, "src")]
    todo = []
    for p in files:
        o = os.path.join(obj_dir, hashlib.md5(p.encode()).hexdigest() + ".o")
        if not os.path.exists(o):
            todo.append((p, o))
    if todo:
        print("compiling LVGL core (%d files, first time only) ..." % len(todo))

        def cc(po):
            r = subprocess.run(["gcc", "-c"] + flags + [po[0], "-o", po[1]], capture_output=True, text=True)
            return r.returncode, po[0], r.stderr
        with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 2))) as ex:
            for rc, p, err in ex.map(cc, todo):
                if rc:
                    raise SystemExit("compile failed: %s\n%s" % (p, err[:400]))
    return [os.path.join(obj_dir, hashlib.md5(p.encode()).hexdigest() + ".o") for p in files], flags


def measure(proj, spec, tk_root, lvgl=None):
    if not shutil.which("gcc"):
        raise SystemExit("truth needs gcc (apt install build-essential / Xcode command line tools).")
    src = ensure_lvgl(lvgl)
    objs, flags = build_lib(src)
    fdir = os.path.join(proj, "squareline", spec["name"], "assets", "fonts")
    fonts = sorted(f for f in os.listdir(fdir) if f.endswith(".c")) if os.path.isdir(fdir) else []
    if not fonts:
        raise SystemExit("no generated fonts: run `slx.py build <proj>` first.")
    names = [os.path.splitext(f)[0] for f in fonts]               # ui_font_Big60
    table = " ".join('{ "%s", &%s },' % (n[len("ui_font_"):], n) for n in names)
    externs = "\n".join("extern const lv_font_t %s;" % n for n in names)
    tmp = os.path.join(CACHE, "run-%s" % spec["name"])
    os.makedirs(tmp, exist_ok=True)
    open(os.path.join(tmp, "harness.c"), "w").write(HARNESS % {"externs": externs, "table": table})
    exe = os.path.join(tmp, "harness")
    r = subprocess.run(["gcc"] + flags + ["-DSW=%d" % spec["width"], "-DSH=%d" % spec["height"], os.path.join(tmp, "harness.c")] +
                       [os.path.join(fdir, f) for f in fonts] + objs + ["-lm", "-o", exe], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("harness link failed:\n" + r.stderr[:800])
    labels = []

    def walk(scr, ch):
        for o in ch or []:
            if o["type"] == "LABEL":
                labels.append((scr, o))
            walk(scr, o.get("children"))
    for sc in spec["screens"]:
        walk(sc["name"], sc["children"])
    feed = "".join("%d %d %d %d %s %s %s\n" % (o["rect"][0], o["rect"][1], o["rect"][2], o["rect"][3], o.get("align", "LEFT"),
                                               o["font"], o["text"].encode("utf-8").hex()) for _s, o in labels)
    out = subprocess.run([exe], input=feed, capture_output=True, text=True, timeout=300).stdout.split("\n")
    res = []
    for (scr, o), line in zip(labels, out):
        b = [int(v) for v in line.split()] if line.strip() else [-1] * 4
        res.append({"screen": scr, "object": o["name"], "text": o["text"], "rect": o["rect"], "ink": b})
    return res


def report(proj, spec, results, tol=2.5):
    ip = [f for f in os.listdir(proj) if f.endswith(".layout.intent.json")]
    intent = json.load(open(os.path.join(proj, ip[0]), encoding="utf-8")) if ip else {}
    bad, ok, blank = [], 0, []
    for r in results:
        x0, y0, x1, y1 = r["ink"]
        if x0 < 0:
            blank.append(r)
            continue
        r["ink_cy"] = (y0 + y1) / 2.0
        it = intent.get("%s/%s" % (r["screen"], r["object"]))
        if it:
            r["intent_cy"] = it["ink_cy"]
            r["dy"] = round(r["ink_cy"] - it["ink_cy"], 1)
            if abs(r["dy"]) > tol:
                bad.append(r)
            else:
                ok += 1
        # clipped by its own box?
        rx, ry, rw, rh = r["rect"]
        if y0 < ry or y1 > ry + rh:
            r.setdefault("notes", []).append("ink leaves its box vertically (box too short / text clipped)")
    return bad, ok, blank
