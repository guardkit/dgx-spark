# Orbit Globe — demo workspace for the two-Spark DeepSeek-V4-Flash-0731 strategist

A standalone agent workspace (no relation to any other project's tooling): `AGENTS.md`
conventions + two `SKILL.md`-standard skills + a task brief. Point a coding harness on the
MacBook at the Sparks' endpoint, open this folder, give the one-line prompt in `TASK.md`.

The `.agents/skills/` path is deliberately the portable one — **both pi and opencode read
it** (pi also reads `.pi/skills/`; opencode also reads `.opencode/skills/` and
`.claude/skills/`).

## Prerequisite: the endpoint must serve TOOL CALLS

A coding harness lives on function calling. The base NVFP4-KV recipe does **not** enable
vLLM's tool-call machinery — the strategist runbook's tool-calling phase
(`RUNBOOK-deepseek-v4-flash-0731-strategist.md`, Phase 3/5) adds the forum-endorsed 0731
flags (`--tool-call-parser deepseek_v4 --reasoning-parser deepseek_v4
--enable-auto-tool-choice --tokenizer-mode hf` + mounted chat template) and gates that a
live `tools=` request returns a parsed `tool_calls` array — **with speculative decoding
on** (DSpark has a documented draft-rejection bug that can shred tool-call opener tags;
the gate exists to catch it, and 0rand's `opencode_compat_proxy` is the fallback shim).
Run that phase green before pointing any harness at the box.

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

## Recording notes

- Route through the LiteLLM `:4000` strategist alias instead of `:8888` when you want the
  no-cloud-gate story in frame; LiteLLM stays up during the DeepSeek window (it's a router).
- Expect ~55–67 tok/s decode; narrative prose ~34 — the constellation app is mostly code,
  which runs at the fast end. Warm the server (5 long generations) before the take.
- Dry-run the warm-up variant end-to-end once, off camera, before the real take.
