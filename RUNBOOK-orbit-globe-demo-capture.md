# Orbit-Globe Demo — Video Capture Runbook

> **Status: SUPERSEDED (2026-08-05)** by [`RUNBOOK-harness-eval-capture.md`](./RUNBOOK-harness-eval-capture.md) — the one-artifact demo video is an occupied genre (the "Best Open Model You Can Actually Run" video one-shot the same ISS tracker on the same 2×GB10). The globe lives on as that eval's **task T4** (its visual centerpiece), and this spine's D1–D6 arc remains the long-form detail for filming T4's full-environment cell. Kept for reference; not the video plan.

**Spine:** *a frontier-class open model running on two desk boxes does real agentic work — a MacBook harness drives it to build a live satellite globe, it checks its own work against mechanical gates, and then I check it against the sky.*

**What this films:** the payoff segment for the two-Spark/DeepSeek material (or a standalone short). A coding agent on the MacBook, brained by DeepSeek-V4-Flash-0731 on the Spark pair, one-shots the [`demo/orbit-globe/`](./demo/orbit-globe/) task and iterates the gate suite to green; the operator closes with an independent validation run.

**Predecessors (must be green before recording):**
1. [`RUNBOOK-deepseek-v4-flash-0731-two-spark.md`](./RUNBOOK-deepseek-v4-flash-0731-two-spark.md) fully green — **including Phase 5.6 (tool-calling gate)**. A coding harness is nothing but tool calls; if 5.6 isn't green, there is no demo.
2. The demo workspace pulled on the MacBook (`git pull` in the dgx-spark clone).
3. The pre-flight below done **once, off camera**, ending with the warm-up-variant dry run.

**How to use this:** a capture spine, not a script. Prompts to say, not lines. Don't hide failures — the fail→fix loop is the content.

---

## The mental model (say a version of this on camera — it's what viewers get wrong)

Everything happens **on the MacBook, in one folder**. Four actors:

| Actor | Where | Role |
|---|---|---|
| **You** | MacBook keyboard | One prompt at the start; one independent `npm run validate` at the end |
| **pi** (the harness) | A process on the MacBook | Hands + loop only: sends context to the model, executes the tool calls that come back — every file write and shell command happens on the Mac |
| **DeepSeek-V4-Flash-0731** | The two Sparks, `:8888` over the LAN | The brain: every decision, every line of code, every "now run the validator" originates here |
| **`validate.mjs`** | The workspace | A dumb script: PASS/FAIL table, exit 0/1 — identical behaviour whoever invokes it |

**Act 1 — the agent's loop (you watch):** pi reads `AGENTS.md` + `TASK.md` + the two skills, writes `index.html`, then — because AGENTS.md instructs it to — runs `npm run validate` *itself* through its bash tool, reads the FAIL lines as feedback, edits, re-runs, until green. That loop is the watchable part.

**Act 2 — your close (you type):** in a **separate terminal, not pi**, run the same `npm run validate` yourself. The line to say: *"an agent's 'all green' is a claim in its own transcript — the receipt is me re-running the gates. And the physics oracle doesn't consult the code it just wrote: it asks the sky. The ISS is either where CelesTrak and wheretheiss.at say it is right now, or the gate fails."*

---

## Pre-flight (once, off camera) &nbsp;·&nbsp; **Gate: the warm-up variant passes end-to-end**

```bash
# MacBook — one-time
node --version                                   # need >= 22.19
npm install -g --ignore-scripts @earendil-works/pi-coding-agent   # pi >= 0.83.0
# paste the models.json block from demo/orbit-globe/README.md into ~/.pi/agent/models.json
cd <clone>/dgx-spark/demo/orbit-globe/validate && npm run setup   # installs Playwright Chromium

# Sparks — DeepSeek up + warm (runbook Phases 4-5 green incl. 5.6), then from the Mac:
curl -s http://promaxgb10-41b1:8888/v1/models    # answers with DeepSeek-V4-Flash-0731

# Dry run (NOT recorded): the warm-up variant from TASK.md — classic single-ISS tracker.
# Proves harness wiring, tool calls, and validator on this exact stack. Then DELETE the
# generated index.html so the recorded take starts clean.
```

- OBS scenes: (a) MacBook terminal running pi, font ≥ 18pt; (b) browser full-screen for the artifact; (c) optional second terminal for the independent close.
- Terminal history cleared; workspace contains only the committed files (no index.html).

---

## Capture phases

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **D1 The environment** | `ls` the workspace; open `AGENTS.md` + a skill briefly | "No mega-prompt. The environment *is* the prompt engineering: conventions in AGENTS.md, domain knowledge in two skills, the task in TASK.md — and a gate suite the agent is told to satisfy. The one-line prompt works because everything else is already here." | Workspace shown; the four actors named (the mental-model table) |
| **D2 The prompt** | Type into pi: `Build the constellation globe described in TASK.md — follow the workspace conventions.` | Say the chain out loud: "pi is just hands on this Mac — every decision is DeepSeek on those two boxes, over my LAN, no cloud anywhere." | Prompt sent; endpoint named on camera |
| **D3 The build** | Code streaming in the TUI | Narrate lightly; let it move. Honest numbers if asked-by-camera: ~55–65 tok/s on code, prose slower. Point out when it *reads the skills* — that's the environment paying off. | Agent visibly consults AGENTS.md/skills; index.html written |
| **D4 The agent's own gates** | pi runs `npm run validate` via its bash tool | "Now it checks its own work — same recon→gate→fix arc as the runbooks. A FAIL line isn't an error message to me; it's feedback to *it*." If gates fail: **leave it in** — the fix loop is the money shot. If first-pass green: say so honestly ("the loop was armed; it didn't need it — that happens"). | Validator run BY THE AGENT on camera; iterate-to-green (or honest first-pass green) captured |
| **D5 The independent close** | Second terminal, you type `npm run validate` | The act-2 line from the mental model above — self-report vs receipt, and the sky as the oracle. Show the PASS table land. | Operator-run gates green on camera |
| **D6 The artifact** | Browser full screen | Hero shot: the constellation, time-warp 60×/600×, click a satellite for its orbit, the ISS highlighted with live readout. Judgment call stated plainly: "the gates prove it's *correct* — whether it's *beautiful* is mine to judge, and that stays human." | Artifact shown doing its thing; correctness-vs-taste line said |

---

## Failure triage (during recording — keep rolling)

| Symptom | Meaning | Move |
|---|---|---|
| pi 400s immediately | `developer` role / `reasoning_effort` rejected | compat flags in `~/.pi/agent/models.json` (README block) — fix on camera, it's a 10-second beat |
| Tool calls appear as raw `<…DSML…>` text in responses | The spec-decode draft-rejection bug (runbook Appendix A) | DeepSeek Phase 5.6 wasn't green — stop, interpose the compat proxy or reduce spec tokens; re-record later |
| Validator T3.live-oracle fails but T3.sgp4 passes | Sim drifted from real time or wheretheiss.at hiccup | Reload artifact (boots at 1×), re-run; if persistent, say so and lean on the SGP4 oracle — honestly, on camera |
| Agent claims green but D5 fails | The exact failure act 2 exists for | **Keep it in.** That moment is worth more than a clean take |
| Globe renders black / no textures | CORS on a non-approved texture URL | The agent violated AGENTS.md — point at the rule, let it fix; good teaching beat |
| Everything works first try, no drama | It happens | Don't fake a failure. The dry-run footage of the warm-up variant can illustrate the loop if needed |

---

## Production notes

- **Edit out**: installs, the Playwright download, long silent generation stretches (jump-cut with tok/s overlay).
- **Do NOT quote leaderboard comparisons** — same rule as the other capture docs. The story is *capability doing work*, not benchmarks.
- **Relationship to the other videos**: this is the payoff after the two-Spark bring-up material; it also stands alone. The runbook-method video ([`VIDEO-executable-runbooks.md`](./VIDEO-executable-runbooks.md)) owns the gates philosophy — here you get to *show* it applied to a freshly generated artifact: the agent iterating against assertions it can't talk its way past, then the operator holding the receipt.
- Evidence for the description/pinned comment: the validator's final PASS table (both runs), the one-line prompt, and the repo path `demo/orbit-globe/`.
