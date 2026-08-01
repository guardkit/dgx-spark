# Video: Runbooks an agent can actually run

**What this is:** the plan for a YouTube video about the runbook technique itself — not about the DGX Spark. The Spark is just the box it happened to run on.

**Tone:** a friend in the industry showing you something that's been working well. Not a keynote, not a claim, not a flex. *"This helped me, it might help you, here's how it works and here's where it bites."*

**Length:** 12–15 min.

**Companion docs:** [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) is the method. [`RESEARCH-executable-runbooks-prior-art.md`](./RESEARCH-executable-runbooks-prior-art.md) is the prior-art reading, for anyone who wants to go deeper — **mention it once, link it, move on.** Nobody clicked for a literature review.

---

## The thing you're actually showing

You point a coding agent at a markdown file. It brings a bare GB10 up to a working multi-model inference fleet (three always-on models plus an on-demand 120B), on its own, and **checks its own work at every step** — not with vibes, but with assertions that stop the run if reality doesn't match.

First time filmed, on a fresh box (`spark-fcf6`, 2026-07-11):

- It hit a **broken model source in my own script** — the chat model was being pulled from a repo with a glob that matched nothing, and `set -e` killed the script dead.
- It **worked out where the real file lived**, pulled it from the official repo instead, and carried on.
- It finished **9 out of 9 gates green**: GPU-bound (not the silent CPU-fallback trap), 56.8 tok/s on the workhorse, 76 GB used against a 115 GB ceiling, embeddings at the right dimension, the process under the right systemd cgroup.
- And it **filed four defects against my own runbook and scripts** on the way through.

That last one is the bit that made me sit up. It didn't just do the job. **It told me my documentation was wrong.**

Results are on the `spark-fcf6` branch: [`RESULTS-single-spark-bring-up-2026-07-11.md`](./RESULTS-single-spark-bring-up-2026-07-11.md) and the drift report next to it. Show them on screen — they're the receipts.

*(Update 2026-08-01: that chat model has since been **retired from the lineup entirely** — a review asked "who actually calls it?" and the answer was nobody. The retirement is itself the method working: a reviewed commit, not a quiet edit, and the trap it taught — include-globs must match what the repo actually ships — stayed behind as a general rule in the staging script even though the model is gone. The cold-open recording stands as history; the runbook a viewer runs today brings up the leaner three-model lineup. Commands rot, models retire — the traps don't.)*

---

## The idea, in one minute

Everyone has a setup doc that's a bit wrong. You know the feeling: you follow your own README from six months ago and step 4 just… doesn't work any more. The version moved. The flag got renamed. The file's in a different place now.

**We all just fix it in our heads and carry on.** And the doc stays wrong, forever, for the next person — who is usually you, in six months, at 11pm.

Here's the thing I stumbled onto: **an agent won't do that.** It's pedantic. It runs what you actually wrote, not what you meant. So when the doc is wrong, it *stops* and tells you, instead of quietly routing around it.

> **That pedantry — the thing we all complain about in AI agents — is exactly what turns a document into code.**
> You can't have executable documentation without an executor stubborn enough to fail on a typo. Humans are too helpful. An agent is *usefully* unhelpful.

That's the whole video, really. Everything else is detail.

---

## Why bother — the pitch to a colleague

Two sentences from Google's own SRE books, which say it better than I can:

> *"…recording the best practices ahead of time in a 'playbook' produces roughly a 3x improvement in MTTR as compared to the strategy of 'winging it.'"*

> *"Details in playbooks go out of date at the same rate as production environment changes."*

**Playbooks are three times better, and they rot as fast as you ship.** Everyone's stuck in that gap. This is just a way out of it: make the doc fail loudly when it starts lying, so it can't rot silently.

*(Fair caveat if you want to be scrupulous: Google states the 3x as an internal finding, not a study. Say "Google's SRE book reckons", not "studies show".)*

---

## The bit that surprised me most

I didn't set out to build a method. I went back through the git history while making this and it's genuinely not a designed thing — it precipitated out of getting things wrong repeatedly.

The clearest tell: in one of the repos, the word **"Gate" shows up as a column in a results table *before* it ever appears as a heading in a runbook.** I was filling in a table of what passed and what didn't, and only later realised the table was the point and started writing the assertions up front.

**The technique got named on the way back from a failure.** If it sounds like I'm underselling it — I'm not. That's just what happened, and I'd rather say so.

Worth showing on screen: the whole thing formed in about **35 hours** across the 28th and 29th of April. Archetype runbook at 06:25, results file 52 minutes later, second version by lunch, third by evening. That's not a design process. That's someone getting increasingly annoyed.

---

## What to steal (the practical middle of the video)

This is the part people actually want. Keep it concrete, show real files.

**1. Pin everything, in one block at the top.**
Every version, model, threshold, in one place. Not "install the latest" — "install `v245`, and here's the gate that proves you got it." And state the number **once**: a single `SWAP_VER` line mirrors the PINS block, and everything downstream — the download URL, the asset name, the version gate — derives from it, so the pin can't drift between where it's stated and where it's checked. When the pin moves (it just did: v219 → v245, twenty-six releases in nine weeks), that's a two-line reviewed edit, and the next run is its validation.

**2. Turn your war stories into assertions.**
This is the core move. You know that thing that cost you a day? Don't write *"watch out for X."* Write the check that stops the run when X happens.

The one from the Spark that I'd put on screen, because it's so cheap and it saved so much pain:

> **Gotcha:** a generic ARM64 llama.cpp build silently falls back to CPU. You get ~2 tok/s and no error. Nothing tells you. You just think the box is rubbish.
> **Gate:** assert `llama-server` shows up in `nvidia-smi` compute-apps with memory held. If it doesn't, **stop**.

That's a one-line check that catches an entire lost afternoon. There's a whole table of them in [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md) §8 — "gotcha → gate" — and it's the most valuable thing in the repo. Commands rot. **The traps don't.**

**3. Make the agent write down what happened.**
Every run emits a `RESULTS-*.md`: what passed, the actual numbers, what broke. Reruns get new dated files. It's a ledger, and it's how you notice things sliding.

**4. Let it check for drift — but don't let it fix itself.**
Before it touches anything, the agent does a read-only recon: has llama-swap released since I pinned it? Anything new on the forum about this GPU? It writes a drift report.

**And then it does exactly nothing about it.** It runs the pinned procedure anyway.

---

## The one opinion I'll actually defend

Everyone else is going the other way. There's a whole product category now selling "agentic runbooks", and one vendor's pitch is literally: *"agentic runbooks **decide**, while traditional automated runbooks **execute**."*

I think that's backwards, and it's the one place I'll plant a flag:

> **The agent can tell me the world has moved. It cannot rewrite the procedure.**
> That's a pull request, and a human reads it.

Because the moment it can improvise its own steps, I've lost the two things that made the runbook worth more than a chat prompt: I can't reproduce it, and I can't trust it.

**And there's a good reason to be twitchy about this.** Sakana AI built a genuinely self-improving agent (the "Darwin Gödel Machine") and told it to reduce its own hallucinations. It **deleted the markers they used to detect hallucinations** — despite being explicitly told not to — and faked a log showing tests had passed when they never ran.

That's not a thought experiment. It's in the paper's appendix.

**An agent that can edit its own success criteria will eventually edit its own success criteria.** So mine can't.

*(Same argument GitOps has been having for years, incidentally — Argo CD doesn't self-heal by default, and Flux ships a literal `warn` mode: tell me about the drift, don't fix it. I only found that out afterwards. Nice to know I'm not alone.)*

---

## The honest bit (do not skip this)

**I didn't invent any of this, and I want to be really clear about that.** When I went looking, I found:

- Executable documentation is **40 years old**. The phrase is literally in the Python standard library docs.
- The closest thing to what I'm doing is **Dan Slimmon's "do-nothing scripting" from 2019** — a script that walks a human through a runbook step by step. **Mine is the do-nothing script with an LLM as the human.** That's the honest description.
- Assertions that halt runbooks have been a **default feature in AWS since about 2016.**
- Markdown-executed-by-an-LLM is now an **open standard** (`SKILL.md`) with 40-odd implementations.
- And while I was making this, **Runme shipped something adjacent** — eight days ago.

**That last one isn't bad news, it's the point.** If several people hit the same wall independently, the wall is real. I'm not showing you something clever; I'm showing you something that's in the air, that worked for me, and that you can nick this afternoon.

If you want the full reading list, it's in the repo — [`RESEARCH-executable-runbooks-prior-art.md`](./RESEARCH-executable-runbooks-prior-art.md). It's dry. You probably don't need it.

**One caveat that matters practically:** a `STOP` written in prose is *soft* — agents do ignore instructions. My gates aren't sentences asking nicely. They're shell commands whose output gets compared to an expected value. **You can't talk an LLM out of `exit 1`.** That distinction is doing all the work, and if you take one implementation detail away, take that one.

---

## Rough running order

| # | Beat | ~min |
|---|------|-----:|
| 1 | **Cold open** — the agent hits my broken model source, works around it, keeps going. No preamble. | 1 |
| 2 | **"You know that doc that's a bit wrong?"** The shared pain. Everyone nods. | 1.5 |
| 3 | **The insight** — agents are pedantic, and that's the feature. | 2 |
| 4 | **Why bother** — Google's two sentences. 3x better, rots daily. | 1 |
| 5 | **The full run** — screen recording. Recon → pinned steps → gates → RESULTS. Talk over it. | 3 |
| 6 | **What to steal** — pins, gotcha→gate, results ledger. Show real files. | 3 |
| 7 | **The one opinion** — it may report drift; it may not rewrite itself. Sakana story. | 2 |
| 8 | **I didn't invent this** — Slimmon, AWS, Runme. Generous, quick, done. Repo link. | 1.5 |

**If it runs long, cut beat 4.** The Google quotes are nice-to-have; beats 3 and 7 are the video.

---

## Titles

1. **"The Agent Told Me My Documentation Was Wrong"** ← leads with the real moment
2. "Runbooks an Agent Can Actually Run"
3. "I Won't Let My AI Agent Improvise"
4. "Agents Are Pedantic. That Turns Out to Be the Point."

---

## Notes to self

- **Show real files, not slides.** The RESULTS file with 9/9 PASS and four defects filed against my own runbook is more persuasive than anything I can say over the top of it.
- **Keep the prior art to 90 seconds.** Generous, credited, gone. It's insurance, not content.
- **Don't oversell.** The honest register — *"this worked for me, it's not new, here's where it bites"* — is the whole reason anyone will trust the rest.
- The `agentic-dataset-factory-runs` data is rsync'd output, not a gate ledger. Don't imply otherwise if it comes up.
- **Fresh on-camera material (2026-08-01):** the v219→v245 pin promotion + its validation run is a live example for beat 6's pins point, and the maintenance segment in [`RUNBOOK-single-spark-video-capture.md`](./RUNBOOK-single-spark-video-capture.md) (M1–M6: backup-first · recon in update mode · the three-verdicts moment — update/defer/decline · first LiteLLM install) is a full arc of its own — borrow the promotion beat here; save the maintenance arc for its own video.
- Verify the Netflix/Google quotes against the originals before they go on screen (see the research doc's caveats).
