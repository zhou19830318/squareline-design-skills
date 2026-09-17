#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Release checklist — run this before shipping the package.

Every item is a claim in the optimisation review that has to keep holding:
"it runs in a bare container", "the validator really checks 10 things",
"no developer paths leaked in", "the zip is UTF-8", "the eval suite passes",
"the archived artifacts do not depend on the build host", and "the packer is
allowlist-driven so a folder-zip cannot leak agent state".

    python tools/preflight.py            # the cheap checks (a few seconds)
    python tools/preflight.py --full     # + the full regression build (minutes)

Exit code 0 = all green, 1 = at least one FAIL.
"""

import argparse
import ast
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "python"

RESULTS = []


def record(name, ok, detail="", required=True):
    RESULTS.append((name, ok, detail, required))
    tag = "PASS" if ok is True else ("SKIP" if ok is None else "FAIL")
    print("[%s] %s" % (tag, name))
    if detail:
        for line in str(detail).splitlines():
            print("       " + line)


def run(args, cwd=ROOT, env=None, timeout=900):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=e, timeout=timeout)


# ---------------------------------------------------------------- checks ---

def check_renderer():
    """Stage A must be able to rasterise an SVG on THIS machine."""
    node = os.environ.get("SQUARELINE_NODE_BIN") or "node"
    shim = os.path.join(ROOT, "tools", "lib", "resvg.mjs")
    if not os.path.exists(shim):
        return record("renderer: SVG -> PNG works", False, "tools/lib/resvg.mjs missing")
    # `node -e "import ... from 'C:\\path'"` dies on Windows with
    # ERR_UNSUPPORTED_ESM_URL_SCHEME: --input-type=module only accepts
    # file:/data:/node: specifiers, and a bare drive path is none of those.
    # Hand the loader a real file:// URL so the probe is portable.
    import pathlib
    shim_url = pathlib.Path(shim).as_uri()
    script = (
        "import {renderSvg, resvgBackend, resvgBackendError} from %s;"
        "const png = renderSvg('<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\""
        " height=\"24\"><rect width=\"24\" height=\"24\" fill=\"#0A84FF\"/></svg>', 24, 24);"
        "console.log('backend=' + resvgBackend() + ' bytes=' + png.length + ' size='"
        " + png.readUInt32BE(16) + 'x' + png.readUInt32BE(20));"
        % json.dumps(shim_url)
    )
    try:
        r = run([node, "--input-type=module", "-e", script], timeout=120)
    except FileNotFoundError:
        return record("renderer: SVG -> PNG works", False,
                      "node not found on PATH (set SQUARELINE_NODE_BIN)")
    if r.returncode != 0:
        return record("renderer: SVG -> PNG works", False, (r.stdout + r.stderr)[-800:])
    out = r.stdout.strip()
    if "size=24x24" not in out:
        return record("renderer: SVG -> PNG works", False, out)
    return record("renderer: SVG -> PNG works", True, out)


def check_bindings():
    """Cross-platform bindings must be vendored — otherwise the zip only runs
    on the machine that built it."""
    resvg = os.path.join(ROOT, "tools", "node_modules", "@resvg")
    want = ["linux-x64-gnu", "linux-x64-musl", "linux-arm64-gnu",
            "darwin-arm64", "darwin-x64", "win32-x64-msvc"]
    missing = [p for p in want if not os.path.isdir(os.path.join(resvg, "resvg-js-" + p))]
    wasm = os.path.exists(os.path.join(resvg, "resvg-wasm", "index_bg.wasm"))
    detail = "vendored: %s | wasm fallback: %s" % (
        ", ".join(p for p in want if p not in missing) or "none",
        "yes" if wasm else "NO")
    return record("resvg bindings vendored for Linux/macOS/Windows", not missing,
                  detail)


def check_snapshot():
    r = run([PY, "tools/sq_catalog.py", "--check"])
    return record("schema snapshot present and usable", r.returncode == 0,
                  (r.stdout + r.stderr).strip())


def _golden_projects():
    return sorted(glob.glob(os.path.join(
        ROOT, "examples", "*", "squareline", "*", "*.spj")))


def check_validator():
    projects = _golden_projects()
    if not projects:
        return record("validator: OK on every archived project", False,
                      "no examples/*/squareline/*/*.spj found")
    lines, ok = [], True
    for p in projects:
        r = run([PY, "tools/validate_squareline_project.py", os.path.dirname(p)])
        good = "OK - project validated" in r.stdout
        ok = ok and good
        src = "snapshot" if "schema_snapshot.json" in r.stdout else "no snapshot!"
        lines.append("%-42s %s  (strtype source: %s)"
                     % (os.path.relpath(p, ROOT), "OK" if good else "FAIL", src))
        if not good:
            lines.append((r.stdout + r.stderr)[-600:])
    return record("validator: OK on every archived project", ok, "\n".join(lines))


def check_validator_without_studio():
    """The whole point of the snapshot: validation must not depend on a local
    SquareLine install.  Simulate a container by hiding SQUARELINE_STUDIO."""
    projects = _golden_projects()
    if not projects:
        return record("validator works without a SquareLine install", None)
    env = {"SQUARELINE_STUDIO": ""}
    r = run([PY, "tools/validate_squareline_project.py", os.path.dirname(projects[0])],
            env=env)
    ok = "OK - project validated" in r.stdout and "check 2 weakened" not in r.stdout
    return record("validator works without a SquareLine install", ok,
                  r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])


def _text_files():
    """Every shipped text file the checks below care about."""
    out = []
    for base, exts in (("tools", (".py", ".mjs")), ("skills", (".md",)),
                       ("eval", (".py", ".md", ".sh")), ("templates", (".md",))):
        d = os.path.join(ROOT, base)
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames
                           if x not in ("node_modules", "__pycache__")]
            for f in filenames:
                if f.endswith(exts):
                    out.append(os.path.join(dirpath, f))
    for f in ("README.md",):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            out.append(p)
    return sorted(out)


def check_source_health():
    r"""Every shipped source file must compile, and no string constant may
    contain a lone surrogate.

    Why this exists: `\udcXX` inside a NON-raw Python string literal decodes
    into a real surrogate character at runtime, and no UTF-8 encoder accepts
    those.  tools/package_release.py demonstrated mojibake in its docstring with
    literal `\udcbf\udcc9` escapes, `__doc__` went straight into argparse, and
    the packager could not even print --help.  The failure mode is nasty because
    `python -c "import x"` looks fine — the encoder only runs later.

    AST-walking for surrogates catches it precisely, and compilation catches
    plain syntax rot at the same time.
    """
    bad_compile, bad_surrogate, bad_text = [], [], []
    esc = re.compile(r"\\u[dD][89abAB][0-9a-fA-F]{2}")
    for p in _text_files():
        rel = os.path.relpath(p, ROOT)
        try:
            raw = open(p, "rb").read()
        except Exception as e:                       # noqa: BLE001
            bad_compile.append("%s: unreadable (%s)" % (rel, e))
            continue
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            bad_text.append("%s: not valid UTF-8 (%s)" % (rel, e))
            continue

        if p.endswith(".py"):
            try:
                tree = ast.parse(txt, filename=p)
            except SyntaxError as e:
                bad_compile.append("%s: SyntaxError line %s (%s)"
                                   % (rel, e.lineno, e.msg))
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    for ch in node.value:
                        if 0xD800 <= ord(ch) <= 0xDFFF:
                            bad_surrogate.append(
                                "%s: string constant holds lone surrogate U+%04X"
                                % (rel, ord(ch)))
                            break
        elif esc.search(txt):
            # JS string literals decode \udXXX the same way Python does
            bad_surrogate.append("%s: contains a \\udXXX escape (JS decodes it "
                                 "to a lone surrogate)" % rel)

    problems = bad_compile + bad_surrogate + bad_text
    detail = "clean (%d file(s) compiled + AST-checked)" % len(_text_files())
    return record("sources: compile, UTF-8 clean, no lone surrogates",
                  not problems, "\n".join(problems[:12]) if problems else detail)


def check_no_personal_paths():
    """No developer-specific absolute paths may ship in tools/, skills/, eval/."""
    # Two halves of the token are joined at runtime so this file's own source
    # does not contain the literal it hunts for (it would flag itself).
    user = "Administr" + "ator"
    pat = re.compile(r"(C:\\+Users\\+[^\\/\"']+|/home/[A-Za-z0-9._-]+|" + user + ")")
    self_path = os.path.abspath(__file__)
    hits = []
    for base, exts in (("tools", (".py", ".mjs")), ("skills", (".md",)),
                       ("eval", (".py", ".sh", ".md"))):
        d = os.path.join(ROOT, base)
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames if x not in ("node_modules", "__pycache__")]
            for f in filenames:
                if not f.endswith(exts):
                    continue
                p = os.path.join(dirpath, f)
                if os.path.abspath(p) == self_path:
                    continue                      # this checker is allowed one hit
                title = "<REDACTED>"           # never echo a hit verbatim
                try:
                    txt = open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                for i, line in enumerate(txt.splitlines(), 1):
                    if pat.search(line):
                        hits.append("%s:%d: %s" % (os.path.relpath(p, ROOT), i,
                                                   pat.sub(title, line.strip())[:110]))
    return record("no developer-specific paths in shipped code", not hits,
                  "\n".join(hits[:12]) if hits else "clean")


def check_zip():
    dist = os.path.join(ROOT, "dist")
    zips = sorted(glob.glob(os.path.join(dist, "*.zip")))
    if not zips:
        return record("release zip: UTF-8 file names", None,
                      "no zip in dist/ — run: python tools/package_release.py")
    import zipfile
    bad = []
    for zp in zips:
        try:
            with zipfile.ZipFile(zp) as z:
                for i in z.infolist():
                    if any(ord(c) > 127 for c in i.filename) and not (i.flag_bits & 0x800):
                        bad.append("%s: %s (UTF-8 flag missing)" % (os.path.basename(zp),
                                                                    i.filename))
                    if "?" in i.filename or "\ufffd" in i.filename:
                        bad.append("%s: %s (replacement char)" % (os.path.basename(zp),
                                                                  i.filename))
        except Exception as e:
            bad.append("%s: unreadable (%s)" % (zp, e))
    return record("release zip: UTF-8 file names", not bad,
                  "\n".join(bad[:10]) if bad else "%d archive(s) clean" % len(zips))


# Things the archive is useless without.  An over-broad EXCLUDE_DIRS rule once
# looked fine because the count was merely "lower" — these assertions make that
# failure loud instead.  Names are suffixed with "/" when a whole dir must ship.
ZIP_REQUIRED = [
    "README.md",
    # The line-ending pin travels with the tree, so a re-clone cannot
    # reintroduce CRLF into the byte-compared goldens.
    ".gitattributes",
    ".gitignore",
    "skills/squareline-ui-pipeline/SKILL.md",
    "skills/squareline-ui-pipeline/REFERENCE.md",
    "templates/设计规格文档模板.md",
    "eval/run_regression.py",
    "eval/test_cases.md",
    "tools/build_from_spec.py",
    "tools/engine/squareline_engine.py",
    "tools/lib/resvg.mjs",
    "tools/schema_snapshot.json",
    "tools/preflight.py",
    "tools/package_release.py",
    "tools/node_modules/lv_font_conv/",
    "tools/node_modules/@resvg/resvg-wasm/",
    "tools/node_modules/@resvg/resvg-js-linux-x64-gnu/",
    "tools/node_modules/@resvg/resvg-js-darwin-arm64/",
    "tools/node_modules/@resvg/resvg-js-win32-x64-msvc/",
    "examples/AIWatchApple/squareline/AIWatchApple/AIWatchApple.spj",
    "examples/AIWatch/squareline/AIWatch/AIWatch.spj",
    "examples/SpecWidget/squareline/SpecWidget/SpecWidget.spj",
    "examples/SpecWidget/SpecWidget.spec.json",
    "fonts/",
]


def check_zip_contents():
    """The archive must actually contain the pipeline, the vendored renderer
    bindings and the archived examples — and nothing else."""
    zips = sorted(glob.glob(os.path.join(ROOT, "dist", "*.zip")))
    if not zips:
        return record("release zip: required payload present", None,
                      "no zip in dist/ — run: python tools/package_release.py")
    import zipfile
    zp = zips[-1]
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
    missing = [r for r in ZIP_REQUIRED
               if not (any(n.startswith(r) for n in names) if r.endswith("/")
                       else r in names)]
    # A folder-shaped archive is the signature of "somebody zipped the working
    # directory": every entry is prefixed with the repo folder name, which is
    # how .workbuddy/ notes and a nested dist/*.zip got shipped once.
    folder_shaped = os.path.basename(zp)[:-4] + "/"
    leaked = [n for n in names
              if n.startswith(("dist/", ".workbuddy/", folder_shaped))
              or ".workbuddy/" in n or "/__pycache__/" in n
              or n.endswith((".zip", ".log", ".pyc", ".pyo"))
              or n.endswith("preview_from_project.html")]
    problems = (["missing: " + m for m in missing]
                + ["should not ship: " + l for l in leaked[:6]])
    return record("release zip: required payload present", not problems,
                  "\n".join(problems) if problems
                  else "%d file(s), all required paths present, no churn"
                  % len(names))


def _golden_text_files():
    """Every non-binary, non-generated file inside an archived project."""
    out = []
    for spj in _golden_projects():
        root = os.path.dirname(spj)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in ("backup", "cache", "components", "ui",
                                        "__pycache__")]
            for f in filenames:
                if f.endswith((".png", ".bin", ".ttf", ".node", ".html",
                               ".preview.json")) or f == ".gitignore":
                    continue
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def _shipped_text_files():
    """Every shippable non-binary file, mirroring package_release.py's walk.

    Deliberately wider than ``_golden_text_files``: the golden projects are only
    the *byte-compared* artifacts, but the same LF rule has to hold for the
    tools and docs we ship, or `.gitattributes` rewrites them on commit and the
    working tree silently diverges from the repository.  That is not
    hypothetical — two shipped tool files were still CRLF when this check was
    first widened, and the golden-only version had reported "all LF".
    """
    skip_top = {"node_modules", ".git", "dist", ".workbuddy", "__pycache__",
                "backup", "cache", "components", "ui", ".pytest_cache",
                ".idea", ".vscode"}
    binary = (".png", ".bin", ".ttf", ".node", ".zip", ".dav", ".ico", ".jpg",
              ".jpeg", ".gif")
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_top]
        for f in filenames:
            if f.endswith(binary):
                continue
            out.append(os.path.join(dirpath, f))
    return sorted(out)


def check_artifact_eol():
    """Shipped text must be **LF-only** — goldens *and* the tools that write them.

    eval/run_regression.py diffs the archived projects byte for byte against a
    fresh build, and the engine pins LF on every host (see engine.dump_json).
    So a CRLF golden can only mean somebody committed it from a machine without
    that fix, or a `git checkout` rewrote it (core.autocrlf=true) — either way
    comparisons go red for a reason that is invisible in the diff.

    The tools and README are held to the same rule, because `.gitattributes`
    (`* text=auto eol=lf`) normalises them on commit: a CRLF working copy then
    differs from what git stores, which shows up as phantom modifications and a
    "CRLF will be replaced by LF" warning on every `git add`.
    """
    files = _shipped_text_files()
    if not files:
        return record("shipped text is LF-only", None, "nothing found to check")
    bad = []
    for p in files:
        try:
            if b"\r" in open(p, "rb").read():
                bad.append(os.path.relpath(p, ROOT).replace("\\", "/"))
        except OSError:
            continue
    if bad:
        goldens = [p for p in bad if p.startswith("examples/")]
        fix = ("fix: python eval/run_regression.py --update"
               if goldens else
               "fix: rewrite the file with newline='\\n' (see engine.dump_json)")
        return record("shipped text is LF-only (host-independent artifacts)",
                      False,
                      "%d file(s) carry CRLF:\n%s\n%s"
                      % (len(bad), "\n".join(bad[:10]), fix))
    return record("shipped text is LF-only (host-independent artifacts)", True,
                  "%d file(s) checked, all LF" % len(files))


def check_doc_scripts_linked():
    """Every script advertised in the README/tools table must actually exist.

    A usage doc is the one file most likely to drift from reality: it is edited
    by hand, never imported, and never executed.  Cross-checking the names it
    mentions against the tool list turns "the README lies" into a red check.
    """
    readme = os.path.join(ROOT, "README.md")
    if not os.path.exists(readme):
        return record("docs: every advertised tool exists", False, "README.md missing")
    body = open(readme, encoding="utf-8").read()
    names = set(re.findall(r"`([A-Za-z_][\w./-]*\.(?:py|mjs|json))`", body))
    missing = []
    for n in sorted(names):
        if n in ("package.json", "schema_snapshot.json"):
            continue
        if n.startswith("lib/"):
            ok = os.path.exists(os.path.join(ROOT, "tools", n))
        else:
            ok = (os.path.exists(os.path.join(ROOT, "tools", n))
                  or os.path.exists(os.path.join(ROOT, "eval", n))
                  or os.path.exists(os.path.join(ROOT, n)))
        if not ok:
            missing.append(n)
    return record("docs: every advertised tool exists", not missing,
                  ("README names missing file(s): " + ", ".join(missing))
                  if missing else "%d referenced script(s) all present" % len(names))


def check_packer_allowlist():
    """The packer must be allowlist-driven.

    `--list` may never mention agent state, build output or a nested archive —
    not even when a stale dist/*.zip is sitting there — because that is exactly
    what a blocklist gets wrong once a new scratch directory appears.
    """
    r = run([PY, "tools/package_release.py", "--list"], timeout=300)
    if r.returncode != 0:
        return record("packer: allowlist keeps agent state out", False,
                      (r.stdout + r.stderr)[-600:])
    # items print as "  <rel>"; the "not shipped" report prints "   - <name>"
    items = [ln.strip() for ln in r.stdout.splitlines()
             if ln.startswith("  ") and not ln.strip().startswith("-")]
    forbidden = ("dist/", ".workbuddy/", "__pycache__/")
    bad = [i for i in items
           if i.startswith(forbidden) or "/.workbuddy/" in i
           or i.endswith((".zip", ".log", ".pyc"))
           or i.endswith("preview_from_project.html")]
    reported = "- .workbuddy/" in r.stdout or "- dist/" in r.stdout
    problems = (["would ship: " + b for b in bad[:8]]
                + ([] if reported else
                   ["the 'not shipped' report did not mention .workbuddy/ or "
                    "dist/ — is the allowlist still applied?"]))
    return record("packer: allowlist keeps agent state out", not problems,
                  "\n".join(problems) if problems
                  else "%d shippable file(s), .workbuddy/ and dist/ excluded"
                  % len(items))


def check_deliverable():
    """Name the single deliverable, and flag any folder-shaped archive sitting
    next to the repo.  The repo cannot be blamed for what is in its parent dir,
    so the second half is advisory (SKIP), but it is the one thing that actually
    went wrong in delivery: a 123 MB `squareline-design-skills.zip` made by
    zipping the working directory shipped the agent's notes to the reviewer."""
    import zipfile
    dist_zips = sorted(glob.glob(os.path.join(ROOT, "dist", "*.zip")))
    ok = bool(dist_zips)
    lines = ["deliverable: %s (%.1f MB)"
             % (os.path.relpath(dist_zips[-1], ROOT).replace("\\", "/"),
                os.path.getsize(dist_zips[-1]) / 1048576)
             if dist_zips else "no dist/*.zip — run: python tools/package_release.py"]
    record("release: exactly one deliverable (dist/*.zip)", ok, "\n".join(lines))

    parent = os.path.dirname(ROOT)
    ours = os.path.basename(ROOT)
    suspicious = []
    try:
        candidates = sorted(f for f in os.listdir(parent)
                            if f.lower().endswith(".zip"))
    except OSError:
        candidates = []
    for f in candidates:
        p = os.path.join(parent, f)
        try:
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
        except Exception:                                  # noqa: BLE001
            continue
        if not any(n.startswith(ours + "/") for n in names):
            continue
        leaks = [n for n in names
                 if n.startswith(ours + "/.workbuddy")
                 or n.startswith(ours + "/dist/")]
        suspicious.append("%s (%.1f MB)%s"
                          % (f, os.path.getsize(p) / 1048576,
                             "  LEAKS: " + ", ".join(sorted(set(leaks))[:3])
                             if leaks else ""))
    return record("release: no folder-shaped archive next to the repo",
                  None if suspicious else True,
                  ("these are NOT deliverables — do not send them:\n"
                   + "\n".join("   - " + s for s in suspicious)
                   + "\n   ship only dist/*.zip (see tools/package_release.py)")
                  if suspicious
                  else "none in %s" % os.path.relpath(parent, ROOT))


# Paths that were deliberately removed from the project.  A cleanup pass is the
# classic moment to leave dangling references behind — a doc still telling the
# reader to open a folder that no longer exists, or worse, the packer still
# listing it in its allowlist (which would silently do nothing).  Naming them
# explicitly turns "did I get them all?" into a mechanical check.
REMOVED_PATHS = (
    "docs/UI-Copilot_可行性评估与架构设计.md",
    "squareline-design-skills-优化建议.md",
)


def check_no_stale_refs():
    """Nothing shipped may still point at a path we have deleted."""
    problems = []
    shipped = [os.path.join(ROOT, "README.md"),
               os.path.join(ROOT, "tools", "package_release.py"),
               os.path.join(ROOT, "tools", "preflight.py"),
               os.path.join(ROOT, "skills", "squareline-ui-pipeline", "SKILL.md"),
               os.path.join(ROOT, "skills", "squareline-ui-pipeline", "REFERENCE.md")]
    for gone in REMOVED_PATHS:
        base = os.path.basename(gone)
        # It is fine (and deliberate) for this check to name them; skip it.
        for p in shipped:
            if not os.path.exists(p) or os.path.basename(p) == "preflight.py":
                continue
            body = open(p, encoding="utf-8", errors="replace").read()
            if base in body:
                problems.append("%s still references the removed %s"
                                % (os.path.relpath(p, ROOT), gone))
    # The packer's allowlist must not name a top-level dir that does not exist:
    # it would look like it ships something while shipping nothing.
    pkg = os.path.join(ROOT, "tools", "package_release.py")
    if os.path.exists(pkg):
        m = re.search(r"SHIP_TOP\s*=\s*\((.*?)\)", open(pkg, encoding="utf-8").read(),
                      re.S)
        if m:
            for entry in re.findall(r'"([^"]+)"', m.group(1)):
                if "/" not in entry and not os.path.exists(os.path.join(ROOT, entry)):
                    problems.append("package_release.py ships '%s' which does not "
                                    "exist at the repo root" % entry)
    return record("cleanup: no dangling references to removed paths",
                  not problems, "\n".join(problems) if problems else
                  "%d removed path(s) unreferenced, allowlist all real"
                  % len(REMOVED_PATHS))



def check_docs():
    skill = os.path.join(ROOT, "skills", "squareline-ui-pipeline", "SKILL.md")
    ref = os.path.join(ROOT, "skills", "squareline-ui-pipeline", "REFERENCE.md")
    tpl = os.path.join(ROOT, "templates", "设计规格文档模板.md")
    readme = os.path.join(ROOT, "README.md")
    problems = []
    if not os.path.exists(tpl):
        problems.append("templates/设计规格文档模板.md missing")
    txt = open(skill, encoding="utf-8").read() if os.path.exists(skill) else ""
    if "设计规格文档模板.md" not in txt:
        problems.append("SKILL.md does not reference the spec-doc template")
    if "通用法则" not in txt or "实例" not in txt:
        problems.append("SKILL.md does not separate instance data from general laws")
    # The optional headless probe must stay OUT of the main flow, but naming it
    # in its own clearly-marked "optional" section is fine (and useful).  So only
    # flag it when it turns up inside a fenced flow/diagram block.
    fences = re.findall(r"```[a-zA-Z]*\n(.*?)```", txt, re.S)
    for block in fences:
        if "probe_headless_render" in block:
            problems.append("SKILL.md lists the optional headless probe in a "
                            "main-flow code block")
            break

    # README is the entry point every agent reads first, so it must document how
    # to plug the skill into the harnesses people actually use — a README that
    # only knows one host hides the fact that nothing here is host-specific.
    if os.path.exists(readme):
        rm = open(readme, encoding="utf-8").read()
        for host in ("Claude Code", "WorkBuddy", "DeepSeek", "豆包", "Freebuff"):
            if host not in rm:
                problems.append("README does not document the %s integration" % host)
        for section in ("接入 agent 工具", "使用方法", "命令速查"):
            if section not in rm:
                problems.append("README is missing the '%s' section" % section)

        # README is a USER guide.  Release/packaging mechanics belong in the
        # maintainer doc, because a reader who only wants to build a project
        # should never have to wade through allowlists and archive assertions.
        # Guard the split in both directions so it cannot silently regress.
        release_doc = os.path.join(ROOT, "tools", "RELEASE.md")
        drifted = [t for t in ("SHIP_TOP", "package_release.py", "dist/*.zip")
                   if t in rm]
        if drifted:
            problems.append("README carries release mechanics (%s) — move them "
                            "to tools/RELEASE.md" % ", ".join(drifted))
        if not os.path.exists(release_doc):
            problems.append("tools/RELEASE.md missing — the release mechanics "
                            "that were removed from README have no home")
        else:
            rl = open(release_doc, encoding="utf-8").read()
            for t in ("SHIP_TOP", "package_release.py", "dist/*.zip"):
                if t not in rl:
                    problems.append("tools/RELEASE.md does not document %s" % t)

    return record("docs: template + per-agent integration documented",
                  not problems, "\n".join(problems) if problems else
                  "SKILL.md + template + README (5 hosts) OK (REFERENCE.md: %s)"
                  % ("present" if os.path.exists(ref) else "MISSING"))


def check_label_height_guide():
    """The LABEL-height rule must be reachable BEFORE the post-build error.

    `run_build()` already errors on `height < line_height`, but only *after*
    fonts are built, and the line height itself is only known by regex-parsing
    the generated .c — so at the moment an author writes coordinates there is
    nothing to consult.  Engineers hit this three times in one project
    (Display96 110<116, Big64 72<78, Score40 48<49).  This check guarantees the
    lookup table exists and that its numbers match what the engine really
    produces, so the doc cannot rot silently.
    """
    doc = os.path.join(ROOT, "tools", "LABEL_SIZING.md")
    if not os.path.exists(doc):
        return record("docs: LABEL height vs line-height guide", False,
                      "tools/LABEL_SIZING.md missing — authors have no lookup "
                      "table for the height>=line_height rule")
    txt = open(doc, encoding="utf-8").read()
    problems = []
    for need in ("line_height", "行高", "height"):
        if need not in txt:
            problems.append("LABEL_SIZING.md does not mention %r" % need)
    # the table must be generated from the real font configs, not hand-typed
    gen = os.path.join(ROOT, "tools", "label_sizing.py")
    if not os.path.exists(gen):
        problems.append("tools/label_sizing.py missing — the table has no "
                        "regenerator and will drift from the engine")
    else:
        r = run([PY, gen, "--check"])
        if r.returncode != 0:
            problems.append("label_sizing --check failed: %s"
                            % (r.stdout + r.stderr).strip()[-400:])
    return record("docs: LABEL height vs line-height guide",
                  not problems,
                  "\n".join(problems) if problems else
                  "tools/LABEL_SIZING.md present and in sync with the engine")


def check_brand_safety_doc():
    """Self-check list for 'inspired by a real product' designs.

    Three separate projects in this repo referenced a real brand (AIWatchApple,
    iWatch, and the Series-12 optimisation), and each time the question "did we
    copy their visual assets, or only their design language?" had to be re-asked
    from scratch.  A written checklist turns that into a reviewable step.
    """
    problems = []
    hits = []
    # The skill docs live under skills/<name>/, not the repo root.
    cands = [os.path.join(ROOT, "skills", "squareline-ui-pipeline", "SKILL.md"),
             os.path.join(ROOT, "skills", "squareline-ui-pipeline", "REFERENCE.md")]
    body = ""
    for p in cands:
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8").read()
        body += t
        if "品牌" in t and ("自查" in t or "清单" in t):
            hits.append(os.path.relpath(p, ROOT))
    if not hits:
        problems.append("no brand-safety self-check list found in "
                        "skills/squareline-ui-pipeline/{SKILL,REFERENCE}.md "
                        "(looking for 品牌 + 自查/清单)")
    # the checklist must name the specific tripwires, not just gesture at them
    for token in ("assets_subdir", "asset"):
        if token not in body:
            problems.append("brand/asset checklist does not cover %r" % token)
    return record("docs: brand-reference self-check list",
                  not problems,
                  "\n".join(problems) if problems else
                  "present in %s" % ", ".join(hits))


def check_eval():
    sh = os.path.join(ROOT, "eval", "run_regression.sh")
    py = os.path.join(ROOT, "eval", "run_regression.py")
    if not os.path.exists(py) and not os.path.exists(sh):
        return record("eval: regression suite passes", None,
                      "eval/run_regression.{py,sh} not present")
    cmd = [PY, py] if os.path.exists(py) else ["bash", sh]
    r = run(cmd, timeout=1800)
    return record("eval: regression suite passes", r.returncode == 0,
                  (r.stdout + r.stderr).strip().splitlines()[-1] if r.stdout.strip() else "")


# ------------------------------------------------------------------ main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true",
                    help="also run the (slow) end-to-end regression build")
    args = ap.parse_args()

    print("preflight — %s\n" % ROOT)
    check_source_health()
    check_renderer()
    check_bindings()
    check_snapshot()
    check_validator()
    check_validator_without_studio()
    check_no_personal_paths()
    check_artifact_eol()
    check_packer_allowlist()
    check_deliverable()
    check_zip()
    check_zip_contents()
    check_docs()
    check_doc_scripts_linked()
    check_no_stale_refs()
    check_label_height_guide()
    check_brand_safety_doc()
    if args.full:
        check_eval()

    print("\n" + "-" * 62)
    failed = [n for n, ok, _d, req in RESULTS if ok is False and req]
    skipped = [n for n, ok, _d, _r in RESULTS if ok is None]
    print("%d checks: %d pass, %d fail, %d skipped"
          % (len(RESULTS), sum(1 for _n, ok, _d, _r in RESULTS if ok is True),
             len(failed), len(skipped)))
    if failed:
        print("FAILED:")
        for n in failed:
            print("  -", n)
        return 1
    print("ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
