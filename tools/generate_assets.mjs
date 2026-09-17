// AIWatch asset generator
// Rasterizes Lucide icons (white strokes, transparent bg) and generates
// programmatic images (wallpaper, avatars, album placeholder).
//
// Sizing basis (watch UI conventions, 410x502 @ ~315ppi canvas => 2px ~= 1dp):
//   - UI body text 16dp = 32px, labels 11-12dp = 22-24px, display 68dp = 68px+
//   - Icon buttons / app icons: min touch target 48dp = 96px (visual 40dp = 80px)
//   - List row icon chips 16dp glyphs on 24dp chips => 32px glyphs, 48px chips
//   - Weather hero 56dp = 112px, hourly 28dp = 56px
//   - Album art 44dp = 88px-> UI 96px, avatars 40dp = 80px
//   - Status bar glyphs 8-9dp = 16-18px
// Run:  node tools/generate_assets.mjs
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
// assets/images); pass `--out <dir>` to target an example folder, e.g.
//   node tools/generate_assets.mjs --out examples/AIWatch/assets/images
const argOut = process.argv.indexOf('--out');
const OUT = argOut !== -1 && process.argv[argOut + 1]
  ? resolve(process.argv[argOut + 1])
  : join(ROOT, '..', 'assets', 'images');
mkdirSync(OUT, { recursive: true });

const W = 'white';
const GRAY = '#999999';
const YELLOW = '#FFD60A';
const RED = '#FF453A';

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

const jobs = [];
function add(file, iconName, w, h, opts = {}) {
  jobs.push({ file, iconName, w, h, opts });
}

/* ---------- 1. status / common (8-9dp glyphs => 16-18px) ---------- */
add('img_status_battery_frame.png',    'battery', 22, 12);
add('img_status_battery_charging.png', 'zap',     14, 12, { color: YELLOW });
add('img_status_wifi.png',             'wifi',    18, 18);
add('img_status_wifi_off.png',         'wifi-off',18, 18, { color: GRAY });
add('img_status_mic_active.png',       'mic',     18, 18, { color: '#FF2D8A' });
add('img_nav_back_arrow.png',          'chevron-right', 14, 24, { color: GRAY });

/* ---------- 2. home grid (visual 40dp in 60dp touch circle => 44px glyph) ---------- */
add('img_home_icon_clock.png',    'clock', 44, 44);
add('img_home_icon_weather.png',  'cloud-sun', 44, 44);
add('img_home_icon_ai.png',       'bot', 44, 44);
add('img_home_icon_pomodoro.png', 'timer', 44, 44);
add('img_home_icon_steps.png',    'person-standing', 44, 44);
add('img_home_icon_music.png',    'music', 44, 44);
add('img_home_icon_settings.png', 'settings', 44, 44);

/* ---------- 3. watchface ---------- */
add('img_watchface_icon_location.png', 'map-pin', 16, 18);
add('img_watchface_icon_weather_mini.png', 'cloud-sun', 48, 48);

/* ---------- 4. weather (hero 56dp=112px, hourly 28dp=56px) ---------- */
const wx = [
  ['sunny', 'sun'], ['cloudy', 'cloud-sun'], ['overcast', 'cloud'],
  ['rain', 'cloud-rain'], ['heavyrain', 'cloud-rain-wind'],
  ['thunder', 'cloud-lightning'], ['snow', 'cloud-snow'], ['fog', 'cloud-fog'],
];
for (const [name, icon] of wx) {
  add(`img_weather_icon_${name}_72.png`, icon, 112, 112);   // keep _72 legacy name, now 112px hero
  add(`img_weather_icon_${name}_28.png`, icon, 56, 56);     // keep _28 legacy name, now 56px hourly
}
add('img_weather_icon_location_pin.png', 'map-pin', 18, 18);

/* ---------- 5. AI chat (avatar 40dp=80px, history glyph 14dp=28px) ---------- */
add('img_ai_icon_history_bubble.png', 'message-circle', 28, 28);
add('img_ai_icon_mic_idle.png',       'mic', 48, 48);
add('img_ai_icon_mic_listening.png',  'mic', 48, 48, { color: '#FF2D8A' });
add('img_ai_icon_mic_speaking.png',   'activity', 48, 48, { color: '#8B5CF6' });

/* ---------- 6. pomodoro (control-button glyphs ~14dp => 28-32px) ---------- */
add('img_pomodoro_icon_list.png',     'list', 30, 30);
add('img_pomodoro_icon_play.png',     'play', 34, 34);
add('img_pomodoro_icon_pause.png',    'pause', 34, 34);
add('img_pomodoro_icon_settings.png', 'settings', 30, 30);

/* ---------- 7. steps ---------- */
add('img_steps_icon_running.png', 'person-standing', 26, 26);
add('img_steps_icon_shoe.png',    'footprints', 32, 32);
add('img_steps_icon_fire.png',    'flame', 24, 24, { color: '#FF9F0A' });
add('img_steps_icon_location.png','map-pin', 24, 24);
add('img_steps_icon_chart.png',   'chart-column', 28, 28);

/* ---------- 8. music ---------- */
add('img_music_icon_note.png',   'music', 24, 24);
add('img_music_icon_prev.png',   'skip-back', 32, 32);
add('img_music_icon_next.png',   'skip-forward', 32, 32);
add('img_music_icon_play.png',   'play', 36, 36);
add('img_music_icon_pause.png',  'pause', 36, 36);
add('img_music_icon_shuffle.png',        'shuffle', 26, 26, { color: GRAY });
add('img_music_icon_shuffle_active.png', 'shuffle', 26, 26, { color: '#FF2D8A' });
add('img_music_icon_volume.png', 'volume-2', 26, 26);

/* ---------- 9. settings (chip glyph 9dp=18px on 24dp chip) ---------- */
add('img_settings_icon_gear.png',      'settings', 22, 22, { color: GRAY });
add('img_settings_icon_bluetooth.png', 'bluetooth', 18, 18);
add('img_settings_icon_brightness.png','sun', 18, 18);
add('img_settings_icon_volume.png',    'volume-2', 18, 18);
add('img_settings_icon_language.png',  'globe', 18, 18);
add('img_settings_icon_about.png',     'info', 18, 18);

/* ---------- 10. album placeholder + avatars (UI-correct sizes) ---------- */
const albumSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#FF2D8A"/><stop offset="0.55" stop-color="#8B5CF6"/><stop offset="1" stop-color="#1a1440"/>
  </linearGradient></defs>
  <rect width="96" height="96" rx="20" fill="url(#g)"/>
  <g transform="translate(25,25) scale(1.9167)" stroke="#ffffff" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 18V5l12-2v13"/>
    <circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
  </g>
</svg>`;
writeFileSync(join(OUT, 'img_music_album_placeholder.png'), renderRaw(albumSvg));

function avatar(file, c1, c2) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/>
  </linearGradient></defs>
  <circle cx="40" cy="40" r="40" fill="url(#g)"/>
  <g stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round" transform="translate(20,20) scale(1.6667)">
    <rect x="4" y="8" width="16" height="12" rx="3"/>
    <path d="M12 4v4"/><circle cx="9" cy="13" r="0.6" fill="#fff"/><circle cx="15" cy="13" r="0.6" fill="#fff"/>
    <path d="M9 17h6"/>
  </g>
</svg>`;
  writeFileSync(join(OUT, file), renderRaw(svg));
}
avatar('img_ai_avatar_bot.png', '#3B82F6', '#8B5CF6');
avatar('img_ai_avatar_user.png', '#64748B', '#334155');

function ensureDir(f) { mkdirSync(dirname(f), { recursive: true }); }

let ok = 0, fail = 0;
for (const j of jobs) {
  try {
    const svg = iconSvg(j.iconName, j.opts);
    const png = renderExact(svg, j.w, j.h);
    const out = join(OUT, j.file);
    ensureDir(out);
    writeFileSync(out, png);
    ok++;
  } catch (e) {
    console.error(`FAIL ${j.file}: ${e.message}`);
    fail++;
  }
}
console.log(`icons: ${ok} written, ${fail} failed`);
console.log('album placeholder + avatars written');

/* ---------- special: battery frame is a wide rounded rect, draw manually ---------- */
const batterySvg = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="12" viewBox="0 0 22 12">
  <rect x="0.75" y="0.75" width="18" height="10.5" rx="3" fill="none" stroke="${W}" stroke-width="1.5"/>
  <path d="M20.2 3.6 v4.8 a2.2 2.2 0 0 0 0-4.8" fill="${W}"/>
</svg>`;
writeFileSync(join(OUT, 'img_status_battery_frame.png'), renderRaw(batterySvg));
console.log('battery frame written (custom svg)');

/* ---------- custom: charging battery 22x12 (full-bleed, same geometry as frame) ---------- */
const batteryChargingSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="12" viewBox="0 0 22 12">
  <rect x="0.75" y="0.75" width="18" height="10.5" rx="3" fill="none" stroke="${W}" stroke-width="1.5"/>
  <path d="M20.2 3.6 v4.8 a2.2 2.2 0 0 0 0-4.8" fill="${W}"/>
  <path d="M10.8 2.2 7.6 6.6h2.2l-.8 3.4 3.4-4.6h-2.2z" fill="${W}"/>
</svg>`;
writeFileSync(join(OUT, 'img_status_battery_charging.png'), renderRaw(batteryChargingSvg));
console.log('battery charging written (custom svg)');

/* ---------- custom colored glyphs: home tomato + runner (white) ---------- */
// 番茄（红果绿蒂，对应参考图主页图标）44x44
const tomatoSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">
  <circle cx="22" cy="26" r="15.5" fill="#FF4133"/>
  <ellipse cx="16.5" cy="21.5" rx="5" ry="3.2" fill="#FF6B5B" opacity="0.65"/>
  <path d="M22 16.5 C20 10.5 15 9 10.5 10.5 C13 15 17.5 17 22 16.5 Z" fill="#3DD874"/>
  <path d="M22 16.5 C24 10.5 29 9 33.5 10.5 C31 15 26.5 17 22 16.5 Z" fill="#2FB862"/>
  <path d="M22 8.5 C21 11 21 14 22 16.5 C23 14 23 11 22 8.5 Z" fill="#2FB862"/>
</svg>`;
writeFileSync(join(OUT, 'img_home_icon_tomato.png'), renderRaw(tomatoSvg));
// 跑步人形（白色，Material Symbols directions_run）44x44
const runnerPath = 'M13.49 5.48c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm-3.6 13.9 1-4.4 2.1 2v6h2v-7.5l-2.1-2 .6-3c1.3 1.5 3.3 2.5 5.5 2.5v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1l-5.2 2.2v4.7h2v-3.4l1.8-.7-1.6 8.1-4.9-1-.4 2 7 1.4z';
const runnerSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 24 24"><path fill="#FFFFFF" d="${runnerPath}"/></svg>`;
writeFileSync(join(OUT, 'img_home_icon_runner.png'), renderRaw(runnerSvg));
console.log('tomato + runner glyphs written');

/* ---------- wallpaper: 410x502 sunset mountain lake ---------- */
function wallpaper() {
  const Wp = 410, Hp = 502;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${Wp}" height="${Hp}" viewBox="0 0 ${Wp} ${Hp}">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1a1440"/>
      <stop offset="0.35" stop-color="#5b2a68"/>
      <stop offset="0.62" stop-color="#c2456e"/>
      <stop offset="0.78" stop-color="#ff8a4c"/>
      <stop offset="0.9" stop-color="#ffc27a"/>
    </linearGradient>
    <linearGradient id="lake" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e8905a"/>
      <stop offset="0.5" stop-color="#7a3d66"/>
      <stop offset="1" stop-color="#201238"/>
    </linearGradient>
    <radialGradient id="sunglow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fff3c4" stop-opacity="1"/>
      <stop offset="0.55" stop-color="#ffb36b" stop-opacity="0.85"/>
      <stop offset="1" stop-color="#ffb36b" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="${Wp}" height="${Hp*0.62}" fill="url(#sky)"/>
  <circle cx="${Wp*0.58}" cy="${Hp*0.545}" r="150" fill="url(#sunglow)"/>
  <circle cx="${Wp*0.58}" cy="${Hp*0.545}" r="30" fill="#ffe9b0"/>
  <!-- far mountains -->
  <path d="M0 ${Hp*0.5} L70 ${Hp*0.40} L130 ${Hp*0.47} L200 ${Hp*0.38} L280 ${Hp*0.48} L340 ${Hp*0.42} L410 ${Hp*0.50} V${Hp*0.62} H0 Z" fill="#3a1f4e" opacity="0.85"/>
  <!-- near mountains -->
  <path d="M0 ${Hp*0.58} L90 ${Hp*0.46} L170 ${Hp*0.56} L250 ${Hp*0.47} L330 ${Hp*0.57} L410 ${Hp*0.50} V${Hp*0.62} H0 Z" fill="#241238"/>
  <!-- lake -->
  <rect y="${Hp*0.62}" width="${Wp}" height="${Hp*0.38}" fill="url(#lake)"/>
  <!-- sun reflection: soft horizontal shimmer only (no vertical pole artifact) -->
  <g fill="#ffd9a0">
    <rect x="${Wp*0.58-26}" y="${Hp*0.65}" width="52" height="4" rx="2" opacity="0.45"/>
    <rect x="${Wp*0.58-40}" y="${Hp*0.71}" width="80" height="4" rx="2" opacity="0.32"/>
    <rect x="${Wp*0.58-20}" y="${Hp*0.77}" width="40" height="4" rx="2" opacity="0.24"/>
    <rect x="${Wp*0.58-32}" y="${Hp*0.83}" width="64" height="4" rx="2" opacity="0.16"/>
  </g>
  <!-- subtle ripples -->
  <g stroke="#ffffff" stroke-opacity="0.10" stroke-width="2">
    <line x1="30" y1="${Hp*0.68}" x2="120" y2="${Hp*0.68}"/>
    <line x1="280" y1="${Hp*0.74}" x2="390" y2="${Hp*0.74}"/>
    <line x1="60" y1="${Hp*0.82}" x2="180" y2="${Hp*0.82}"/>
    <line x1="240" y1="${Hp*0.88}" x2="370" y2="${Hp*0.88}"/>
  </g>
  <!-- birds -->
  <g stroke="#2a1740" stroke-width="2.5" fill="none" stroke-linecap="round">
    <path d="M120 150 q8 -8 16 0 M136 150 q8 -8 16 0"/>
    <path d="M300 120 q7 -7 14 0 M314 120 q7 -7 14 0" opacity="0.8"/>
  </g>
</svg>`;
  return renderRaw(svg, { background: '#000000' });
}
writeFileSync(join(OUT, 'img_watchface_bg_01.png'), wallpaper());
console.log('wallpaper written');

/* ---------- drag handle 36x4 ---------- */
const dragSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="4" viewBox="0 0 36 4"><rect width="36" height="4" rx="2" fill="#5a5a5a"/></svg>`;
writeFileSync(join(OUT, 'img_weather_drag_handle.png'), renderRaw(dragSvg));
console.log('drag handle written');

/* ---------- waveform frames 200x40 (5 frames) ---------- */
for (let f = 1; f <= 5; f++) {
  const bars = [];
  const n = 20;
  for (let i = 0; i < n; i++) {
    const phase = (i / n) * Math.PI * 2 * 2 + f * 1.2;
    const amp = 4 + 14 * Math.abs(Math.sin(phase)) * (0.6 + 0.4 * Math.sin(f * 0.9 + i));
    const x = 10 + i * 9.5;
    bars.push(`<rect x="${x.toFixed(1)}" y="${(20 - amp).toFixed(1)}" width="5" height="${(amp * 2).toFixed(1)}" rx="2.5" fill="#FF2D8A" opacity="${(0.45 + 0.55 * Math.abs(Math.sin(phase + f))).toFixed(2)}"/>`);
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="40" viewBox="0 0 200 40">${bars.join('')}</svg>`;
  writeFileSync(join(OUT, `img_ai_waveform_frame0${f}.png`), renderRaw(svg));
}
console.log('waveform frames written');
console.log(`DONE (renderer: ${resvgBackend()})`);
