# RESULTS — DeepSeek-V4-Flash-0731 first run (2026-08-08)

**Runbook:** [`RUNBOOK-deepseek-v4-flash-0731-two-spark.md`](./RUNBOOK-deepseek-v4-flash-0731-two-spark.md) · mode **fresh** · executed by agent (Claude Code / Fable 5)
**Nodes:** A = promaxgb10-41b1 (head, :8888) · B = spark-fcf6 (worker) · direct CX-7 link 169.254.207.1 ↔ .2 (enp1s0f1np1 / rocep1s0f1 both)

## Pins as executed

| Component | Value |
|---|---|
| recipe commit | `cd366d5e20a00426f3c6fce1f08a179acd936262` (HEAD drift: +1 docs-only commit bf3d4ea, not taken) |
| runtime image | `vllm-dspark-runtime:dspark-nvfp4-stage-c` — Node A `sha256:9e0455a2181b…`, Node B `sha256:84b5294ff161…` (per-node builds, same source) |
| image vLLM version | `0.21.1rc1.dev339+g1967a5627bc3` (stage-c import check green both nodes) |
| weights revision | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` (48 shards, 156 GiB deref = 167 decimal GB, both nodes) |
| drift report | [`DRIFT-deepseek-v4-flash-0731-2026-08-08.md`](./DRIFT-deepseek-v4-flash-0731-2026-08-08.md) + execution-time addendum (7652c4e) — run proceeded on PINS |

## Phase log

| Phase | Result | Evidence |
|---|---|---|
| 0 recon | PASS (advisory) | pins re-verified live; addendum committed; no new pin-affecting drift |
| 1.1 fabric | **PASS** | all_gather busbw **22.17 GB/s** ≥ 20, transport **NET/IB** (16G, post-drain re-run; pre-drain attempt failed on buffer alloc with fleet resident — ordering artifact, not fabric) |
| 1.2 firmware | **PASS** | 28.45.4028 both nodes (boot log; mstflint needs sudo — used journalctl) |
| 1.3 weights | **PASS** | 48 shards both; `du -sL` 156 GiB (runbook's `du -s` reads ~1 GB — HF snapshot dirs are symlinks; check needs `-L`); writable uid 1000 both |
| 1.4 disk/driver | **PASS** | 218G / 2581G free; driver 580.173.02 both; libcuda 96 MB sane both (real path `/usr/lib/aarch64-linux-gnu/`, runbook's `/lib/…` stale) |
| 1.5 drain | **PASS** | snapshots `/tmp/predrain-*.json` (A: coach-ft-v4, embed, qwen36-workhorse · B: embed, gemma4-tutor, parakeet-tdt-0.6b-v3, qwen3-tts-0.6b, tutor-coach); drained; **111 / 112 GB** available (B needed ~8 s to settle) |
| 2 image+Patch 4 | **PASS** (deviation D1) | built ~45 min/node in parallel; **Patch 4 mapping PRE-BAKED in image** at this pin — mount staged with each image's own copy (diff vs orig = 0; both `shared_experts.gate_up_proj` tuples present; B's copy byte-identical to pinned overlay source) |
| 3 config | **PASS 19/19** | all anchored greps green (one first-pass fail = banned string in an explanatory comment, reworded) |
| 4 launch | **PASS** | worker-first via orchestrator script; cold start ~9 min (shards 2:30 + draft pass 0:32); `/v1/models` root field + served id `deepseek-v4-flash-0731` ✓; B12X Mxfp4 backend ✓; **0 dropped shared_experts BOTH nodes** (the Patch 4 log gate); KV **1,976,191 tokens**; script smoke chat ✓ |
| 5.2 acceptance | **PASS** | structured request delta: **0.994 per-token, mean accept length 5.97/6**. Content-class blended: narrative-only warm-up read 0.256 (= coincidentally the banked unpatched figure — content mix, not Patch 4; see note N1) |
| 5.3 decode | **PASS** | structured counting, stream:false: **83.8 tok/s** (≥45; = table's 84 peak) |
| 5.4 prefill | **PASS** | **1,529 tok/s** @ 7k prompt (≥1,000; table ~1,500 @8k) |
| 5.5 classes | recorded | code/JSON **77.6** (band 54–64, above) · narrative **30.3** (band 31–35, at floor) · warm-up narrative 29.9–32.3 |
| 5.6 tools | **PASS after in-run fix** | (a) 5/5 parsed tool_calls, 0 DSML leaks, follow-ups non-empty · (a+) multi-turn 2nd in-session call clean (MiaAI #21 guard) · (b) no reasoning spill (note N2) · (c) /tokenize: max **+79 tok**, high **+0** (silent no-op confirmed), low +0; tool JSON valid at max+low · (d) prefix cache warm 2.66→0.62 s · (e) **first run FAIL — one empty `tool_calls: []` SSE delta (t/372268 #573)**; applied the Appendix-A one-line parser patch (image's own `deepseekv32_tool_parser.py` + fix, ro bind-mount, both nodes), relaunched, re-verified — see below |
| 6 front door | **PASS** | canonical row pair deployed to `/opt/litellm/config.yaml` (backup: `config.yaml.bak-0731-run`); bare-`deepseek` row count ==1; upstream id + `:8888` greps ✓; `deepseek-fp8` present ✓; live listing shows both names; bare alias returned `SEAT-0731-OK` from the seat; down lane failed loudly (500, `Fallbacks=None`); both no-cloud greps ✓ |
| 7 mini-soak | **PASS** | 10 min @ c=4: **152 requests, 0 HTTP errors, 0 empty, 0 soft-empty**; aggregate **80.5 tok/s**; mix 26 structured / 26 code / 25 json / 25 qa / 25 narrative / **25 tools**; memory **flat** (A 13→13, B 16→16 GB avail); soak accept-len 2.94 (corruption watch ≤2.0: clean); no #607-class engine death under concurrent variable-length tool traffic |
| 9 revival | **PASS** | seat down both nodes; llama-swap restarted both; `/running` **identical to pre-drain snapshots** (A: 3 models, B: 5 models, all ready); workhorse probe non-empty (needed max_tokens **1500** — reasoning ate 700, see D6); Node B end-to-end: gemma4-tutor answered via :9000, audio-parakeet/qwen3tts self-recovered healthy, study_tutor_http healthy. `:8477` probe **unverifiable as written** (D6) |

## Phase 8 decision gate

| # | Gate | Threshold | Result |
|---|------|-----------|--------|
| 1.1 | CX-7 link + NCCL | busbw ≥ 20 GB/s, NET/IB | **PASS — 22.17 GB/s, NET/IB** |
| 1.2 | Firmware | ≥ 28.45.4028 both | **PASS — 28.45.4028 both** |
| 1.3 | Weights | 48 shards, ≥165 GB, writable, both | **PASS — 48 / 156 GiB (=167 GB) / writable, both** |
| 1.4 | Driver/libcuda | ≥ 580.173.02, libcuda sane | **PASS — 580.173.02, 96 MB libcuda both** |
| 1.5 | Drain | `/running` empty both, ≥110 GB avail | **PASS — 111 / 112 GB** |
| 2 | Image + Patch 4 staged | version-matched diff | **PASS — patch pre-baked; mount = image's own copy (D1)** |
| 3 | Config traps | all anchored greps PASS | **PASS 19/19** |
| 4 | Launch | B12X, zero dropped shared_experts, /v1/models 200, served id | **PASS — all four, both nodes** |
| 5.2 | Acceptance | ≥ 0.50 | **PASS — 0.994 structured delta (N1)** |
| 5.3 | Decode | ≥ 45 tok/s structured | **PASS — 83.8** |
| 5.4 | Prefill | ≥ 1,000 tok/s @8k | **PASS — 1,529 @7k** |
| 5.6 | Tool calls (spec ON) | 5/5 parsed, zero DSML leaks | **PASS — incl. multi-turn; (e) pass after #573 fix (N3)** |
| 6 | Front door | bare row ==1 → :8888 · fp8 present · no-cloud | **PASS — + live routing proof both lanes** |
| 7 | Mini-soak | 0 errors, 0 empty, mem stable | **PASS — 152/0/0, flat** |
| 9 | Fleet revived | preload ready both, probes answer | **PASS — snapshot-identical, live completions both nodes** |

**VERDICT: ALL GATES GREEN — the 0731 DSpark seat is validated end-to-end and the fleet is provably revived.**

## Deviations

- **D1 — Patch 4 pre-baked:** PINS state "Patch 4 is NOT in the image", but the pinned commit's `recipe/overlay/vllm/v1/spec_decode/dspark.py` carries the w1/w3→gate_up_proj mapping ("Added 2026-07-31") and the build bakes the overlay in. The bind-mount is therefore the image's own copy (version-match gate trivially satisfied, foreign-version crash impossible); the runbook's "diff == patch line count" expectation doesn't apply to a pre-applied patch. Functional proof deferred to the Phase 4 loader-log gate + 5.2 acceptance. **Amendment candidate:** PINS Patch-4 wording for images built from cd366d5e onward.
- **D2 — keepalive timer absent:** `llama-swap-keepalive.timer` (named in Phase 1.5/9) is not loaded on either node; only `llama-swap.service` exists. Drain/revive operate on what exists; revive gate is the snapshot diff + probes.
- **D3 — builder's worker-build tail step:** `build-dspark-vllm-runtime.sh` defaults `WORKER_BUILD=1` and errors post-build without `WORKER_HOST` (env file didn't exist at build start). Both nodes' local images built and self-validated; the redundant cross-build step was skipped by that error. Harmless.
- **D5 — transient XOR violation via unit dependency:** `litellm.service` carries `Wants=llama-swap.service`, so the Phase 6 litellm restart silently revived llama-swap (embed seat loaded; Node A fell to 2 GB available with 10 GB swap in use). Caught by the pre-soak memory check; remedied by re-stopping llama-swap (A recovered to 13 GB avail). **Amendment candidate:** Phase 6 must re-assert the drain after any litellm restart (or the seat session should mask llama-swap: `systemctl --user mask --runtime llama-swap` during drain).
- **D4 — runbook check nits:** weights-size check needs `du -sL` (D1.3); libcuda path is `/usr/lib/aarch64-linux-gnu/` on this OS layout; Phase 4's illustrative container name `dspark-head` is actually `dspark-recipe-vllm-dspark-1`.
- **D6 — Phase 9 probe defects:** (a) the workhorse probe's "max_tokens ≥ 600" is insufficient — qwen36-workhorse (`--reasoning auto`) spent >700 tokens reasoning on the probe question and returned empty content; 1500 produced a clean answer. (b) The Node B ":8477 office front door" exists nowhere but the runbook line (no unit/container/compose/listener on B references it — pre-existing, not a casualty of this run); substituted functional probes: gemma4-tutor completion via :9000 + audio/tutor container health. **Amendment candidates:** raise the probe budget; replace or delete the :8477 assertion.

## Notes

- **N1 — acceptance is strongly content-dependent:** per-token acceptance measured 0.994 on structured counting vs 0.256 on narrative essays (mean accept length 5.97 vs 2.28). The 5.2 gate's single blended `/metrics` number is meaningless without the traffic mix — measure a structured-request *delta* when re-running. The banked "unpatched = 0.257" figure can be coincidentally reproduced by an all-narrative mix on a healthy patched engine.
- **N2 — reasoning channel:** with `thinking:true` + effort max, probes returned clean direct answers; `reasoning_content` stayed empty, zero `<think>` markers or token-eating in content (usage ≈ visible text). Consistent with Issue #16's refinement (encoder puts `<think>` in the prompt). Chat-UI reasoning spill not observed on this stack today.
- **N3 — in-run remedy applied (#573):** gate 5.6(e) caught one empty `tool_calls: []` SSE delta. Root cause in image source: `deepseekv32_tool_parser.py:299–300` passes an explicitly-empty list into content-only `DeltaMessage`s (the v4 parser subclasses v3.2). Fix = the thread's one-liner (emit `tool_calls` only when non-empty), staged at `/opt/dspark/deepseekv32_tool_parser.patched.py` on both nodes, mounted ro in the compose next to the Patch 4 mount. Amendment candidate: bake into the next image pin or adopt PR #17's minimal guard when merged.

## Measurements

(to be filled during Phases 4–7)

- per-node memory — post-drain: A 111 / B 112 GB avail · at launch: A 110 / B 107 GB **used** · post-Phase-5 + re-drain: A 13 / B 16 GB avail · post-soak: identical (flat)
- KV pool: **1,976,191 tok (boot 1) · 1,731,449 tok (boot 2)** — the known boot-to-boot UMA wobble, both > the ~1.5M expectation; GiB line not emitted by this vLLM version
- acceptance (per-token accepted/drafted · mean accept length): structured **0.994 · 5.97/6** · narrative 0.256 · 2.28 · soak mix 0.388 · 2.94
- decode single-stream: structured **83.8 tok/s** · code/JSON **77.6** · narrative **30.3** (warm-up 29.9–32.3)
- prefill: **1,529 tok/s @ 7k** (@100k not measured this run — optional, table expects ~2,600)
- soak: 152 req / 615 s @ c=4 · **80.5 tok/s aggregate** · 0 errors / 0 empty / 0 soft-empty · mix 26/26/25/25/25/25 (structured/code/json/qa/narrative/tools)
- effort mechanics: /tokenize max **+79 tok**, high **+0** (silent no-op confirmed), low +0; tool JSON valid at max and low
- cold start: ~9 min boot 1 (shards 2:30 cold) · boot 2 shards ~32 s (page-cache warm)
- revive diff vs snapshot: **identical both nodes** — A {coach-ft-v4, embed, qwen36-workhorse} · B {embed, gemma4-tutor, parakeet-tdt-0.6b-v3, qwen3-tts-0.6b, tutor-coach}, all `ready`
