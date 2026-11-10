#!/usr/bin/env python3
"""Fill in the placeholders before the first push.
   python3 scripts/set_owner.py --name "Your Name" --github your-github-username [--email you@example.com]"""
import argparse
import os

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--github", required=True)
ap.add_argument("--email", default="")
a = ap.parse_args()
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rep = {"YOUR_NAME": a.name, "YOUR_GITHUB_USERNAME": a.github}
n = 0
for d, dirs, files in os.walk(root):
    dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "__pycache__")]
    for f in files:
        if not f.endswith((".md", ".json", ".txt", ".py", ".yml")) and f != "LICENSE":
            continue
        p = os.path.join(d, f)
        if os.path.abspath(p) == os.path.abspath(__file__):
            continue
        try:
            t = open(p, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        u = t
        for k, v in rep.items():
            u = u.replace(k, v)
        if u != t:
            open(p, "w", encoding="utf-8", newline="\n").write(u)
            n += 1
if a.email:
    p = os.path.join(root, ".claude-plugin", "marketplace.json")
    t = open(p, encoding="utf-8").read().replace('"owner": {\n    "name": "%s"' % a.name, '"owner": {\n    "name": "%s",\n    "email": "%s"' % (a.name, a.email))
    open(p, "w", encoding="utf-8", newline="\n").write(t)
print("updated %d file(s). Leftover placeholders:" % n)
left = 0
for d, dirs, files in os.walk(root):
    dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "__pycache__")]
    for f in files:
        try:
            t = open(os.path.join(d, f), encoding="utf-8").read()
        except Exception:
            continue
        if ("YOUR_NAME" in t or "YOUR_GITHUB_USERNAME" in t) and f != "set_owner.py":
            print("  ", os.path.relpath(os.path.join(d, f), root))
            left += 1
print("none" if not left else "(%d file(s) above still contain placeholders)" % left)
