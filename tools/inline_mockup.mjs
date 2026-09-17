// Inline a mockup HTML's relative font/image refs as base64 data URIs so the
// Freebuff preview tab (which serves only a single HTML file) can show them.
// Usage: node tools/inline_mockup.mjs [src.html] [out.html]
// Relative paths resolve against the CURRENT WORKING DIRECTORY (portable);
// absolute paths are used as-is. Defaults: mockup.html -> mockup_standalone.html
import { readFileSync, writeFileSync } from 'fs';
import { join, resolve, isAbsolute, dirname } from 'path';

const TOOLS = dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
function argPath(a, dflt) {
  const p = a || dflt;
  return isAbsolute(p) ? p : resolve(process.cwd(), p);
}
const srcPath = argPath(process.argv[2], 'mockup.html');
const outPath = argPath(process.argv[3], 'mockup_standalone.html');
const BASE = dirname(srcPath);   // relative asset refs resolve against the src file
let html = readFileSync(srcPath, 'utf8');

let count = 0;

function readRel(rel) {
  const p = isAbsolute(rel) ? rel : join(BASE, rel);
  return readFileSync(p);
}

// 1. @font-face url(...) → base64 TTF data URIs.
html = html.replace(/url\('([^']+\.ttf)'\)/g, (m, rel) => {
  const b64 = readRel(rel).toString('base64');
  count++;
  return `url(data:font/ttf;base64,${b64})`;
});

// 2. <img src="assets/...png"> → base64 PNG.
//
// TWO path conventions are in play and BOTH must be inlined:
//   * SOURCE pack (what the mockup points at):  assets/images/img_x.png
//                                               assets/images_apple/img_x.png
//   * PROJECT  (what build_from_spec.py emits): assets/img_x.png   <- FLAT
// The flat form has no subdirectory because the spec's IMAGE `asset` field is
// "path relative to the project dir" and `assets_subdir` only selects where the
// *source* pack is read from (engine.configure: SRC_IMAGES = ASSETS_ROOT/subdir).
// An earlier version of this regex only matched the subdir form, so any mockup
// written against the project convention inlined zero images — silently, since
// the count is only printed, never asserted.  Match any depth under assets/.
const IMG_EXT = '(?:png|jpg|jpeg|gif|webp)';
const IMG_SRC = new RegExp(`src="((?:\\.\\.?/)?assets/[^"]+\\.${IMG_EXT})"`, 'g');
const IMG_JS = new RegExp(`'((?:\\.\\.?/)?assets/[^'"]+\\.${IMG_EXT})'`, 'g');

html = html.replace(IMG_SRC, (m, rel) => {
  const b64 = readRel(rel).toString('base64');
  count++;
  return `src="data:image/png;base64,${b64}"`;
});

// 3. JS 字符串中的 'assets/....png' 字面量（如状态切换映射表）→ base64 PNG
html = html.replace(IMG_JS, (m, rel) => {
  const b64 = readRel(rel).toString('base64');
  count++;
  return `"data:image/png;base64,${b64}"`;
});

// 4. Fail LOUDLY on leftovers instead of silently shipping a broken preview.
//
// The old script printed "inlined 0 resources" and exited 0 when its regex did
// not recognise the path shape — the operator had no way to tell "nothing to
// do" from "the pattern is wrong".  A standalone file that still points at
// relative paths is unusable in a single-file preview tab, so treat any
// remaining local ref as an error.
const leftovers = [...html.matchAll(
  /(?:src|href)="((?:\.\.?\/)?assets\/[^"]+)"/g)].map((m) => m[1]);
if (leftovers.length) {
  console.error(`ERROR: ${leftovers.length} local ref(s) were NOT inlined — ` +
                `the standalone file will show broken images:`);
  for (const l of [...new Set(leftovers)].slice(0, 10)) console.error('  ' + l);
  process.exitCode = 1;
}

writeFileSync(outPath, html);
console.log(`inlined ${count} resources into ${outPath}` +
            (leftovers.length ? ` (${leftovers.length} LEFT OVER)` : ''));
