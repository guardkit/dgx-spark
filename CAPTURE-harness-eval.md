# Harness Eval — Video Capture Spine

**Spine:** *"The harness can 3× the model" is a claim everyone repeats and nobody measures. So we measure it: same local DeepSeek, five gated tasks, three harness tiers, one pass-rate table — on my desk.*

**What this films:** the successor to the orbit-globe demo capture (now [superseded](./CAPTURE-orbit-globe-demo.md); the globe survives as eval task **T4**). Instead of demoing one artifact — a genre the field has now thoroughly filmed — this video runs a **private eval**: the same DeepSeek-V4-Flash-0731 on the Spark pair, driven through the same tasks under three escalating harnesses, scored by the same mechanical validators, ending in a number.

**The claim under test (the genre supplies it):** the "Best Open Model You Can Actually Run" video ([youtube](https://www.youtube.com/watch?v=_Ae4osPymXY) · local transcript/insights doc) states it plainly — DeepSweep jumped 7%→54% *under DeepSeek's own harness*; OpenAI's ARC-AGI harness study went 13%→40% on the same model; *"it's not just about the model, it's all about the harness around it."* It also — generously, this is not a dunk — ends on the genre's tell: a beautiful one-shot ISS tracker with the ISS **visibly in the wrong place** and a shrug ("I don't think that's right… we can tweak the API call"). Stated, never measured; rendered, never checked. This video does the measuring and the checking.

**Predecessors (must be green before recording):**
1. [`RUNBOOK-deepseek-v4-flash-0731-two-spark.md`](./RUNBOOK-deepseek-v4-flash-0731-two-spark.md) fully green — **including the tool-calling gate (Phase 5.6)**. H2/H3 are nothing but tool calls.
2. The five task workspaces are **built** under [`demo/harness-eval/`](./demo/harness-eval/) — **its README is the operating manual** (pi-from-zero primer, `cell.sh`/`score.sh` per-cell commands, one-time setup incl. the T1/T5 validator selftests and the T2/T3/T4 `npm run setup`).
3. Pre-flight below done once, off camera.

**How to use this:** a capture spine, not a script. Prompts to say, not lines. Don't hide failures — a FAIL cell is a *data point*, not a blooper.

---

## The experiment (the content is a table, not an artifact)

**Held constant:** DeepSeek-V4-Flash-0731 on the two-Spark seat (`:8888`), same sampling settings, same task briefs.

| Tier | Harness | What it is |
|---|---|---|
| **H1** | Mega-prompt one-shot | One `/v1/chat/completions` call, the full brief pasted in, the response saved verbatim. No tools, no iteration. *This is what the genre films.* |
| **H2** | Bare agent | pi with tools in an **empty** workspace — the same brief as the prompt; no AGENTS.md, no skills, no validator instruction. The agent can act but has no environment. |
| **H3** | Full environment | AGENTS.md conventions + domain skills + the gate suite + a one-line prompt; the agent is instructed to iterate until the gates are green. |

**Scoring:** every cell is scored by the **same validator, operator-run, after the fact** — the agent's own claims count for nothing. Score per cell = gates green / total gates; a cell **passes** only all-green. 5 tasks × 3 tiers = 15 cells. The result graphic is the pass-rate per tier.

**Fairness rules (what makes this an eval, not a rigged demo — say them on camera):**
- **Every tier gets the identical brief**, including the full acceptance checklist *and the testability contract* (e.g. `window.__orbitGlobe`). H1/H2 are never failed for not knowing a requirement only H3 was told.
- What H1/H2 lack is **not information about the task** — it's the conventions, the domain skills, the tools/iteration loop, and a runnable gate suite. That *is* the harness. That's the variable.
- **n=1 per cell on camera** — say so plainly: "this is a vibe-check of the harness effect on my tasks, not a paper." Optional insurance: re-run the grid ×3 overnight (it's free — that's the E6 point) and pin the aggregate in a comment.
- T5 under H1 fails **by construction** (a one-shot cannot touch a filesystem). Don't hide it — it's the finding: *some work cannot exist without an agentic harness*, the same shape as "two boxes don't make the model faster, they make it exist."

---

## The eval tasks

| ID | Task | The gate asks… | Oracle | Status |
|---|---|---|---|---|
| **T1** | **Golden extraction** — mixed-format server log → strict normalized JSON ([`t1`](./demo/harness-eval/t1-golden-extract/)) | …does the output canonically match the golden fixture? | Golden files | **built** (selftested) |
| **T2** | **Chess board** — single-file, fully self-contained, real rules ([`t2`](./demo/harness-eval/t2-chess-stockfish/)) | …does its move generator agree with Stockfish perft-1 across 8 positions (castling, pins, ep, promotion, mate/stalemate)? | A real engine | **built** |
| **T3** | **Next-bus board** — live TfL departure board, configurable stop ([`t3`](./demo/harness-eval/t3-next-bus/)) | …do the shown rows match an independent fetch (≥60% within 2 min), and does a blocked API produce an honest visible state? | Live transit API (+ the human close: stand at the stop) | **built** |
| **T4** | **Constellation globe** — whole-sky live satellite cloud, ISS highlighted ([`demo/orbit-globe/`](./demo/orbit-globe/)) | …is the ISS *actually there*? | Independent SGP4 + live wheretheiss.at | **built** |
| **T5** | **Tool-effects** — reorganize a file tree per dated/categorized rules + manifest ([`t5`](./demo/harness-eval/t5-tool-effects/)) | …is the filesystem actually in the specified state (hashes, placements, mtime decoys not taken)? Nothing the model *says* counts. | Re-scan of reality (Phase 5.6 generalized) | **built** (selftested) |

Design rule for new tasks: every gate must consult something **outside the generated code** — fixtures, an engine, a live API, the filesystem, the sky. Self-consistent-but-wrong must be catchable.

---

## Mental model (say a version on camera)

| Actor | Where | Role |
|---|---|---|
| **You** | MacBook keyboard | Fire each cell; run every scoring pass yourself |
| **pi** (H2/H3) | A process on the MacBook | Hands + loop only — every decision comes back from the model |
| **DeepSeek-V4-Flash-0731** | The two Sparks, `:8888` | The brain — *identical in every cell; only the harness changes* |
| **The validators** | Each task workspace | Dumb scripts: PASS/FAIL table, exit 0/1 — identical behaviour whoever invokes them |

---

## Pre-flight (once, off camera) &nbsp;·&nbsp; **Gate: wiring proven, validators smoke-tested**

```bash
# MacBook (as the orbit-globe README): node >= 22.19, pi >= 0.83.0, models.json block pasted.
curl -s http://promaxgb10-41b1:8888/v1/models          # DeepSeek-V4-Flash-0731 answers
# Wiring dry run (NOT recorded): the T4 warm-up variant (classic single-ISS tracker) under H3
# — proves tool calls, skills loading, and the validator on this exact stack. Then delete its
# index.html. (On camera the classic tracker appears ONLY as the E1 foil.)
# Full setup + per-cell commands + the pi primer: demo/harness-eval/README.md
#   (cell.sh prepares each cell per tier; score.sh is the operator's scoring run;
#    T1/T5 validator selftests are instant; T2/T3/T4 need `npm run setup` once.)
# T3: confirm the transit API answers for the chosen stop TODAY — the one oracle with opening hours.
```

- OBS scenes: (a) MacBook terminal, font ≥ 18pt; (b) browser for artifacts; (c) the grid graphic (a markdown table filling up is fine); (d) LiteLLM spend dashboard for E6.
- Terminal history cleared; workspaces contain only committed files.

---

## Capture phases

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **E1 The foil** | Run H1 on the *classic* single-ISS tracker — mega-prompt, one call, open the pretty globe. Then run the T4-class validator against it | Generous name-check of the genre ("the model deserves the hype"). Then: "beautiful. Now let's ask the sky." Watch the physics-oracle FAIL land. "That's the difference between a demo and engineering: **who checks?**" Delete it. | The foil built AND mechanically failed on camera |
| **E2 The claim** | The two quotes + ARC-AGI 13→40 on screen; the empty 5×3 grid | "Harness effects are stated everywhere and measured nowhere you can see. Companies keep private evals for exactly this. So: my tasks, my gates, my desk." | Claim + experiment design stated |
| **E3 The tiers** | The H1/H2/H3 table + fairness rules | Walk the tiers; land the fairness beat: "every tier gets the same brief — H1 fails on *capability*, never on a secret requirement." | Tiers + fairness on camera |
| **E4 The grid runs** | Montage of cells; **live centerpieces:** T4 under H1 vs H3 (watch H3 read the skills, run the validator itself, iterate a FAIL to green), and T5 under H1 (the by-construction fail) | Narrate lightly. Honest numbers on tok/s if asked-by-camera. If an H3 cell fails: **leave it in** — a harness ceiling is a finding. If first-pass green: say so ("the loop was armed; it didn't need it"). | ≥2 cells live incl. one iterate-to-green (or honest first-pass); rest summarized honestly |
| **E5 The table** | The filled grid; pass-rate per tier | Read the number: "on my five tasks, the harness was worth ×N — n=1, my gates, your mileage. That's the point: **build your own**." | The measured table shown; n=1 honesty said |
| **E6 The economics** | LiteLLM spend dashboard: the grid's token volume + per-key spend | The honest econ claim (see production notes): "the grid cost ~£0 marginal and I can re-run it every night forever — against a frontier API this token volume is real money. Private evals are exactly the workload a local workhorse makes free. And nothing left the building." | Spend receipt on camera; claim stays within the honesty rules |
| **E7 Dessert** | T4's H3 artifact full-screen: constellation, time-warp, orbit-on-click, live ISS readout | "The gates prove it's *correct* — whether it's *beautiful* stays a human call." | Hero shots captured |

---

## Failure triage (during recording — keep rolling)

| Symptom | Meaning | Move |
|---|---|---|
| pi 400s immediately | `developer` role / `reasoning_effort` rejected | compat flags in `~/.pi/agent/models.json` (orbit-globe README block) — 10-second on-camera fix |
| Raw `<…DSML…>` in responses | Spec-decode draft-rejection bug | Phase 5.6 wasn't green — stop; compat proxy or reduce spec tokens; re-record later |
| T4 live-oracle fails, SGP4 oracle passes | Sim drift or wheretheiss.at hiccup | Reload (boots at 1×), re-run; if persistent, lean on SGP4 and say so |
| T3 transit API down / stop dark | The one oracle with opening hours | Skip the T3 column on camera, say so, fill it in the pinned comment |
| Agent claims green, operator run fails | The exact failure the operator-scoring rule exists for | **Keep it in** — worth more than any clean take |
| A whole tier goes 0/5 or 5/5 | The tasks are mis-calibrated, not the harness measured | Say it straight; recalibrate task difficulty off camera; re-run the grid — don't ship a degenerate table |
| Everything green everywhere, no drama | It happens | Don't fake a failure; the E1 foil already carries the fail beat |

---

## Production notes

- **The honest-economics rule (load-bearing):** do **NOT** claim "cheaper than the DeepSeek API" — at ~$0.02/M in / ~$0.30/M out their API is at the cost Pareto frontier and would likely beat your electricity. The defensible claims: *unlimited iteration* (re-run the grid nightly, free), *privacy* (tasks and outputs never leave the LAN), and the *frontier-API counterfactual* (the same token volume through an Opus-class API is real money). Keep E6 inside those.
- **Do NOT quote leaderboard comparisons** — unchanged from the other capture docs. This video's only number is one you measured.
- **Stay generous to the foil video** — it's the audience feeder, not the villain. The critique is of the *genre's missing receipt*, and it names its own caveat ("not apples-to-apples") — we're finishing its thought, not correcting it.
- **Edit out**: installs, long silent generation (jump-cut + tok/s overlay), the 13 cells not filmed live.
- **Evidence for the description/pinned comment**: the filled grid, every cell's validator output (commit under `demo/harness-eval/results/<date>/`), the identical brief given to all tiers, and the overnight ×3 aggregate if run.
- **Relationship to the other videos**: the two-Spark material owns "capacity, not speed worth stacking for"; this owns "harness, not model" — each video one falsifiable claim, one measured number. [`VIDEO-executable-runbooks.md`](./VIDEO-executable-runbooks.md) owns the gates philosophy this applies.
