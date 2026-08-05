# Harness Eval — workspaces, validators, and how to run every cell

The private eval behind [`CAPTURE-harness-eval.md`](../../CAPTURE-harness-eval.md) (the
recording-day spine — beats and say-lines live there; **this file is the operating
manual**). Five gated tasks × three harness tiers, same model, every cell scored by the
same operator-run validator:

| | Task | Oracle | Deliverable | Validator deps |
|---|---|---|---|---|
| **T1** | [`t1-golden-extract/`](./t1-golden-extract/) — messy log → strict JSON | golden fixture | `extract.json` | none |
| **T2** | [`t2-chess-stockfish/`](./t2-chess-stockfish/) — playable chess board | **Stockfish** (perft-1) | `index.html` | playwright + stockfish |
| **T3** | [`t3-next-bus/`](./t3-next-bus/) — live TfL departure board | the **live API** (independent fetch) | `index.html` | playwright |
| **T4** | [`../orbit-globe/`](../orbit-globe/) — constellation globe | independent SGP4 + **the sky** | `index.html` | playwright + satellite.js |
| **T5** | [`t5-tool-effects/`](./t5-tool-effects/) — reorganize a file tree | the **filesystem** re-scanned | end-state + `manifest.json` | none |

Tiers: **H1** mega-prompt one-shot (no tools) · **H2** bare agent (pi, tools, empty
environment) · **H3** full environment (AGENTS.md + skills + validator, one-line prompt).
Fairness rules and honesty rules are in the capture spine — read them before filming.

---

## pi from zero (you have never used it — start here)

**What pi is:** a terminal coding agent, like Claude Code, except you point it at *your
own* OpenAI-compatible endpoint — here, DeepSeek on the Spark pair. You run `pi` inside a
folder; you type a request; the model replies with tool calls (write file, run command);
pi executes them **in that folder** and loops until the model stops. That loop is the
"harness" this eval measures.

**Install (MacBook, once):**

```bash
node --version    # need >= 22.19
npm install -g --ignore-scripts @earendil-works/pi-coding-agent   # pi >= 0.83.0
```

**Point it at the Sparks (once):** create/merge `~/.pi/agent/models.json` — the exact
block lives in [`../orbit-globe/README.md`](../orbit-globe/README.md) § *Harness A: pi*
(provider `sparks`, model id `DeepSeek-V4-Flash-0731`, plus two `supports*: false` compat
flags that stop vLLM 400s). It hot-reloads — no restart needed.

**Driving it (all you actually need):**

- `cd <the run folder>` then `pi` — opens the TUI session **scoped to that folder**.
- Type the prompt (exact prompts below), press enter, watch. Everything it writes lands in
  the folder you launched from — which is why every cell gets its own `runs/` directory.
- `/model` switches model if the wrong one is selected (pick *DeepSeek V4 Flash (2x Spark)*).
- When it stops and summarizes, it's done. Interrupt with `Esc`; quit with `Ctrl+C` (twice)
  or `/exit`. Nothing you do in the TUI affects scoring — scoring is `./score.sh`, run by
  you, afterwards.
- Non-interactive alternative: `pi -p "<prompt>"` runs one request headless — handy for
  re-runs, but for filming use the TUI (the loop is the footage).

**Prerequisite that beats everything:** the endpoint must serve **tool calls** —
`RUNBOOK-deepseek-v4-flash-0731-two-spark.md` green **including Phase 5.6**. A coding
agent against an endpoint that shreds tool calls produces `<…DSML…>` soup, and no harness
tier can save it.

---

## One-time setup (before any cell)

```bash
cd demo/harness-eval
# validator selftests (no deps, instant — proves the gates test what we think):
( cd t1-golden-extract/validate && npm run selftest )
( cd t5-tool-effects/validate  && npm run selftest )
# heavier validators (downloads Chromium once each + Stockfish for T2):
( cd t2-chess-stockfish/validate && npm run setup )
( cd t3-next-bus/validate        && npm run setup )
( cd ../orbit-globe/validate     && npm run setup )   # T4
# endpoint answers?
curl -s http://promaxgb10-41b1:8888/v1/models
```

T3 only: check the stop in [`t3-next-bus/config.json`](./t3-next-bus/config.json) has
arrivals *today* (`curl -s "https://api.tfl.gov.uk/StopPoint/490000173RC/Arrivals" | head -c 300`)
— it's the one oracle with opening hours; swap in any TfL stop id you like (find one via
`https://api.tfl.gov.uk/StopPoint/Search/<name>?modes=bus`).

---

## Running the grid — exact commands

Every cell: **prepare** with `./cell.sh`, (for H2/H3) **drive** with pi, **score** with
`./score.sh`. The prompts are fixed — use them verbatim so tiers differ only by harness:

| Tier | Prepare | Then | Prompt (verbatim) |
|---|---|---|---|
| H1 | `./cell.sh t1 h1` | nothing — the call runs and saves the artifact | *(assembled automatically: TASK.md + inputs + "reply with only the file")* |
| H2 | `./cell.sh t1 h2` | `cd runs/t1-h2 && pi` | `Complete the task described in TASK.md.` |
| H3 | `./cell.sh t1 h3` | `cd runs/t1-h3 && pi` | `Do the task in TASK.md — follow the workspace conventions.` |

Then score from `demo/harness-eval/`: `./score.sh t1 h2` etc. Same shape for `t2`, `t3`,
`t4`, `t5`. The full grid, in a sensible filming order:

```bash
# the foil + centerpiece first (T4), then the quick tasks
for t in t4 t1 t2 t3 t5; do for h in h1 h2 h3; do ./cell.sh $t $h; done; done   # h2/h3 pause for you to drive pi
```

Notes per task:
- **T5/H1** is the by-construction fail — `cell.sh` stages it with a NOTE; just score it.
- **T5** cells: the fixtures (fixed contents *and mtimes*) are staged into the run dir
  automatically; if an agent mangles it mid-take, `./cell.sh t5 h2 --force` restages.
- **T4** H2/H3 runs take the longest (a real build); budget accordingly. H1 is minutes.
- Between H2/H3 cells, pi keeps per-folder sessions — each run dir is fresh, so no
  cross-contamination; don't reuse a run dir without `--force`.

**Scoring is the receipt:** run `./score.sh <task> <tier>` yourself, on camera for the
live cells. Record each PASS/FAIL table into `results/<date>/` and fill
[`results/GRID-template.md`](./results/GRID-template.md). The agent saying "all gates
green" is not a score.

---

## Troubleshooting

| Symptom | Meaning | Move |
|---|---|---|
| pi errors 400 immediately | `developer` role / `reasoning_effort` sent | the two `supports*: false` compat flags in `models.json` (orbit-globe README block) |
| Tool calls appear as `<…DSML…>` text | endpoint tool-parsing not green | back to the DeepSeek runbook Phase 5.6 — do not film |
| `cell.sh … exists` | protecting a finished run | `--force` only if you mean to discard it |
| T3 oracle FAIL at night | quiet-hours stop | different stop in `config.json`, or note-and-skip per the spine |
| T2 validator hangs on first run | Stockfish wasm cold start | re-run once; `npm run setup` done? |
| H1 artifact is prose, not the file | model ignored the reply-only instruction | that's a legitimate H1 data point — score it as-is |
