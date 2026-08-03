# Runbook: DeepSeek-V4-Flash-0731 — Two Sparks, Native Weights, 1M Context

**Purpose:** serve DeepSeek-V4-Flash-0731 (284B/13B-active MoE, MIT) across the two-Spark pair at native quality — FP4-QAT experts + FP8 attention, NVFP4 applied to the **KV cache only** — with DSpark speculative decoding, as an on-demand **planning/teaching seat**. The fleet is drained for the session and provably revived at the end; both acts are gated phases of this runbook.
**Machine:** both nodes (Node A = head, Node B = worker).
**Predecessor:** [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) Phases 2–7 (firmware, cable, NCCL fabric, mesh SSH, front-door guard). This overlay **supersedes that runbook's Phase 8** (the plain-FP8 DeepSeek — eugr Docker default, jasl reference build), which remains the pinned **fallback lane**.
**Execution-results:** `RESULTS-deepseek-v4-flash-0731-first-run.md` (create on first run; template in Appendix B).
**Expected wall-clock:** first run ~2–3 h (runtime image builds ~30–60 min/node dominate — edit out of any recording; weights must be pre-staged, see Phase 1.3). Re-run on a built box: ~25 min including the mini-soak. DeepSeek cold-start alone: ~6–8 min.

**Target architecture**

```
   Node A (head)                          Node B (worker)
 ┌──────────────────────────┐          ┌──────────────────────────┐
 │ vLLM DSpark runtime      │  CX-7    │ vLLM DSpark runtime      │
 │ TP=2 rank 0  · API :8888 │◄────────►│ TP=2 rank 1              │
 │ ~84 GB weights shard     │ 200G     │ ~84 GB weights shard     │
 │ NVFP4 MLA KV (~10 GiB/1M)│ NET/IB   │ NVFP4 MLA KV             │
 └──────────────────────────┘          └──────────────────────────┘
   llama-swap :9000 STOPPED               llama-swap :9000 STOPPED
   (drained Phase 1.6, revived Phase 9 — the pool XOR DeepSeek rule)
```

**Execution modes**

```
  fresh    — run top to bottom (first bring-up of the 0731 seat)
  re-run   — same file on a built pair; idempotent phases no-op, gates re-verify
  update   — Phase 0 recon reports drift; re-run affected phases; record new baselines in RESULTS
```

**Overlay contract (conventions §2.1):** Phase 1 is a machine-checked precondition gate on the two-spark bring-up's *output state* (fabric + firmware + front-door), not a pointer to re-run it. From there this file executes only its own delta.

---

## PINS (single source of truth)

```
PINS (set 2026-08-01)
  recipe repo        github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark
                     @ d728faee9f5a8d5ebafe7bc44bca6c5d8d0d192f          (HEAD at pin date)
  runtime image      vllm-dspark-runtime:dspark-nvfp4-stage-c            (built per node from the recipe;
                     Patches 2b+3 baked IN — Patch 4 is NOT, see next pin)
  PATCH 4            manual read-only bind-mount of the patched dspark.py (recipe README, 2026-07-31)
                     MANDATORY for 0731 — without it the draft loader silently drops 12 shared-expert
                     tensors and acceptance collapses 60.2% → 25.7% (decode ~halves)
  weights            deepseek-ai/DeepSeek-V4-Flash-0731    167 GB · 48 shards · native FP4-QAT experts
                     + FP8 attention · DSpark drafter ships IN-weights (no second model)
  spec decode        method=dspark · num_speculative_tokens ≤ 5   (dspark_block_size=5; the HF card
                     recommends 7 — a TRAP: nst>5 silently collapses acceptance to ~4%)
  KV cache dtype     nvfp4_ds_mla        (patched-build-only; stock vLLM rejects the dtype)
  context lanes      1M lane:   --max-model-len 1048576  --max-num-seqs 6   spec-3
                     short lane: --max-model-len 163840   --max-num-seqs 12  spec-5
                     (1,048,576 is the calibrated YaRN ceiling — never run the old 1.5M profile)
  gpu_mem_util       0.78    (spec-decode buffers allocate LAZILY on first request — do not raise)
  B12X MoE backend   VLLM_USE_B12X_MOE=1   (the entire speed difference; =0 → ~29 tok/s silently)
  MTP_NUM_TOKENS     5       (recipe .env leftover =3 costs ~24% decode)
  tool calling       --tokenizer-mode deepseek_v4 · --tool-call-parser deepseek_v4 ·
                     --reasoning-parser deepseek_v4 · --enable-auto-tool-choice
                     + the model card's OFFICIAL ENCODING PACKAGE (encoding_dsv4.py via
                     DSPARK_ENCODING_FILE — the model card ships NO Jinja template; the
                     MiaAI-Lab compose auto-installs it on both nodes).
                     ⚠️ SUPERSEDES t/372268 post 538 (--tokenizer-mode hf + mounted
                     chat_template.jinja): four adverse reports 08-02/03 INCLUDING ITS OWN
                     AUTHOR (#540 · #544 invalid JSON at high/max · #554 jinja re-renders
                     destroy prefix cache · #558 tool calls return empty) and an explicit
                     recommendation against (#560). Native deepseek_v4 tokenizer is
                     deterministic and cache-friendly. REQUIRED for the demo lane.
  crash knobs        VLLM_DSPARK_GPU_REJECTED_CONTEXT_MASK=1 (Patch-2 ragged-path
                     requirement) · NO repetition_penalty anywhere (illegal-memory crash;
                     if one appears anyway, remove it before any other diagnosis)
  socket ifnames     GLOO_SOCKET_IFNAME + TP_SOCKET_IFNAME = same value as
                     NCCL_SOCKET_IFNAME (PR #13: TP init FAILED on a non-author Spark
                     pair without them; zero cost if redundant)
  KV fallback        fp8_ds_mla if nvfp4_ds_mla misbehaves (the author's firmware is
                     stated NOWHERE — nvfp4_ds_mla on our FW 28.45.4028 is unproven
                     until our smoke; PR #13 anticipated this with a KV_CACHE_DTYPE env)
  LANE fallback #2   MiaAI-Lab/DeepSeek-v4-Flash-DSpark-2x-DGX-Spark — prebuilt
                     ghcr.io/anemll/dspark-vllm-gx10:0.1.1 (Patch-4-equivalent BAKED, same
                     nvfp4_ds_mla/1M/TP=2, no manual mount; one named forum reproducer)
  A/B candidate      eugr B12X 0731 stack — archived at vendor/eugr-0731-ab/ (fp8 KV;
                     runs as a measured A/B in a LATER session, never this bring-up)
  head/API           Node A :8888  ·  worker-first launch order (worker up before head)
  MEM_CEILING_GB     115 per node        (121 usable; freeze observed at 114)
  fabric (inherited) CX-7 FW ≥ 28.45.4028 · NCCL busbw ≥ 20 GB/s · transport NET/IB (never TCP)
  FALLBACK lane      eugr/spark-vllm-docker @ f7d6e3b5 · recipe deepseek-v4-flash · FP8 TP=2 · MTP k=2
                     · Docker, --no-ray --port 8080   (= two-spark runbook Phase 8, the escape hatch;
                     0731 is architecture-identical to the April checkpoint so the recipe carries over.
                     The ~42–44 tok/s expectation is from the jasl/vllm @ dda4668b + torch 2.9.1
                     reference build, kept for A/B — re-baseline the eugr lane on first exercise)
```

---

## Phase 0: Recon (read-only, advisory) — emits the drift report

### 0.1 Deterministic pin checks

```bash
# Recipe repo HEAD vs pin
PINNED=d728faee9f5a8d5ebafe7bc44bca6c5d8d0d192f
LATEST=$(git ls-remote https://github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark HEAD | cut -f1)
[ "$PINNED" = "$LATEST" ] && echo "recipe: pinned == HEAD" || echo "DRIFT: recipe HEAD moved ($LATEST)"

# Weights repo revision (record it; the 0731 repo should be static post-release)
python3 - <<'EOF'
from huggingface_hub import HfApi
print("weights revision:", HfApi().model_info("deepseek-ai/DeepSeek-V4-Flash-0731").sha)
EOF

# Runtime image present? (informs whether Phase 2 will build or no-op)
docker image inspect vllm-dspark-runtime:dspark-nvfp4-stage-c >/dev/null 2>&1 \
  && echo "image: present" || echo "image: absent (Phase 2 builds it)"
```

### 0.2 Source scan (fixed list, LLM judgment)

```
RECON SOURCES (fixed)
  - recipe repo commits + issues        (esp. anything superseding Patch 4, image rebuilds;
                                         PR #13 portability merge state · Issue #16 think-token)
  - NVIDIA forum thread 378824          (the recipe's companion thread — new field reports)
  - NVIDIA forum thread 372268 tail     (tool-calling/parser consensus moves here first)
  - MiaAI-Lab/DeepSeek-v4-Flash-DSpark-2x-DGX-Spark  (the baked-image fallback lane — image tags)
  - vLLM PR #41834 (SM12x enablement)   (if MERGED into a release: upstream may retire this fork path)
  - HF deepseek-ai/DeepSeek-V4-Flash-0731 discussions (checkpoint issues, template/parser bugs)
RECON TASK
  "Report only items newer than the PINS date affecting a pinned component or a known
   gotcha (Appendix A). Emit a drift report. Do NOT propose edited steps. Do NOT change any pin."
```

### 0.3 Emit `DRIFT-deepseek-v4-flash-0731-<timestamp>.md` (conventions §5) and commit it.
**▶ GATE (advisory):** operator reviews `[DRIFT]`/`[FLAG]` items; the run proceeds on current PINS. Degrades gracefully (DF-001): network down → `recon: skipped`, proceed on PINS.

---

## Phase 1: Pre-flight — precondition + drain gates (go/no-go)

### 1.1 Fabric green (the predecessor's output state, re-asserted live)
```bash
# On BOTH nodes: link up
ibdev2netdev | grep -q "(Up)" && echo PASS || { echo "FAIL: CX-7 link not Up — run two-spark Phases 2-3"; exit 1; }
# Quick NCCL re-assert (short all_gather run, both signals — see two-spark Phase 4 for the full form):
#   busbw ≥ 20 GB/s  AND  log shows NET/IB transport (TCP fallback = FAIL, ~12 tok/s downstream)
```

### 1.2 Firmware floor (both nodes)
```bash
mstflint -d $(ibdev2netdev | awk '{print $1}' | head -1) q | grep -i 'FW Version' \
  # assert >= 28.45.4028 — the Apr-2026 all_gather-halving regression floor
```

### 1.3 Weights staged (both nodes) — stage OVERNIGHT, never on the clock
```bash
D=$(python3 -c "from huggingface_hub import snapshot_download; print(snapshot_download('deepseek-ai/DeepSeek-V4-Flash-0731', local_files_only=True))" ) \
  && echo "PASS: cache at $D" || { echo "FAIL: weights not fully staged"; exit 1; }
ls "$D"/*.safetensors | wc -l   # assert 48 shards
du -s --block-size=1G "$D"      # assert ≥ 165 GB
# uid-1000 lock-file trap: the container writes HF lock files — cache must be writable by uid 1000
[ -w "$D" ] && echo PASS || echo "FAIL: HF cache not writable by uid 1000"
```

### 1.4 Disk + driver sanity (both nodes)
```bash
df --output=avail -BG / | tail -1        # assert ≥ 60 GB free (image build headroom)
nvidia-smi --query-gpu=driver_version --format=csv,noheader   # assert ≥ 580.173.02
# libcuda "file too short" trap (forum field report 2026-08-01): host libcuda must be sane
S=$(stat -c%s /lib/aarch64-linux-gnu/libcuda.so.1 2>/dev/null || echo 0); [ "$S" -gt 1000000 ] \
  && echo PASS || echo "FAIL: host libcuda.so.1 missing/truncated — do not launch containers"
```

### 1.5 Snapshot the fleet, then drain — **▶ GATE: pool XOR DeepSeek, asserted not assumed**
```bash
# On BOTH nodes, record the pre-drain state (Phase 9 revives against this snapshot):
curl -s localhost:9000/running > /tmp/predrain-$(hostname).json && cat /tmp/predrain-$(hostname).json
# Drain:
systemctl --user stop llama-swap-keepalive.timer llama-swap
# Assert drained + memory actually returned:
curl -s --max-time 3 localhost:9000/running | grep -q . && { echo "FAIL: llama-swap still answering"; exit 1; } || echo "PASS: drained"
free -g | awk '/^Mem:/ { if ($7 >= 110) print "PASS: " $7 " GB available"; else { print "FAIL: only " $7 " GB available"; exit 1 } }'
```

---

## Phase 2: Runtime image + Patch 4 (both nodes, idempotent)

```bash
# Clone at the PIN (skip-if-present at the right commit):
git clone https://github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark ~/dspark-recipe
git -C ~/dspark-recipe checkout d728faee9f5a8d5ebafe7bc44bca6c5d8d0d192f
# Build the Stage A/B/C runtime (heavy — 30-60 min; no-ops if the image exists):
cd ~/dspark-recipe && ./build-dspark-vllm-runtime.sh
docker image inspect vllm-dspark-runtime:dspark-nvfp4-stage-c >/dev/null && echo PASS || exit 1
```

**Patch 4 (mandatory for 0731 — the image does NOT contain it):** stage the patched `dspark.py` per the recipe README ("two lines, no rebuild — bind-mount it read-only" over the image's `/opt/env/lib/python3.12/site-packages/vllm/v1/spec_decode/dspark.py`).
**⚠️ TWO files in the recipe are named `dspark.py` — this is the root of the forum's filepath confusion. Patch 4's target is `recipe/overlay/vllm/v1/spec_decode/dspark.py`** (the proposer's `_STACKED_PARAM_NAME_MAPPING`, lines 15–18; the patch header reads `--- a/vllm/v1/spec_decode/dspark.py`). It is **NOT** `recipe/overlay/vllm/models/deepseek_v4/nvidia/dspark.py` (the draft weight loader — already baked into stage-c; never mount that one).
**▶ GATE — version-match:** the patched file must come from **this image's** vLLM tree (a `dspark.py` lifted from another vLLM version crashes with `propose() got an unexpected keyword argument`). Extract the image's own copy, apply the two-line w1/w3→`gate_up_proj` mapping to *that*, and diff to confirm only those lines changed:

```bash
docker run --rm --entrypoint cat vllm-dspark-runtime:dspark-nvfp4-stage-c \
  /opt/env/lib/python3.12/site-packages/vllm/v1/spec_decode/dspark.py > /opt/dspark/dspark.orig.py
# apply the recipe's Patch 4 hunk to a copy → /opt/dspark/dspark.patched.py
diff /opt/dspark/dspark.orig.py /opt/dspark/dspark.patched.py | grep -c '^[<>]'   # assert exactly the patch's line count
```

---

## Phase 3: Configuration — every trap is an anchored grep

Copy `~/dspark-recipe/.env.dspark.example` → `.env.dspark` and set for OUR topology (direct CX-7 link, not the recipe's RoCE switch). Then assert — do not eyeball:

```bash
cd ~/dspark-recipe
grep -q '^DSPARK_MODEL=deepseek-ai/DeepSeek-V4-Flash-0731$' .env.dspark && echo PASS \
  || echo "FAIL: DSPARK_MODEL — the example DEFAULTS TO THE PREVIEW checkpoint"
grep -q '^VLLM_USE_B12X_MOE=1$'  .env.dspark && echo PASS || echo "FAIL: B12X off → ~29 tok/s silently"
grep -q '^MTP_NUM_TOKENS=5$'     .env.dspark && echo PASS || echo "FAIL: leftover =3 costs ~24% decode"
grep -Eq 'num_speculative_tokens.:\s*[1-5]\b' docker-compose.dspark.yml && echo PASS \
  || echo "FAIL: nst > 5 collapses acceptance to ~4% (dspark_block_size=5)"
grep -q 'nvfp4_ds_mla' docker-compose.dspark.yml && echo PASS || echo "FAIL: KV dtype"
grep -q 'max-model-len 1048576' docker-compose.dspark.yml && echo PASS || echo "FAIL: ctx (no 1.5M profile)"
# NCCL pinned to the direct-link iface (resolve per node via ibdev2netdev — never hardcode):
grep -Eq '^NCCL_SOCKET_IFNAME=' .env.dspark && grep -Eq '^NCCL_IB_HCA=' .env.dspark && echo PASS || echo FAIL
# Crash trap: server-side repetition_penalty on the spec-decode path = illegal memory access
grep -rq 'repetition_penalty' docker-compose.dspark.yml .env.dspark && echo "FAIL: remove it" || echo PASS
# Patch 4 bind-mount present in the compose:
grep -q 'dspark.patched.py:/opt/env/lib/python3.12/site-packages/vllm/v1/spec_decode/dspark.py:ro' \
  docker-compose.dspark.yml && echo PASS || echo "FAIL: Patch 4 not mounted"
# Tool calling — the demo lane dies without these (and raw DSML leaks into content without the parsers):
grep -q 'tokenizer-mode deepseek_v4'    docker-compose.dspark.yml && echo PASS || echo "FAIL: NATIVE deepseek_v4 tokenizer-mode (the hf+jinja path is SUPERSEDED — see PINS)"
grep -q 'tool-call-parser deepseek_v4'  docker-compose.dspark.yml && echo PASS || echo "FAIL: tool-call parser"
grep -q 'reasoning-parser deepseek_v4'  docker-compose.dspark.yml && echo PASS || echo "FAIL: reasoning parser"
grep -q 'enable-auto-tool-choice'       docker-compose.dspark.yml && echo PASS || echo "FAIL: auto tool choice"
grep -q 'chat_template.jinja' docker-compose.dspark.yml \
  && echo "FAIL: mounted Jinja template present — the post-538 path is KNOWN-BAD (#540/#544/#554/#558/#560); remove it" || echo "PASS: no jinja mount"
grep -qE 'DSPARK_ENCODING_FILE|encoding_dsv4' .env.dspark docker-compose.dspark.yml \
  && echo PASS || echo "FAIL: official encoding package not wired (encoding_dsv4.py via DSPARK_ENCODING_FILE)"
grep -q 'VLLM_DSPARK_GPU_REJECTED_CONTEXT_MASK=1' .env.dspark && echo PASS || echo "FAIL: Patch-2 ragged-path mask"
# Socket ifnames — TP init failed on a non-author Spark pair without these (PR #13):
grep -qE '^GLOO_SOCKET_IFNAME=' .env.dspark && grep -qE '^TP_SOCKET_IFNAME=' .env.dspark \
  && echo PASS || echo "FAIL: set GLOO_SOCKET_IFNAME + TP_SOCKET_IFNAME = NCCL_SOCKET_IFNAME's value"
# Container plumbing: network_mode host · ipc host · shm 64gb · /dev/infiniband · memlock unlimited
```

---

## Phase 4: Launch (worker-first) — **▶ GATE: Patch 4 proven from the loader log**

```bash
# Node B first: ./start-deepseek-v4-flash-dspark.sh worker   → then Node A: ... head
# Cold start ~6-8 min. Then, on the head:
curl -s localhost:8888/v1/models | grep -q DeepSeek-V4-Flash-0731 && echo PASS || exit 1
docker logs dspark-head 2>&1 | grep -q "B12X" && echo "PASS: B12X MoE backend active" || echo FAIL
# THE load-bearing assertion — the draft loader must NOT have dropped shared-expert tensors:
docker logs dspark-head 2>&1 | grep "Skipping unknown DSpark weight" | grep -c "shared_experts" \
  # assert 0 — any hit means Patch 4 did not take; acceptance will read ~25% in Phase 5. HALT.
docker logs dspark-head 2>&1 | grep -i "KV cache size"   # record tokens + GiB in RESULTS (expect ~1.5M tok / ~10 GiB)
```

---

## Phase 5: Warm-up + performance gates — **benchmark with `stream:false`, never stream deltas**

Under speculative decoding vLLM emits at most one SSE chunk per decode *step* — counting stream deltas measures steps/s, not tok/s (14.7 vs 60.1 on the same request). All gates below use `"stream": false` and the API's own token counts + wall time.

```bash
# 5.1 Warm-up: FIVE long generations (~1k tokens each) — cold-start costs ~30%; do not gate on them.
# 5.2 Acceptance gate (the Patch 4 functional proof):
curl -s localhost:8888/metrics | grep spec_decode   # assert mean acceptance ≥ 0.50 (post-fix 0.602; unpatched 0.257)
# BANKED FAILURE SIGNATURES (diagnose by shape, not guesswork):
#   Signature A — drafting healthy but acceptance ~26%: Patch 4 mount not in effect. A WRONG
#     mapping raises KeyError loudly (DSPARK-SHARED-EXPERT-FIX.md), so clean boot + low
#     acceptance = the mount is MISSING, not wrong.
#   Signature B — ~12 tok/s, acceptance 1.5-4.5%, mean accept length ~1.1: the mixed-quant
#     drafter corruption seen ONLY on the quantized -NVFP4 checkpoint (t/378824 #11-12).
#     If you see this, you are serving the WRONG WEIGHTS — assert --model points at the
#     official deepseek-ai/DeepSeek-V4-Flash-0731 snapshot, not a -NVFP4 variant.
# 5.3 Decode gate: structured/counting prompt, single stream, stream:false
#     assert ≥ 45 tok/s   (expected 55-67 mean, 84 peak; ~30 = the unpatched signature → HALT, recheck Phase 2)
# 5.4 Prefill sanity: ≥ 1,000 tok/s at 8k-token prompt (expected ~1,500 @8k, ~2,600 @100k)
# 5.5 Expectation table (do NOT false-fail on content class):
#     structured 55-84 · code/JSON ~54-64 · narrative prose 31-35 tok/s single-stream
#     mixed agent traffic ~88 tok/s aggregate at c=4 (~22/stream)
# 5.6 TOOL-CALLING gate — run WITH speculative decoding ON (the draft-rejection trap):
#     DSpark spec decode can shred the tool-call opener tag at draft-rejection boundaries,
#     leaking calls into content as raw DSML (t/372268 post 296). Four blocking sub-checks
#     (each maps to a reported 08-02/03 failure mode on the retired hf+jinja path):
#     (a) FIVE live requests with a simple tools=[...] schema, stream:false → every response
#         carries choices[0].message.tool_calls as a PARSED array, content holds zero raw
#         DSML markup, AND the follow-up turn returns NON-EMPTY content (t/372268 #558:
#         calls fired but answers came back empty);
#     (b) reasoning separation: <think>/reasoning lands in reasoning_content, never in
#         content (recipe Issue #16, open — watch it);
#     (c) tool-JSON validity at reasoning_effort HIGH and MAX (t/372268 #544: invalid JSON
#         appeared only at high/max);
#     (d) a 3-turn session keeps the prefix cache warm (TTFT turn-3 ≪ turn-1 — the #554
#         regression class the jinja path caused).
#     Any failure: interpose the opencode_compat_proxy shim (Appendix A) or reduce
#     num_speculative_tokens and re-test — do NOT record the harness demo until all clean.
```

---

## Phase 6: Front door (optional lane) — `deepseek` alias, no-cloud guard re-proven

Add to the LiteLLM `:4000` config: `model_name: deepseek` → `openai/deepseek-v4-flash-0731`, `api_base: http://<NODE_A>:8888/v1`. Then **re-run the two-spark runbook's Phase 7 anchored no-cloud greps verbatim** (`fallbacks: []`, `context_window_fallbacks: []`, no cloud model in any chain after comment-stripping). A new alias is exactly when that gate earns its keep (DF-001).

The coding-harness demo workspace for this endpoint lives at [`demo/orbit-globe/`](./demo/orbit-globe/) — harness wiring (pi primary, opencode backup), AGENTS.md + skills environment, and the task brief. It presumes Phase 5.6 green.

---

## Phase 7: Mini-soak — **▶ GATE: clean 10 minutes at c=4**

The 0731 checkpoint has <48 h of public field time; the recipe's 40-min soak was on the preview. This phase is our own evidence: 10 min mixed traffic at concurrency 4. Assert: zero HTTP errors · zero empty/soft-empty completions · `free -g` available on both nodes within 3 GB of its post-launch value (memory-growth guard). Record request count, aggregate tok/s, and acceptance in RESULTS.

---

## Phase 8: Decision Gate

| # | Gate | Threshold | Result |
|---|------|-----------|--------|
| 1.1 | CX-7 link + NCCL | busbw ≥ 20 GB/s, NET/IB | |
| 1.2 | Firmware | ≥ 28.45.4028 both | |
| 1.3 | Weights | 48 shards, ≥165 GB, writable, both | |
| 1.4 | Driver/libcuda | ≥ 580.173.02, libcuda sane | |
| 1.5 | Drain | `/running` empty both, ≥110 GB avail | |
| 2 | Image + Patch 4 staged | version-matched diff | |
| 3 | Config traps | all anchored greps PASS | |
| 4 | Launch | B12X active, **zero dropped shared_experts**, /v1/models 200 | |
| 5.2 | Acceptance | ≥ 0.50 | |
| 5.3 | Decode | ≥ 45 tok/s structured, stream:false | |
| 5.4 | Prefill | ≥ 1,000 tok/s @8k | |
| 5.6 | Tool calls (spec decode ON) | 5/5 parsed `tool_calls`, zero DSML leaks | |
| 6 | No-cloud guard | anchored greps PASS | |
| 7 | Mini-soak | 0 errors, 0 empty, mem stable | |
| 9 | **Fleet revived** | preload ready both, probes answer | |

---

## Phase 9: Teardown + fleet revival — the runbook ends fleet-green, provably

```bash
# Stop the DeepSeek seat (both nodes):
cd ~/dspark-recipe && docker compose -f docker-compose.dspark.yml down
# Revive (both nodes):
systemctl --user start llama-swap && systemctl --user start llama-swap-keepalive.timer
# ▶ GATE: revive proven against the Phase 1.5 snapshot, not assumed:
curl -s localhost:9000/running    # assert the preload set is state=ready on each node (diff vs /tmp/predrain-*.json)
# Node A workhorse probe — max_tokens ≥ 600 (the reasoning channel eats small probes):
#   assert non-empty content. Node B: assert the office front door answers again (its :8477 page loads).
```

---

## Appendix A — Known-issues register (recon watches these; gates catch them)

| Issue | Status at pin date | Caught by |
|---|---|---|
| Draft-loader drops shared_experts w1/w3 (0731) | Patch 4 manual, NOT in image | Phase 4 log gate + 5.2 acceptance |
| `VLLM_USE_B12X_MOE` unset → ~29 tok/s | silent | Phase 3 grep + 5.3 decode |
| nst > 5 → acceptance ~4% | HF card recommends 7 (trap) | Phase 3 grep |
| Preview checkpoint is the `.env` default | silent wrong-model | Phase 3 grep + Phase 4 /v1/models |
| Server-side repetition_penalty → illegal memory access crash | documented | Phase 3 grep |
| Stream-delta benchmarking undercounts ~4× | methodological | Phase 5 preamble |
| libcuda.so.1 "file too short" in container (aarch64, 08-01 field report, unresolved) | open | Phase 1.4 |
| Recipe issue #8: EngineDeadError under chat traffic (pre-Patch-3 era) | open, status unclear | Phase 7 soak |
| Cold-start ~30% perf penalty | expected | Phase 5.1 warm-up |
| gpu_mem_util > 0.78 + lazy spec buffers → OOM on first request | design | PINS |
| Fabric validated by recipe author on a RoCE **switch**; ours is the direct link | our variance | Phase 1.1 NCCL gate |
| DSpark draft-rejection shreds tool-call opener → raw DSML leaks (t/372268 post 296) | open; parser not spec-aware | Phase 5.6 gate; fallback = 0rand `opencode_compat_proxy` shim (90/100 hardmode after) |
| Harness 400s on `developer` role / `reasoning_effort` (typical vLLM) | expected | harness compat flags — see `demo/orbit-globe/README.md` |
| The t/372268 post-538 tool path (`--tokenizer-mode hf` + jinja mount) | **SUPERSEDED 08-03** — 4 adverse reports incl. its author (#540/#544/#554/#558/#560) | PINS pin the native `deepseek_v4` tokenizer + encoding package; Phase 3 grep FAILS if a jinja mount reappears |
| Missing `<think>` token in reasoning content (recipe Issue #16, opened 08-02) | open | Phase 5.6(b); recon watches the issue |
| GB10 UMA accounting: available KV capacity varies 4.22–5.34 GiB across boots (vLLM #48140) | open | clean reboot before the demo session; record the boot's KV line in RESULTS |
| Concurrent-agent fairness: `--max-num-batched-tokens 8192` starves decode under concurrent prefill | single-source (t/378890, published harness) | OPTIONAL: 2048 for multi-agent sessions (p95 gap 6.1s→1.6s); not for the single-stream demo |

## Appendix B — Rollback + RESULTS template

**Rollback:** Phase 9 teardown + revival *is* the rollback — the fleet returns regardless of gate outcomes (run it even after a mid-run HALT). The staged weights and image persist for the next attempt (~230 GB disk; reclaim with `docker rmi` + HF cache delete only on an explicit abandon decision). **Fallback serving lane:** two-spark runbook Phase 8 (eugr Docker FP8; ~42–44 tok/s = the jasl reference-build number) — architecture-identical checkpoint, config carries over.

**RESULTS records:** recipe commit · image digest · weights revision · per-node resident GB at idle/launch/soak · KV pool tokens+GiB · acceptance · decode (structured/code/narrative) · prefill @8k/@100k · soak table · revive diff vs snapshot · deviations.
