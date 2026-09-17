#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""End-to-end regression suite: "given input -> expected output" must hold.

Before this existed there was no way to tell whether a change to the engine
broke a project short of eyeballing a preview.  Now every archived example is
rebuilt from scratch and compared **byte for byte** against the committed
golden project, then validated.

What runs
---------
Stage A (assets)   node tools/generate_assets*.mjs        -> assets/images*
                   once with the native resvg binding, and once with
                   RESVG_FORCE_WASM=1 so the Linux/container code path is
                   exercised on any machine.
Stage C (project)  python tools/build_squareline_*.py
                   python tools/build_from_spec.py <spec>
                   -> .spj/.sll/.slp/Themes.slt/project.info + assets/
Stage D (verify)   python tools/validate_squareline_project.py <built>
                   python tools/preview_from_project.py       <built>
                   both must exit 0.

What is compared
----------------
Every file under the built project except editor churn and dev artifacts:
    backup/ cache/ components/ ui/ __pycache__/   (+ *_files/ backups)
    preview_from_project.html, *.preview.json
Font .c/.bin/.fcfg triples, PNGs, and the JSON project files are all compared,
so a font-subset change or a shader tweak cannot slip through.

Line endings are part of the contract
-------------------------------------
The archived goldens are **LF-only**, and the engine pins LF on every host
(see `engine.dump_json`), so the artifact bytes depend on the spec and not on
whether you built on Windows or Linux.  Two checks enforce that: goldens are
scanned for CRLF up front, and a byte mismatch that is *only* CRLF is reported
as such rather than as a bare `changed :`.

Usage
-----
    python eval/run_regression.py              # everything
    python eval/run_regression.py --no-assets  # skip the (slow) Stage A pass
    python eval/run_regression.py --keep       # keep the scratch dir
    python eval/run_regression.py --update     # rewrite the goldens (intentional
                                               # changes only — review the diff first)

Exit code 0 = every case matched and validated.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "python"
NODE = os.environ.get("SQUARELINE_NODE_BIN") or "node"

# ------------------------------------------------------------------ config --
# Directories the editor creates on save / our own dev artifacts: never diffed,
# never committed.
IGNORE_DIRS = {"backup", "cache", "components", "ui", "__pycache__",
               "node_modules", "dist"}
IGNORE_FILES = {"preview_from_project.html"}
IGNORE_SUFFIXES = (".preview.json",)

# Stage A: (case name, generator, output subdir of the scratch dir, golden dir)
ASSET_CASES = [
    ("AIWatchApple assets (native)",
     "tools/generate_assets_apple.mjs", "images_apple",
     "examples/AIWatchApple/assets/images_apple", {}),
    ("AIWatchApple assets (wasm fallback)",
     "tools/generate_assets_apple.mjs", "images_apple_wasm",
     "examples/AIWatchApple/assets/images_apple", {"RESVG_FORCE_WASM": "1"}),
    ("AIWatch assets (native)",
     "tools/generate_assets.mjs", "images",
     "examples/AIWatch/assets/images", {}),
]

# Stage C: (case name, argv builder, scratch subdir, golden project dir)
# Deliberately the BARE command — each project carries its own asset pack in its
# descriptor (PROJECT["assets"]), so no --assets flag is needed.  If that ever
# regresses, the diff shows up as `missing: assets/*.png` right here.
PROJECT_CASES = [
    ("AIWatchApple",
     lambda out: [PY, "tools/build_squareline_apple.py", "--out", out],
     "golden_apple",
     "examples/AIWatchApple/squareline/AIWatchApple"),
    ("AIWatch",
     lambda out: [PY, "tools/build_squareline_project.py", "--out", out],
     "golden_rect",
     "examples/AIWatch/squareline/AIWatch"),
    ("SpecWidget",
     lambda out: [PY, "tools/build_from_spec.py",
                  "examples/SpecWidget/SpecWidget.spec.json", "--out", out],
     "golden_spec",
     "examples/SpecWidget/squareline/SpecWidget"),
]

RESULTS = []


# ------------------------------------------------------------------ helpers --
def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    tag = "PASS" if ok else "FAIL"
    print("[%s] %s" % (tag, name))
    for line in str(detail).splitlines():
        if line.strip():
            print("       " + line)


def run(argv, env_extra=None, cwd=ROOT, timeout=1800):
    env = dict(os.environ)
    env.setdefault("SQUARELINE_NODE_BIN", NODE)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def tail(proc, n=14):
    txt = (proc.stdout or "") + (proc.stderr or "")
    return "\n".join(txt.strip().splitlines()[-n:])


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def wanted(rel):
    """Is this relative path part of the reproducible artifact set?"""
    parts = rel.replace("\\", "/").split("/")
    if any(p in IGNORE_DIRS for p in parts[:-1]):
        return False
    base = parts[-1]
    if base in IGNORE_FILES:
        return False
    if base.endswith(IGNORE_SUFFIXES):
        return False
    return True


def manifest(root):
    """{relpath: sha256} for every reproducible file under root."""
    out = {}
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            if wanted(rel):
                out[rel] = sha256(p)
    return out


def diff_manifests(a, b, got_root=None, gold_root=None, limit=18):
    """Files in a (got) vs b (golden).  Returns (equal, report lines).

    When a file's bytes differ, say *why* if the reason is line endings.  A
    Windows-built golden vs a Linux rebuild used to produce three bare
    `changed : x.spj` lines that looked like a broken generator; the real cause
    was `open(..., "w")` translating `\\n` to CRLF on Windows.  The engine now
    pins LF (see `dump_json`), so this should never fire — but if something
    reintroduces CRLF, name it here instead of leaving a mystery diff.
    """
    lines, eol_only = [], []
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    for k in only_b[:limit]:
        lines.append("missing  : %s" % k)
    for k in only_a[:limit]:
        lines.append("unexpected: %s" % k)
    for k in changed[:limit]:
        if (got_root and gold_root
                and eol_only_difference(os.path.join(got_root, k),
                                        os.path.join(gold_root, k))):
            eol_only.append(k)
            lines.append("changed  : %s   <-- LINE ENDINGS ONLY (CRLF vs LF)" % k)
        else:
            lines.append("changed  : %s" % k)
    if eol_only:
        lines.append("")
        lines.append("!! %d file(s) differ only by CRLF. The engine pins LF "
                     "(engine.dump_json); a golden that is CRLF means it was "
                     "committed from a machine without that fix, or git "
                     "rewrote it on checkout. Fix: `python eval/run_regression.py "
                     "--update`." % len(eol_only))
    extra = (len(only_a) + len(only_b) + len(changed)) - len(lines)
    if extra > 0:
        lines.append("... and %d more" % extra)
    return (not only_a and not only_b and not changed), lines


def eol_only_difference(pa, pb):
    """True when two files differ only in line endings (CRLF vs LF)."""
    if not (os.path.isfile(pa) and os.path.isfile(pb)):
        return False
    try:
        a = open(pa, "rb").read()
        b = open(pb, "rb").read()
    except OSError:
        return False
    if a == b:
        return False
    return a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n")



# -------------------------------------------------------------------- main --
def check_assets(scratch, no_assets):
    if no_assets:
        record("Stage A: asset generators reproducible", True,
               "skipped (--no-assets)")
        return
    for name, script, subdir, golden_rel, env in ASSET_CASES:
        out = os.path.join(scratch, subdir)
        p = run([NODE, script, "--out", out], env_extra=env)
        if p.returncode != 0:
            record("Stage A: %s" % name, False, tail(p))
            continue
        got = manifest(out)
        gold_root = os.path.join(ROOT, golden_rel)
        gold = manifest(gold_root)
        if not gold:
            record("Stage A: %s" % name, False,
                   "golden dir empty/missing: %s" % golden_rel)
            continue
        ok, lines = diff_manifests(got, gold, out, gold_root)
        backend = "wasm" if env.get("RESVG_FORCE_WASM") else "native"
        record("Stage A: %s [%s]" % (name, backend), ok,
               "%d png(s) identical to %s" % (len(got), golden_rel)
               if ok else "\n".join(lines))


def mirror(src, dst):
    """Make `dst` an exact copy of `src`'s reproducible file set.

    Used by `--update`.  Returns (copied, removed).  Only the reproducible set
    moves, so editor churn and our own *.preview.json / preview HTML are left
    alone on both sides.
    """
    removed = 0
    for dirpath, dirnames, filenames in os.walk(dst):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f in IGNORE_FILES or f.endswith(IGNORE_SUFFIXES):
                continue
            os.remove(os.path.join(dirpath, f))
            removed += 1
    copied = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            s = os.path.join(dirpath, f)
            rel = os.path.relpath(s, src).replace("\\", "/")
            if not wanted(rel):
                continue
            d = os.path.join(dst, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(s, d)
            copied += 1
    return copied, removed


def check_golden_eol():
    """Committed goldens must be LF-only.

    This is the guard the missing one would have needed.  The engine now pins
    LF, but CRLF can still creep back in two ways that have nothing to do with
    the generator: building the goldens on Windows before the fix (what
    happened), or a `git checkout` with `core.autocrlf=true` rewriting them.
    Either way three golden comparisons go red for a reason that is invisible
    in the diff, so state it once, up front, with the offending files named.
    """
    bad = []
    for _name, _fn, _sub, golden_rel in PROJECT_CASES:
        root = os.path.join(ROOT, golden_rel)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for f in filenames:
                if f in IGNORE_FILES or f.endswith(IGNORE_SUFFIXES):
                    continue
                if f.endswith((".png", ".bin", ".ttf", ".node")) or f == ".gitignore":
                    continue          # binary: no line endings to normalise
                p = os.path.join(dirpath, f)
                try:
                    if b"\r" in open(p, "rb").read():
                        bad.append(os.path.relpath(p, ROOT).replace("\\", "/"))
                except OSError:
                    continue
    record("goldens are LF-only (host-independent artifacts)", not bad,
           ("%d file(s) carry CRLF:\n%s\nfix: python eval/run_regression.py "
            "--update" % (len(bad), "\n".join(bad[:10]))) if bad
           else "%d archived project(s) clean" % len(PROJECT_CASES))


def check_projects(scratch, update=False):
    for name, argv_fn, subdir, golden_rel in PROJECT_CASES:
        out = os.path.join(scratch, subdir)
        p = run(argv_fn(out))
        if p.returncode != 0:
            record("Stage C: %s builds" % name, False, tail(p))
            continue
        gold_root = os.path.join(ROOT, golden_rel)
        if update:
            copied, removed = mirror(out, gold_root)
            record("Stage C: %s golden refreshed" % name, True,
                   "%d file(s) written, %d stale removed -> %s"
                   % (copied, removed, golden_rel))
        got = manifest(out)
        gold = manifest(gold_root)
        if not gold:
            record("Stage C: %s builds" % name, False,
                   "golden project missing: %s" % golden_rel)
            continue
        ok, lines = diff_manifests(got, gold, out, gold_root)
        record("Stage C: %s == golden (%d files)" % (name, len(gold)), ok,
               "byte-identical to %s" % golden_rel if ok else "\n".join(lines))

        # Stage D — verify the freshly built project, not the committed one.
        v = run([PY, "tools/validate_squareline_project.py", out])
        vok = v.returncode == 0 and "OK - project validated" in v.stdout
        record("Stage D: %s validates" % name, vok,
               v.stdout.strip().splitlines()[-1] if vok else tail(v))

        pr = run([PY, "tools/preview_from_project.py", out])
        pok = pr.returncode == 0 and os.path.exists(
            os.path.join(out, "preview_from_project.html"))
        record("Stage D: %s previews" % name, pok,
               pr.stdout.strip().splitlines()[-1] if pok else tail(pr))


def check_spec_compiler_contract(scratch):
    """The declarative path must fail loudly on bad input and succeed on
    minimal input.  Two regressions this locks down:

    * a malformed spec must produce `spec error: ...` on stderr, NOT a Python
      traceback (the compiler is user-facing, the engine is not);
    * a minimal spec that omits `order` / `initial_screen` must still build.
      It used to die with `KeyError: 'home'` because descriptor() read the
      screen list from a field only populated later, inside build_screens().
    """
    def write(name, obj):
        p = os.path.join(scratch, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return p

    def no_spec_error(out):
        return "spec error" in out and "Traceback" not in out

    # (a) unknown $schema
    p = write("bad_schema.spec.json", {"$schema": "squareline-spec/999",
                                       "name": "X", "width": 10, "height": 10,
                                       "screens": [{"name": "a"}]})
    r = run([PY, "tools/build_from_spec.py", p, "--out",
             os.path.join(scratch, "bad_schema_out")])
    out = (r.stdout or "") + (r.stderr or "")
    record("Spec: unknown $schema rejected cleanly", r.returncode != 0
           and no_spec_error(out), tail(r, 3))

    # (b) missing required key
    p = write("bad_missing.spec.json", {"$schema": "squareline-spec/1",
                                        "name": "X", "width": 10, "height": 10})
    r = run([PY, "tools/build_from_spec.py", p, "--out",
             os.path.join(scratch, "bad_missing_out")])
    out = (r.stdout or "") + (r.stderr or "")
    record("Spec: missing required key rejected cleanly", r.returncode != 0
           and no_spec_error(out), tail(r, 3))

    # (c) minimal spec, NO order / initial_screen -> the KeyError regression
    out_dir = os.path.join(scratch, "minimal_out")
    p = write("minimal.spec.json", {
        "$schema": "squareline-spec/1", "name": "Minimal", "width": 64,
        "height": 64, "shape": "RECT",
        "fonts": [{"codename": "F16", "ttf":
                   "noto-sans-sc-v40-chinese-simplified-regular.ttf",
                   "size": 16, "kind": "text"}],
        "screens": [
            {"name": "home", "bg": [0, 0, 0, 255], "children": [
                {"type": "LABEL", "name": "t", "rect": [0, 20, 64, 24],
                 "text": "hi", "font": "F16", "color": [255, 255, 255, 255],
                 "align": "CENTER"}]},
            {"name": "second", "bg": [0, 0, 0, 255], "children": [
                {"type": "LABEL", "name": "t2", "rect": [0, 20, 64, 24],
                 "text": "ho", "font": "F16", "color": [255, 255, 255, 255],
                 "align": "CENTER"},
                {"type": "PANEL", "name": "btn", "rect": [8, 44, 48, 16],
                 "bg": [30, 30, 30, 255], "radius": 4,
                 "events": [{"on": "CLICKED",
                             "actions": [{"type": "CHANGE_SCREEN",
                                          "target": "home"}]}]}]},
        ]})
    r = run([PY, "tools/build_from_spec.py", p, "--out", out_dir])
    out = (r.stdout or "") + (r.stderr or "")
    spj = os.path.join(out_dir, "Minimal.spj")
    ok = (r.returncode == 0 and os.path.exists(spj)
          and "Traceback" not in out and "ERROR" not in out)
    record("Spec: minimal spec (no order/initial_screen) builds", ok, tail(r, 6))

    if ok:
        v = run([PY, "tools/validate_squareline_project.py", out_dir])
        vok = v.returncode == 0 and "OK - project validated" in v.stdout
        record("Spec: minimal spec output validates", vok,
               v.stdout.strip().splitlines()[-1] if vok else tail(v))

    # (d) the documented skeleton must stay parseable
    r = run([PY, "tools/build_from_spec.py", "--example"])
    ok = r.returncode == 0 and '"$schema"' in r.stdout
    if ok:
        try:
            json.loads(r.stdout)
        except Exception as e:      # noqa: BLE001
            ok = False
            r = type("X", (), {"stdout": "skeleton is not valid JSON: %s" % e})()
    record("Spec: --example prints a valid skeleton", ok,
           "parses as JSON" if ok else tail(r))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-assets", action="store_true",
                    help="skip the Stage A asset generators (slow)")
    ap.add_argument("--keep", action="store_true", help="keep the scratch dir")
    ap.add_argument("--scratch", help="use this scratch dir instead of a temp one")
    ap.add_argument("--update", action="store_true",
                    help="overwrite the archived goldens with the freshly built "
                         "output; use ONLY after confirming the change is intended")
    args = ap.parse_args()

    scratch = args.scratch or tempfile.mkdtemp(prefix="sqeval-")
    os.makedirs(scratch, exist_ok=True)
    print("regression — %s" % ROOT)
    print("scratch    — %s\n" % scratch)
    if args.update:
        print("!! --update: the archived goldens WILL be rewritten.\n")

    check_golden_eol()
    check_assets(scratch, args.no_assets)
    check_projects(scratch, update=args.update)
    check_spec_compiler_contract(scratch)

    if not args.keep and not args.scratch:
        shutil.rmtree(scratch, ignore_errors=True)

    print("\n" + "-" * 68)
    failed = [n for n, ok, _d in RESULTS if not ok]
    print("%d checks: %d pass, %d fail"
          % (len(RESULTS), len(RESULTS) - len(failed), len(failed)))
    if failed:
        print("FAILED:")
        for n in failed:
            print("  -", n)
        return 1
    print("ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
