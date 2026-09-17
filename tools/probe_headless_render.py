#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPTIONAL deep check — rasterise a frame with SquareLine's own Micropython renderer.

                    ***  NOT part of the normal pipeline  ***

`preview_from_project.py` (pure Python, project-agnostic) is the supported way to
see what a generated .spj looks like; it always works.  This probe is a
belt-and-braces extra: it drives the *real* LVGL build that ships inside the
SquareLine Studio desktop app, so it can catch rendering differences the HTML
re-renderer cannot.  It therefore only runs on a machine that has SquareLine
Studio installed, with a GUI-capable build of the bundled `micropython.exe`.

Use it when you have a local Studio and want ground truth before shipping.
Inside a container — or anywhere without SquareLine — skip it; the validator plus
`preview_from_project.py` are the contract.

Flow: spawn `micropython server.py` -> TCP -> PING/PONG -> SCRIPT builds a screen
      -> BBREQ pulls the framebuffer back -> save PNG.

Usage
-----
    python tools/probe_headless_render.py                      # auto-detect Studio
    SQUARELINE_STUDIO="/opt/SquareLine Studio 1.6.2" python tools/probe_headless_render.py
    python tools/probe_headless_render.py --width 240 --height 240 --out /tmp/frame.png
"""

import argparse
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time

MAGIC = 1229865290
T_SCRIPT, T_BBREQ, T_PING = 1, 3, 4
T_ERR, T_MSG, T_BB, T_PONG = 0, 1, 2, 4

LW = 4          # LVGL stride in bytes (ARGB8888)

DEFAULT_STUDIO_DIRS = [
    r"D:\Program Files\SquareLine Studio 1.6.2",
    r"C:\Program Files\SquareLine Studio 1.6.2",
    "/Applications/SquareLine Studio 1.6.2.app/Contents/MacOS",
    "/opt/SquareLine Studio 1.6.2",
]


def _lvgl_rank(path):
    """Higher = newer.  SquareLine ships several LVGL trees side by side
    (lvgl_v8_3_11, lvgl_v9_2_2, ...); the v9 one is the one to talk to — v8's
    micropython has no `lv.screen_load` and errors out in a confusing way."""
    import re
    m = re.search(r"lvgl_v(\d+)(?:_(\d+))?(?:_(\d+))?", path)
    if not m:
        return (0, 0, 0)
    return tuple(int(x or 0) for x in m.groups())


def find_renderer(explicit=None, lvgl_version=None):
    """Locate SquareLine's bundled micropython + its lvgl server dir.

    A Studio install carries several LVGL trees (lvgl_v8_3_11, lvgl_v9_1_0,
    lvgl_v9_2_2, lvgl_v9_3, lvgl_v9_5, ...).  Pick the one matching the target
    project's `info.lvgl_version` when known, else the newest.

    Returns (server_dir, micropython_path, all_candidates).
    """
    cands = ([explicit] if explicit else []) + \
            ([os.environ["SQUARELINE_STUDIO"]] if os.environ.get("SQUARELINE_STUDIO") else []) + \
            DEFAULT_STUDIO_DIRS
    found = []
    for base in cands:
        if not base or not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            if "server.py" in files and ("micropython.exe" in files or "micropython" in files):
                mpy = os.path.join(root, "micropython.exe")
                if not os.path.exists(mpy):
                    mpy = os.path.join(root, "micropython")
                found.append((root, mpy))
        if found:
            break
    if not found:
        return None, None, []

    want = tuple(int(x) for x in lvgl_version.split(".")) if lvgl_version else None

    def key(t):
        r = _lvgl_rank(t[0])
        return (r == want, r)

    found.sort(key=key, reverse=True)
    return found[0][0], found[0][1], found


def pkt(typ, payload=b""):
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return struct.pack("III", MAGIC, typ, len(payload)) + payload


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("socket closed")
        buf += chunk
    return buf


def recv_pkt(sock, timeout=10.0):
    sock.settimeout(timeout)
    hdr = recv_exact(sock, 12)
    magic, typ, length = struct.unpack("III", hdr)
    assert magic == MAGIC, "bad magic %d" % magic
    payload = recv_exact(sock, length) if length else b""
    return typ, payload


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--studio", default=None, help="SquareLine Studio install dir")
    ap.add_argument("--width", type=int, default=410)
    ap.add_argument("--height", type=int, default=502)
    ap.add_argument("--port", type=int, default=20099)
    ap.add_argument("--out", default=None, help="PNG path (default: tempdir/probe_frame.png)")
    ap.add_argument("--script", default=None, help="extra micropython to run before the grab")
    ap.add_argument("--lvgl-version", default=None,
                    help="prefer the LVGL tree matching this version (e.g. 9.2.2; "
                         "read from the project's info.lvgl_version)")
    args = ap.parse_args()

    if not args.lvgl_version:
        # Read it straight off the default project so the right tree is picked
        # without the user having to know which LVGL versions they have.
        try:
            import glob as _glob
            import json as _json
            cand = sorted(_glob.glob(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "squareline", "*", "*.spj")))
            if cand:
                args.lvgl_version = _json.load(
                    open(cand[0], encoding="utf-8")).get("info", {}).get("lvgl_version")
                if args.lvgl_version:
                    print("target lvgl_version:", args.lvgl_version, "(from %s)"
                          % os.path.basename(cand[0]))
        except Exception:
            pass

    try:
        from PIL import Image
    except ImportError:
        sys.exit("ERROR: Pillow is required (pip install Pillow).")

    server_dir, mpy, all_cands = find_renderer(args.studio, args.lvgl_version)
    if not server_dir:
        sys.exit(
            "SKIP - SquareLine Studio's bundled renderer was not found.\n"
            "       This probe is OPTIONAL and only works on a machine with SquareLine\n"
            "       Studio installed. Set SQUARELINE_STUDIO to your install dir, or use\n"
            "       `python tools/preview_from_project.py <project>` instead."
        )
    print("renderer:", mpy)
    print("server dir:", server_dir)
    if len(all_cands) > 1:
        print("other LVGL trees present (ignored):")
        for r, _m in all_cands[1:]:
            print("   ", r)

    W, H = args.width, args.height
    tmpdir = args.out and os.path.dirname(os.path.abspath(args.out)) or \
        tempfile.mkdtemp(prefix="probe_sl_render_")
    os.makedirs(tmpdir, exist_ok=True)

    proc = subprocess.Popen(
        [mpy, "-X", "heapsize=512m", "server.py", str(W), str(H), str(args.port), tmpdir],
        cwd=server_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    print("server pid", proc.pid)
    time.sleep(2.5)

    sock = socket.create_connection(("127.0.0.1", args.port), timeout=10)
    print("connected")

    try:
        sock.sendall(pkt(T_PING, b""))
        typ, pl = recv_pkt(sock)
        print("handshake: type=%d payload=%r" % (typ, pl[:20]))

        script = (
            "scr = lv.obj()\n"
            "scr.set_style_bg_color(lv.color_hex(0x101828), lv.PART.MAIN)\n"
            "lv.screen_load(scr)\n"
            "lbl = lv.label(scr)\n"
            'lbl.set_text("PROBE OK")\n'
            "lbl.set_style_text_color(lv.color_hex(0xFF2D8A), lv.PART.MAIN)\n"
            "lbl.center()\n"
        )
        if args.script:
            with open(args.script, encoding="utf-8") as f:
                script += f.read() + "\n"
        sock.sendall(pkt(T_SCRIPT, script))
        time.sleep(0.8)
        print("script sent")

        bb_code = (
            "import ustruct\n"
            'strBB = ustruct.pack("IIIII", 0, 0, scr_width-1, scr_height-1, 0)'
            " + bytes(buf1_1)\n"
        )
        sock.sendall(pkt(T_BBREQ, bb_code))
        typ, pl = recv_pkt(sock, timeout=15)
        print("BB response: type=%d len=%d (expect %d)" % (typ, len(pl), 20 + W * H * LW))

        if typ == T_ERR:
            print("ERROR payload:", pl[:400])
            return 2

        x1, y1, x2, y2, scrid = struct.unpack("IIIII", pl[:20])
        print("area=(%d,%d)-(%d,%d) screen=%d" % (x1, y1, x2, y2, scrid))
        img = Image.frombytes("RGBA", (W, H), pl[20:], "raw", "BGRA").convert("RGB")
        out = args.out or os.path.join(tmpdir, "probe_frame.png")
        img.save(out)
        print("saved", out)
        return 0
    finally:
        try:
            sock.close()
        except Exception:
            pass
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
