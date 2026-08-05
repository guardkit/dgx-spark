#!/usr/bin/env node
// T5 gates: only the filesystem end-state counts. Pure node, no deps.
// Usage: node validate.mjs [target-dir]   (default: the workspace root above this script)
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { FILES } from "./fixtures.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(process.argv[2] ?? join(here, ".."));
const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const shaStr = (s) => createHash("sha256").update(s).digest("hex");

const walk = (dir, out = { files: [], dirs: [] }) => {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) { out.dirs.push(p); walk(p, out); } else out.files.push(p);
  }
  return out;
};

const results = [];
const gate = (id, fn) => {
  try { const d = fn(); results.push([id, "PASS", d ?? ""]); }
  catch (e) { results.push([id, "FAIL", e.message]); }
};

const WORK = join(target, "work");
let tree = null;

gate("E1.structure", () => {
  if (!existsSync(WORK)) throw new Error("work/ missing (run `npm run reset` then the task)");
  const top = readdirSync(WORK);
  if (top.length !== 1 || top[0] !== "organized")
    throw new Error(`work/ must contain only organized/ — found: ${top.join(", ")}`);
  tree = walk(WORK);
  for (const d of tree.dirs)
    if (readdirSync(d).length === 0) throw new Error(`empty directory left: ${relative(target, d)}`);
  for (const f of tree.files) {
    const rel = relative(target, f).split("\\").join("/");
    if (!/^work\/organized\/\d{4}\/\d{2}\/(docs|images|data|other)\/[^/]+$/.test(rel))
      throw new Error(`unexpected layout: ${rel}`);
  }
  return `${tree.files.length} files under organized/`;
});

gate("E2.nothing-lost", () => {
  if (!tree) throw new Error("skipped: E1 failed");
  const want = FILES.map((f) => shaStr(f.content)).sort();
  const have = tree.files.map(sha).sort();
  if (JSON.stringify(want) !== JSON.stringify(have)) {
    const missing = want.filter((h) => !have.includes(h)).length;
    const extra = have.filter((h) => !want.includes(h)).length;
    throw new Error(`content mismatch: ${missing} original file(s) missing/altered, ${extra} unexpected`);
  }
  return "every original byte-identical, nothing extra";
});

gate("E3.placement", () => {
  if (!tree) throw new Error("skipped: E1 failed");
  const misses = [];
  for (const f of FILES) {
    const p = join(target, f.expected);
    if (!existsSync(p)) { misses.push(`${f.expected} (expected home of ${f.path})`); continue; }
    if (sha(p) !== shaStr(f.content)) misses.push(`${f.expected} exists but holds the wrong file`);
  }
  if (misses.length) throw new Error(`${misses.length} misplaced — first: ${misses[0]}`);
  return "all files in their rule-derived homes (mtime decoys not taken)";
});

gate("E4.manifest", () => {
  const mPath = join(target, "manifest.json");
  const manifest = JSON.parse(readFileSync(mPath, "utf8"));
  if (!Array.isArray(manifest)) throw new Error("manifest.json is not an array");
  if (manifest.length !== FILES.length)
    throw new Error(`${manifest.length} entries, expected ${FILES.length}`);
  for (let i = 1; i < manifest.length; i++)
    if (manifest[i].newPath < manifest[i - 1].newPath) throw new Error(`not sorted by newPath at ${i}`);
  const byExpected = new Map(FILES.map((f) => [f.expected, f]));
  for (const [i, e] of manifest.entries()) {
    for (const k of ["originalPath", "newPath", "sizeBytes", "sha256"])
      if (e[k] === undefined) throw new Error(`entry ${i}: missing "${k}"`);
    const spec = byExpected.get(e.newPath);
    if (!spec) throw new Error(`entry ${i}: newPath "${e.newPath}" is not a correct destination`);
    if (e.originalPath !== spec.path)
      throw new Error(`entry ${i}: originalPath "${e.originalPath}", expected "${spec.path}"`);
    const p = join(target, e.newPath);
    if (!existsSync(p)) throw new Error(`entry ${i}: newPath does not exist on disk`);
    if (statSync(p).size !== e.sizeBytes) throw new Error(`entry ${i}: sizeBytes wrong`);
    if (sha(p) !== e.sha256) throw new Error(`entry ${i}: sha256 wrong`);
  }
  return "manifest accurate for every entry";
});

const w = Math.max(...results.map(([id]) => id.length));
for (const [id, verdict, detail] of results)
  console.log(`${id.padEnd(w)}  ${verdict}${detail ? `  ${detail}` : ""}`);
const failed = results.filter(([, v]) => v === "FAIL").length;
console.log(failed ? `\n${failed}/${results.length} gates FAILED` : `\nall ${results.length} gates green`);
process.exit(failed ? 1 : 0);
