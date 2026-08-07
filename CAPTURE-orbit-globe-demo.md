# Orbit Globe, Two Ways — Video Capture Spine

**Spine:** *Same model, same task, asked twice — once like a demo, once like an engineer. The difference was never the model.*

**Status: PARKED (2026-08-06) — no globe video is planned.** Every cut of this — the single demo, the harness-eval experiment (git history: `acb4323`), the two-take A/B below — ends up *a demo that looks like the genre's existing demos* (the operator's verdict). The [`demo/orbit-globe/`](./demo/orbit-globe/) workspace stays as repo bonus content and possible b-roll for the two-Spark video. The selected follow-up direction is now the standalone [DeepSeek continual harness-learning experiment](./BRIEF-deepseek-harness-demo-task-selection.md), subject to its feasibility gates. This file is kept only as the record of the rejected staged-demo approach.

**What this films:** the payoff for the two-Spark/DeepSeek material (teed at the two-Spark video's P5; also stands alone). One task — the whole-sky satellite globe in [`demo/orbit-globe/`](./demo/orbit-globe/) — attempted twice by the same local DeepSeek, with the same mechanical checker run on both attempts. Red, then green. One command carries the whole video: `npm run validate`.

**The context (one beat, said warmly):** the "Best Open Model You Can Actually Run" video one-shot an ISS tracker on this same hardware — genuinely impressive, and its ISS was visibly in the wrong place, waved off with "we can tweak the API call." Not a dunk: *nobody* in the demo genre checks. This video is the check.

**Before recording (all off camera):**
1. [`RUNBOOK-deepseek-v4-flash-0731-two-spark.md`](./RUNBOOK-deepseek-v4-flash-0731-two-spark.md) green **including its tool-calling gate** — a coding agent is nothing but tool calls; without it there is no Take 2.
2. MacBook: pi installed + pointed at the Sparks — the exact steps are in [`demo/orbit-globe/README.md`](./demo/orbit-globe/README.md).
3. One full dry run of Take 2, then delete the built `index.html` so the recorded take starts clean.

**How to use this:** a capture spine, not a script. Prompts to say, not lines. Don't hide failures — the fail→fix loop is the content.

---

## Take 1 — the demo everyone makes (~4 min of film)

| Step | On screen | Say (prompts, not lines) |
|---|---|---|
| 1 | `mkdir ~/one-shot && cd ~/one-shot`, launch `pi`, paste the big prompt (committed at [`demo/orbit-globe/foil-prompt.txt`](./demo/orbit-globe/foil-prompt.txt) — `pbcopy < …` before the take) | "This is the move you've seen in every local-model video — the whole ask in one giant prompt. Including my favourite line: *'make sure the ISS placement is accurate.'* Said to a model, that's a wish." |
| 2 | A globe appears. Admire it | Be honest: "…and look at it. This is why the genre exists. The model deserves the hype." |
| 3 | The check: `cp index.html <clone>/demo/orbit-globe/`, then `cd <clone>/demo/orbit-globe/validate && npm run validate` | "Now the question nobody asks: is any of it *true*? This checker doesn't read the code's opinion of itself — it does its own orbital math and asks the live tracking API where the ISS actually is." |
| 4 | Red FAIL lines land | "There's the difference between a demo and engineering: **who checks.**" Delete the foil's `index.html` on camera. |

## Take 2 — the same brain, asked like an engineer (~8 min of film)

| Step | On screen | Say |
|---|---|---|
| 1 | `cd <clone>/demo/orbit-globe`, `ls`, open `AGENTS.md` and a skill briefly | "Same model, same task — the brief is word-for-word what Take 1 got. What's different is the *folder*: conventions, two pages of domain notes, and that same checker sitting right there. No mega-prompt — the environment is the engineering." |
| 2 | Launch `pi`, type one sentence: `Build the constellation globe described in TASK.md — follow the workspace conventions.` | "One sentence, because everything else is already here." |
| 3 | Watch it work — reading the notes, building, then **running the checker itself** and fixing its own red lines | Narrate lightly. If gates fail then pass, **leave it in — the fix loop is the film**. If it's green first try, say so plainly ("the loop was armed; it didn't need it — that happens"). |
| 4 | The close, in a second terminal — **you** type `npm run validate` | "Its 'all green' is a claim in its own transcript. This one is mine. And the physics gate still answers to the sky, not to the code it just wrote." Green lands. |
| 5 | Hero shot: the constellation, time-warp, click a satellite for its orbit, the ISS readout | "The gates prove it's *correct*. Whether it's *beautiful* stays a human call — deliberately." |

**The closing line of the video:** *"Same model. Same task. Same checker. Red, then green — and the only thing that changed was how I asked. The difference was never the model."*

---

## If things go wrong on camera (keep rolling)

| Symptom | Meaning | Move |
|---|---|---|
| pi 400s immediately | vLLM rejecting `developer` role / `reasoning_effort` | the two compat flags in `~/.pi/agent/models.json` (workspace README) — a 10-second on-camera fix |
| Tool calls appear as raw `<…DSML…>` text | the endpoint's tool-call phase isn't green | stop; re-run the DeepSeek runbook's tool-calling phase — don't film |
| Physics gate fails but the SGP4 gate passes | live-API hiccup or sim drift | reload (it boots at 1× real time), re-run; if persistent, lean on the SGP4 oracle and say so |
| **The one-shot passes everything** | it happens — a good day | film Take 2 anyway and say the truth: "this one landed — but I only *know* that because the checker exists. One lucky demo doesn't make checking optional." |
| Agent claims green, your close run fails | the exact moment the independent close exists for | **keep it in** — worth more than any clean take |
| Everything green everywhere, no drama | also happens | don't fake a failure; the dry-run footage can illustrate the loop if needed |

## Production notes

- **Fairness is the credibility of the whole video**: Take 1's pasted prompt carries the same brief Take 2's workspace does (task, rules, status-object contract, approved endpoints) — say so on camera. The variable is the *asking*, never the information.
- **Edit out**: installs, long silent generation (jump-cut + tok/s overlay). Warm the endpoint (a few long generations) before either take; expect ~55–67 tok/s on code, prose slower.
- **No leaderboard comparisons** — the only evidence in this video is produced on screen.
- **Stay generous to the demo genre** — it's the audience, not the villain.
- **Evidence for the description/pinned comment**: both validator outputs, both prompts, the repo path `demo/orbit-globe/`.

## Relationship to the other artifacts

- [`CAPTURE-two-spark-video.md`](./CAPTURE-two-spark-video.md) — the preceding video (capacity, not speed worth stacking for); its P5 tees this one.
- [`VIDEO-executable-runbooks.md`](./VIDEO-executable-runbooks.md) — owns the gates philosophy this video applies to a freshly generated artifact.
- [`demo/orbit-globe/README.md`](./demo/orbit-globe/README.md) — the workspace: pi setup, the validator's three tiers, and `foil-prompt.txt` (Take 1's pasted brief).
