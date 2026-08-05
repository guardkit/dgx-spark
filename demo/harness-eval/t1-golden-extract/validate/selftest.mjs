#!/usr/bin/env node
// Validator self-test: the golden fixture itself, presented as an artifact, must go all-green;
// a mutated copy must FAIL. Proves the gates test what we think they test.
import { mkdtempSync, writeFileSync, readFileSync, cpSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const golden = readFileSync(join(here, "golden", "expected.json"), "utf8");
const run = (dir) => spawnSync("node", [join(here, "validate.mjs"), dir], { encoding: "utf8" });

const good = mkdtempSync(join(tmpdir(), "t1-good-"));
writeFileSync(join(good, "extract.json"), golden);
const g = run(good);
if (g.status !== 0) { console.error("SELFTEST FAIL: golden-as-artifact did not pass:\n" + g.stdout); process.exit(1); }

const bad = mkdtempSync(join(tmpdir(), "t1-bad-"));
const mutated = JSON.parse(golden); mutated[3].level = "ERROR"; // FATAL -> ERROR must be caught
writeFileSync(join(bad, "extract.json"), JSON.stringify(mutated));
const b = run(bad);
if (b.status === 0) { console.error("SELFTEST FAIL: mutated artifact passed"); process.exit(1); }

console.log("selftest green: golden passes, mutation fails");
