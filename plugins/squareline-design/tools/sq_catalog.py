#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export / regenerate the SquareLine property catalog (`tools/schema_snapshot.json`).

Why a snapshot exists
---------------------
The validator's strongest check is "every `strtype` we emit must also appear in
an official example project" — that is what keeps the editor from refusing to
open a generated .spj.  Reading that set from a *local SquareLine Studio install*
made the check silently degrade to a WARN inside a container, which is exactly
where the skill has to run.  So the set is frozen once, on a machine that has
the editor, and shipped inside the package.

Two jobs:
  * regenerate the snapshot  ->  needs a SquareLine install  (rare, on a dev box)
  * print a human-readable catalog -> for eyeballing a release

Usage
-----
    python tools/sq_catalog.py                      # regenerate the snapshot
    python tools/sq_catalog.py --print              # human-readable dump
    python tools/sq_catalog.py --studio "/opt/SquareLine Studio 1.6.2"
    python tools/sq_catalog.py --check              # is the snapshot usable?

Environment
-----------
    SQUARELINE_STUDIO   install dir (overrides the OS default guess)
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, "tools", "schema_snapshot.json")

# Candidate install locations, most likely first.  Deliberately no personal
# paths: only documented defaults plus the env var.
DEFAULT_STUDIO_DIRS = [
    r"D:\Program Files\SquareLine Studio 1.6.2",
    r"C:\Program Files\SquareLine Studio 1.6.2",
    "/Applications/SquareLine Studio 1.6.2.app/Contents/MacOS",
    "/opt/SquareLine Studio 1.6.2",
    os.path.expanduser("~/SquareLine Studio 1.6.2"),
]


def find_studio(explicit=None):
    """Return the first usable SquareLine install dir, or None."""
    for cand in ([explicit] if explicit else []) + \
                ([os.environ["SQUARELINE_STUDIO"]] if os.environ.get("SQUARELINE_STUDIO") else []) + \
                DEFAULT_STUDIO_DIRS:
        if cand and os.path.isdir(os.path.join(cand, "examples")):
            return cand
    return None


def _no_studio_msg(explicit=None):
    tried = "\n".join("    - %s" % d for d in
                      ([explicit] if explicit else []) + DEFAULT_STUDIO_DIRS)
    return (
        "ERROR: no SquareLine Studio install found (looked for a directory\n"
        "       containing examples/*.spj under each of):\n%s\n\n"
        "  Fix one of these ways:\n"
        "    * point at your install:  SQUARELINE_STUDIO=\"/path/to/SquareLine Studio 1.6.2\"\n"
        "                              python tools/sq_catalog.py\n"
        "    * or just skip it — the shipped snapshot is already good:\n"
        "                              python tools/sq_catalog.py --check\n"
        % tried
    )


def collect(studio_dir):
    """Walk every official example and tally what the editor can express."""
    files = (glob.glob(os.path.join(studio_dir, "examples", "**", "*.spj"), recursive=True) +
             glob.glob(os.path.join(studio_dir, "examples", "**", "*.ecomp"), recursive=True))
    strtypes = Counter()
    object_types = Counter()
    base_types = Counter()
    style_parts = Counter()
    fonts = set()
    assets = set()
    info_shapes = Counter()

    def walk(o):
        if isinstance(o, dict):
            t = o.get("strtype")
            if t:
                strtypes[t] += 1
                if t.startswith("_style/") or "/Style_" in t:
                    style_parts[t] += 1
                if t.endswith("/Text_Font") and o.get("strval"):
                    fonts.add(o["strval"])
                if t.endswith("/Asset") and o.get("strval"):
                    assets.add(o["strval"])
            if "saved_objtypeKey" in o:
                object_types[o["saved_objtypeKey"]] += 1
            if "saved_basetypeKey" in o:
                base_types[o["saved_basetypeKey"]] += 1
            if isinstance(o.get("info"), dict) and o["info"].get("shape"):
                info_shapes[o["info"]["shape"]] += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    bad = []
    for f in files:
        try:
            walk(json.load(open(f, encoding="utf-8")))
        except Exception as e:
            bad.append("%s: %s" % (f, e))

    version = None
    for f in files:
        try:
            v = json.load(open(f, encoding="utf-8")).get("info", {}).get("editor_version")
            if v:
                version = v
                break
        except Exception:
            pass

    return {
        "schema_version": 1,
        "generated_by": "tools/sq_catalog.py",
        "editor_version": version or "unknown",
        "source_root": os.path.basename(studio_dir.rstrip("/\\")),
        "source_files": len(files) - len(bad),
        "parse_errors": bad,
        # the actual contract the validator enforces: the set of legal strtypes
        "strtypes": dict(sorted(strtypes.items())),
        "object_types": dict(sorted(object_types.items())),
        "base_types": dict(sorted(base_types.items())),
        "style_parts": dict(sorted(style_parts.items())),
        "official_font_codenames": sorted(fonts),
        "info_shapes": dict(sorted(info_shapes.items())),
        "sample_assets": sorted(assets)[:24],
    }


def load_snapshot(path=SNAPSHOT):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--studio", default=None,
                    help="SquareLine Studio install dir (default: $SQUARELINE_STUDIO, "
                         "then the usual per-OS locations)")
    ap.add_argument("--out", default=SNAPSHOT)
    ap.add_argument("--check", action="store_true",
                    help="only report whether the shipped snapshot is usable")
    ap.add_argument("--print", dest="dump", action="store_true",
                    help="print the catalog instead of writing the snapshot")
    args = ap.parse_args()

    if args.check:
        if not os.path.exists(args.out):
            print("MISSING - %s does not exist. Run: python tools/sq_catalog.py "
                  "(needs a SquareLine install)." % args.out)
            return 1
        snap = load_snapshot(args.out)
        n = len(snap.get("strtypes", {}))
        print("OK - snapshot: %d strtypes, %d object types, from %d example file(s), "
              "editor %s" % (n, len(snap.get("object_types", {})),
                             snap.get("source_files", 0),
                             snap.get("editor_version", "?")))
        return 0 if n else 1

    studio = find_studio(args.studio)
    if not studio:
        print(_no_studio_msg(args.studio))
        return 1
    print("studio:", studio)

    snap = collect(studio)
    print("files:", snap["source_files"], "| strtypes:", len(snap["strtypes"]),
          "| object types:", len(snap["object_types"]),
          "| editor:", snap["editor_version"])
    if snap["parse_errors"]:
        print("parse errors:", snap["parse_errors"][:3])

    if args.dump:
        print("\n=== strtype catalog ===")
        for t, n in sorted(snap["strtypes"].items()):
            print("%6d  %s" % (n, t))
        print("\n=== object types ===", sorted(snap["object_types"]))
        print("\n=== fonts referenced ===", snap["official_font_codenames"])
        print("\n=== shapes ===", snap["info_shapes"])
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(snap, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")
    print("wrote", args.out, "(%d bytes)" % os.path.getsize(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
