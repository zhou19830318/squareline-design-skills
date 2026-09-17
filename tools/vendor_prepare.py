#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vendor the platform-specific @resvg native bindings (+ the WASM fallback).

Why this exists
---------------
`@resvg/resvg-js` is a napi-rs native module: `npm install` only downloads the
prebuilt `.node` binary matching the **machine that ran the install**.  A package
built on Windows therefore explodes with

    Cannot find module '@resvg/resvg-js-linux-x64-gnu'

the moment it is unzipped inside a Linux container — Stage A dies before any of
the interesting work starts.  This script fixes that by side-loading every
target platform's binding into `tools/node_modules/@resvg/`, so the shipped tree
runs offline on Windows / Linux (glibc + musl) / macOS, no `npm install` needed.

It also prunes `lucide-static` down to the only directory the generators read
(`icons/`), which reclaims ~46 MB — enough to pay for the extra bindings.

Usage
-----
    python tools/vendor_prepare.py                 # bundle the default target set
    python tools/vendor_prepare.py --prune-lucide  # also shrink lucide-static
    python tools/vendor_prepare.py --verify        # smoke-test the renderer
    python tools/vendor_prepare.py --list          # show what is present/missing
    python tools/vendor_prepare.py --platforms linux-riscv64-gnu --force
"""

import argparse
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request

RESVG_VERSION = "2.6.2"
REGISTRY = "https://registry.npmjs.org"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE_MODULES = os.path.join(ROOT, "tools", "node_modules")
RESVG_DIR = os.path.join(NODE_MODULES, "@resvg")

# Bindings worth shipping inside the package.  Everything else can be pulled on
# demand with --platforms <name> on a machine that has network access.
DEFAULT_PLATFORMS = [
    "linux-x64-gnu",        # Debian/Ubuntu containers — the common freebuff case
    "linux-x64-musl",       # Alpine containers
    "linux-arm64-gnu",      # Graviton / Apple-Silicon docker
    "linux-arm64-musl",     # Alpine on ARM
    "darwin-arm64",         # Apple Silicon macOS
    "darwin-x64",           # Intel macOS
    "win32-x64-msvc",       # Windows x64
]
# Deliberately not bundled by default (add via --platforms when you need them):
#   linux-arm-gnueabihf (32-bit Raspberry Pi), win32-arm64-msvc, win32-ia32-msvc,
#   android-arm64, android-arm-eabi

# What `vendor_prepare.py --prune-lucide` keeps.  The generators only ever read
# node_modules/lucide-static/icons/<name>.svg — the font/ and dist/ trees are
# 45 MB of dead weight for this pipeline.
LUCIDE_KEEP = {"icons", "package.json", "LICENSE", "README.md"}

# file that must exist inside each unpacked platform package
BINDING_FILE = {
    "win32-x64-msvc": "resvgjs.win32-x64-msvc.node",
    "win32-ia32-msvc": "resvgjs.win32-ia32-msvc.node",
    "win32-arm64-msvc": "resvgjs.win32-arm64-msvc.node",
    "darwin-x64": "resvgjs.darwin-x64.node",
    "darwin-arm64": "resvgjs.darwin-arm64.node",
    "linux-x64-gnu": "resvgjs.linux-x64-gnu.node",
    "linux-x64-musl": "resvgjs.linux-x64-musl.node",
    "linux-arm64-gnu": "resvgjs.linux-arm64-gnu.node",
    "linux-arm64-musl": "resvgjs.linux-arm64-musl.node",
    "linux-arm-gnueabihf": "resvgjs.linux-arm-gnueabihf.node",
    "android-arm64": "resvgjs.android-arm64.node",
    "android-arm-eabi": "resvgjs.android-arm-eabi.node",
}


def log(*a):
    print(*a, flush=True)


def fetch_tarball(name, version):
    """Download an npm package tarball, return (tmpdir, extracted_pkg_dir)."""
    url = "%s/%s/-/%s-%s.tgz" % (REGISTRY, name.replace("/", "%2F"),
                                 name.split("/")[-1], version)
    tmp = tempfile.mkdtemp(prefix="vendor_")
    tgz = os.path.join(tmp, "pkg.tgz")
    log("  GET %s" % url)
    with urllib.request.urlopen(url, timeout=90) as r, open(tgz, "wb") as f:
        shutil.copyfileobj(r, f)
    with tarfile.open(tgz, "r:gz") as tf:
        tf.extractall(tmp)
    return tmp, os.path.join(tmp, "package")


def install_platform(platform, version, force=False):
    pkg = "resvg-js-%s" % platform
    dest = os.path.join(RESVG_DIR, pkg)
    marker = os.path.join(dest, BINDING_FILE.get(platform, "package.json"))
    if os.path.exists(marker) and not force:
        log("  = %-24s already vendored" % pkg)
        return True
    if os.path.exists(dest):
        shutil.rmtree(dest)
    try:
        tmp, src = fetch_tarball("@resvg/" + pkg, version)
    except Exception as e:
        log("  x %-24s download failed: %s" % (pkg, e))
        return False
    shutil.copytree(src, dest)
    # drop npm bookkeeping that only confuses a checked-in tree
    for junk in ("_resvgjs.node",):
        j = os.path.join(dest, junk)
        if os.path.exists(j):
            os.remove(j)
    shutil.rmtree(tmp, ignore_errors=True)
    ok = os.path.exists(marker)
    log("  %s %-24s %s" % ("+" if ok else "x", pkg,
                           "%d KB" % (os.path.getsize(marker) // 1024) if ok else "MISSING BINDING"))
    return ok


def install_wasm(version, force=False):
    """The universal fallback: no native binding, runs on any Node >= 12."""
    dest = os.path.join(RESVG_DIR, "resvg-wasm")
    if os.path.exists(os.path.join(dest, "index.js")) and not force:
        log("  = resvg-wasm                already vendored")
        return True
    try:
        tmp, src = fetch_tarball("@resvg/resvg-wasm", version)
    except Exception as e:
        log("  x resvg-wasm                download failed: %s" % e)
        return False
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    shutil.rmtree(tmp, ignore_errors=True)
    n = sum(os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(dest) for f in fs)
    log("  + resvg-wasm                %d KB" % (n // 1024))
    return True


def prune_lucide():
    base = os.path.join(NODE_MODULES, "lucide-static")
    if not os.path.isdir(base):
        log("lucide-static not found — run `npm install` in tools/ first")
        return False
    before = sum(os.path.getsize(os.path.join(dp, f))
                 for dp, _, fs in os.walk(base) for f in fs)
    for entry in os.listdir(base):
        if entry in LUCIDE_KEEP:
            continue
        p = os.path.join(base, entry)
        shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
    after = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(base) for f in fs)
    log("lucide-static pruned: %.1f MB -> %.1f MB (kept: %s)"
        % (before / 1048576, after / 1048576, ", ".join(sorted(LUCIDE_KEEP))))
    return True


def report():
    log("\n%-26s %s" % ("package", "state"))
    log("-" * 60)
    for p in DEFAULT_PLATFORMS:
        mark = BINDING_FILE.get(p, "package.json")
        d = os.path.join(RESVG_DIR, "resvg-js-%s" % p)
        ok = os.path.exists(os.path.join(d, mark))
        log("%-26s %s" % ("resvg-js-" + p, "OK" if ok else "missing"))
    w = os.path.join(RESVG_DIR, "resvg-wasm", "index.js")
    log("%-26s %s" % ("resvg-wasm", "OK" if os.path.exists(w) else "missing"))
    core = os.path.join(RESVG_DIR, "resvg-js", "index.js")
    log("%-26s %s" % ("resvg-js (core)", "OK" if os.path.exists(core) else "missing"))


def verify():
    """Render a tiny SVG through the same shim the generators use."""
    import subprocess
    node = os.environ.get("SQUARELINE_NODE_BIN") or shutil.which("node") or "node"
    shim = os.path.join(ROOT, "tools", "lib", "resvg.mjs")
    script = (
        "import {renderSvg} from %s;"
        "const png = await renderSvg('<svg xmlns=\"http://www.w3.org/2000/svg\""
        " width=\"24\" height=\"24\"><rect width=\"24\" height=\"24\""
        " fill=\"#0A84FF\"/></svg>', 24, 24);"
        "console.log('backend=' + (globalThis.__RESVG_BACKEND__||'?')"
        " + ' bytes=' + png.length"
        " + ' size=' + png.readUInt32BE(16) + 'x' + png.readUInt32BE(20));"
        % json.dumps(shim)
    )
    log("\nrenderer smoke test (node=%s)" % node)
    r = subprocess.run([node, "--input-type=module", "-e", script],
                       capture_output=True, text=True, cwd=ROOT)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        log("VERIFY FAILED")
        return False
    log("VERIFY OK")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platforms", nargs="*", default=None,
                    help="extra/different platform bindings to vendor "
                         "(e.g. win32-arm64-msvc linux-arm-gnueabihf), "
                         "'all' vendors every published target")
    ap.add_argument("--version", default=RESVG_VERSION)
    ap.add_argument("--no-wasm", action="store_true", help="skip the WASM fallback")
    ap.add_argument("--prune-lucide", action="store_true",
                    help="delete lucide-static's unused font/ and dist/ trees (~46 MB)")
    ap.add_argument("--verify", action="store_true", help="smoke-test the renderer after")
    ap.add_argument("--force", action="store_true", help="re-download even if present")
    ap.add_argument("--list", action="store_true", help="only report what is vendored")
    args = ap.parse_args()

    if args.list:
        report()
        return 0

    os.makedirs(RESVG_DIR, exist_ok=True)
    platforms = DEFAULT_PLATFORMS if args.platforms is None else args.platforms
    if platforms == ["all"]:
        platforms = sorted(BINDING_FILE)

    log("vendoring @resvg bindings into tools/node_modules/@resvg/")
    failed = [p for p in platforms if not install_platform(p, args.version, args.force)]
    if not args.no_wasm:
        install_wasm(args.version, args.force)

    if args.prune_lucide:
        prune_lucide()

    report()
    if failed:
        log("\n!! could not vendor: %s" % ", ".join(failed))
        return 1
    if args.verify:
        return 0 if verify() else 1
    log("\ndone. The tree now runs offline on: %s" % ", ".join(platforms))
    return 0


if __name__ == "__main__":
    sys.exit(main())
