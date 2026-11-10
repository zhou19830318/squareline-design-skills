#!/usr/bin/env node
// svg_to_png.mjs — generic SVG -> PNG converter (project-agnostic Stage A tool).
//
// Why this exists
// ---------------
// generate_assets*.mjs are *curated* generators: their icon list is written for
// one specific project.  A general-purpose skill must also accept icons the
// user (or the agent) downloaded from an icon site — Iconify, SVG Repo, Tabler,
// Bootstrap, Feather, Material Symbols, ... — and turn them into PNGs without
// editing any script.  This tool is that door.  It renders through the same
// lib/resvg.mjs shim the curated generators use (native binding first, WASM
// fallback), so it inherits the offline / cross-platform behaviour for free.
//
// Usage
// -----
//   node tools/svg_to_png.mjs icon.svg                       # next to input
//   node tools/svg_to_png.mjs icon.svg --out assets/images   # explicit dir
//   node tools/svg_to_png.mjs icon.svg --name img_logo --size 64
//   node tools/svg_to_png.mjs a.svg b.svg c.svg --size 48 --color "#FFFFFF"
//   node tools/svg_to_png.mjs icons_dir --recursive --out assets/images
//   node tools/svg_to_png.mjs icon.svg --width 64 --height 40   # non-square
//
// Options
//   --size N         square output, N px on a side (default: the SVG's own
//                    width/height, falling back to 24)
//   --width/--height explicit non-square size (overrides --size)
//   --name STR       output basename (default: input basename, extension
//                    swapped to .png); a version suffix is added only when
//                    several sizes of one file are rendered into the same dir
//   --color CSS      replace stroke="currentColor" (and fill="currentColor")
//                    with this colour; default white #FFFFFF
//   --stroke N       rewrite stroke-width to N (same units as the SVG uses)
//   --bg CSS         paint a background rect first (default: transparent)
//   --out DIR        output directory (default: the input file's directory)
//   --recursive      when the input is a directory, descend into subdirs
//
// Conventions that keep the output buildable
// ------------------------------------------
//   * Output names default to the input basename.  Give --name when the site's
//     file name is not the one your spec/manifest references (the manifest
//     convention is `img_<screen-or-domain>_<meaning>[_<state>].png`).
//   * LVGL wants straight sRGB PNGs with alpha; resvg already emits those.
//   * The PNG header is re-read after writing so "did it really render at the
//     requested size" is a fact, not a hope (the curated generators audit the
//     same way — stretched assets shipped twice before anyone noticed).

import { renderRaw, resvgBackend } from './lib/resvg.mjs';
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, readdirSync } from 'fs';
import { join, dirname, resolve, basename, extname } from 'path';
import { fileURLToPath } from 'url';

const SELF = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------- argv -----
const argv = process.argv.slice(2);
function opt(name) {
  const i = argv.indexOf('--' + name);
  return i !== -1 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : undefined;
}
function hasFlag(name) { return argv.includes('--' + name); }

const inputs = argv.filter(a => !a.startsWith('--')
  && argv[argv.indexOf(a) - 1] !== '--out'
  && !['--size', '--width', '--height', '--name', '--color', '--stroke', '--bg'].includes(argv[argv.indexOf(a) - 1]));
const OUT = opt('out') ? resolve(opt('out')) : null;
const SIZE = opt('size') ? parseInt(opt('size'), 10) : null;
const WIDTH = opt('width') ? parseInt(opt('width'), 10) : null;
const HEIGHT = opt('height') ? parseInt(opt('height'), 10) : null;
const NAME = opt('name');
const COLOR = opt('color') || '#FFFFFF';
const STROKE = opt('stroke') ? parseFloat(opt('stroke')) : null;
const BG = opt('bg');
const RECURSIVE = hasFlag('recursive');

if (!inputs.length || hasFlag('help') || hasFlag('h')) {
  console.log(`usage: node tools/svg_to_png.mjs <file.svg|dir> [more.svg ...] [--out DIR]
       [--size N | --width W --height H] [--name STR] [--color CSS] [--stroke N]
       [--bg CSS] [--recursive]

Renders SVG files (any icon-site download) to PNG via resvg, same backend
shim as the curated generators: native binding first, WASM fallback.`);
  process.exit(inputs.length ? 0 : 1);
}

// ---------------------------------------------------------------- svg ------ 
function pngSize(buf) {
  // PNG IHDR: width @ byte 16, height @ byte 20 (u32 BE) — same audit the
  // curated generators use, so a silently-wrong render cannot pass unnoticed.
  return buf.readUInt32BE(16) + 'x' + buf.readUInt32BE(20);
}

function recolour(svg) {
  let out = svg.replace(/stroke="currentColor"/g, `stroke="${COLOR}"`);
  out = out.replace(/fill="currentColor"/g, `fill="${COLOR}"`);
  if (STROKE !== null) out = out.replace(/stroke-width="[\d.]+"/g, `stroke-width="${STROKE}"`);
  return out;
}

function backgroundRect(w, h) {
  return BG ? `<rect x="0" y="0" width="${w}" height="${h}" fill="${BG}"/>` : '';
}

// Rebuild the SVG with an explicit viewport: preserve the source viewBox (so a
// 24x24 icon scales cleanly to 64x64), inject xmlns when a site download
// omitted it, and never inherit width="100%"-style responsive attributes.
function normalizeSvg(svg, w, h) {
  const root = svg.match(/<svg[^>]*>/i);
  let vb = null;
  if (root) {
    const v = root[0].match(/viewBox="([\d.\-\s]+)"/i);
    if (v) vb = v[1].trim();
  }
  if (!vb) {
    const wm = svg.match(/\bwidth="([\d.]+)"/), hm = svg.match(/\bheight="([\d.]+)"/);
    if (wm && hm) vb = `0 0 ${wm[1]} ${hm[1]}`;
  }
  const inner = svg.replace(/^[\s\S]*?<svg[^>]*>/i, '').replace(/<\/svg>\s*$/i, '');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"`
    + `${vb ? ` viewBox="${vb}"` : ''}>${backgroundRect(w, h)}${inner}</svg>`;
}

function renderOne(file, outName, w, h) {
  let svg = readFileSync(file, 'utf8');
  // Strip XML comments and licence banners (icon-site downloads carry them).
  svg = svg.replace(/<!--[\s\S]*?-->\s*/g, '');
  svg = recolour(svg);

  const png = renderRaw(normalizeSvg(svg, w, h));
  mkdirSync(dirname(outName), { recursive: true });
  writeFileSync(outName, png);
  const got = pngSize(png);
  const ok = got === `${w}x${h}`;
  console.log(`${ok ? 'ok  ' : 'WARN'} ${outName}  (${got}${ok ? '' : ` != ${w}x${h}`})`);
  return ok;
}

// ------------------------------------------------------------ discovery ---- 
function collectSvgFiles(target) {
  const st = statSync(target);
  if (st.isFile()) return [target];
  const out = [];
  for (const f of readdirSync(target)) {
    const p = join(target, f);
    const s = statSync(p);
    if (s.isDirectory() && RECURSIVE) out.push(...collectSvgFiles(p));
    else if (s.isFile() && extname(f).toLowerCase() === '.svg') out.push(p);
  }
  return out;
}

// ----------------------------------------------------------------- main ----
const all = [];
for (const t of inputs) {
  const p = resolve(t);
  if (!existsSync(p)) { console.error(`ERROR: no such file: ${t}`); process.exit(1); }
  all.push(...collectSvgFiles(p));
}
if (!all.length) { console.error('ERROR: no .svg file(s) found in the given input(s)'); process.exit(1); }

// Size per file: explicit flag wins; else the SVG's own width/height attr;
// else 24 (the de-facto icon-canvas default every icon site follows).
function sizeFor(file) {
  if (WIDTH && HEIGHT) return [WIDTH, HEIGHT];
  if (SIZE) return [SIZE, SIZE];
  const head = readFileSync(file, 'utf8').slice(0, 2048);
  const w = head.match(/\bwidth="(\d+(?:\.\d+)?)"/);
  const h = head.match(/\bheight="(\d+(?:\.\d+)?)"/);
  const v = head.match(/\bviewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.\-]+)\s+([\d.\-]+)"/);
  if (w && h) return [Math.round(parseFloat(w[1])), Math.round(parseFloat(h[1]))];
  if (v) return [Math.round(parseFloat(v[1])), Math.round(parseFloat(v[2]))];
  return [24, 24];
}

let fails = 0;
const usedNames = new Map(); // basename -> count, to disambiguate multi-size runs
for (const file of all) {
  const [w, h] = sizeFor(file);
  let base = NAME || basename(file, extname(file));
  if (!NAME && all.length > 1) {
    const seen = usedNames.get(base) || 0;
    usedNames.set(base, seen + 1);
    if (seen > 0) base = `${base}_${w}x${h}`;   // two sizes of one basename
  }
  const dir = OUT || dirname(file);
  const out = join(dir, `${base}.png`);
  try {
    if (!renderOne(file, out, w, h)) fails++;
  } catch (e) {
    console.error(`FAIL ${file}: ${e.message}`);
    fails++;
  }
}
console.log(`backend: ${resvgBackend ? resvgBackend() : 'resvg'}  files: ${all.length}  failures: ${fails}`);
process.exit(fails ? 1 : 0);
