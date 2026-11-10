# -*- coding: utf-8 -*-
"""Node dependencies are installed per machine (npm ci), never copied around: @resvg ships one native binding per
platform and npm picks the right one.  Everything that needs lv_font_conv / lucide / resvg calls ensure()."""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # <toolkit>/tools


def present():
    nm = os.path.join(HERE, "node_modules")
    return (os.path.exists(os.path.join(nm, "lv_font_conv", "lv_font_conv.js"))
            and os.path.isdir(os.path.join(nm, "lucide-static", "icons"))
            and os.path.isdir(os.path.join(nm, "@resvg")))


def ensure(quiet=False):
    """Install the Node dependencies once.  Returns True when they are usable."""
    if present():
        return True
    npm = shutil.which("npm")
    if not npm:
        print("slx: Node dependencies are missing and `npm` was not found. Install Node.js (https://nodejs.org), then run:\n"
              "     python3 %s setup" % os.path.join(HERE, "slx.py"), file=sys.stderr)
        return False
    if not quiet:
        print("slx: installing the Node dependencies (one time, needs network): npm ci in %s" % HERE, flush=True)
    cmd = [npm, "ci", "--omit=dev", "--no-audit", "--no-fund"] if os.path.exists(os.path.join(HERE, "package-lock.json")) \
        else [npm, "install", "--omit=dev", "--no-audit", "--no-fund"]
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not present():
        print("slx: npm failed:\n%s\nIf this machine is offline, copy a node_modules folder that was installed ON THE SAME OS/CPU into %s "
              "(do not copy one from another platform)." % ((r.stderr or r.stdout)[-600:], HERE), file=sys.stderr)
        return False
    if not quiet:
        print("slx: Node dependencies ready.")
    return True
