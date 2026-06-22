# Slide content — "So You've Got a DGX Spark — Now What?"

**Purpose:** the slide-by-slide source for the deck (hand this to Claude Cowork / PowerPoint to generate slides). We iterate on *content* here; Cowork does layout.
**Pairs with:** [`TALK-ddd-southwest-got-a-spark-now-what.md`](./TALK-ddd-southwest-got-a-spark-now-what.md) (abstract + 7-beat spine) — this expands that spine into slides.
**Serves both:** the **DDD South West talk** (~30–45 min) *and* the **single-Spark YouTube video** (the live demo = a screen recording of the runbook executing). Slides tagged `[video]` are the framing slides the video reuses; the rest are talk-only.
**Scope:** this is the **foundation** deck (single Spark, the runbook method). The two-Spark *capacity-not-speed* payoff is a **separate deck** (outline in the appendix; spine = `RUNBOOK-two-spark-video-capture.md`).

**Design system (notes for Cowork):** dark technical theme; monospace for commands/gates; one idea per slide; terminal screenshots > bullet walls. Recurring visual motif: **"watch-out → I-lost-a-day → a gate that STOPS"** (the three-ways-to-encode-a-gotcha). Accent colour for `GATE PASS`/`GATE FAIL`. Keep the live-demo slides minimal (the recording carries them).

---

## Slide 1 — Title `[video]`

**On screen:**
- **So You've Got a DGX Spark — Now What?**
- *Runbooks an agent can actually run.*
- [your name / handle] · DDD South West
- small: the two boxes on the desk (photo) + the ConnectX-7 cable coiled next to them

**Notes:** Open with the question people actually arrive with. "I'm not going to teach you to set one up — the community already did. I'm going to show you how to make that setup *reliable and repeatable*, by having a coding agent run a runbook."

---

## Slide 2 — The cliff `[video]`

**On screen:**
- You unboxed it. **The hardware was the easy part.**
- The knowledge to turn it into a reliable multi-model stack is:
  - **scattered** across a dozen blogs + forum threads
  - written as **"I lost a day to this"** war stories
  - **out of date** by the time you read it
- *"Just ask Claude to set up my Spark" = an improviser, not a procedure.*

**Notes:** Land the shared pain. The room nods. The gap isn't knowledge existing — it's that it's not *repeatable* or *self-verifying*.

---

## Slide 3 — Stand on the giants `[video]`

**On screen:**
- I'm **standing on** the people who documented the stack:
  - NVIDIA DGX Spark / GB10 **playbooks** + forum
  - **martinB78** — full-stack LiteLLM + llama-swap + vLLM + llama.cpp
  - **Dre Dyson** — multi-model build + gotchas
  - **mostlygeek/llama-swap** · **Spark Arena** leaderboard
- *"I'm not competing with these. I'm adding the layer that makes it reproducible."*

**Notes:** Integrity + armour against "isn't this just a wrapper?" Name them on a topology slide. The contribution is the **method and the gates**, not the stack.

---

## Slide 4 — The whole idea, in one slide `[video]`

**On screen — one gotcha, three ways:**
| Source | What it gives you |
|---|---|
| Forum post | *"watch out for the ARM64 CPU-fallback"* |
| Blog | *"I lost a day to ~2 tok/s before I realised"* |
| **This repo** | **a gate that STOPS the run** until the GPU is proven to be doing the work |

- Blogs **teach** the stack. They don't make it **repeatable** or **self-verifying**.

**Notes:** This is the thesis in one slide. The difference between a tutorial and a runbook is that the runbook *asserts* the thing the blog *warns* about.

---

## Slide 5 — A runbook is an executable spec

**On screen:**
- A runbook here is **not a tutorial**. It's a spec an **agent executes** (Claude Code / Codex / OpenCode), with three properties:
  1. **Deterministic** — every version pinned. Same procedure today and in three months.
  2. **Self-verifying** — gotchas are **gates that fail loudly and halt**, not prose you skim.
  3. **Reproducible** — emits a `RESULTS-*` artifact; changes are reviewed commits, never mid-run edits.

**Notes:** This is your software-engineering discipline (document-first, outcome gates) pointed at infra.

---

## Slide 6 — Anatomy of a runbook

**On screen (vertical flow):**
- **`PINS`** block — one source of truth for every version / model / threshold
- **Phase 0: Recon** — read-only; checks the forum + upstream the morning you run it → **drift report**
- **Phases 1…N** — pinned steps, each ending in an inline **PASS/FAIL gate**
- **Decision Gate table** — the single place to read "is the run green?"
- *Anti-goal:* an agent that **rewrites its own steps mid-run** is an improviser. Research informs; **gates decide**; a human ratifies.

**Notes:** Walk the shape. Emphasise recon ≠ improvisation — it *reports*, it never edits the procedure.

---

## Slide 7 — Gates vs research (the split that matters)

**On screen:**
| | **Recon** (Phase 0) | **Gate** (in-step) |
|---|---|---|
| When | before side effects | at the step |
| Reads | forum, upstream repos | the live machine |
| Output | a drift report | PASS / FAIL → halt |
| Authority | advisory (informs a human) | **decisive (stops the run)** |
| Edits the procedure? | **never** | never |

**Notes:** Two independent safety nets. Recon says a value *might* need changing *before* you hit the gate; the gate enforces the invariant *regardless* of what recon said.

---

## Slide 8 — The gotcha → gate registry (the receipts)

**On screen — a few real GB10 traps, each with its assertion:**
- `mmap` on unified memory → severe slowdown → **every cmd has `--no-mmap`**
- generic ARM64 binary → silent CPU-only ~2 tok/s → **gate: `llama-server` is GPU-bound (`used_memory > 0`)**
- 121 GB ceiling, freeze at 114 → **gate: total unified mem `< 115 GB` before load**
- f16 KV degrades on SM121 → **`--cache-type q8_0` on large-ctx models**
- `llama-swap` double-dash flags silently rejected → **single-dash `-config`/`-listen`**
- process under the VS Code cgroup gets reaped → **gate: cgroup is the systemd unit**
- embeddings "1024 dims" but the model emits **768** → **gate: served dim == index dim**

**Notes:** These are the war stories, converted. This table is the durable asset — commands rot, the *traps* don't.

---

## Slide 9 — What it builds: an open, reproducible box `[video]`

**On screen — single-Spark topology (diagram):**
```
clients (Claude Code / agents — OpenAI & Anthropic compatible)
        │
   llama-swap :9000   ← the front door (all-llama.cpp, one process tree)
   always-on (~65 GB): workhorse · coach · chat · embed
```
- **workhorse** Qwen3.6-35B-A3B · **coach** Gemma-4-26B-A4B · **chat** gpt-oss-20b · **embed** Qwen3-Embedding-0.6B
- 100% **open, downloadable** models — a viewer can reproduce the whole box.
- *Honest:* the live front door is **llama-swap on :9000**. **LiteLLM is the Phase-4 layer** — documented, not yet production.

**Notes:** New visual (single-Spark). Mention the leaderboard-topping Qwen3.6-35B + the 17/17-on-tool-calling Gemma-4 coach so the model picks feel earned, not arbitrary.

---

## Slide 10 — The value proposition `[video]`

**On screen:**
- ```
  git clone …/dgx-spark && cd dgx-spark
  claude "execute RUNBOOK-single-spark-bring-up.md"
  ```
- **Clone → point an agent at the runbook → walk away.**
- The agent does *everything*: installs, the ~35 GB model pull, the SM121 build, serve, validate — **inline** (you edit out the wait).
- One-time box setup: **passwordless sudo** (run once). That's it.

**Notes:** This is the payoff of the method — not "ask Claude to set it up" (improvised, irreproducible) but "Claude executes a deterministic, gated spec." The downloads/build are the only "wait" and they're edited out.

---

## Slide 11 — Live demo: what you're about to watch `[video]`

**On screen:**
- **Recon → Execute → Gate-catch** (≈ the money arc)
1. Agent runs **Phase 0 recon** → shows a **drift report** (one flagged regression)
2. Agent executes the pinned build/serve steps
3. **A gate fires** on the flagged regression — **halts loudly**
4. Fix = **a PR**, not a runtime hack → re-run green

**Notes:** Frame it before rolling the recording. "Watch it catch a known landmine before it costs me an afternoon."

---

## Slide 12 — [LIVE RECORDING] `[video]`

**On screen:** full-screen terminal capture of the real run (no slide chrome). The drift report; the steps moving; the **`GATE FAIL … STOP.`** line; the PR fix; the re-run green.

**Notes:** The recording *is* the slide. If a beat doesn't land live, a second take is fine — keep it real, the gotchas are the content.

---

## Slide 13 — What just happened `[video]`

**On screen:**
- Recon **predicted** the drift (didn't rewrite a step).
- A gate **stopped** the run at the exact trap.
- The fix was a **reviewed pin change**, then a green re-run.
- *Reproducible, not improvised.*

**Notes:** Recap the arc in four lines so it sticks even if the live run was bumpy.

---

## Slide 14 — Why it generalises

**On screen:**
- **Agent-agnostic** — Claude Code / Codex / OpenCode. The **spec** is the asset, not the tool.
- This is **document-first development + outcome gates** — the discipline you already use for software, pointed at **infra**.
- Recon **degrades gracefully** — no internet? It runs the pinned procedure and notes `recon: skipped`. Network is additive, never on the critical path (DF-001).

**Notes:** Take it from "a Spark trick" to "a transferable engineering practice."

---

## Slide 15 — Takeaways

**On screen:**
1. The unit of local-AI ops is a **runbook as executable spec**, not a tutorial.
2. **Gotchas belong in gates** — encode the trap as an assertion that halts.
3. **Recon, not improvisation** — check current sources, emit a drift report, keep the procedure deterministic.
4. It's your **SWE discipline applied to infra** — and it's agent-agnostic.

**Notes:** The four things to remember. Mirror the abstract's takeaways.

---

## Slide 16 — Close + what's next `[video]`

**On screen:**
- Repo: **github.com/guardkit/dgx-spark** (the runbooks, the conventions, the gate registry)
- *"Got it reliable on **one** box. The next question is **two** boxes — and the answer surprised me."*
- → **"I stacked two DGX Sparks — it wasn't faster. Here's why."** (capacity, not speed)

**Notes:** Tee the second talk. Thank the giants again. End on the tease, not a summary.

---

## Appendix — the two-Spark payoff deck (separate, outline only)

*Spine: `RUNBOOK-two-spark-video-capture.md` + `DECISION-DF-004`. Build this deck after the foundation one.*

- **The intuition:** "two boxes, twice the tokens, right?"
- **The reality:** the **200 G ConnectX-7 link (~22 GB/s, wired as 2× PCIe Gen5 x4)** is the ceiling. A model that fits one node is **faster** on one node.
- **The reframe:** you stack for **capacity** (run a model too big for 128 GB) and **parallelism**, then **time-share** the boxes — never for single-stream speed.
- **The proof:** DeepSeek-V4-Flash (284B-A13B, ~158 GB) across two nodes via vLLM `--tp 2`, ~44 tok/s warm — vs the same-class model running faster single-node.
- **The architecture:** one LiteLLM `:4000` front door → llama-swap pool (Node A) **XOR** the cross-node TP proposer (memory budget per session). [diagram: `diagrams/two-spark-fleet-serving-architecture.svg`]
- **The honest gotchas** (the bring-up war story): any QSFP port (the "same port" myth), prove RoCE not TCP (`NET/IB`), the firmware hard-power-off, MTP-or-decode-collapses.
- **Close:** capacity not speed — *share the boxes by time, not at once.*

---

## Production notes

- **Video vs talk:** the YouTube single-Spark video = slides 1–4, 9–13, 16 (framing) wrapped around the live recording. The talk = the full deck. Same narrative, different density.
- **Diagrams:** slide 9 needs a *new* single-Spark topology graphic (simple — the ASCII above, drawn). The two-Spark appendix reuses `diagrams/two-spark-fleet-serving-architecture.svg` (re-export from `.excalidraw` for clean layout first).
- **Live demo safety:** record on a box where llama.cpp is already built (so the demo is ~8–10 min, not 90); the drift-report + gate-catch is the part that must land on camera.
