#!/usr/bin/env node
// Recreate the pristine work/ tree (contents AND mtimes) from the fixture spec.
// Usage: node setup.mjs [target-dir]   (default: the workspace root above this script)
import { mkdirSync, writeFileSync, rmSync, utimesSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { FILES, EMPTY_DIRS } from "./fixtures.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(process.argv[2] ?? join(here, ".."));

rmSync(join(target, "work"), { recursive: true, force: true });
rmSync(join(target, "manifest.json"), { force: true });
for (const f of FILES) {
  const p = join(target, f.path);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, f.content);
  const t = new Date(f.mtime);
  utimesSync(p, t, t);
}
for (const d of EMPTY_DIRS) mkdirSync(join(target, d), { recursive: true });
console.log(`pristine work/ recreated: ${FILES.length} files, ${EMPTY_DIRS.length} empty dir(s)`);
