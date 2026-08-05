#!/usr/bin/env node
// T3 gates: the board's rows cross-checked against an independent fetch of the same
// live TfL Arrivals endpoint, plus a blocked-API honesty phase.
// Usage: node validate.mjs [target-dir]   (default: the workspace root above this script)
import { readFileSync, existsSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, join, resolve, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(process.argv[2] ?? join(here, ".."));
const ART = join(target, "index.html");
const cfgPath = existsSync(join(target, "config.json")) ? join(target, "config.json") : join(here, "..", "config.json");
const CFG = JSON.parse(readFileSync(cfgPath, "utf8"));
const API = `${CFG.apiBase}/StopPoint/${CFG.stopId}/Arrivals`;
const MIME = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript" };

const results = [];
const gate = async (id, fn) => {
  try { const d = await fn(); results.push([id, "PASS", d ?? ""]); }
  catch (e) { results.push([id, "FAIL", e.message]); }
};

await gate("B1.static", () => {
  if (!existsSync(ART)) throw new Error("index.html missing");
  const html = readFileSync(ART, "utf8");
  const apiHost = new URL(CFG.apiBase).host;
  const refs = [...html.matchAll(/https?:\/\/([^/"'\s)]+)/gi)].map((m) => m[1]);
  const foreign = refs.filter((h) => h !== apiHost);
  if (foreign.length) throw new Error(`non-approved host(s): ${[...new Set(foreign)].join(", ")}`);
  return "no foreign hosts";
});

// serve the workspace so ./config.json resolves
const server = createServer((req, res) => {
  const file = join(target, req.url === "/" ? "index.html" : req.url.split("?")[0]);
  try {
    res.setHeader("Content-Type", MIME[extname(file)] ?? "text/plain");
    res.end(readFileSync(file));
  } catch { res.statusCode = 404; res.end("not found"); }
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}/`;

const browser = await chromium.launch();
let page = await browser.newPage();
const consoleErrors = [];
page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
page.on("pageerror", (e) => consoleErrors.push(String(e)));

let board = null;
await gate("B2.contract", async () => {
  await page.goto(base, { waitUntil: "load" });
  await page.waitForFunction(
    () => (window.__busBoard?.departures?.length ?? 0) > 0 || (window.__busBoard?.errors?.length ?? 0) > 0,
    null, { timeout: 25000 }
  );
  board = await page.evaluate(() => JSON.parse(JSON.stringify(window.__busBoard)));
  if (board.stopId !== CFG.stopId) throw new Error(`stopId "${board.stopId}" != config "${CFG.stopId}"`);
  for (const [i, d] of board.departures.entries())
    for (const k of ["line", "destination", "etaMin", "expectedIso"])
      if (d[k] === undefined || d[k] === null) throw new Error(`departure ${i}: missing "${k}"`);
  if (board.departures.length > 10) throw new Error(`${board.departures.length} rows shown (max 10)`);
  for (let i = 1; i < board.departures.length; i++)
    if (board.departures[i].etaMin < board.departures[i - 1].etaMin) throw new Error(`not sorted at row ${i}`);
  return `${board.departures.length} rows, sorted`;
});

await gate("B3.live-oracle", async () => {
  if (!board) throw new Error("skipped: B2 failed");
  const res = await fetch(API, { signal: AbortSignal.timeout(10000) });
  if (!res.ok) throw new Error(`oracle fetch ${res.status} — try again / check the stop`);
  const oracle = await res.json();
  if (oracle.length === 0) {
    if (board.departures.length === 0 && board.errors.length > 0)
      return "oracle empty (quiet hours) and the board says so honestly";
    if (board.departures.length > 0)
      throw new Error("oracle has no arrivals but the board shows rows — where are they from?");
    throw new Error("oracle empty and the board is silent about having no data");
  }
  const rows = board.departures.slice(0, 5);
  if (rows.length === 0) throw new Error("oracle has arrivals but the board shows none");
  let matched = 0;
  for (const r of rows) {
    const hit = oracle.find(
      (p) =>
        String(p.lineName).toLowerCase() === String(r.line).toLowerCase() &&
        Math.abs(new Date(p.expectedArrival) - new Date(r.expectedIso)) <= 120000
    );
    if (hit) matched++;
  }
  if (matched / rows.length < 0.6)
    throw new Error(`only ${matched}/${rows.length} shown rows match the live API (need >=60% — predictions churn, but not this much)`);
  return `${matched}/${rows.length} rows corroborated by an independent fetch`;
});

await gate("B4.console-clean", async () => {
  if (consoleErrors.length) throw new Error(`${consoleErrors.length} error(s): ${consoleErrors[0]}`);
});

await gate("B5.blocked-api-honesty", async () => {
  const p2 = await browser.newPage();
  const uncaught = [];
  p2.on("pageerror", (e) => uncaught.push(String(e)));
  await p2.route((url) => url.href.startsWith(CFG.apiBase), (r) => r.abort());
  await p2.goto(base, { waitUntil: "load" });
  await p2.waitForFunction(() => (window.__busBoard?.errors?.length ?? 0) > 0, null, { timeout: 25000 });
  const state = await p2.evaluate(() => ({
    errors: window.__busBoard.errors,
    deps: window.__busBoard.departures.length,
    text: document.body.innerText,
  }));
  if (state.deps > 0) throw new Error("API blocked but rows still presented as live");
  if (!/error|unavailable|failed|no data|unable/i.test(state.text))
    throw new Error("errors[] set but nothing visible on the board says so");
  if (uncaught.length) throw new Error(`uncaught error while degraded: ${uncaught[0]}`);
  await p2.close();
  return "visible honest failure state";
});

await browser.close();
server.close();

const w = Math.max(...results.map(([id]) => id.length));
for (const [id, verdict, detail] of results)
  console.log(`${id.padEnd(w)}  ${verdict}${detail ? `  ${detail}` : ""}`);
const failed = results.filter(([, v]) => v === "FAIL").length;
console.log(failed ? `\n${failed}/${results.length} gates FAILED` : `\nall ${results.length} gates green`);
process.exit(failed ? 1 : 0);
