# -*- coding: utf-8 -*-
"""Requirements traceability.

A requirements document is prose; a model that "reads it and remembers" drops clauses (the
"no hands" rule was nearly lost in one run).  This module turns the document into numbered atomic
requirements, forces a disposition for every one, auto-verifies what it can against the spec, and
writes a traceability matrix.

requirements.json
  {"version":1,"sources":[...],"items":[
     {"id":"R001","text":"...","strength":"MUST|MUST_NOT|SHOULD|INFO","section":"...","source":"file:line",
      "status":"todo|done|deviation|out_of_scope|blocked|info","evidence":"...","reason":"...",
      "verify": null | {"type": ...}, "auto": null|"pass"|"fail"} ]}

Dispositions
  done          implemented in the project; `evidence` required (object/screen/file or a verify rule)
  deviation     implemented differently / partly;  `reason` required
  out_of_scope  belongs to firmware / hardware / another team; `reason` required
  blocked       cannot be done with this engine / data;  `reason` required
  info          not a requirement (context)
"""
import json
import os
import re

STATUSES = ("todo", "done", "deviation", "out_of_scope", "blocked", "info")

MUST_NOT = re.compile(r"(不得|不可以|不可|不能|不允许|禁止|严禁|不应|不要|禁用|切勿|无[^法]{0,2}边框)")
MUST = re.compile(r"(必须|务必|须|应当|应该|需要|(?<![需应])要求|保证|仅|只能|只显示|只[有保能]|默认|至少|不少于|不超过|不低于|"
                  r"必需|唯一|≤|≥|(?<![响对适反供])应(?![用答对急变聘付酬声运战]))")
SHOULD = re.compile(r"(建议|推荐|宜|尽量|最好|优先|可选|可以|可)")
NUMERIC = re.compile(r"\d+\s*(px|ms|fps|FPS|MHz|KB|MB|GB|英寸|寸|×|x|%|帧|秒|分钟|Hz|dpi)")
HEADING_STRICT = re.compile(r"(验收|约束|禁止|要求|规范|限制|红线|必须|硬性)")


def _strength(text):
    if MUST_NOT.search(text):
        return "MUST_NOT"
    if MUST.search(text):
        return "MUST"
    if SHOULD.search(text):
        return "SHOULD"
    if NUMERIC.search(text):
        return "MUST"
    return None


def _clean(t):
    t = re.sub(r"^\s*([-*+]|\d+[.)、])\s*(\[[ xX]\])?\s*", "", t)
    t = re.sub(r"[`*_]{1,3}", "", t)
    return re.sub(r"\s+", " ", t).strip(" |")


def extract(path, existing=None):
    """Return the items found in one document (heuristic: bullets, table rows, sentences with cues)."""
    items, section, in_code = [], "", False
    base = os.path.basename(path)
    for no, raw in enumerate(open(path, encoding="utf-8", errors="ignore").read().splitlines(), 1):
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line or line.startswith(("---", ">")):
            continue
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                # a separator row: the row just above was the table HEADER, not a requirement
                if items and items[-1]["source"].endswith(":%d" % (no - 1)):
                    items.pop()
                continue
            cands = [" ｜ ".join(c for c in cells if c)]
        elif re.match(r"^\s*([-*+]|\d+[.)、])\s+", raw):
            cands = [line]
        else:
            cands = [s for s in re.split(r"(?<=[。！？；;])", line) if s.strip()]
        for c in cands:
            text = _clean(c)
            if len(text) < 6:
                continue
            st = _strength(text)
            if st is None and HEADING_STRICT.search(section) and re.match(r"^\s*([-*+]|\d+[.)、])\s+", raw):
                st = "MUST"
            if st is None:
                continue
            items.append({"text": text, "strength": st, "section": section, "source": "%s:%d" % (base, no)})
    return items


def load(proj):
    p = os.path.join(proj, "requirements.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def save(proj, data):
    with open(os.path.join(proj, "requirements.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def cmd_extract(proj, files):
    data = load(proj) or {"version": 1, "sources": [], "items": []}
    have = {i["text"] for i in data["items"]}
    n_new = 0
    for f in files:
        if f not in data["sources"]:
            data["sources"].append(f)
        for it in extract(f):
            if it["text"] in have:
                continue
            have.add(it["text"])
            data["items"].append(dict(it, id="R%03d" % (len(data["items"]) + 1), status="todo", evidence="", reason="",
                                      verify=None, auto=None))
            n_new += 1
    save(proj, data)
    by = {}
    for i in data["items"]:
        by[i["strength"]] = by.get(i["strength"], 0) + 1
    print("requirements.json: +%d new, %d total  %s" % (n_new, len(data["items"]), by))
    print("This is a HEURISTIC pass: skim the list, `reqs set <proj> <id> info` for non-requirements, and add any clause it missed "
          "with `reqs add <proj> \"text\" --strength MUST`.")
    return 0


# ------------------------------------------------------------------- verifiers
def _walk(ch):
    for o in ch or []:
        yield o
        for c in _walk(o.get("children")):
            yield c


def verify(rule, spec, proj, tk):
    """Return (ok, message) for one auto-verify rule."""
    t = rule.get("type")
    screens = {s["name"]: s for s in spec["screens"]}
    allobjs = [(s["name"], o) for s in spec["screens"] for o in _walk(s["children"])]
    if t == "canvas":
        ok = (int(spec["width"]), int(spec["height"]), spec["shape"].upper()) == (rule["width"], rule["height"], rule.get("shape", spec["shape"]).upper())
        return ok, "canvas is %sx%s %s" % (spec["width"], spec["height"], spec["shape"])
    if t == "screen_exists":
        return rule["screen"] in screens, "screen %r" % rule["screen"]
    if t == "screens_min":
        return len(screens) >= rule["n"], "%d screens (need >= %d)" % (len(screens), rule["n"])
    if t == "object_exists":
        s = screens.get(rule["screen"])
        ok = bool(s) and any(o.get("name") == rule["object"] for o in _walk(s["children"]))
        return ok, "%s/%s" % (rule["screen"], rule["object"])
    if t == "object_hidden":
        s = screens.get(rule["screen"])
        o = next((o for o in _walk(s["children"]) if o.get("name") == rule["object"]), None) if s else None
        return bool(o) and bool(o.get("hidden")) == rule.get("hidden", True), "%s/%s hidden=%s" % (rule["screen"], rule["object"], o and o.get("hidden"))
    if t == "text_present":
        want, scr = rule["text"], rule.get("screen")
        ok = any(o.get("type") == "LABEL" and want in str(o.get("text", "")) and (not scr or s == scr) for s, o in allobjs)
        return ok, "text %r%s" % (want, " on " + scr if scr else "")
    if t == "event_wired":
        scr = screens.get(rule["screen"])
        if not scr:
            return False, "screen %r missing" % rule["screen"]
        evs = list(spec.get("screen_events", {}).get(rule["screen"], []) or [])
        for o in _walk(scr["children"]):
            if not rule.get("object") or o.get("name") == rule["object"]:
                evs += o.get("events") or []
        ok = any(e.get("on") == rule["on"] and any(a.get("type") == "CHANGE_SCREEN" and a.get("target") == rule.get("target", a.get("target"))
                                                       for a in e.get("actions", [])) for e in evs)
        return ok, "%s %s -> %s" % (rule["screen"], rule["on"], rule.get("target"))
    if t == "event_absent":
        txt = json.dumps(spec, ensure_ascii=False)
        return ('"on": "%s"' % rule["on"]) not in txt.replace('":"', '": "'), "no %s anywhere" % rule["on"]
    if t == "event_exists":
        scr = screens.get(rule["screen"])
        o = next((o for o in _walk(scr["children"]) if o.get("name") == rule["object"]), None) if scr else None
        return bool(o) and any(e.get("on") == rule["on"] for e in (o.get("events") or [])), "%s/%s has %s" % (rule["screen"], rule["object"], rule["on"])
    if t == "clickables_have":
        miss = [(s, o["name"]) for s, o in allobjs if any(e.get("on") == "CLICKED" for e in (o.get("events") or []))
                and not any(e.get("on") == rule["on"] for e in (o.get("events") or []))]
        return not miss, "%d clickable object(s) lack %s%s" % (len(miss), rule["on"], (": %s/%s ..." % miss[0]) if miss else "")
    if t == "asset_exists":
        d = os.path.join(proj, "assets", "images")
        names = os.listdir(d) if os.path.isdir(d) else []
        return any(n.startswith(rule["name"]) for n in names), "asset %s*" % rule["name"]
    if t == "asset_absent":
        d = os.path.join(proj, "assets", "images")
        names = os.listdir(d) if os.path.isdir(d) else []
        return not any(rule["name"] in n for n in names), "no asset containing %r" % rule["name"]
    if t == "font_min":
        mn = min(int(f["size"]) for f in spec["fonts"])
        return mn >= rule["px"], "smallest font is %d px (need >= %d)" % (mn, rule["px"])
    if t == "reachable":
        from . import lint
        f = [x for x in lint.run(proj, spec, tk) if x.code == "W-NAV-UNREACH" and x.where == rule["screen"]]
        return not f, "screen %r reachable by touch" % rule["screen"]
    if t == "no_errors":
        from . import lint
        e = [x for x in lint.run(proj, spec, tk) if x.level == "ERROR"]
        return not e, "lint has %d error(s)" % len(e)
    if t == "manual":
        return None, "needs a human/vision check: %s" % rule.get("how", "")
    return False, "unknown verify type %r" % t


def cmd_check(proj, spec, tk, quiet=False):
    data = load(proj)
    if not data:
        print("no requirements.json. If the user gave a requirements document: `slx.py reqs extract <file> --proj <proj>`.")
        return 2
    bad, todo_must, rows = 0, [], []
    for it in data["items"]:
        it["auto"] = None
        if it.get("verify"):
            ok, msg = verify(it["verify"], spec, proj, tk)
            it["auto"] = "pass" if ok is True else ("fail" if ok is False else "manual")
            it["auto_msg"] = msg
            if ok is False:
                bad += 1
                print("FAIL  %s auto-verify: %s   [%s]" % (it["id"], msg, it["text"][:60]))
        st = it["status"]
        if st not in STATUSES:
            print("ERROR %s: unknown status %r" % (it["id"], st))
            bad += 1
        elif st == "todo" and it["strength"] in ("MUST", "MUST_NOT"):
            todo_must.append(it)
        elif st == "done" and not (it.get("evidence") or it.get("verify")):
            print("ERROR %s: 'done' needs evidence (or a verify rule)" % it["id"])
            bad += 1
        elif st in ("deviation", "out_of_scope", "blocked") and not it.get("reason"):
            print("ERROR %s: '%s' needs a reason" % (it["id"], st))
            bad += 1
    save(proj, data)
    cnt = {}
    for it in data["items"]:
        cnt[it["status"]] = cnt.get(it["status"], 0) + 1
    must = [i for i in data["items"] if i["strength"] in ("MUST", "MUST_NOT")]
    print("requirements: %d total | %s" % (len(data["items"]), ", ".join("%s=%d" % kv for kv in sorted(cnt.items()))))
    print("hard (MUST/MUST_NOT): %d | undisposed hard: %d | auto-verify fail: %d" % (len(must), len(todo_must), bad))
    for it in todo_must[:12]:
        print("  TODO %s [%s] %s   (%s)" % (it["id"], it["strength"], it["text"][:90], it["source"]))
    if len(todo_must) > 12:
        print("  ... +%d more (`slx.py reqs todo <proj>` lists them in batches)" % (len(todo_must) - 12))
    return 1 if (todo_must or bad) else 0


def cmd_todo(proj, n=15):
    data = load(proj)
    todo = [i for i in data["items"] if i["status"] == "todo"]
    todo.sort(key=lambda i: {"MUST_NOT": 0, "MUST": 1, "SHOULD": 2, "INFO": 3}.get(i["strength"], 4))
    for it in todo[:n]:
        print("%s [%s] %s\n    section: %s | %s" % (it["id"], it["strength"], it["text"], it["section"], it["source"]))
    print("\n%d todo in total. Decide each: `slx.py reqs set <proj> <id>... done --evidence \"screen/object or file\"` | deviation|out_of_scope|blocked --reason \"...\" | info" % len(todo))
    return 0


def cmd_set(proj, ids, status, evidence="", reason="", verify_json=None):
    data = load(proj)
    wanted = set()
    for i in ids:
        if "-" in i and i.count("R") == 2:                       # R010-R020
            a, b = i.split("-")
            wanted.update("R%03d" % k for k in range(int(a[1:]), int(b[1:]) + 1))
        else:
            wanted.add(i)
    n = 0
    for it in data["items"]:
        if it["id"] in wanted:
            it["status"] = status
            if evidence:
                it["evidence"] = evidence
            if reason:
                it["reason"] = reason
            if verify_json:
                it["verify"] = json.loads(verify_json)
            n += 1
    save(proj, data)
    print("updated %d item(s) -> %s" % (n, status))
    return 0 if n else 1


def cmd_add(proj, text, strength="MUST", section="user", source="added"):
    data = load(proj) or {"version": 1, "sources": [], "items": []}
    nid = "R%03d" % (len(data["items"]) + 1)
    data["items"].append({"id": nid, "text": text, "strength": strength, "section": section, "source": source,
                          "status": "todo", "evidence": "", "reason": "", "verify": None, "auto": None})
    save(proj, data)
    print("added", nid)
    return 0


def cmd_report(proj, name):
    data = load(proj)
    L = ["# 需求追溯矩阵（%s）\n" % name,
         "> 由 `slx.py reqs report` 从 `requirements.json` 生成，请勿手改。来源：%s\n" % "、".join(data["sources"] or ["—"])]
    cnt = {}
    for it in data["items"]:
        cnt[it["status"]] = cnt.get(it["status"], 0) + 1
    L.append("**汇总**：%s\n" % "，".join("%s %d" % kv for kv in sorted(cnt.items())))
    icon = {"done": "✅", "deviation": "⚠️", "out_of_scope": "➡️", "blocked": "⛔", "todo": "❓", "info": "·"}
    for title, sts in (("偏差 / 越界 / 无法实现（务必看）", ("deviation", "blocked", "out_of_scope")), ("已实现", ("done",)), ("未处置", ("todo",))):
        rows = [i for i in data["items"] if i["status"] in sts]
        if not rows:
            continue
        L.append("\n## %s（%d）\n" % (title, len(rows)))
        L.append("| ID | 强度 | 需求 | 状态 | 证据 / 原因 | 自动验证 |\n|---|---|---|---|---|---|")
        for i in rows:
            ev = i.get("reason") or i.get("evidence") or ""
            au = {"pass": "通过", "fail": "**失败**", "manual": "需人工", None: ""}.get(i.get("auto"), "")
            L.append("| %s | %s | %s | %s %s | %s | %s |" % (i["id"], i["strength"], i["text"].replace("|", "｜"),
                                                              icon.get(i["status"], ""), i["status"], str(ev).replace("|", "｜").replace("\n", " "), au))
    out = os.path.join(proj, "需求追溯矩阵.md")
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("wrote", out)
    return 0
