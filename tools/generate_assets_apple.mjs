// AIWatch Apple-style asset generator — 240x240 ROUND screen (2px ~= 1dp at
// this panel => 1dp ~= 1px; keep glyphs at native UI size).
// White Lucide strokes + custom SVGs (gemini star, grid dots, hands, battery).
// Output: assets/images_apple (round-pack). Run: node tools/generate_assets_apple.mjs
// SVG → PNG goes through tools/lib/resvg.mjs: native binding first, WASM
// fallback second, so this runs on Windows / Linux (glibc + musl) / macOS
// without a per-platform `npm install` (see tools/vendor_prepare.py).
import { renderSvg, renderRaw, resvgBackend } from './lib/resvg.mjs';
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const ICONS = join(ROOT, 'node_modules', 'lucide-static', 'icons');

// Where the PNGs land.  Default keeps the historical layout (repo-root
// assets/images_apple); pass `--out <dir>` to target an example folder, e.g.
//   node tools/generate_assets_apple.mjs --out examples/AIWatchApple/assets/images_apple
const argOut = process.argv.indexOf('--out');
const OUT = argOut !== -1 && process.argv[argOut + 1]
  ? resolve(process.argv[argOut + 1])
  : join(ROOT, '..', 'assets', 'images_apple');
mkdirSync(OUT, { recursive: true });

const W = '#FFFFFF';

function iconSvg(name, { color = W, strokeWidth = 2 } = {}) {
  const p = join(ICONS, `${name}.svg`);
  if (!existsSync(p)) throw new Error(`missing icon: ${name}`);
  let svg = readFileSync(p, 'utf8');
  svg = svg.replace(/<!--[\s\S]*?-->\s*/g, '');
  svg = svg.replace(/stroke="currentColor"/g, `stroke="${color}"`);
  if (strokeWidth !== 2) svg = svg.replace(/stroke-width="2"/g, `stroke-width="${strokeWidth}"`);
  return svg;
}

const renderExact = renderSvg;   // same contract, now platform-agnostic

function writePng(file, svg, w, h) {
  writeFileSync(join(OUT, file), renderExact(svg, w, h));
}

const jobs = [];
function add(file, iconName, w, h, opts = {}) {
  jobs.push({ file, iconName, w, h, opts });
}

/* ---------- 1. home app circles (circle 44px in UI, glyph 24px) ---------- */
add('img_apple_icon_clock.png', 'clock', 24, 24, { color: '#1C1C1E', strokeWidth: 2.4 });
add('img_apple_icon_weather.png', 'cloud-sun', 24, 24);
add('img_apple_icon_heart.png', 'heart-pulse', 24, 24);
add('img_apple_icon_runner.png', 'person-standing', 24, 24);
add('img_apple_icon_settings.png', 'settings', 24, 24);
add('img_apple_icon_music.png', 'music', 24, 24);
add('img_apple_icon_message.png', 'message-circle', 24, 24);

/* ---------- 2. clock ---------- */
add('img_apple_footsteps.png', 'footprints', 16, 16);

/* ---------- 3. weather (hero 64, hourly 24, pin 16) ---------- */
const wx = [
  ['sunny', 'sun'], ['cloudy', 'cloud-sun'], ['overcast', 'cloud'],
  ['rain', 'cloud-rain'], ['heavyrain', 'cloud-rain-wind'],
  ['thunder', 'cloud-lightning'], ['snow', 'cloud-snow'], ['fog', 'cloud-fog'],
];
for (const [name, icon] of wx) {
  add(`img_apple_weather_${name}_64.png`, icon, 64, 64, { color: '#FFD60A' });
  add(`img_apple_weather_${name}_24.png`, icon, 24, 24, { color: '#FFD60A' });
}
add('img_apple_moon_64.png', 'moon', 64, 64, { color: '#FFD60A' });
add('img_apple_moon_24.png', 'moon', 24, 24, { color: '#FFD60A' });
add('img_apple_pin.png', 'map-pin', 16, 16, { color: '#FFD60A' });

/* ---------- 4. health ---------- */
add('img_apple_health_heart.png', 'heart', 24, 24, { color: '#FF453A' });
add('img_apple_health_drop.png', 'droplet', 12, 12);
add('img_apple_health_temp.png', 'thermometer', 12, 12);
add('img_apple_health_sleep.png', 'moon', 12, 12);

/* heart-rate trace 192x56 */
const tracePts = [];
{
  const n = 48;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const base = 30 + 7 * Math.sin(t * Math.PI * 6 + 1.2);
    const spike = (i % 8 === 4) ? -17 : (i % 8 === 5 ? 11 : 0);
    const y = Math.max(4, Math.min(52, base + spike + 3 * Math.sin(t * 21.7)));
    tracePts.push(`${(3 + t * 186).toFixed(1)},${y.toFixed(1)}`);
  }
}
const traceSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="192" height="56" viewBox="0 0 192 56">
  <polyline points="${tracePts.join(' ')}" fill="none" stroke="#FF453A" stroke-width="2.4"
    stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;
writeFileSync(join(OUT, 'img_apple_health_trace.png'),
  renderRaw(traceSvg));

/* ---------- 5. steps ---------- */
add('img_apple_steps_runner.png', 'person-standing', 24, 24, { color: '#30D158' });
add('img_apple_steps_flame.png', 'flame', 14, 14, { color: '#FF9F0A' });
add('img_apple_steps_location.png', 'map-pin', 14, 14, { color: '#30D158' });
add('img_apple_steps_floors.png', 'activity', 14, 14, { color: '#0A84FF' });

/* weekly bars 176x52 (overlay card) */
const chartSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="176" height="52" viewBox="0 0 176 52">
  ${[52, 68, 45, 80, 62, 90, 74].map((p, i) => {
    const h = Math.round(46 * p / 100);
    return `<rect x="${7 + i * 24}" y="${50 - h}" width="14" height="${h}" rx="3" fill="#30D158"/>`;
  }).join('')}
</svg>`;
writeFileSync(join(OUT, 'img_apple_steps_chart_bars.png'),
  renderRaw(chartSvg));

/* ---------- 6. ai ---------- */
add('img_apple_ai_chevron_left.png', 'chevron-left', 16, 16);
add('img_apple_ai_more.png', 'more-vertical', 16, 16);
add('img_apple_ai_mic.png', 'mic', 24, 24);
add('img_apple_ai_mic_listening.png', 'mic', 24, 24, { color: '#64D2FF' });
add('img_apple_ai_mic_speaking.png', 'audio-lines', 24, 24, { color: '#64D2FF' });

/* waveform frames 120x28 (5 frames) */
for (let f = 1; f <= 5; f++) {
  const bars = [];
  const n = 12;
  for (let i = 0; i < n; i++) {
    const phase = (i / n) * Math.PI * 2 * 1.6 + f * 1.1;
    const amp = 4 + 9 * Math.abs(Math.sin(phase)) * (0.55 + 0.45 * Math.sin(f * 0.9 + i));
    const x = 6 + i * 9.4;
    bars.push(`<rect x="${x.toFixed(1)}" y="${(14 - amp).toFixed(1)}" width="4" height="${(amp * 2).toFixed(1)}" rx="2" fill="#64D2FF" opacity="${(0.5 + 0.5 * Math.abs(Math.sin(phase + f))).toFixed(2)}"/>`);
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="28" viewBox="0 0 120 28">${bars.join('')}</svg>`;
  writeFileSync(join(OUT, `img_apple_ai_waveform_frame0${f}.png`),
    renderRaw(svg));
}

/* ---------- 7. settings ---------- */
add('img_apple_settings_wifi.png', 'wifi', 12, 12);
add('img_apple_settings_bluetooth.png', 'bluetooth', 12, 12);
add('img_apple_settings_brightness.png', 'sun', 12, 12, { color: '#1C1C1E', strokeWidth: 2.4 });
add('img_apple_settings_volume.png', 'volume-2', 12, 12);
add('img_apple_settings_info.png', 'info', 12, 12);
add('img_apple_chevron.png', 'chevron-right', 10, 16, { color: '#8E8E93' });

/* ---------- custom glyphs ---------- */

/* gemini 4-point star, parametric (original art drawn at c=22, R=10) */
function starPath(c, s) {
  const f = n => +(n * s).toFixed(2);
  return `M${c} ${c - f(10)} C${c + f(0.9)} ${c - f(6.8)} ${c + f(4.8)} ${c - f(2.9)} ${c + f(10)} ${c - f(2)}`
    + ` C${c + f(4.8)} ${c - f(1.1)} ${c + f(0.9)} ${c + f(2.8)} ${c} ${c + f(8)}`
    + ` C${c - f(0.9)} ${c + f(2.8)} ${c - f(4.8)} ${c - f(1.1)} ${c - f(10)} ${c - f(2)}`
    + ` C${c - f(4.8)} ${c - f(2.9)} ${c - f(0.9)} ${c - f(6.8)} ${c} ${c - f(10)} Z`;
}
/* home gemini disc: blue-purple gradient — 44px (ring size) + 64px (centre hero) */
function gemDisc(size) {
  const c = size / 2;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#4A7CFF"/><stop offset="1" stop-color="#BF5AF2"/>
  </linearGradient></defs>
  <circle cx="${c}" cy="${c}" r="${c}" fill="url(#g)"/>
  <path d="${starPath(c, size / 44)}" fill="#FFFFFF"/>
</svg>`;
}
for (const size of [44, 64]) {
  const name = size === 44 ? 'img_apple_circle_gemini.png' : 'img_apple_circle_gemini64.png';
  writeFileSync(join(OUT, name),
    renderRaw(gemDisc(size)));
}

/* gemini 4-point star (white) 24x24 */
const starSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <path d="M12 2 C12.9 7.2 16.8 11.1 22 12 C16.8 12.9 12.9 16.8 12 22 C11.1 16.8 7.2 12.9 2 12 C7.2 11.1 11.1 7.2 12 2 Z" fill="#FFFFFF"/>
</svg>`;
writeFileSync(join(OUT, 'img_apple_icon_gemini.png'),
  renderRaw(starSvg));

/* gemini header star (gradient) 32x32 */
const starGradSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#4A7CFF"/><stop offset="1" stop-color="#BF5AF2"/>
  </linearGradient></defs>
  <path d="M16 2 C17.2 9.6 22.4 14.8 30 16 C22.4 17.2 17.2 22.4 16 30 C14.8 22.4 9.6 17.2 2 16 C9.6 14.8 14.8 9.6 16 2 Z" fill="url(#g)"/>
</svg>`;
writeFileSync(join(OUT, 'img_apple_ai_star.png'),
  renderRaw(starGradSvg));

/* home grid-dots icon 24x24 (3x3 colored dots) */
const dots = [];
const dotCols = ['#FF453A', '#FF9F0A', '#FFD60A', '#30D158', '#64D2FF', '#0A84FF', '#BF5AF2', '#FF2D8A', '#8E8E93'];
for (let r = 0; r < 3; r++) {
  for (let c = 0; c < 3; c++) {
    dots.push(`<circle cx="${5 + c * 7}" cy="${5 + r * 7}" r="2.2" fill="${dotCols[r * 3 + c]}"/>`);
  }
}
const dotsSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">${dots.join('')}</svg>`;
writeFileSync(join(OUT, 'img_apple_icon_grid.png'),
  renderRaw(dotsSvg));

/* clock ticks — PRE-ROTATED (baked) so the .spj needs no IMAGE/Rotation at
   all: 12 squares 12x12, blue bar centered, rotated by θ. */
const TICK_ANG = { M0: 0, M90: 90, M180: 180, M270: 270,
  m30: 30, m60: 60, m120: 120, m150: 150,
  m210: 210, m240: 240, m300: 300, m330: 330 };
for (const [nm, deg] of Object.entries(TICK_ANG)) {
  const major = nm.startsWith('M');
  const len = major ? 12 : 10, wid = major ? 4 : 3;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">
    <rect x="${6 - wid / 2}" y="${6 - len / 2}" width="${wid}" height="${len}" rx="1" fill="#0A84FF"
      transform="rotate(${deg} 6 6)"/>
  </svg>`;
  writeFileSync(join(OUT, `img_apple_tick_${nm}.png`),
    renderRaw(svg));
}

/* analog hands — PRE-ROTATED square canvases, pivot = canvas centre = screen
   centre (120,120).  10:09:35 -> hour 304.5°, minute 54°, second 210°.
   lengths: hour 56px, minute 78px, second 90px — full-size on the 240 bezel. */
function handCanvas(size, len, tail, width, color, deg) {
  const c = size / 2;
  const rad = deg * Math.PI / 180;
  const tip = [c + len * Math.sin(rad), c - len * Math.cos(rad)].map(v => v.toFixed(2));
  const tlp = [c - tail * Math.sin(rad), c + tail * Math.cos(rad)].map(v => v.toFixed(2));
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <line x1="${tlp[0]}" y1="${tlp[1]}" x2="${tip[0]}" y2="${tip[1]}" stroke="${color}"
    stroke-width="${width}" stroke-linecap="round"/>
</svg>`;
}
writeFileSync(join(OUT, 'img_apple_hand_hour.png'), renderRaw(handCanvas(144, 58, 12, 5, '#FFFFFF', 304.5)));
writeFileSync(join(OUT, 'img_apple_hand_minute.png'), renderRaw(handCanvas(208, 88, 14, 3.5, '#FFFFFF', 54)));
writeFileSync(join(OUT, 'img_apple_hand_second.png'), renderRaw(handCanvas(232, 98, 16, 2, '#0A84FF', 210)));

/* battery 18x10 */
const battSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="10" viewBox="0 0 18 10">
  <rect x="0.5" y="0.5" width="14.5" height="9" rx="2.8" fill="none" stroke="${W}" stroke-width="1.1"/>
  <path d="M16.6 3.2 v3.6 a1.85 1.85 0 0 0 0 -3.6" fill="${W}"/>
  <rect x="2" y="2" width="9.5" height="6" rx="1.4" fill="${W}"/>
</svg>`;
writeFileSync(join(OUT, 'img_apple_battery.png'),
  renderRaw(battSvg));

/* clock ticks removed — superseded by baked-rotation set above */

/* ---------- run jobs ---------- */
let ok = 0, fail = 0;
for (const j of jobs) {
  try {
    const svg = iconSvg(j.iconName, j.opts);
    writeFileSync(join(OUT, j.file), renderExact(svg, j.w, j.h));
    ok++;
  } catch (e) {
    console.error(`FAIL ${j.file}: ${e.message}`);
    fail++;
  }
}
console.log(`icons: ${ok} written, ${fail} failed`);
console.log('custom glyphs + 240-round sizing done');
console.log(`renderer: ${resvgBackend()}`);
