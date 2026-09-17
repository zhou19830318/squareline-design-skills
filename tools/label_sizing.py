#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate tools/LABEL_SIZING.md — the LABEL height vs font line-height table.

Why this exists
---------------
`run_build()` rejects a LABEL whose height is smaller than its font's
`line_height` (CJK glyphs get clipped top and bottom).  That check is correct
but *late*: it only runs after fonts are built, and `line_height` is only known
by regex-parsing the generated `.c`.  So while an author is choosing
`size`/`height` in the spec there is nothing to consult, and the failure mode is
trial-and-error — an engineer building one watch project hit it three separate
times (Display96 110<116, Big64 72<78, Score40 48<49).

This script reads every font `.c` that a build has already produced and emits
the exact `size -> line_height` mapping, so the numbers in the doc are *derived*
from the engine rather than hand-typed.  Preflight runs it with `--check` and
fails if the committed doc no longer matches, which is what stops it rotting.

Usage:
    python tools/label_sizing.py            # write/refresh tools/LABEL_SIZING.md
    python tools/label_sizing.py --check    # exit 1 if the doc is out of date
    python tools/label_sizing.py --print    # just dump the table
"""

import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "tools", "LABEL_SIZING.md")

# Note the deliberate asymmetry: `line_height` is *always* strictly greater than
# `size` for these faces, because the metrics include the ascender+descender box
# rather than the em size.  The ratio is what makes the rule non-obvious.
LINE_RE = re.compile(r"\.line_height = (\d+)")
BASE_RE = re.compile(r"\.base_line = (-?\d+)")


def scan_font_c():
    """{font_codename: {size: [line_height, base_line, src_path, n_variants]}}

    `line_height` is **not** a constant per (font, size): it is
    max(ascent)+max(descent) over the glyphs a project actually included, so two
    projects with different charsets get different values for the same face at
    the same size (measured: Body16@16 is 21 in AIWatch but 20 in SpecWidget).
    We therefore keep the *maximum* seen for each (font, size) - the
    conservative value - and count the variants so the doc can flag the
    instability instead of hiding it.
    """
    table = {}
    pats = [os.path.join(ROOT, "squareline", "*", "assets", "fonts", "*.c"),
            os.path.join(ROOT, "examples", "*", "squareline", "*", "assets",
                         "fonts", "*.c")]
    seen = set()
    for pat in pats:
        for c in sorted(glob.glob(pat)):
            rp = os.path.realpath(c)
            if rp in seen:
                continue
            seen.add(rp)
            txt = open(c, encoding="utf-8", errors="ignore").read()
            lh = LINE_RE.search(txt)
            if not lh:
                continue
            bl = BASE_RE.search(txt)
            # lv_font_conv stamps the loader name into the Opts comment (there is
            # NO `.lv_font_name` field in the generated C — the name only appears
            # in that comment and in the include guard), so parse it from there,
            # falling back to the file name ui_font_<Codename>.c.
            m_size = re.search(r"--size (\d+)", txt)
            if not m_size:
                continue
            m_name = re.search(r"--lv-font-name (\S+)", txt)
            name = (m_name.group(1) if m_name
                    else os.path.splitext(os.path.basename(c))[0])
            size = int(m_size.group(1))
            base = name[len("ui_font_"):] if name.startswith("ui_font_") else name
            rel = os.path.relpath(c, ROOT).replace("\\", "/")
            prev = table.setdefault(base, {}).get(size)
            if prev is None:
                table[base][size] = [int(lh.group(1)),
                                     int(bl.group(1)) if bl else 0, rel, 1]
            else:
                prev[3] += 1
                if int(lh.group(1)) > prev[0]:
                    prev[0] = int(lh.group(1))
                    prev[1] = int(bl.group(1)) if bl else 0
                    prev[2] = rel
    return table


def render(table):
    rows = []
    clashes = []
    for base in sorted(table):
        for size in sorted(table[base]):
            lh, bl, src, nvar = table[base][size]
            clash = nvar > 1
            if clash:
                clashes.append((base, size, nvar))
            rows.append((base, size, lh, bl, src, clash))
    return rows, clashes


def build_doc(rows):
    L = []
    L.append("# LABEL 高度 vs 字体行高（速查表）")
    L.append("")
    L.append("> 本文件由 `tools/label_sizing.py` 从**已构建工程的字体 `.c`** 自动生成，")
    L.append("> 请勿手改。`python tools/preflight.py` 会校验它与工程是否同步。")
    L.append("")
    L.append("## 为什么需要这张表")
    L.append("")
    L.append("`run_build()` 会拒绝 `height < line_height` 的 LABEL —— 这是对的，")
    L.append("但**报错太晚**：字体是构建期生成的，`line_height` 只能靠正则解析产物 `.c` 才拿得到，")
    L.append("所以在写 spec 坐标的那一刻没有任何东西可查，只能反复试错。")
    L.append("")
    L.append("关键点（反直觉）：**`line_height` 一定大于 `size`**。")
    L.append("因为行高包含 ascender + descender 的整体高度，而不是 em 字号本身。")
    L.append("按 `height >= size` 留尺寸必然被裁切。")
    L.append("")
    L.append("## ⚠️ 行高不是常量：同一个字体在不同工程里会不一样")
    L.append("")
    L.append("`line_height = max(该字体实际包含字形的 ascent) + max(descent)`，")
    L.append("所以**它取决于工程收进了哪些字形**，而不是只取决于字号。实测：")
    L.append("")
    L.append("| 字体 | size | 字形数 | line_height | 工程 |")
    L.append("|---|---|---|---|---|")
    L.append("| `Body16` | 16 | 820 | **21** | `examples/AIWatch` |")
    L.append("| `Body16` | 16 | 293 | **20** | `examples/SpecWidget` |")
    L.append("| `Title20` | 20 | 346 | **24** | `examples/AIWatchApple` |")
    L.append("| `Title20` | 20 | 293 | **23** | `examples/SpecWidget` |")
    L.append("")
    L.append("结论：**下表只能当起始估计，不能当权威值。**")
    L.append("权威值永远是你自己那次构建输出里的 `lineheight:` 一行。")
    L.append("把下表取**最大值**、或直接按经验公式留余量，才是安全做法。")
    L.append("")
    L.append("## 经验公式（推荐）")
    L.append("")
    L.append("```")
    L.append("height >= ceil(size * 1.35)     # 单行中文的安全下界（含跨工程余量）")
    L.append("```")
    L.append("")
    L.append("实测 `line_height / size` 落在 **1.19 ~ 1.31**（小字号比例更大，因为")
    L.append("hinting/取整对小字号影响更重）。取 **1.35** 可覆盖上表所有行并留出余量；")
    L.append("宁可稍高也不要压线，压线在不同工程/不同字形集下会翻车。")
    L.append("多行文案再乘以行数。")
    L.append("")
    L.append("## 实测对照表（按字体名+字号去重，取各工程最大值）")
    L.append("")
    L.append("| font | size | line_height | 安全 height (≥) | 比例 | base_line | 来源工程 |")
    L.append("|---|---|---|---|---|---|---|")
    for base, size, lh, bl, src, clash in rows:
        ratio = lh / float(size) if size else 0
        flag = " ⚠️" if clash else ""
        L.append("| `%s`%s | %d | %d | %d | %.2f | %d | `%s` |"
                 % (base, flag, size, lh, lh, ratio, bl, src))
    L.append("")
    L.append("⚠️ = 同一个字体+字号在不同工程里行高不一致（见上一节），此时取的是最大值。")
    L.append("")
    L.append("## 怎么用")
    L.append("")
    L.append("1. 先按经验公式 `ceil(size * 1.35)` 定 LABEL 高度，别凭字号猜。")
    L.append("2. 想精确核对，跑一次 `python tools/build_from_spec.py <spec.json>`，")
    L.append("   构建输出里的 `lineheight:` 一行列出**你这个工程**的真实行高：")
    L.append("   ```")
    L.append("   lineheight: {'Title20': 23, 'Body16': 20}")
    L.append("   ```")
    L.append("3. 多行文案（`text` 里含 `\\n`）把安全高度乘以行数。")
    L.append("4. 仍然 `height < line_height` 会被报成 `ERROR`（构建返回非 0），")
    L.append("   文案换行后超出控件高度会报成 `WARN`。")
    L.append("")
    L.append("## 构建输出的相关几行")
    L.append("")
    L.append("```")
    L.append("fonts     : [('Big48', 48, 13), ('Title20', 20, 293), ('Body16', 16, 293)]")
    L.append("charset   : ui-text 46, doc-headroom 291 (+246 usable)     # 字形来源与余量")
    L.append("lineheight: {'Big48': 60, 'Title20': 23, 'Body16': 20}     # 本工程真实行高")
    L.append("```")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if tools/LABEL_SIZING.md is stale")
    ap.add_argument("--print", dest="dump", action="store_true",
                    help="print the generated doc to stdout")
    args = ap.parse_args()

    table = scan_font_c()
    if not table:
        print("no built font .c files found under squareline/ or examples/ — "
              "build a project first")
        return 2
    rows, clashes = render(table)
    doc = build_doc(rows)

    if clashes:
        print("NOTE: same (font,size) has different line_height across projects "
              "(kept the max) — see the doc's warning section:")
        for base, size, nvar in clashes:
            print("   %s @ %d (%d variants)" % (base, size, nvar))

    if args.dump:
        sys.stdout.write(doc)
        return 0

    if args.check:
        if not os.path.exists(DOC):
            print("STALE: tools/LABEL_SIZING.md does not exist")
            return 1
        cur = open(DOC, encoding="utf-8").read()
        if cur != doc:
            print("STALE: tools/LABEL_SIZING.md differs from the built fonts "
                  "(%d rows)" % len(rows))
            print("   run: python tools/label_sizing.py")
            return 1
        print("OK: tools/LABEL_SIZING.md in sync (%d rows, %d fonts)"
              % (len(rows), len(table)))
        return 0

    with open(DOC, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    print("written: %s (%d rows, %d fonts)" % (os.path.relpath(DOC, ROOT),
                                               len(rows), len(table)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
