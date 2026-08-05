# Orbit Globe — demo workspace for the two-Spark DeepSeek-V4-Flash-0731 seat

> Recording this as a video? The capture spine — the two-take story, say-lines, failure
> triage — is [`CAPTURE-orbit-globe-demo.md`](../../CAPTURE-orbit-globe-demo.md).
> `foil-prompt.txt` in this folder is Take 1's pasted one-shot brief (same information as
> this workspace carries — the fairness beat).

A standalone agent workspace (no relation to any other project's tooling): `AGENTS.md`
conventions + two `SKILL.md`-standard skills + a task brief. Point a coding harness on the
MacBook at the Sparks' endpoint, open this folder, give the one-line prompt in `TASK.md`.

The `.agents/skills/` path is deliberately the portable one — **both pi and opencode read
it** (pi also reads `.pi/skills/`; opencode also reads `.opencode/skills/` and
`.claude/skills/`).

## Prerequisite: the endpoint must serve TOOL CALLS

A coding harness lives on function calling. The base NVFP4-KV recipe does **not** enable
vLLM's tool-call machinery — the two-Spark runbook's tool-calling phase
(`RUNBOOK-deepseek-v4-flash-0731-two-spark.md`, Phase 3/5) adds the **native** path
(`--tokenizer-mode deepseek_v4 --tool-call-parser deepseek_v4 --reasoning-parser
deepseek_v4 --enable-auto-tool-choice` + the model card's official encoding package via
`DSPARK_ENCODING_FILE`; the earlier hf-tokenizer + mounted-Jinja approach is **superseded**
— it broke tool JSON at high effort and destroyed prefix caching) and gates that live
`tools=` requests return parsed `tool_calls` arrays with non-empty follow-ups — **with
speculative decoding on** (DSpark has a documented draft-rejection bug that can shred
tool-call opener tags; the gate exists to catch it, and 0rand's `opencode_compat_proxy`
is the fallback shim). Run that phase green before pointing any harness at the box.

## Harness A (primary): pi

Install on the MacBook (Node ≥ 22.19):

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent   # v0.83.0+ — older builds had a custom-provider hang (#3168)
```

`~/.pi/agent/models.json` (hot-reloads on `/model` — no restart needed):

```json
{
  "providers": {
    "sparks": {
      "baseUrl": "http://promaxgb10-41b1:8888/v1",
      "api": "openai-completions",
      "apiKey": "dummy",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false,
        "maxTokensField": "max_tokens",
        "thinkingFormat": "chat-template",
        "chatTemplateKwargs": { "thinking": { "$var": "thinking.enabled" } }
      },
      "models": [
        {
          "id": "DeepSeek-V4-Flash-0731",
          "name": "DeepSeek V4 Flash (2x Spark)",
          "reasoning": true,
          "contextWindow": 163840,
          "maxTokens": 16384
        }
      ]
    }
  }
}
```

Notes: `id` must equal vLLM's `--served-model-name`; the two `supports*: false` flags are
the documented cure for vLLM rejecting `developer` role / `reasoning_effort`;
`thinkingFormat: "chat-template"` is pi's DeepSeek-behind-vLLM path (added in 0.79.9).
Run `pi` in this folder (TUI) — or `pi -p "<prompt>"` for a clean single-shot take.

## Harness B (backup): opencode

`opencode.json` already sits in this folder — `opencode` here picks it up. Known risk: the
AI-SDK streamed-tool-call path has a long issue trail against vLLM parsers; if tool calls
render as text instead of executing, that's the known failure — switch to pi or interpose
the compat proxy.

## Validating what it builds (the gates, not vibes)

Correctness is mechanical, three tiers, in [`validate/`](./validate/):

- **T1 static** — single file, HTTPS-only, no open-notify, approved CDNs only.
- **T2 runtime** — headless Chromium against the `window.__orbitGlobe` testability contract
  (required by AGENTS.md): catalog >1000 sats, boots at 1× real time, ISS actually moves,
  ≥30fps, zero console errors, and a second run with CelesTrak *blocked* must show a
  visible error state (never a blank globe).
- **T3 the physics oracle — the part the builder can't game**: the validator independently
  fetches fresh ISS elements and runs its **own** SGP4 propagation (tolerance 1.5°), then
  cross-checks against the **live** wheretheiss.at position (tolerance 3°, skew-guarded).
  The ISS is either where the sky says it is, or the gate fails.

One-time setup on the MacBook: `cd validate && npm run setup` (installs Playwright's
Chromium). Run: `npm run validate` — PASS/FAIL table, non-zero exit on any FAIL.

Two-tier use in the demo: the **agent self-runs it and iterates to green** (that's the
arc on camera), then the operator runs it once more as the independent close — same suite,
but the T3 oracle answers to the sky, not to the code that was just written. Judgment
calls the gates can't cover (does it *look* right, is the highlight legible in frame)
stay human, on camera, deliberately.

## Recording notes

- Route through the LiteLLM `:4000` `deepseek` alias instead of `:8888` when you want the
  no-cloud-gate story in frame; LiteLLM stays up during the DeepSeek window (it's a router).
- Expect ~55–67 tok/s decode; narrative prose ~34 — the constellation app is mostly code,
  which runs at the fast end. Warm the server (5 long generations) before the take.
- Dry-run the warm-up variant end-to-end once, off camera, before the real take.
