#!/usr/bin/env node
// Validator self-test: setup a temp workspace, apply the reference solution (straight from
// the fixture spec's hand-derived `expected` paths), expect all-green; then mutate and
// expect FAIL. Proves setup + gates agree before any model is scored against them.
import { mkdtempSync, mkdirSync, renameSync, rmSync, writeFileSync, readdirSync, statSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { FILES } from "./fixtures.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const run = (script, dir) => spawnSync("node", [join(here, script), dir], { encoding: "utf8" });

const ws = mkdtempSync(join(tmpdir(), "t5-self-"));
if (run("setup.mjs", ws).status !== 0) { console.error("SELFTEST FAIL: setup errored"); process.exit(1); }

// reference solution
for (const f of FILES) {
  mkdirSync(join(ws, dirname(f.expected)), { recursive: true });
  renameSync(join(ws, f.path), join(ws, f.expected));
}
const prune = (dir) => {
  for (const e of readdirSync(dir, { withFileTypes: true }))
    if (e.isDirectory()) prune(join(dir, e.name));
  if (readdirSync(dir).length === 0) rmSync(dir, { recursive: true });
};
for (const top of readdirSync(join(ws, "work"))) if (top !== "organized") prune(join(ws, "work", top));
const manifest = FILES.map((f) => ({
  originalPath: f.path,
  newPath: f.expected,
  sizeBytes: statSync(join(ws, f.expected)).size,
  sha256: createHash("sha256").update(readFileSync(join(ws, f.expected))).digest("hex"),
})).sort((a, b) => (a.newPath < b.newPath ? -1 : 1));
writeFileSync(join(ws, "manifest.json"), JSON.stringify(manifest, null, 2));

const good = run("validate.mjs", ws);
if (good.status !== 0) { console.error("SELFTEST FAIL: reference solution did not pass:\n" + good.stdout); process.exit(1); }

rmSync(join(ws, FILES[0].expected)); // mutate: lose a file
const bad = run("validate.mjs", ws);
if (bad.status === 0) { console.error("SELFTEST FAIL: mutated tree passed"); process.exit(1); }

console.log("selftest green: reference solution passes, mutation fails");
