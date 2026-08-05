#!/usr/bin/env node
// H1 tier: the mega-prompt one-shot, exactly as the genre does it — one chat completion,
// the whole brief in the prompt, the reply saved verbatim as the artifact.
// Usage: node lib/h1-oneshot.mjs <run-dir> <deliverable>   (env: EVAL_URL, EVAL_MODEL)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const [runDir, deliverable] = process.argv.slice(2);
if (!runDir || !deliverable) { console.error("usage: h1-oneshot.mjs <run-dir> <deliverable>"); process.exit(1); }

const URL_ = process.env.EVAL_URL ?? "http://promaxgb10-41b1:8888/v1/chat/completions";
const MODEL = process.env.EVAL_MODEL ?? "DeepSeek-V4-Flash-0731";

let prompt = readFileSync(join(runDir, "TASK.md"), "utf8");
for (const extra of ["input/server.log", "config.json"])
  if (existsSync(join(runDir, extra)))
    prompt += `\n\n--- ${extra} (provided verbatim) ---\n\n${readFileSync(join(runDir, extra), "utf8")}`;
prompt += `\n\n--- one-shot instruction ---\nReply with ONLY the complete contents of \`${deliverable}\` — no commentary, no markdown fences.`;

writeFileSync(join(runDir, "prompt.txt"), prompt);
console.log(`H1 one-shot -> ${MODEL} @ ${URL_} (${prompt.length} chars)…`);

const res = await fetch(URL_, {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: "Bearer dummy" },
  body: JSON.stringify({ model: MODEL, messages: [{ role: "user", content: prompt }], max_tokens: 16384, temperature: 0 }),
  signal: AbortSignal.timeout(1_800_000),
});
if (!res.ok) { console.error(`endpoint ${res.status}: ${(await res.text()).slice(0, 300)}`); process.exit(1); }
const body = await res.json();
writeFileSync(join(runDir, "raw-response.json"), JSON.stringify(body, null, 2));

let out = body.choices?.[0]?.message?.content ?? "";
out = out.replace(/^\s*```[a-z]*\s*\n/i, "").replace(/\n```\s*$/i, "").trim() + "\n"; // fences despite instruction: the genre's reality
writeFileSync(join(runDir, deliverable), out);
console.log(`saved ${deliverable} (${out.length} bytes) + prompt.txt + raw-response.json`);
