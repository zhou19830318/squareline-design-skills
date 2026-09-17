#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Build the ONE release artifact: dist/squareline-design-skills.zip.

Two problems this solves
------------------------
**1. Chinese filenames must survive the trip to Linux.**
Zipping with Windows' built-in tools (Explorer "Send to > Compressed folder",
older `Compress-Archive`, some 7-Zip settings) stores filenames in the local
ANSI codepage and leaves the UTF-8 flag bit unset.  Unzipping that on Linux
turns a name like

    <名称>_\udcbf\udcc9...md

i.e. mojibake, and the file is effectively unreachable.  Python's `zipfile`
always marks non-ASCII names with the UTF-8 flag (bit 11), so building the
archive here makes the result portable by construction — and the script then
*re-opens the archive and decodes every name* to prove it.

NOTE: this docstring must stay a **raw** string.  As a normal string the two
``\udcbf`` / ``\udcc9`` escapes above would be decoded into lone surrogates
(U+DCBF, U+DCC9), which no UTF-8 encoder accepts — and ``__doc__`` is handed
straight to argparse, so merely printing ``--help`` would then blow up with
``UnicodeEncodeError: 'utf-8' codec can't encode characters ... surrogates not
allowed``.  tools/preflight.py now guards every shipped text file against this.

**2. "Zip the working directory" must not be able to leak.**
That is what actually shipped once: a plain folder-压缩 of the repo root.  It
carried ``.workbuddy/`` (the agent's own working notes, complete with machine
absolute paths), a 61 MB ``dist/*.zip`` nested inside itself, and the review
brief — none of which belong in the deliverable.  Worse, because it was made by
Explorer it also reproduced the mojibake problem in full, so the file that
reached the reviewer was the *broken* one even though the fixed artifact
already existed inside it.

The defence is an **allowlist of top-level entries** (``SHIP_TOP``), not a
blocklist.  A blocklist only excludes what its author remembered: the next
scratch directory, log dir or agent state dir slips through.  An allowlist
cannot leak by construction — a new top-level directory is simply not shipped
until someone adds it here deliberately, and every skipped entry is printed so
the omission is visible rather than silent.

Usage
-----
    python tools/package_release.py                # -> dist/squareline-design-skills.zip
    python tools/package_release.py --out dist/x.zip
    python tools/package_release.py --no-vendor    # skip tools/node_modules (~32 MB)
    python tools/package_release.py --list         # just print what would ship

Ship the file it names.  Never zip the working directory.
"""

import argparse
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "dist", "squareline-design-skills.zip")

# ---- the allowlist: the *only* things that may appear at the archive root ---
# Add to this deliberately when the skill gains a new top-level directory.
SHIP_TOP = (
    "README.md",     # entry point / usage
    "skills",        # the SKILL.md bundle itself
    "tools",         # every generator, validator, compiler, packer
    "templates",     # the Stage-0 design-spec template
    "eval",          # regression suite
    "examples",      # archived reference projects (build + diff baselines)
    "fonts",         # source TTFs the asset/font stages subset
    ".gitignore",    # repo hygiene travels with the tree
    ".gitattributes",
)

# Excluded *within* an allowed top (editor churn, caches, dev leftovers).
# NB: `node_modules` is deliberately absent — the vendored deps ship on purpose.
EXCLUDE_DIR_NAMES = {"backup", "cache", "components", "ui", "__pycache__",
                     ".pytest_cache", ".idea", ".vscode", ".git"}
EXCLUDE_FILE_SUFFIX = (".pyc", ".pyo", ".zip", ".log", ".bak", ".orig", ".rej")
# `preview_from_project.html` is a *generated* contact sheet: running
# tools/preview_from_project.py against a committed example drops one inside the
# golden dir, and examples/ is an allowed top, so without this it ships.
# The `mockup*.html` files under examples/ ARE Stage-B deliverables — keep them.
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "desktop.ini",
                 "preview_from_project.html"}

# Paths that must never appear in the archive, whatever else changes.
# NB: `dist/` is matched at the ARCHIVE ROOT only.  Vendored npm packages ship
# their own `…/node_modules/<pkg>/dist/` build folders, and those are legitimate
# payload — flagging them would make every release "fail".
FORBIDDEN_PREFIXES = (".workbuddy/", "dist/", "__pycache__/", ".git/")
FORBIDDEN_SEGMENTS = ("/__pycache__/", "/.workbuddy/")
FORBIDDEN_SUFFIXES = (".zip", ".log", ".pyc", ".pyo")

SKIPPED_TOP = []


def walk(skip_vendor=False):
    """Yield (abs_path, archive_relpath) for the shippable file set only."""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT).replace("\\", "/")

        if rel_dir == ".":
            # Archive root: allowlist.  Everything else is reported, not silently
            # dropped — that is the whole point of the change.
            keep = []
            for d in sorted(dirnames):
                if d in SHIP_TOP:
                    keep.append(d)
                else:
                    SKIPPED_TOP.append(d + "/")
            dirnames[:] = keep
            for f in sorted(filenames):
                if f in SHIP_TOP and not f.endswith(EXCLUDE_FILE_SUFFIX):
                    yield os.path.join(dirpath, f), f
                elif f not in EXCLUDE_FILES:
                    SKIPPED_TOP.append(f)
            continue

        dirnames[:] = sorted(d for d in dirnames
                             if d not in EXCLUDE_DIR_NAMES)
        if skip_vendor and rel_dir == "tools":
            dirnames[:] = [d for d in dirnames if d != "node_modules"]

        for f in sorted(filenames):
            if f in EXCLUDE_FILES or f.endswith(EXCLUDE_FILE_SUFFIX):
                continue
            p = os.path.join(dirpath, f)
            yield p, os.path.relpath(p, ROOT).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--no-vendor", action="store_true",
                    help="leave tools/node_modules out (the archive then needs "
                         "`npm install` + `python tools/vendor_prepare.py`)")
    ap.add_argument("--list", action="store_true", help="only list what would ship")
    args = ap.parse_args()

    del SKIPPED_TOP[:]
    items = list(walk(args.no_vendor))
    total = sum(os.path.getsize(p) for p, _ in items)
    print("%d files, %.1f MB uncompressed" % (len(items), total / 1048576))

    if SKIPPED_TOP:
        print("\nnot shipped (outside the top-level allowlist):")
        for s in SKIPPED_TOP:
            print("   - %s" % s)
        print("   ^ add to SHIP_TOP in this file if any of these SHOULD ship.")

    if args.list:
        for _p, rel in items:
            print("  " + rel)
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    if os.path.exists(args.out):
        os.remove(args.out)

    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as z:
        for p, rel in items:
            # ZipInfo carries the name; zipfile sets the UTF-8 flag (0x800)
            # automatically for anything that is not pure ASCII.
            zi = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(p, "rb") as fh:
                z.writestr(zi, fh.read())

    size_mb = os.path.getsize(args.out) / 1048576
    print("\nwrote %s (%.1f MB)" % (args.out, size_mb))

    # ---- verify the archive we just built --------------------------------
    bad, nonascii = [], []
    with zipfile.ZipFile(args.out) as z:
        names = z.namelist()
        tops = sorted({n.split("/")[0] for n in names if n})
        nested_root = os.path.basename(args.out)[:-4] + "/"
        for i in z.infolist():
            name = i.filename
            if any(ord(c) > 127 for c in name):
                nonascii.append(name)
                # the raw bytes must be valid UTF-8 AND the flag must be set
                if not (i.flag_bits & 0x800):
                    bad.append((name, "UTF-8 flag bit not set"))
                try:
                    name.encode("utf-8").decode("utf-8")
                except Exception as e:                        # noqa: BLE001
                    bad.append((name, str(e)))
            if "?" in name or "\ufffd" in name:
                bad.append((name, "replacement char in name"))

        leaks = [n for n in names
                 if n.startswith(FORBIDDEN_PREFIXES)
                 or any(seg in n for seg in FORBIDDEN_SEGMENTS)
                 or n.endswith(FORBIDDEN_SUFFIXES)
                 or n.startswith(nested_root)]
        missing = [t for t in ("README.md", "skills", "tools") if t not in tops]

    print("non-ASCII filenames: %d" % len(nonascii))
    for n in nonascii[:8]:
        print("   ", n)
    print("root entries: %s" % ", ".join(tops))

    if leaks:
        print("\n!! HYGIENE PROBLEM — the archive contains things that must not ship:")
        for n in leaks[:12]:
            print("   -", n)
        if len(leaks) > 12:
            print("   ... and %d more" % (len(leaks) - 12))
        print("   This is what a 'zip the whole working directory' archive looks")
        print("   like. Rebuild with this script and ship ONLY its output.")
    if missing:
        print("\n!! missing expected root entries: %s" % ", ".join(missing))
    if bad:
        print("\n!! ENCODING PROBLEMS")
        for n, why in bad:
            print("   -", n, "->", why)

    if leaks or bad or missing:
        return 1

    print("name encoding: OK (all names are clean UTF-8, flag bit set)")
    print("""
=======================  DELIVERABLE  =======================
  %s
  Ship THIS FILE. Never zip the working directory: that is how
  .workbuddy/ notes and a nested dist/*.zip got shipped before.
=============================================================""" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
