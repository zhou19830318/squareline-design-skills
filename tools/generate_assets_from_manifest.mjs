#!/usr/bin/env node
// generate_assets_from_manifest.mjs — declarative asset generation (Stage A).
//
// Why this exists
// ---------------
// generate_assets.mjs / generate_assets_apple.mjs are *curated* generators:
// their icon lists are hard-coded for one specific project, and every new panel
// meant writing another 200-line script.  That is the same engine/content weld
// that build_from_spec.py removed for screens — applied to assets.
//
// A manifest is data; this compiler is engine-only code.  Three icon sources
// are supported, deliberately, because icon needs arrive in three ways:
//
//   1. lucide   — the vendored lucide-static set (offline, ISC licence).
//                 Icon name + size + colour; the curated generators' path.
//   2. svg      — a real .svg file on disk: something an agent downloaded
//                 from an icon site (Iconify / SVG Repo / Tabler / ...) or
//                 drew by hand.  Rendered as-is (currentColor is recoloured).
//   3. builtin  — small parametric SVGs written inline by the agent into the
//                 manifest itself (weather glyphs, waveforms, custom logos).
//
// PNG is the deliverable; every source lands in ONE flat directory with ONE
// naming scheme, so the spec's `assets/img_x.png` references never depend on
// where an icon came from.
//
// Manifest contract (see templates/设计规格文档模板.md §7)
// ---------------------------------------------------------
//   {
//     "out": "assets/images",              // repo-root relative (or --out)
//     "defaults": { "size": 48, "color": "#FFFFFF", "stroke_width": 2 },
//     "icons": [
//       { "name": "img_home_icon_clock",
//         "source": "lucide", "icon": "clock", "size": 44 },
//       { "name": "img_home_icon_logo",
//         "source": "svg", "file": "downloads/logo.svg", "size": 64 },
//       { "name": "img_weather_icon_sunny_72",
//         "source": "builtin", "svg": "<svg ...>...</svg>", "size": 112 },
//       { "name": "img_weather_icon_rain_72",
//         "source": "lucide", "icon": "cloud-rain", "size": 112, "color": "#7DD3FC" }
//     ]
//   }
//
// Rules
//   * `name` is the output basename WITHOUT .png.  It should already follow
//     the img_<screen>_<meaning>[_<state>][_size].png convention — the size
//     suffix must be IN the name, because LVGL references are flat and the
//     builder never renames anything.
//   * `file` for the svg source is repo-root relative.
//   * Per-icon keys override defaults.  Unknown source => loud error, not a
//     silently skipped icon.
//   * One icon = one PNG.  Need two sizes => two entries (the naming
//     convention's `_72` / `_28` suffixes exist exactly for this).
//
// Usage
//   node tools/generate_assets_from_manifest.mjs examples/N/assets.manifest.json
//   node tools/generate_assets_from_manifest.mjs m.json --out assets/images_x

import { renderRaw, resvgBackend } from './lib/resvg.mjs';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const SELF = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(SELF, '..');   // this file lives in tools/, repo root is one up
const LUCIDE = join(SELF, 'node_modules', 'lucide-static', 'icons');

const argv = process.argv.slice(2);
const outFlagIdx = argv.indexOf('--out');
const OUT_FLAG = outFlagIdx !== -1 && argv[outFlagIdx + 1] ? resolve(argv[outFlagIdx + 1]) : null;
const manifestArg = argv.find((a, i) => !a.startsWith('--') && (outFlagIdx === -1 || i !== outFlagIdx + 1));
if (!manifestArg) {
  console.error('usage: node tools/generate_assets_from_manifest.mjs <manifest.json> [--out DIR]');
  process.exit(1);
}
const MANIFEST_PATH = resolve(manifestArg);
if (!existsSync(MANIFEST_PATH)) { console.error('no such manifest: ' + manifestArg); process.exit(1); }

let M;
try { M = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8')); }
catch (e) { console.error('manifest is not valid JSON: ' + e.message); process.exit(1); }

const OUT = OUT_FLAG || (M.out ? resolve(ROOT, M.out) : null);
if (!OUT) { console.error('manifest needs an "out" directory (or pass --out DIR)'); process.exit(1); }
mkdirSync(OUT, { recursive: true });

const DEF = M.defaults || {};
const DEF_SIZE = DEF.size || 48;
const DEF_COLOR = DEF.color || '#FFFFFF';
const DEF_STROKE = DEF.stroke_width || null;

let fails = 0, made = 0;

function pngSize(buf) { return buf.readUInt32BE(16) + 'x' + buf.readUInt32BE(20); }

function emit(name, svg, w, h) {
  const png = renderRaw(svg, { fitTo: { mode: 'width', value: w } });
  const file = join(OUT, `${name}.png`);
  writeFileSync(file, png);
  const got = pngSize(png);
  if (got !== `${w}x${h}`) { console.error(`WARN ${name}: header ${got} != ${w}x${h}`); fails++; }
  made++;
  console.log(`ok  ${name}.png  ${got}`);
}

function colourize(svg, color) {
  // One colour knob for every source: lucide uses stroke, inline/downloaded
  // SVGs may use either currentColor attr form, so normalise all of them.
  return svg
    .replace(/stroke="currentColor"/g, `stroke="${color}"`)
    .replace(/fill="currentColor"/g, `fill="${color}"`);
}

function lucideSvg(iconName, color, strokeW, w, h) {
  const p = join(LUCIDE, `${iconName}.svg`);
  if (!existsSync(p)) {
    throw new Error(`lucide has no icon named "${iconName}" (looked in ${p}). ` +
      `Browse names at https://lucide.dev/icons`);
  }
  let svg = readFileSync(p, 'utf8');
  svg = svg.replace(/<!--[\s\S]*?-->\s*/g, '');
  svg = svg.replace(/stroke="currentColor"/g, `stroke="${color}"`);
  if (strokeW) svg = svg.replace(/stroke-width="2"/g, `stroke-width="${strokeW}"`);
  // Lucide ships `fill="none"` on the ROOT element and its glyphs rely on
  // inheriting that — resvg (and every other SVG renderer) falls back to the
  // SVG default `fill:black` when the attribute is missing, which used to turn
  // every stroke-only icon into a solid silhouette.  Copy the root's paint
  // attributes into the rebuilt element instead of dropping them.
  const rootAttrs = svg.match(/<svg\b([^>]*)>/i)?.[1] ?? '';
  const paint = [...rootAttrs.matchAll(/\b(fill|fill-rule|fill-opacity|stroke|stroke-width|stroke-linecap|stroke-linejoin|stroke-opacity|stroke-dasharray)="[^"]*"/gi)]
    .map((m) => m[0]).join(' ');
  if (paint && !/\bfill=/.test(paint)) paint += ' fill="none"';
  // Rebuild the root element with an explicit viewport: lucide ships 24x24
  // with viewBox preserved, so the 24x24 grid scales cleanly to any size.
  const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/i, '').replace(/<\/svg>\s*$/i, '');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 24 24"${paint ? ' ' + paint : ''}>${inner}</svg>`;
}

for (const it of (M.icons || [])) {
  if (!it.name || !it.source) {
    console.error(`FAIL: icon entry needs "name" and "source" — got ${JSON.stringify(it)}`);
    fails++;
    continue;
  }
  const w = it.width || it.size || DEF_SIZE;
  const h = it.height || it.size || DEF_SIZE;
  const color = it.color || DEF_COLOR;
  try {
    if (it.source === 'lucide') {
      if (!it.icon) throw new Error('lucide entry needs "icon" (the lucide name)');
      emit(it.name, lucideSvg(it.icon, color, it.stroke_width ?? DEF_STROKE, w, h), w, h);
    } else if (it.source === 'svg') {
      if (!it.file) throw new Error('svg entry needs "file" (repo-root relative .svg path)');
      const f = resolve(ROOT, it.file);
      if (!existsSync(f)) throw new Error('svg file not found: ' + it.file);
      let svg = readFileSync(f, 'utf8').replace(/<!--[\s\S]*?-->\s*/g, '');
      svg = colourize(svg, color);
      // Force an explicit viewport (keep the source viewBox so up/down-scaling
      // stays proportional); many site downloads are "responsive" with no
      // absolute width/height at all.
      const root = svg.match(/<svg[^>]*>/i);
      let vb = null;
      if (root) {
        const v = root[0].match(/viewBox="([\d.\-\s]+)"/i);
        if (v) vb = v[1].trim();
      }
      const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/i, '').replace(/<\/svg>\s*$/i, '');
      emit(it.name,
        `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"`
        + `${vb ? ` viewBox="${vb}"` : ''}>${inner}</svg>`,
        w, h);
    } else if (it.source === 'builtin') {
      if (!it.svg) throw new Error('builtin entry needs "svg" (inline SVG markup)');
      let bsvg = colourize(String(it.svg), color);
      // Inline SVGs written by hand often omit xmlns; resvg refuses them
      // ("document does not have a root node"), so add the declaration when
      // the root element lacks it.  Hand-authored viewBox is preserved.
      if (!/<svg[^>]*xmlns=/.test(bsvg)) {
        bsvg = bsvg.replace(/<svg/i, '<svg xmlns="http://www.w3.org/2000/svg"');
      }
      emit(it.name, bsvg, w, h);
    } else {
      throw new Error(`unknown source "${it.source}" (lucide | svg | builtin)`);
    }
  } catch (e) {
    console.error(`FAIL ${it.name}: ${e.message}`);
    fails++;
  }
}

console.log(`backend: ${resvgBackend ? resvgBackend() : 'resvg'}  made: ${made}  failures: ${fails}`);
process.exit(fails ? 1 : 0);
