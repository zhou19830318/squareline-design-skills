/**
 * resvg.mjs — one import, every platform.
 *
 * `@resvg/resvg-js` is a napi-rs native module: npm only fetches the prebuilt
 * binary for the machine that ran the install, so a package assembled on
 * Windows dies in a Linux container with
 *
 *     Cannot find module '@resvg/resvg-js-linux-x64-gnu'
 *
 * (that is exactly how Stage A broke in the freebuff sandbox).  This shim tries
 * the native binding first and transparently falls back to `@resvg/resvg-wasm`,
 * which is a plain WebAssembly module and therefore runs on any OS/CPU — musl
 * Alpine, ARMv7, Windows-on-ARM, whatever.
 *
 * Re-vendor the bindings any time with:
 *     python tools/vendor_prepare.py --list
 *     python tools/vendor_prepare.py --platforms linux-riscv64-gnu
 *
 * Public API (synchronous — the backend is resolved during module load):
 *   renderSvg(svg: string, width: number, height: number, opts?) -> Buffer
 *   resvgBackend() -> 'native' | 'wasm'
 *   resvgBackendError() -> Error | null   (why native failed, when it did)
 */

import { createRequire } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const NM = join(HERE, '..', 'node_modules');

let ResvgCtor = null;
let backend = 'none';
let backendError = null;

/* ---------------------------------------------------------------- native -- */
// RESVG_FORCE_WASM=1 exercises the fallback path on a machine whose native
// binding is fine — the only way to test the Linux code path from Windows.
const FORCE_WASM = /^(1|true|yes)$/i.test(process.env.RESVG_FORCE_WASM || '');
if (FORCE_WASM) backendError = new Error('RESVG_FORCE_WASM=1 (native skipped on purpose)');
try {
  if (FORCE_WASM) throw backendError;
  const native = require('@resvg/resvg-js');
  ResvgCtor = native.Resvg;
  backend = 'native';
} catch (err) {
  backendError = err;
  // Explain *which* binary is missing instead of dumping a stack trace — this
  // is the single most confusing failure mode of the whole toolchain.
  const plat = `${process.platform}-${process.arch}`;
  if (FORCE_WASM) {
    console.error('[resvg] RESVG_FORCE_WASM=1 — native binding skipped on purpose');
  } else {
    console.error(
      `[resvg] native binding unavailable (${plat}) — falling back to WASM.\n` +
      `        reason: ${err.code || err.message}\n` +
      `        fix:    python tools/vendor_prepare.py   (vendors every platform)`
    );
  }
}

/* ------------------------------------------------------------------ wasm -- */
if (!ResvgCtor) {
  try {
    const wasm = await import('@resvg/resvg-wasm');
    const wasmPath = join(NM, '@resvg', 'resvg-wasm', 'index_bg.wasm');
    if (!existsSync(wasmPath)) {
      throw new Error('resvg-wasm binary not found at ' + wasmPath);
    }
    await wasm.initWasm(readFileSync(wasmPath));
    ResvgCtor = wasm.Resvg;
    backend = 'wasm';
  } catch (err) {
    throw new Error(
      'No usable SVG renderer.\n' +
      `  native: ${backendError ? backendError.message : 'n/a'}\n` +
      `  wasm:   ${err.message}\n` +
      '  run `python tools/vendor_prepare.py` (needs network once) or ' +
      '`cd tools && npm install`.'
    );
  }
}

globalThis.__RESVG_BACKEND__ = backend;

/* ------------------------------------------------------------------ api --- */

/** Render an SVG string at its own declared size. */
export function renderRaw(svg, options = {}) {
  const r = new ResvgCtor(String(svg), {
    background: 'rgba(0,0,0,0)',
    ...options,
  });
  const png = r.render().asPng();
  return Buffer.isBuffer(png) ? png : Buffer.from(png);
}

/** Render an SVG string to a PNG Buffer at exactly `width` x `height`
 *  (the declared width/height are rewritten; viewBox keeps the aspect). */
export function renderSvg(svg, width, height, options = {}) {
  const sized = String(svg).replace(
    /<svg([^>]*?)width="[\d.]+"([^>]*?)height="[\d.]+"/,
    `<svg$1width="${width}"$2height="${height}"`
  );
  return renderRaw(sized, options);
}

export function resvgBackend() { return backend; }
export function resvgBackendError() { return backendError; }
export { ResvgCtor as Resvg };
