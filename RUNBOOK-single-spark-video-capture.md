# Single-Spark Bring-Up — Video Capture Runbook

**Spine:** *One box runs my whole local-AI loop — build the dataset, fine-tune the model, host it, then point my agents at it to ship features. Here's how I get that box set up so it just works.*

**Channel fit:** @RichWoollcott — a software engineer crossing into AI. This is the **companion video** to the *"2026: The Year of the Software Factory"* talk. The talk is the *system*; this video is the **machine underneath it** — the one box that does the local inference, the dataset building, and the fine-tuning the factory runs on.

**The deliberate non-goal — say this out loud in the hook:** this is **not** a tokens-per-second video. The forums are wall-to-wall speed benchmarks and leaderboard drag-races. The thing almost nobody shows is *what the box is actually for* and *how to make it reliable enough to trust with real work*. That gap **is** the video. Leave the tok/s to the people geeking out in the forums.

**How to use this:** a capture *spine*, not a script. Record the real bring-up with OBS and narrate as you go. Don't write lines, don't re-shoot for polish, don't hide failures — the gotchas are the content. If a phase doesn't land, pick it up in a second session.

Audience: software engineers who have (or are about to get) a local-AI box and want it to *do useful work*, not benchmark well. Target: ~10–15 min build-log + purpose explainer.

---

## The one idea (open on it, close on it)

This box isn't a benchmark rig — it's the **factory floor for one developer**. It does four jobs end to end, with **no cloud on the critical path**:

1. **Build the dataset** — an agent turns my source material (books, docs, PDFs) into validated training data. *(The "Agentic Dataset Factory" from the talk.)*
2. **Fine-tune** — train an open-weight model on that data, on-box, with Unsloth.
3. **Host** — serve the fine-tuned model *and* the open-weight models behind **one local front door** (LiteLLM → llama-swap + vLLM), so anything OpenAI/Anthropic-compatible can call them — with a hard **no-cloud-fallback guard** so an unattended run can never phone home to a paid API.
4. **Build** — my **LangGraph DeepAgents** and **guardkit AutoBuild** call that box to do the work. They build features against *my* local models, not someone's cloud.

The rest of the video is the honest part: **how I get this box reliable enough to trust with all four** — by pointing a coding agent at a gated runbook, not by hand-following a blog.

---

## Pre-read (open in tabs before recording)

- **Software Factory deck** — have these slides ready as the framing cutaways: *The Factory / Fleet Architecture* (slide 9, "every model through one endpoint"), *The Player-Coach Loop* (slide 10), *Evidence — 26B fine-tune vs GPT-5.5* (slide 12), *Agentic Dataset Factory* (slide 13), *The Stack — four layers* (slide 14).
- **`./RUNBOOK-single-spark-bring-up.md`** — the executable, gated runbook this video *films*. Run it once before recording.
- `RUNBOOK-CONVENTIONS.md` — the recon → drift → gates method (the "how it stays reliable" half).
- **Front-door rationale** — `DECISION-DF-004` (LiteLLM `:4000` as the unified front door) + the `dark-factory-economics-and-model-serving.md` §3.8 split (llama-swap = lifecycle/memory; LiteLLM = routing/keys/spend) and the DF-001 no-cloud-fallback guard. This is the "building on top of the community stack" story.
- The single-Spark topology diagram *(to draw — see Production notes)*.

---

## Pre-flight — recording setup &nbsp; · &nbsp; **Gate:** scenes ready, framing slides loaded, terminal legible

- OBS scenes: (a) desk/hardware cam, (b) full-screen terminal, (c) slide/diagram cutaway. Terminal font ≥ 18pt.
- The Spark powered; single clean shell, history cleared; the bring-up dry-run done once so you know it goes green.

---

## Capture phases

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **P1 Hook** *(what it's for)* | The box on the desk | "This one box is my whole AI loop — I build datasets on it, fine-tune models on it, host them, then point my agents at it to ship features. And I'm **not** going to talk to you about tokens per second — that's the forums' game. I'm going to show you what it's *for* and how to make it reliable." | Purpose + anti-benchmark promise stated on camera |
| **P2 The loop** *(the purpose beat — the differentiator)* | Cut to the Fleet Architecture slide (9) + Dataset Factory slide (13) | Walk the four jobs, one line each: **dataset** (an agent turns my books/PDFs into validated training data) → **fine-tune** (open-weight model, on-box, Unsloth) → **host** (every model behind one local front door — **LiteLLM → llama-swap + vLLM**) → **build** (DeepAgents + AutoBuild call the box, not the cloud). Land it: "everything from here is making *this* box trustworthy enough to run all four unattended." | The four jobs explained as one loop |
| **P3 How I got here** *(the origin war story — the differentiator)* | Talking head; cut to old provisioning scripts + the early llama-swap config | Tell it honestly: Claude Code wrote my first provisioning **scripts**, and I spent days **debugging them by hand** — getting vLLM serving, then a **llama-swap config** to put every model behind one front door. It *worked* — but it wasn't **reproducible**: every rebuild was another debugging session, and a production cutover still bit me with traps I hadn't encoded anywhere. The turn: I stopped hand-running scripts and started writing the whole procedure as an **executable runbook an agent runs end to end**. I'd **never worked this way before — and it was the game-changer.** | The scripts → hand-debug → executable-runbook arc told honestly |
| **P4 What an executable runbook is** *(gotchas become gates)* | Full-screen terminal | `git clone … && claude "execute RUNBOOK-single-spark-bring-up.md"`. The anatomy, in plain terms: **pinned** versions (same result in three months), a Phase-0 **recon** pass that reports what's drifted the morning you run it, and the hard-won gotchas encoded as **gates that fail loudly and STOP** — not prose you skim past. "A blog says *watch out*; the runbook *stops*." A favourite to show on camera: a gate that asserts **no cloud fallback** is configured — auto cloud-fallback is LiteLLM's headline feature, and I **deliberately disable it with an assertion** so an unattended overnight run can never silently bill a frontier API (it bit me once). Clone → point an agent at it → walk away. | Runbook-as-spec (pinned · recon · gates that stop) landed |
| **P5 Live demo** *(the proof it's reliable)* | The real run, full-screen | Roll the recording: Phase-0 **recon → drift report** (one flagged regression), agent **executes** the pinned build/serve, a **gate fires** on the flagged trap (e.g. the **115 GB memory-ceiling** gate — the documented freeze at 114 GB) and **halts loudly**, the fix is **a reviewed PR**, then a green re-run. Talk over it; let it move. | Recon → execute → gate-catch → PR-fix → green captured |
| **P6 Payoff** *(close the loop on camera)* | Terminal / a DeepAgent or AutoBuild run | The box is now serving my models behind the one front door. Show it being *used*: a **DeepAgent** or **AutoBuild** actually calling the box to do real work (e.g. an architecture review by the fine-tuned model, or a feature task). "Datasets, fine-tune, host, build — all on the one box, no cloud in the loop." | The box shown doing useful work, not a benchmark |
| **P7 Close** | Back to hardware / channel card | Restate the one idea (factory floor for one developer). Repo + channel. Tease the next video on **what a second box unlocks** — running a *more capable Player* (DeepSeek V4 Flash) than fits on one box, to drive the dataset factory and AutoBuild harder — *capacity, not speed.* | One idea restated; next video teed on utility |

---

## Edit & publish kit (use after filming)

*Everything you reach for once filming is done — to cut the video and upload it. (No LLM prompts here — "talking points" below are lines to say, not a script.)*

- **Title options (utility-framed, never speed):**
  - "One Box, the Whole AI Loop: I Build Datasets, Fine-Tune & Host My Own Models — Then Build With Them"
  - "How a Software Engineer Runs a Local AI Lab on One Box (Dataset → Fine-Tune → Ship a Feature)"
  - "The Machine Behind My Software Factory: One DGX Spark, No Cloud"
- **Thumbnail text (no numbers):** `BUILD → FINE-TUNE → HOST → SHIP` · or `ONE BOX. THE WHOLE LOOP.`
- **Chapters** = the phases: `00:00` What it's for · The loop · How I got here · What a runbook is · The live run · Using it · Close.
- **Talking points (the spine, safe to repeat):** the box is a *factory floor*, not a benchmark rig · four jobs on one box (dataset · fine-tune · host · build) · one local front door — **LiteLLM → llama-swap + vLLM** — the full community stack, with a hard **no-cloud-fallback gate** · no cloud on the critical path · I went from *hand-debugging Claude-written scripts* to *executable runbooks an agent runs* — the game-changer · gotchas belong in *gates*, not prose · I'm pointing my own agents at my own models.
- **Do NOT:** quote tokens/sec or compare to a leaderboard (that's the forums' game — and the whole point is to *not* play it) · re-shoot for polish · script lines · cut the failures · let the camera slow the build.
- **Must-haves to make the video** (any gate that failed → a second session is fine): (1) the "what it's for / not a tok/s video" hook on camera, (2) the four-job loop explained, (3) the **origin story** — scripts → hand-debug → executable runbooks (the game-changer), (4) what a runbook-as-spec is (pinned · recon · gates), (5) the gate catching a trap live, (6) the box shown *doing useful work*, (7) the close.

---

## Production notes

- **Relationship to the talk:** this video is the **machine** under the *Software Factory* talk — reuse the talk's Fleet Architecture (9), Dataset Factory (13), and Stack (14) slides as cutaways so the channel and the talk reinforce each other. Same narrative, more hands-on density.
- **Diagram:** P2 needs a simple single-Spark "the four jobs on one box" graphic (the loop: dataset → fine-tune → host → build, with **LiteLLM** as the front door over **llama-swap + vLLM**). Draw it once; reuse on the slide.
- **Origin-story sources (P3):** the real arc is on record — the early hand-debugged vLLM scripts (`scripts/archive-vllm/`), the prose `llama-swap-setup.md` "Setup Guide", and the **v2 → v3** deployment runbooks (`RUNBOOK-v2-all-llamacpp-architecture.md`, `RUNBOOK-v3-production-deployment.md`, private `guardkit` repo) where the production cutover surfaced traps. Pull a couple of those as on-screen B-roll to make "scripts → runbooks" concrete.
- **Live-demo safety:** record on a box where llama.cpp is already built so the run is ~8–10 min, not 90. The drift-report + gate-catch is the part that must land on camera; the long download/build is edited out.
- **Front door = LiteLLM (the full community stack):** present the front door as **LiteLLM `:4000` → llama-swap `:9000` (+ vLLM)** — genuinely building *on top of* the martinB78/Dre stack, not a stripped-down version of it. LiteLLM is the unifier (one endpoint, per-agent virtual keys, usage/spend dashboard, `claude-*` wildcard routing); llama-swap stays the unified-memory/lifecycle layer underneath. The deliberate divergence to call out on camera: **no cloud fallback** (`fallbacks: []` *and* `context_window_fallbacks: []`), enforced by a gate (DF-001).
  - ⚠️ **Pre-film dependency (runbook-later):** the LiteLLM front-door phase + its two gates (no-cloud-fallback; CPU-pin LiteLLM separately from llama-swap — Dre's #1 mistake) still need adding to `RUNBOOK-single-spark-bring-up.md` before this is filmed, so the live demo matches the narrative. Tracked as a follow-up.

---
*Companion to `TALK`/`SLIDES-got-a-spark-now-what.md` and the Software Factory deck. The two-Spark payoff has its own spine: `RUNBOOK-two-spark-video-capture.md` — teed at the close as capacity, not speed.*
