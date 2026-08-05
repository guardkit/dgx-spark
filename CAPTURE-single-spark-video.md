# Single-Spark Bring-Up — Video Capture Spine

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
- **Front-door rationale** — `DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md` (the single-node decision: LiteLLM `:4000` front door, the two gates, the implementation spec) — backed by `DECISION-DF-004` (two-node) and `dark-factory-economics-and-model-serving.md` §3.8 (llama-swap = lifecycle/memory; LiteLLM = routing/keys/spend) + the DF-001 no-cloud-fallback guard. This is the "building on top of the community stack" story.
- The single-Spark topology diagram *(to draw — see Production notes)*.

---

## Pre-flight — recording setup &nbsp; · &nbsp; **Gate:** scenes ready, framing slides loaded, terminal legible, tunnel up + `:9000/ui` renders in Safari

- OBS scenes: (a) desk/hardware cam, (b) full-screen terminal, (c) slide/diagram cutaway, (d) Safari — the web dashboards. Terminal font ≥ 18pt.
- The Spark powered; single clean shell, history cleared; the bring-up dry-run done once so you know it goes green.
- **MacBook browser scene (the web dashboards):** NVIDIA Connect is an SSH relay — Safari can't reach the box's ports directly, so carry both UIs over **one** tunnel from the MacBook:

  ```bash
  ssh -N -L 9000:127.0.0.1:9000 -L 4000:127.0.0.1:4000 richardwoollcott@promaxgb10-41b1
  ```

  Tabs to preload: **llama-swap** `http://localhost:9000/ui` · **LiteLLM** `http://localhost:4000/` (Swagger — live only after M5; refused-to-connect before that is expected, and the before/after is usable footage). Local port = remote port deliberately, so the URLs on camera are exactly what a viewer types on their own box. **One hop only** — don't `ssh -L` again from the box back to itself (that's the `bind … Address already in use` noise from the office-manager session; the outer tunnel was already doing the work). `-N` keeps the tunnel window shell-free so it can't wander into the recording.

---

## Capture phases

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **P1 Hook** *(what it's for)* | The box on the desk | "This one box is my whole AI loop — I build datasets on it, fine-tune models on it, host them, then point my agents at it to ship features. And I'm **not** going to talk to you about tokens per second — that's the forums' game. I'm going to show you what it's *for* and how to make it reliable." | Purpose + anti-benchmark promise stated on camera |
| **P2 The loop** *(the purpose beat — the differentiator)* | Cut to the Fleet Architecture slide (9) + Dataset Factory slide (13) | Walk the four jobs, one line each: **dataset** (an agent turns my books/PDFs into validated training data) → **fine-tune** (open-weight model, on-box, Unsloth) → **host** (every model behind one local front door — **LiteLLM → llama-swap + vLLM**) → **build** (DeepAgents + AutoBuild call the box, not the cloud). Land it: "everything from here is making *this* box trustworthy enough to run all four unattended." | The four jobs explained as one loop |
| **P3 How I got here** *(the origin war story — the differentiator)* | Talking head; cut to old provisioning scripts + the early llama-swap config | Tell it honestly: Claude Code wrote my first provisioning **scripts**, and I spent days **debugging them by hand** — getting vLLM serving, then a **llama-swap config** to put every model behind one front door. It *worked* — but it wasn't **reproducible**: every rebuild was another debugging session, and a production cutover still bit me with traps I hadn't encoded anywhere. The turn: I stopped hand-running scripts and started writing the whole procedure as an **executable runbook an agent runs end to end**. I'd **never worked this way before — and it was the game-changer.** | The scripts → hand-debug → executable-runbook arc told honestly |
| **P4 What an executable runbook is** *(gotchas become gates)* | Full-screen terminal | `git clone … && claude "execute RUNBOOK-single-spark-bring-up.md"`. The anatomy, in plain terms: **pinned** versions (same result in three months), a Phase-0 **recon** pass that reports what's drifted the morning you run it, and the hard-won gotchas encoded as **gates that fail loudly and STOP** — not prose you skim past. "A blog says *watch out*; the runbook *stops*." A favourite to show on camera: a gate that asserts **no cloud fallback** is configured — auto cloud-fallback is LiteLLM's headline feature, and I **deliberately disable it with an assertion** so an unattended overnight run can never silently bill a frontier API (it bit me once). Clone → point an agent at it → walk away. | Runbook-as-spec (pinned · recon · gates that stop) landed |
| **P5 Live demo** *(the proof it's reliable)* | The real run, full-screen | Roll the recording: Phase-0 **recon → drift report** (one flagged regression), agent **executes** the pinned build/serve, a **gate fires** on the flagged trap (e.g. the **115 GB memory-ceiling** gate — the documented freeze at 114 GB) and **halts loudly**, the fix is **a reviewed PR**, then a green re-run. Talk over it; let it move. | Recon → execute → gate-catch → PR-fix → green captured |
| **P6 Payoff** *(close the loop on camera)* | Terminal / a DeepAgent or AutoBuild run, with the `:9000/ui` activity view beside it (see Web dashboards) | The box is now serving my models behind the one front door. Show it being *used*: a **DeepAgent** or **AutoBuild** actually calling the box to do real work (e.g. an architecture review by the fine-tuned model, or a feature task). "Datasets, fine-tune, host, build — all on the one box, no cloud in the loop." | The box shown doing useful work, not a benchmark |
| **P7 Close** | Back to hardware / channel card | Restate the one idea (factory floor for one developer). Repo + channel. Tease the next video on **what a second box unlocks** — running a *more capable Player* (DeepSeek V4 Flash) than fits on one box, to drive the dataset factory and AutoBuild harder — *capacity, not speed.* | One idea restated; next video teed on utility |

---

## Maintenance segment — the runbook as the box's *update* tool (this Dell GB10, live)

**The beat this earns:** the strongest proof a runbook is an *executable spec* and not a setup blog is pointing it back at the box it built, months later, in **`update` mode** (RUNBOOK-CONVENTIONS §2.2): Phase-0 recon reports what drifted, only the affected phases re-run, the gates re-prove the invariants, and RESULTS records the new validated baselines. This Dell GB10 is the honest demo — hand-assembled era parts (vLLM containers ~Feb, llama-swap ~May) on a freshly patched OS (2026-07-30) — so the drift report has real teeth *and* a bounded fix list. It also answers the "just search the forum" culture directly: the forum search is done once, encoded as recon sources + gates, and re-run by an agent every time.

**Act two is genuinely new on this box:** LiteLLM has **never been installed here** (`:4000` not listening, binary present, no systemd unit — the estate's only live front door is on the other Spark). So the segment films the overlay in **`fresh` mode** — its first-ever run on this machine — right after the update pass proves the `:9000` fleet green underneath it.

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **M1 Backup first** | Live config vs the repo's config-of-record | "Before an agent updates anything: snapshot what's *actually running* and commit it." The tracked example config is ~2 weeks behind the live box (it predates the current coach + the preload rotation) — **the drift is the content.** Be precise about the runbook's own net: its config-deploy step (bring-up §3.2) *does* auto-back-up any existing config (`config.yaml.bak-<ts>`) and fires a ⚠️ before replacing a divergent lineup — but it **never auto-restores**, and its end state is the PUBLIC config. So **on this box §3.2 does not run** — the live factory lineup outranks the public target — and §4.3's keepalive *install* is likewise skipped (the personal keepalive stays; only its active state is re-asserted). | Live config committed; timestamped backup exists; §3.2/§4.3-install explicitly out of scope |
| **M2 Recon, update mode** | The drift report scrolling | Run recon against the pinned sources; read the report out loud: **llama-swap v219** (built 2026-05-29 — carries the documented hot-reload full-preload hazard) vs latest · **vLLM serving images 2–6 months old** · two **llama.cpp build dirs** (May-30 general, Jul-25 coach pin) vs upstream · OS/driver **already current** (2026-07-30) — "recon *bounds* the work; half the estate needs nothing." | `DRIFT-*.md` emitted and committed |
| **M3 The three verdicts** | Drift report, annotated | The judgment beat — say each decision *before* touching anything: **UPDATE** (llama-swap binary — a real hazard motivates it; the stale vLLM images) · **DEFER with canary** (the May-30 llama.cpp build — any build ≥ 2026-07-29 requires a `llama-bench` prefill A/B first: an MMQ shared-memory gate merged that day has an open misfire report cratering prefill 1200→40 t/s on a healthy GPU) · **DECLINE** (the coach's Jul-25 pin — recon found **zero Gemma-4 changes upstream in the entire window since**; "the method says don't churn a pin with no delta behind it"). An agent that updates what needs it and *refuses* what doesn't is the whole thesis. | Three verdicts stated on camera before any mutation |
| **M4 Execute the bounded update** | The agent running the phases | **The PINS PR comes first** — the runbook *installs its pin* (§3.1's single `SWAP_VER` line, mirroring the PINS block), so "update llama-swap" is recon's `[DRIFT]` line becoming a reviewed edit to those two lines, *then* §3.1 re-runs at the new pin (conventions §6 — "the runbook never edits itself mid-run" said out loud). **The draft PR is already made: v219 → v245 (latest, released 2026-07-31) — this on-camera run is its validation half.** Then only the affected phases re-run: binary updated, fleet drained and revived, the **keepalive law** re-asserted (preload list ≡ keepalive allowlist — llama-swap doesn't revive crashed children), stale images refreshed. Gates re-prove: `/running` shows the preload set ready, the workhorse probe answers (`max_tokens ≥ 600` — small probes vanish into the reasoning channel). | PINS PR made + reviewed; fleet green re-proved; new baselines in RESULTS |
| **M5 Act two: LiteLLM, first install** | [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) fresh run | The overlay's Phase 1 *asserts* the `:9000` fleet is green (precondition gate, not prose), then installs the front door. Two things to say on camera: (1) LiteLLM is the deliberate **float-with-baseline** exception (conventions §3) — install latest, record the validated-at version in RESULTS; the contrast with the exact llama.cpp pins *is* the pins lesson; (2) the **no-cloud-fallback gates** run as anchored greps (`fallbacks: []` **and** `context_window_fallbacks: []`, comment-stripped cloud scan — DF-001): "auto cloud-fallback is the headline feature; I assert it off." Note the install is **additive** — nothing repoints at `:4000` in this video; consumers migrate later at their own pace. | `:4000` live · no-cloud greps PASS · routes gate PASS · validated-at version recorded |
| **M6 Segment close** | Both endpoints answering — the two Safari tabs (`:9000/ui` fleet green · `:4000` Swagger) beside the terminal | "The file that built this box just updated it, declined to churn what didn't need it, and added the front door — same method, same gates, months apart." | Box ends fleet-green with the front door live |

**Fixed recon inputs for this segment (verified on-box 2026-08-01 — reuse, don't re-derive):** llama-swap `v219` built 2026-05-29 (hot-reload re-runs the full preload; observed 115 GB peak on a July config reload) · newest vLLM image `v0.22.0-aarch64-cu129` (~2 months), oldest `26.01-py3` (~6 months) · driver `580.173.02`, OS patched 2026-07-30 · coach pin `720d7fa` = **vanilla mainline 2026-07-25, clean tree** — zero Gemma-4 merges upstream since (through b10219, 2026-08-01); its two named **watch-PRs** for future recon: q8_0 quantization value-range change (alters q8_0 KV numerics when merged) and default load-mode-auto on unified-memory devices · CUDA toolkit 13.0 (outside the 13.2+ CCCL top-k hazard) · config uses no `kv-unified` · LiteLLM absent (`:4000` closed, no unit) · latest llama-swap upstream = **v245** (2026-07-31; the PINS draft promotes v219→v245; v230's `-config-dir` flagged for a future promotion, not this one) · gpt-oss-20b `chat` **retired from the public lineup 2026-08-01** (over a year old, redundant beside the two 2026 MoEs — removed from config/LiteLLM/stage script/runbook coherently).

**Production notes for the segment:** film it *after* the P1–P7 spine or as a standalone short — it stands alone well ("I pointed the runbook back at the box it built"). The M3 verdicts moment is the must-land shot. If the llama-swap update itself misbehaves, keep it in — a gate catching a bad update and the rollback (old binary re-linked, fleet revived) is a *better* segment than a clean pass.

---

## Web dashboards — what to show (Safari on the MacBook, via the Pre-flight tunnel)

*Both UIs ride the one `ssh -L` tunnel from Pre-flight, so the on-camera URLs are the same `localhost` URLs a viewer types on their own box.*

- **llama-swap — `http://localhost:9000/ui` — the fleet made visible.** Three shots worth having:
  1. **Models page, preload set `ready`** (pairs with M4's `/running` gate) — the terminal *proves* the fleet is green; the UI is the same fact a viewer can *see*. Cut them together.
  2. **A swap, live** — one curl to a non-preload alias, then watch the state flip `stopped → starting → ready` while the upstream-log pane streams the llama-server boot. That's the lifecycle/memory layer doing its one job — the clearest twenty seconds of "what llama-swap *is*" you can film.
  3. **Activity during P6** — keep the UI beside the terminal while the DeepAgent/AutoBuild run hits the box: real requests from a real agent doing real work. The anti-benchmark point, made visually.
  - **Don't** click the UI's load/unload controls on this box mid-segment — model state belongs to the keepalive law (preload ≡ allowlist); here the UI is a window, not a control panel.
- **LiteLLM — `http://localhost:4000/` — an API surface, not an app.** After M5: the Swagger page at `/` (the OpenAI- and Anthropic-compatible surface in one place), then `http://localhost:4000/v1/models` listing the same fleet aliases through the front door — the "one endpoint" claim, visible in a browser. Say the honest bit out loud: this install is **DB-less**, so there is **no `/ui` spend dashboard** — that's the documented opt-in (Postgres + `master_key`, bottom of the example config), deliberately *not* part of this run; per-request cost still comes back on every response as `x-litellm-response-cost` — show the header once by running M5's gate curl with `-i`.

---

## Edit & publish kit (use after filming)

*Everything you reach for once filming is done — to cut the video and upload it. (No LLM prompts here — "talking points" below are lines to say, not a script.)*

- **Title options (utility-framed, never speed):**
  - "One Box, the Whole AI Loop: I Build Datasets, Fine-Tune & Host My Own Models — Then Build With Them"
  - "How a Software Engineer Runs a Local AI Lab on One Box (Dataset → Fine-Tune → Ship a Feature)"
  - "The Machine Behind My Software Factory: One DGX Spark, No Cloud"
- **Thumbnail text (no numbers):** `BUILD → FINE-TUNE → HOST → SHIP` · or `ONE BOX. THE WHOLE LOOP.`
- **Chapters** = the phases: `00:00` What it's for · The loop · How I got here · What a runbook is · The live run · Using it · **Maintaining it (the runbook updates the box + first LiteLLM install)** · Close.
- **Talking points (the spine, safe to repeat):** the box is a *factory floor*, not a benchmark rig · four jobs on one box (dataset · fine-tune · host · build) · one local front door — **LiteLLM → llama-swap + vLLM** — the full community stack, with a hard **no-cloud-fallback gate** · no cloud on the critical path · I went from *hand-debugging Claude-written scripts* to *executable runbooks an agent runs* — the game-changer · gotchas belong in *gates*, not prose · I'm pointing my own agents at my own models.
- **Do NOT:** quote tokens/sec or compare to a leaderboard (that's the forums' game — and the whole point is to *not* play it) · re-shoot for polish · script lines · cut the failures · let the camera slow the build.
- **Must-haves to make the video** (any gate that failed → a second session is fine): (1) the "what it's for / not a tok/s video" hook on camera, (2) the four-job loop explained, (3) the **origin story** — scripts → hand-debug → executable runbooks (the game-changer), (4) what a runbook-as-spec is (pinned · recon · gates), (5) the gate catching a trap live, (6) the box shown *doing useful work*, (7) the close, (8) the maintenance segment's **three-verdicts moment** (update / defer / decline, stated before touching anything) and the first LiteLLM install with the **no-cloud gate on camera**.

---

## Production notes

- **Relationship to the talk:** this video is the **machine** under the *Software Factory* talk — reuse the talk's Fleet Architecture (9), Dataset Factory (13), and Stack (14) slides as cutaways so the channel and the talk reinforce each other. Same narrative, more hands-on density.
- **Diagram:** P2 needs a simple single-Spark "the four jobs on one box" graphic (the loop: dataset → fine-tune → host → build, with **LiteLLM** as the front door over **llama-swap + vLLM**). Draw it once; reuse on the slide.
- **Origin-story sources (P3):** the real arc is on record — the early hand-debugged vLLM scripts (`scripts/archive-vllm/`), the prose `llama-swap-setup.md` "Setup Guide", and the **v2 → v3** deployment runbooks (`RUNBOOK-v2-all-llamacpp-architecture.md`, `RUNBOOK-v3-production-deployment.md`, private `guardkit` repo) where the production cutover surfaced traps. Pull a couple of those as on-screen B-roll to make "scripts → runbooks" concrete.
- **Live-demo safety:** record on a box where llama.cpp is already built so the run is ~8–10 min, not 90. The drift-report + gate-catch is the part that must land on camera; the long download/build is edited out.
- **Front door = LiteLLM (the full community stack), in two acts:** the box comes up as two runbooks — **act one** `RUNBOOK-single-spark-bring-up.md` stands up the **llama-swap `:9000`** fleet (a complete host on its own), and **act two** the optional overlay [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) bolts **LiteLLM `:4000`** on top — genuinely building *on top of* the martinB78/Dre stack, not a stripped-down version of it. LiteLLM is the unifier (one endpoint, per-agent virtual keys, usage/spend dashboard, `claude-*` wildcard routing); llama-swap stays the unified-memory/lifecycle layer underneath. The deliberate divergence to call out on camera (act two): **no cloud fallback** (`fallbacks: []` *and* `context_window_fallbacks: []`), enforced by a gate (DF-001).
  - ✅ **Both runbooks exist and are filmable:** the LiteLLM front-door phase + its gates (no-cloud-fallback; CPU-pin LiteLLM disjoint from llama-swap) live in [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) (extracted from the single-Spark runbook per `DECISION-DF-005`). Film act one to standing fleet, then act two for the front door + the no-cloud gate. Do the operator's end-to-end dry-run of both before recording so the live demo matches the narrative.

---
*Companion to `TALK`/`SLIDES-got-a-spark-now-what.md` and the Software Factory deck. The two-Spark payoff has its own spine: `CAPTURE-two-spark-video.md` — teed at the close as capacity, not speed.*
