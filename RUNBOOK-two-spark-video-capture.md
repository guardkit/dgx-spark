# Two-Spark Bring-Up — Video Capture Runbook

**Spine:** *A second node buys capacity, not speed worth stacking for — share the boxes by time, not at once.* (DECISION-DF-004)

**How to use this:** a capture *spine*, not a script. Record the real bring-up with OBS and narrate as you go. Don't re-shoot for polish, don't write lines, don't hide failures — the gotchas are the content. Don't let the camera slow the build; if a phase doesn't land, pick it up in a second session.
Audience: AI engineers. Target: ~12–18 min build-log + architecture explainer.

## The one idea (three beats — open on beat 1, close on beat 3)

1. **The intuition** — "Two boxes, twice the tokens, right?" Everyone assumes stacking = speed — and the leaderboards *look* like they agree, until you read what they measure.
2. **The reality** — a model that fits one box gains only ~1.3–1.5× single-stream from TP=2 (corti: ~35–50 → ~55–75 tok/s for a fitting ~120B) — at 2× the hardware, with **both** boxes claimed: a per-box regression. The near-2× two-node rows you've seen (e.g. Spark Arena's gpt-oss-120b) are **concurrency throughput** — the leaderboard tests at c=5/c=10 — i.e. parallelism, not speed. And the batch-1 killer isn't the 200G link's bandwidth (those all-reduces are kilobytes): it's per-layer sync **latency** plus the unsharded remainder; the ~25 GB/s ceiling (wired as 2× PCIe Gen5 x4, not one x8) binds at *prefill* and concurrency.
3. **The consequence** — so you still don't stack for speed — you stack for what one box **cannot do**: **capacity** (run the model that *cannot exist* on one 128 GB box — DeepSeek-V4-Flash-0731's native weights are ~167 GB) and **parallel throughput**, then **time-share** the boxes: the swap fleets own them day-to-day, the one oversized DeepSeek takes both for a session, and gated drain/revive makes the handover provable.

## Pre-read (open in tabs before recording)

- `diagrams/two-spark-fleet-serving-architecture.svg` and `diagrams/two-spark-request-routing.svg` — the **only two diagrams for this video** (the static topology + the request-routing). The `fleet-memory-write-path` diagram is a fleet-memory subsystem asset, out of scope for the two-Spark story.
- `DECISION-DF-004-two-spark-serving-topology-unified-front-door.md` (§2.1 topology, §2.2 memory rule)
- **`./RUNBOOK-two-spark-bring-up.md`** — the executable, gated fabric arc this video *films* in P2 (its Phases 2–7). Run it once before recording.
- **`./RUNBOOK-deepseek-v4-flash-0731-two-spark.md`** — the DeepSeek seat overlay P3 films (supersedes the bring-up runbook's old Phase 8 jasl lane, which is now the pinned fallback). Its PINS block is the source of every number and flag in P3.
- `two-spark-serving-research-and-references.md` (the gotchas + the expected numbers)
- **`./RUNBOOK-orbit-globe-demo-capture.md`** — the payoff segment this video tees at P5 (a MacBook agent doing real work against the DeepSeek seat).

## Pre-flight — recording setup &nbsp; · &nbsp; **Gate:** scenes ready, diagrams loaded, terminal legible

- OBS scenes: (a) desk/hardware cam, (b) full-screen terminal, (c) diagram/browser. Terminal font ≥ 18pt.
- Both Sparks powered; CX-7 cable in hand for the cold open; single clean shell, history cleared.

## Capture phases

| # | On screen | Say (prompts, not lines) | Gate (pass/fail) |
|---|-----------|--------------------------|------------------|
| **P1 Hook** | The two Sparks + the cable | Beat 1 then beat 3 in ~30s: "I stacked two of these — and the lesson wasn't what I expected." | Thesis stated on camera |
| **P2 Bring-up** *(the war story)* | Firmware **verify** BOTH nodes — already at 28.45.4028 (checked 2026-08-02 from boot logs; no flash — tell the Apr-2026 *all_gather-halving* story and the **held `mlnx-fw-updater`** brick guard rather than performing an update). Bonus gotcha to show live: **the CX-7 isn't in `lspci` until you cable it** (Jan-2026 hot-plug power-gating, ~18 W) — watch it appear on insertion; if a QSFP56 DAC flaps (~20 s vanishing act), the hotplug-disable flag is the fix (bring-up Phase 3 notes) → cable to **any** QSFP port each end (same-port is tidiness, *not* required; don't cable both ports or it halves to 100 GbE) → `ibdev2netdev (Up)`, use `enp1…` (4 names for 2 ports) → pin fabric `NCCL_SOCKET_IFNAME/UCX_NET_DEVICES/OMPI_MCA_btl_tcp_if_include` → `all_gather_perf -b 16G -e 16G -f 2` | Narrate each gotcha live. The money gotcha: the firmware **hard power-off under load** (still open Jun-2026) — show `-lgc 200,2150` **and** say it's unverified, the real fix is thermal (repaste/airflow). Then the silent one: busbw can look fine while NCCL fell back to **TCP** — prove RoCE with `NCCL_DEBUG=INFO` = `NET/IB`. | Link `(Up)` + busbw ≥ ~20 GB/s + `NET/IB` (not `NET/Socket`) on camera |
| **P3 Proof** *(the model that can't fit one box)* | Run [`RUNBOOK-deepseek-v4-flash-0731-two-spark.md`](./RUNBOOK-deepseek-v4-flash-0731-two-spark.md) on camera: drain gate (`/running` empty both nodes) → worker-first launch of the B12X runtime (official 0731 weights, ~84 GB/node; **Patch 4** proven from the loader log — zero dropped `shared_experts`) → warm-up (5 long gens, cold costs ~30%) → the perf + **tool-calling** gates | The capacity thesis made literal: "these native weights are ~167 GB — there is **no** single-box build of this model at real quality; the only thing that fits one Spark is an unmeasured 2-bit quant. Two boxes don't make this model faster — there is no one-box version to compare against; they make it *exist*." Read the numbers as they land: decode **55–67 tok/s mean / ~84 peak** (DSpark speculation, acceptance ~60% — *halves* if Patch 4 is missing), prefill **~1,500 tok/s @8k → ~2,600 @100k**, ~**197 tok/s aggregate** at 6 streams, cold start ~6–8 min. Two teachable traps on camera: **benchmark with `stream:false`** (SSE emits one chunk per decode *step* under speculation — stream-counting under-reads ~4×), and **NVFP4 is the KV cache, not the weights** — a full **1M-token context costs ~10 GiB/node** ("context is nearly free; weights are the whole problem"). Close the phase on the **Phase 5.6 tool-call gate** (parsed `tool_calls`, zero DSML leaks, spec decode ON) — "that green light is what makes the next video possible." | Drain gate + Patch-4 log line + decode/prefill/cold-start + 5.6 tool-calls captured on camera |
| **P4 Payoff** *(architecture)* | The two SVG diagrams | Walk the layered stack: one **LiteLLM :4000** front door → **llama-swap** pools (the day-to-day fleets) → **DeepSeek-V4-Flash-0731 TP=2** across both nodes when a session needs it. State the **memory rule** (the ~105 GiB/node DeepSeek and the swap fleets can't co-reside — the runbook *drains with a gate and revives against a snapshot*, so the handover is proven, not hoped) and the **no auto cloud fallback** guard (DF-001 — LiteLLM stays up through the DeepSeek seat window; it's a router, and its gates still refuse the cloud). | Topology + "share by time" rule + the gated handover explained |
| **P5 Close** | Back to hardware / diagram | Restate beat 3; then the tee: "next video, this seat does real work — a coding agent on my MacBook builds a live satellite globe against it, and checks its own work against the sky" ([`RUNBOOK-orbit-globe-demo-capture.md`](./RUNBOOK-orbit-globe-demo-capture.md)). | Lesson restated; demo teed |

## Evidence / RESULTS — prompt pack (for the edit + publish)

- **Title options:** "I Stacked Two DGX Sparks — It Wasn't Faster (Here's Why)" · "DeepSeek V4 Flash on Two DGX Sparks — 1M Context, No Cloud" · "Two-Node Local LLM Serving — The Honest Bring-Up"
- **Thumbnail text:** `2× THE BOX ≠ 2× THE SPEED` · or `167 GB OF MODEL. 128 GB OF BOX.`
- **Chapters** = the phases: `00:00` Hook · Bring-up · The model that can't fit one box · The architecture · Close.
- **Lower-third captions** (drop your real numbers): decode mean/peak tok/s (spec acceptance %) · prefill @8k/@100k · aggregate @6 streams · cold-start time · link busbw · KV GiB @1M ctx.
- **Say-these truths** (the spine, safe to repeat): the interconnect is the ceiling · TP only for models that don't fit one node — and 0731 literally doesn't · NVFP4 here means the KV cache, context is nearly free · stack for capacity + parallelism · share the boxes by time, not at once — with gates, not hope.
- **Do NOT:** re-shoot for polish · script lines · cut the failures · let the camera slow the build.
- **Must-haves to make the video** (any gate that failed → a second session is fine): (1) thesis on camera, (2) ≥2 bring-up gotchas captured live, (3) the DeepSeek seat numbers + the Patch-4/`stream:false` traps, (4) the **5.6 tool-call gate green** (it tees the demo video), (5) the architecture explainer with the gated drain/revive, (6) the close.

---
*Source material: DECISION-DF-004 (corrected 2026-06-22), the executable `./RUNBOOK-two-spark-bring-up.md` (fabric) + `./RUNBOOK-deepseek-v4-flash-0731-two-spark.md` (the serving lane of record, updated 2026-08-01/02; the old jasl FP8 Phase-8 lane ~44 tok/s remains its pinned fallback), `two-spark-serving-research-and-references.md`, and the `diagrams/` SVGs. Numbers in P3 are captured live, not pre-stated — the figures quoted here are the recipe's published expectations, used only to know when a live number looks wrong. The same-physical-port "requirement" was a myth — any QSFP port works (official connect-two-sparks playbook).*
