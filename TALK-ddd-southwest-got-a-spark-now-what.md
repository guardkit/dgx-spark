# Talk: "So You've Got a DGX Spark — Now What?"

**Venue fit:** DDD South West (and similar practitioner meetups). Bristol-local, .NET-and-adjacent, practitioner crowd that buys *engineering practice*, not hardware tips. ~30–45 min + Q&A.

**Status:** CFP-ready abstract + session spine. Live demo built on `RUNBOOK-single-spark-bring-up.md` (to be built) and the recon→drift→gates pattern in `RUNBOOK-CONVENTIONS.md`.

---

## Title options

1. **So You've Got a DGX Spark — Now What? Runbooks an Agent Can Actually Run**
2. Gotchas as Gates: Reproducible Local-AI Setup with Claude Code and Runbooks
3. From Unboxing to Trusted: Agent-Executed Runbooks for the DGX Spark

(Lead with #1 — it's the question people actually arrive with.)

---

## Abstract (CFP blurb)

You unboxed a DGX Spark (or a Strix Halo box, or a 128 GB Mac). The hard part isn't the hardware — it's the cliff right after: the knowledge to turn it into a reliable multi-model inference stack is real but scattered across a dozen blog posts and forum threads, written as "I lost a day to this" war stories, and out of date by the time you read it.

This talk isn't another setup tutorial — the community already wrote those, and I'll point you at the good ones. It's about the layer on top: turning that scattered knowledge into **runbooks an agent executes** — Claude Code or Codex — where the procedure is version-pinned and deterministic, the hard-won gotchas are encoded as **gates that fail loudly** instead of prose you skim past, and a **read-only recon pass checks the forum and the upstream repos the morning you run it**, telling you what's drifted since the runbook was written — without rewriting itself.

Live, we'll watch the agent run a bring-up: it produces a drift report against current sources, executes the pinned steps, and a gate catches a known regression before it can burn an afternoon. You'll leave with the pattern (and a repo), not just a command list.

---

## Audience & takeaways

**For:** practitioners who have, or are about to get, a local-AI box and want it to be *reliable*, not a weekend of debugging. Comfortable with the idea of agentic tooling; this is not a beginner hardware walkthrough.

**Takeaways:**
1. The useful unit of local-AI ops is a **runbook as executable spec**, not a tutorial — and why that beats "ask Claude to set up my Spark."
2. **Gotchas belong in gates**, not prose: encode the trap as an assertion that halts the run.
3. **Recon, not improvisation** — leverage the executing LLM to check current sources and emit a drift report, while keeping the procedure deterministic. Research informs; gates decide; a human ratifies.
4. The pattern is **agent-agnostic** and is just *your software-engineering discipline applied to infra*.

---

## Session spine

| # | Beat | ~min | On screen / point |
|---|------|-----:|---|
| 1 | **The cliff** | 4 | "You've got a Spark — now what?" The post-unboxing reality: the knowledge exists but is scattered, version-churny, written as war stories. The room nods. |
| 2 | **Stand on the giants** | 3 | Name the prior art — NVIDIA playbooks, the GB10 forum, martinB78's full-stack guide, Dre Dyson, `mostlygeek/llama-swap`. "I'm not competing with these. I'm standing on them." Integrity *and* armour against "isn't this just a wrapper?" |
| 3 | **The gap = reliable + reproducible** | 4 | The blogs *teach* the stack; they don't make it repeatable or self-verifying. Show a single gotcha three ways: a forum "watch out", a blog "I lost a day", and **a gate that stops the run**. That's the whole idea in one slide. |
| 4 | **The method** | 6 | Runbook = executable spec with three properties (deterministic, self-verifying, reproducible). The anatomy: `PINS` block → Phase 0 recon → pinned steps with inline gates → Decision Gate table. The anti-goal: an agent that rewrites its own steps is an improviser, not a runbook. |
| 5 | **Live demo** | 10 | The centrepiece (below). Recon drift report → agent executes → a gate catches a regression the report predicted. |
| 6 | **Why it generalises** | 4 | Agent-agnostic (Claude Code / Codex / OpenCode — the *spec* is the asset). This is document-first development + outcome gates, the same discipline you already use for software, pointed at infra. |
| 7 | **Close + what's next** | 3 | Repo link. "Got it reliable on one box — next question is *two* boxes, and the answer surprised me." Tee the two-Spark *capacity-not-speed* talk. |

---

## Live demo — beats (capture, don't script)

The demo *is* the differentiator. Screen-record a real run; narrate. Beats:

1. **Kick off recon.** Agent hits the fixed source list, runs the deterministic pin checks (`llama-swap` release, `llama.cpp` HEAD, the graphiti fork tag) and the forum scan. **Show the drift report** — one flagged regression (e.g. a CX-7 firmware thread, or a `gpu-memory-utilization` change), procedure unchanged.
2. **Agent executes the pinned steps** — build/serve through `llama-swap` on `:9000`. Let it move; talk over it.
3. **A gate fires.** The run hits the assertion for the regression the drift report flagged (e.g. the ARM64 silent-CPU-fallback gate, or the memory-ceiling gate) and **halts loudly**. This is the money shot: the gate caught a known trap before it cost an afternoon.
4. **Show the fix is a PR, not a runtime hack** — the pin gets updated, reviewed, re-run green. Reproducible, not improvised.

If a beat doesn't land live, a second take is fine — but keep it real (the gotchas are the content).

---

## Honest caveats (say these — they make it stronger, not weaker)

- **Commands rot**, fast, on the Spark especially. So the durable thing I'm selling is the **method and the gates**, not the exact commands; the repo is a living artifact, and Phase 0 recon is precisely the response to staleness.
- **Recon degrades gracefully.** No live internet to the forum? The runbook still executes the pinned procedure and notes `recon: skipped`. The network is additive, never on the critical path (DECISION-DF-001).
- **Honest about the stack:** the live front door is **llama-swap on `:9000`** (all-llama.cpp). **LiteLLM is the Phase-4 routing layer** (the martinB78/community pattern) — documented, not yet the production front door. The talk presents it that way.

---

## Series

This is the **foundation** talk. The **payoff** is the second one: *"I stacked two DGX Sparks — it wasn't faster, and here's why"* — the capacity-not-speed reframe, where the two-node multi-model intersection is genuinely empty prior-art territory. Sequence them foundation → reframe. Capture spine for the second talk already exists: `RUNBOOK-two-spark-video-capture.md`.
