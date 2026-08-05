#!/usr/bin/env node
// T2 gates: the artifact's move generator cross-examined by Stockfish.
// Usage: node validate.mjs [target-dir]   (default: the workspace root above this script)
import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(process.argv[2] ?? join(here, ".."));
const ART = join(target, "index.html");
const POSITIONS = JSON.parse(readFileSync(join(here, "positions.json"), "utf8"));

// ---------- Stockfish oracle ----------
async function startEngine() {
  const mod = await import("stockfish");
  const engine = mod.default();
  const lines = [];
  let waiter = null;
  engine.onmessage = (msg) => {
    const line = typeof msg === "string" ? msg : msg?.data ?? "";
    lines.push(line);
    if (waiter && waiter.test(line)) waiter.resolve();
  };
  const send = (cmd, doneRe, timeoutMs = 15000) =>
    new Promise((res, rej) => {
      const t = setTimeout(() => { waiter = null; rej(new Error(`stockfish timeout on "${cmd}"`)); }, timeoutMs);
      waiter = { test: (l) => doneRe.test(l), resolve: () => { clearTimeout(t); waiter = null; res(); } };
      engine.postMessage(cmd);
    });
  await send("uci", /^uciok/);
  await send("isready", /^readyok/);
  return {
    lines,
    send,
    async perft1(fen) {
      lines.length = 0;
      engine.postMessage(`position fen ${fen}`);
      await send("go perft 1", /Nodes searched/i);
      return lines
        .map((l) => l.match(/^([a-h][1-8][a-h][1-8][qrbn]?)\s*:\s*1\b/))
        .filter(Boolean)
        .map((m) => m[1].toLowerCase())
        .sort();
    },
    async fenAfter(moves) {
      lines.length = 0;
      engine.postMessage(`position startpos moves ${moves.join(" ")}`);
      await send("d", /^Fen:/i);
      const l = lines.find((x) => /^Fen:/i.test(x));
      return l.replace(/^Fen:\s*/i, "").trim();
    },
    quit() { try { engine.postMessage("quit"); } catch { /* wasm teardown */ } },
  };
}

// ---------- gates ----------
const results = [];
const gate = async (id, fn) => {
  try { const d = await fn(); results.push([id, "PASS", d ?? ""]); }
  catch (e) { results.push([id, "FAIL", e.message]); }
};

await gate("C1.static", () => {
  if (!existsSync(ART)) throw new Error("index.html missing");
  const html = readFileSync(ART, "utf8");
  const ext = html.match(/\b(?:src|href)\s*=\s*["']https?:\/\/[^"']+["']/gi);
  if (ext) throw new Error(`external reference(s): ${ext[0]}…`);
  return "single file, no external refs";
});

let browser, page;
const consoleErrors = [];
await gate("C2.contract", async () => {
  browser = await chromium.launch();
  page = await browser.newPage();
  await page.route(/^https?:\/\//, (r) => r.abort()); // offline-clean is part of the spec
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(m.text()));
  page.on("pageerror", (e) => consoleErrors.push(String(e)));
  await page.goto(pathToFileURL(ART).href, { waitUntil: "load" });
  await page.waitForTimeout(500);
  const shape = await page.evaluate(() =>
    ["load", "fen", "legalMoves", "move", "status"].map((k) => typeof window.__chess?.[k])
  );
  if (shape.some((t) => t !== "function"))
    throw new Error(`window.__chess incomplete: [${shape.join(", ")}]`);
});

const engine = page ? await startEngine() : null;
for (const p of POSITIONS) {
  await gate(`C3.movegen.${p.id}`, async () => {
    if (!page || !engine) throw new Error("skipped: C2 failed");
    const appMoves = await page.evaluate((fen) => {
      if (!window.__chess.load(fen)) return { err: "load() returned false" };
      return { moves: window.__chess.legalMoves().map((m) => m.toLowerCase()).sort() };
    }, p.fen);
    if (appMoves.err) throw new Error(appMoves.err);
    const oracle = await engine.perft1(p.fen);
    const app = appMoves.moves;
    if (JSON.stringify(app) !== JSON.stringify(oracle)) {
      const missing = oracle.filter((m) => !app.includes(m));
      const extra = app.filter((m) => !oracle.includes(m));
      throw new Error(
        `${app.length} vs oracle ${oracle.length}` +
        (missing.length ? `; missing: ${missing.slice(0, 4).join(",")}` : "") +
        (extra.length ? `; illegal: ${extra.slice(0, 4).join(",")}` : "")
      );
    }
    return `${oracle.length} moves agree`;
  });
  if (p.expectStatus)
    await gate(`C4.status.${p.id}`, async () => {
      if (!page) throw new Error("skipped: C2 failed");
      const s = await page.evaluate((fen) => {
        window.__chess.load(fen);
        return window.__chess.status();
      }, p.fen);
      if (s !== p.expectStatus) throw new Error(`status "${s}", expected "${p.expectStatus}"`);
    });
}

await gate("C5.fen-after-moves", async () => {
  if (!page || !engine) throw new Error("skipped: C2 failed");
  const seq = ["e2e4", "c7c5", "g1f3", "d7d6", "f1b5", "c8d7", "e1g1"]; // incl. castling
  const appFen = await page.evaluate((moves) => {
    window.__chess.load("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    for (const m of moves) if (!window.__chess.move(m)) return { err: `move(${m}) refused` };
    return { fen: window.__chess.fen() };
  }, seq);
  if (appFen.err) throw new Error(appFen.err);
  const oracle = await engine.fenAfter(seq);
  if (appFen.fen.trim() !== oracle) throw new Error(`got "${appFen.fen}", oracle "${oracle}"`);
  return "exact FEN match incl. counters";
});

await gate("C6.console-clean", async () => {
  if (!page) throw new Error("skipped: C2 failed");
  if (consoleErrors.length) throw new Error(`${consoleErrors.length} console error(s): ${consoleErrors[0]}`);
});

engine?.quit();
await browser?.close();

const w = Math.max(...results.map(([id]) => id.length));
for (const [id, verdict, detail] of results)
  console.log(`${id.padEnd(w)}  ${verdict}${detail ? `  ${detail}` : ""}`);
const failed = results.filter(([, v]) => v === "FAIL").length;
console.log(failed ? `\n${failed}/${results.length} gates FAILED` : `\nall ${results.length} gates green`);
process.exit(failed ? 1 : 0);
