// Convert Noto Sans SC (= Source Han Sans SC) TTFs to LVGL C fonts.
// Charset = every character that appears in the two project docs
// (i.e. every string the UI will actually render), minus glyphs the font lacks
// (emoji / box-drawing chars — not real UI text).
// Run:  node tools/generate_fonts.mjs
import { execFileSync } from 'child_process';
import { readFileSync, mkdirSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';

const ROOT = dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const FONTDIR = join(ROOT, '..', 'assets', 'fonts');
const OUTDIR = join(FONTDIR, 'lvgl');

// glyphs confirmed missing from Noto Sans SC v40 (emoji & box-drawing, not UI text)
const SKIP = new Set('℃≈├📍⚠💡⏸→🔋▶─\uFE0F'.split(''));

const chars = new Set();
for (const doc of ['AI手表UI设计规格文档.md', 'AIWatch图片字体资源清单.md']) {
  const txt = readFileSync(join(ROOT, '..', doc), 'utf8');
  for (const ch of txt) {
    if (ch === '\n' || ch === '\r' || ch === '\t' || ch === ' ') continue;
    if (SKIP.has(ch)) continue;
    // keep everything: Basic Latin will be added via --range anyway,
    // but including doc chars here guarantees CJK + punctuation coverage
    chars.add(ch);
  }
}
for (const c of '°∶') { if (!SKIP.has(c)) chars.add(c); }
const fullSymbols = [...chars].join('');
console.log(`full charset: ${fullSymbols.length} chars`);

// per-font subsets per AIWatch图片字体资源清单.md §三:
// big display fonts only carry digits + a few units, body fonts carry the full set
const DIGITS = '0123456789';
const time72 = DIGITS + ':月周日';
const num48 = DIGITS + ':.%-+°C步卡路里公里时';

function pick(set) {
  return [...new Set([...set])].filter(c => !SKIP.has(c)).join('');
}

// invoke lv_font_conv's JS entry directly (no cmd shell) so Chinese args
// survive Windows GBK console encoding
const LFC = join(ROOT, 'node_modules', 'lv_font_conv', 'lv_font_conv.js');

const LATIN = '0x20-0x7F';
const DIGITS_R = '0x25,0x2B,0x2D,0x2E,0x30-0x3A,0x43,0xB0'; // % + - . 0-9 : C °

const fonts = [
  { file: 'noto-sans-sc-v40-chinese-simplified-700.ttf',     size: 72, out: 'font_time_display_72.c',   symbols: pick(time72), range: DIGITS_R },
  { file: 'noto-sans-sc-v40-chinese-simplified-700.ttf',     size: 48, out: 'font_number_bold_48.c',    symbols: pick(num48),  range: DIGITS_R },
  { file: 'noto-sans-sc-v40-chinese-simplified-500.ttf',     size: 22, out: 'font_title_22.c',          symbols: fullSymbols, range: LATIN },
  { file: 'noto-sans-sc-v40-chinese-simplified-regular.ttf', size: 16, out: 'font_body_16.c',           symbols: fullSymbols, range: LATIN },
  { file: 'noto-sans-sc-v40-chinese-simplified-regular.ttf', size: 14, out: 'font_body_medium_14.c',    symbols: fullSymbols, range: LATIN },
  { file: 'noto-sans-sc-v40-chinese-simplified-regular.ttf', size: 12, out: 'font_caption_12.c',         symbols: fullSymbols, range: LATIN },
];

mkdirSync(OUTDIR, { recursive: true });
for (const f of fonts) {
  const args = [
    LFC,
    '--font', join(FONTDIR, f.file),
    '--format', 'lvgl',
    '--lv-include', 'lvgl.h',
    '--bpp', '4',
    '--size', String(f.size),
    '--range', `${f.range},0x2014,0x2018-0x2019,0x201C-0x201D,0x3001,0x3002,0xFF01-0xFF5E`,
    '--symbols', f.symbols,
    '-o', join(OUTDIR, f.out),
  ];
  execFileSync(process.execPath, args, { stdio: 'inherit', cwd: ROOT });
  console.log(`written ${f.out}`);
}
console.log('DONE');
