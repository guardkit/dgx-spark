// Orbit-globe artifact validator — the gate suite.
// Usage:  node validate.mjs [path/to/index.html]   (default ../index.html)
// Exit 0 = all gates PASS. Non-zero = at least one FAIL (table printed either way).
//
// Three tiers:
//   T1 static  — file shape, forbidden endpoints, approved CDNs only
//   T2 runtime — headless Chromium: console errors, the __orbitGlobe contract,
//                satellite count, motion, FPS, visible error-state on TLE failure
//   T3 oracle  — physics the builder cannot game: the app's ISS position vs an
//                INDEPENDENT SGP4 propagation of fresh CelesTrak elements, and vs
//                the live wheretheiss.at API (time-skew tolerant)

import { readFileSync, existsSync } from 'node:fs';
import { createServer } from 'node:http';
import { resolve, dirname } from 'node:path';
import { chromium } from 'playwright';
import * as satellite from 'satellite.js';

const target = resolve(process.argv[2] ?? new URL('../index.html', import.meta.url).pathname);
const gates = [];
const gate = (id, ok, detail) => { gates.push({ id, ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${id}  ${detail ?? ''}`); };
const angDist = (a, b) => { // great-circle degrees between {lat,lng} pairs
  const r = Math.PI / 180, φ1 = a.lat * r, φ2 = b.lat * r, dφ = (b.lat - a.lat) * r, dλ = (b.lng - a.lng) * r;
  const h = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2;
  return (2 * Math.asin(Math.min(1, Math.sqrt(h)))) / r;
};

// ---------- T1: static ----------
if (!existsSync(target)) { gate('T1.file-exists', false, target); finish(); }
const html = readFileSync(target, 'utf8');
gate('T1.file-exists', true, target);
gate('T1.no-open-notify', !/open-notify/i.test(html), 'open-notify is HTTP-only (mixed-content death)');
const httpHits = [...html.matchAll(/http:\/\/[^"'` )\]]+/g)].map(m => m[0]).filter(u => !/localhost|127\.0\.0\.1|www\.w3\.org/.test(u));
gate('T1.https-only', httpHits.length === 0, httpHits.slice(0, 3).join(' ') || 'no plain-http URLs');
const extSrc = [...html.matchAll(/(?:src|href)=["'](https:\/\/[^"']+)["']/g)].map(m => m[1]);
const badCdn = extSrc.filter(u => !/^(https:\/\/cdn\.jsdelivr\.net\/|https:\/\/unpkg\.com\/)/.test(u));
gate('T1.approved-cdns', badCdn.length === 0, badCdn.slice(0, 3).join(' ') || 'jsdelivr/unpkg only');

// ---------- independent ground truth (fetched BEFORE the app runs) ----------
let issSatrec = null;
try {
  const tle = await (await fetch('https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle')).text();
  const lines = tle.split(/\r?\n/);
  const i = lines.findIndex(l => /ISS \(ZARYA\)/.test(l));
  if (i >= 0) issSatrec = satellite.twoline2satrec(lines[i + 1], lines[i + 2]);
  gate('T3.oracle-tle-fetch', !!issSatrec, issSatrec ? 'independent ISS elements loaded' : 'ISS not found in stations group');
} catch (e) { gate('T3.oracle-tle-fetch', false, `celestrak unreachable: ${e.message} (oracle checks will be skipped, not failed)`); }

// ---------- static file server for the workspace ----------
const root = dirname(target);
const srv = createServer((req, res) => {
  try {
    const p = resolve(root, '.' + new URL(req.url, 'http://x').pathname.replace(/\/$/, '/index.html'));
    if (!p.startsWith(root)) { res.writeHead(403); return res.end(); }
    const ext = p.split('.').pop();
    res.writeHead(200, { 'content-type': { html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json' }[ext] ?? 'application/octet-stream' });
    res.end(readFileSync(p));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(r => srv.listen(0, r));
const base = `http://localhost:${srv.address().port}/index.html`;

// ---------- T2: runtime ----------
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push(String(e)));

  await page.goto(base, { waitUntil: 'load', timeout: 30_000 });

  // The testability contract (AGENTS.md): window.__orbitGlobe updated every frame.
  const booted = await page.waitForFunction(
    () => window.__orbitGlobe && window.__orbitGlobe.satCount > 1000 && window.__orbitGlobe.iss,
    null, { timeout: 90_000 }).then(() => true).catch(() => false);
  gate('T2.contract+catalog', booted, booted ? 'window.__orbitGlobe live, satCount>1000, iss present' : '__orbitGlobe missing/incomplete after 90s');

  if (booted) {
    const A = await page.evaluate(() => JSON.parse(JSON.stringify(window.__orbitGlobe)));
    gate('T2.boots-at-1x', (A.timeWarp ?? 1) === 1 && Math.abs(A.simTime - Date.now()) < 15_000,
      `timeWarp=${A.timeWarp} skew=${Math.round((A.simTime - Date.now()) / 1000)}s (must boot at 1× real time)`);

    await page.waitForTimeout(6_000);
    const B = await page.evaluate(() => JSON.parse(JSON.stringify(window.__orbitGlobe)));
    const moved = angDist({ lat: A.iss.lat, lng: A.iss.lng }, { lat: B.iss.lat, lng: B.iss.lng });
    gate('T2.iss-moves', B.simTime > A.simTime && moved > 0.05, `Δ${moved.toFixed(3)}° over ${(B.simTime - A.simTime) / 1000}s sim`);

    const fps = await page.evaluate(() => new Promise(res => {
      let c = 0; const t0 = performance.now();
      const loop = () => { c++; performance.now() - t0 < 4000 ? requestAnimationFrame(loop) : res(c / 4); };
      requestAnimationFrame(loop);
    }));
    gate('T2.fps', fps >= 30, `${fps.toFixed(0)} fps over 4s (floor 30)`);

    // ---------- T3: the physics oracle ----------
    if (issSatrec) {
      const when = new Date(B.simTime);
      const pv = satellite.propagate(issSatrec, when);
      if (pv.position) {
        const gmst = satellite.gstime(when);
        const geo = satellite.eciToGeodetic(pv.position, gmst);
        const truth = { lat: satellite.degreesLat(geo.latitude), lng: satellite.degreesLong(geo.longitude) };
        const err = angDist(truth, { lat: B.iss.lat, lng: B.iss.lng });
        gate('T3.sgp4-oracle', err < 1.5, `app vs independent SGP4: ${err.toFixed(2)}° (tol 1.5°)`);
      } else gate('T3.sgp4-oracle', false, 'oracle propagation returned no position');
    }
    try {
      const live = await (await fetch('https://api.wheretheiss.at/v1/satellites/25544')).json();
      const skewS = Math.abs(B.simTime - Date.now()) / 1000;
      if ((B.timeWarp ?? 1) === 1 && skewS < 20) {
        const err = angDist({ lat: live.latitude, lng: live.longitude }, { lat: B.iss.lat, lng: B.iss.lng });
        gate('T3.live-oracle', err < 3, `app vs wheretheiss.at: ${err.toFixed(2)}° (tol 3°, skew ${skewS.toFixed(0)}s)`);
      } else gate('T3.live-oracle', false, `sim not at 1×/now (warp=${B.timeWarp}, skew=${skewS.toFixed(0)}s) — cannot cross-check live truth`);
    } catch (e) { console.log(`SKIP  T3.live-oracle  wheretheiss.at unreachable: ${e.message}`); }
  }
  gate('T2.zero-console-errors', consoleErrors.length === 0, consoleErrors.slice(0, 2).join(' | ') || 'clean');

  // ---------- T2b: visible error state when the TLE source is down ----------
  const ctx2 = await browser.newContext();
  await ctx2.route('**celestrak.org**', r => r.abort());
  const p2 = await ctx2.newPage();
  await p2.goto(base, { waitUntil: 'load', timeout: 30_000 });
  const errState = await p2.waitForFunction(() => {
    const og = window.__orbitGlobe;
    const domErr = document.body && /error|failed|unavailable|couldn.t/i.test(document.body.innerText || '');
    return (og && og.errors && og.errors.length > 0) || domErr;
  }, null, { timeout: 30_000 }).then(() => true).catch(() => false);
  gate('T2b.visible-error-state', errState, errState ? 'error surfaced with TLE source blocked' : 'blank/silent app on TLE failure');
  await ctx2.close();
} finally { await browser.close(); srv.close(); }
finish();

function finish() {
  const fails = gates.filter(g => !g.ok);
  console.log(`\n== ${gates.length - fails.length}/${gates.length} gates green ==`);
  process.exit(fails.length ? 1 : 0);
}
