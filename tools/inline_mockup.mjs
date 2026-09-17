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

// 2. <img src="assets/images[/images_apple]/..."> → base64 PNG
html = html.replace(/src="(assets\/(?:images|images_apple)\/[^"]+)"/g, (m, rel) => {
  const b64 = readRel(rel).toString('base64');
  count++;
  return `src="data:image/png;base64,${b64}"`;
});

// 3. JS 字符串中的 'assets/images[/images_apple]/....png' 字面量（如状态切换映射表）→ base64 PNG
html = html.replace(/'(assets\/(?:images|images_apple)\/[^'\"]+\.png)'/g, (m, rel) => {
  const b64 = readRel(rel).toString('base64');
  count++;
  return `"data:image/png;base64,${b64}"`;
});

writeFileSync(outPath, html);
console.log(`inlined ${count} resources into ${outPath}`);
