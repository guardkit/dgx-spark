# Runbook: DeepSeek-V4-Flash-0731 — Two Sparks, Native Weights, 1M Context

**Purpose:** serve DeepSeek-V4-Flash-0731 (284B/13B-active MoE, MIT) across the two-Spark pair at native quality — FP4-QAT experts + FP8 attention, NVFP4 applied to the **KV cache only** — with DSpark speculative decoding, as an on-demand **planning/teaching seat**. The fleet is drained for the session and provably revived at the end; both acts are gated phases of this runbook.
**Machine:** both nodes (Node A = head, Node B = worker).
**Predecessor:** [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) Phases 2–7 (firmware, cable, NCCL fabric, mesh SSH, front-door guard). This overlay **supersedes that runbook's Phase 8** (the jasl FP8 DeepSeek), which remains the pinned **fallback lane**.
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
  tool calling       --tool-call-parser deepseek_v4 · --reasoning-parser deepseek_v4 ·
                     --enable-auto-tool-choice · --tokenizer-mode hf + chat_template.jinja
                     mounted :ro  (the endorsed 0731 solution — forum t/372268 post 538;
                     thinking via --default-chat-template-kwargs thinking_mode=thinking).
                     REQUIRED for the coding-harness demo lane (demo/orbit-globe/) —
                     the base NVFP4-KV recipe does NOT ship these.
  head/API           Node A :8888  ·  worker-first launch order (worker up before head)
  MEM_CEILING_GB     115 per node        (121 usable; freeze observed at 114)
  fabric (inherited) CX-7 FW ≥ 28.45.4028 · NCCL busbw ≥ 20 GB/s · transport NET/IB (never TCP)
  FALLBACK lane      jasl/vllm @ dda4668b + torch 2.9.1 · FP8 TP=2 · MTP k=2 · ~42–44 tok/s
                     (= two-spark runbook Phase 8, kept as the escape hatch; 0731 is architecture-
                     identical to the April checkpoint so that recipe carries over)
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
  - recipe repo commits + issues        (esp. anything superseding Patch 4, image rebuilds)
  - NVIDIA forum thread 378824          (the recipe's companion thread — new field reports)
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
grep -q 'tool-call-parser deepseek_v4'  docker-compose.dspark.yml && echo PASS || echo "FAIL: tool-call parser"
grep -q 'reasoning-parser deepseek_v4'  docker-compose.dspark.yml && echo PASS || echo "FAIL: reasoning parser"
grep -q 'enable-auto-tool-choice'       docker-compose.dspark.yml && echo PASS || echo "FAIL: auto tool choice"
grep -q 'tokenizer-mode hf'             docker-compose.dspark.yml && grep -q 'chat_template.jinja' docker-compose.dspark.yml \
  && echo PASS || echo "FAIL: hf tokenizer-mode + mounted chat template (t/372268 post 538 — the 0731 fix)"
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
# 5.3 Decode gate: structured/counting prompt, single stream, stream:false
#     assert ≥ 45 tok/s   (expected 55-67 mean, 84 peak; ~30 = the unpatched signature → HALT, recheck Phase 2)
# 5.4 Prefill sanity: ≥ 1,000 tok/s at 8k-token prompt (expected ~1,500 @8k, ~2,600 @100k)
# 5.5 Expectation table (do NOT false-fail on content class):
#     structured 55-84 · code/JSON ~54-64 · narrative prose 31-35 tok/s single-stream
#     mixed agent traffic ~88 tok/s aggregate at c=4 (~22/stream)
# 5.6 TOOL-CALLING gate — run WITH speculative decoding ON (the draft-rejection trap):
#     DSpark spec decode can shred the tool-call opener tag at draft-rejection boundaries,
#     leaking calls into content as raw DSML (t/372268 post 296). Assert the parsed path:
#     (a) template sanity: prompts at reasoning_effort low/high/max produce ~5/84/97
#         template tokens respectively (post 538's verification) — record in RESULTS;
#     (b) FIVE live requests with a simple tools=[...] schema, stream:false → every response
#         carries choices[0].message.tool_calls as a PARSED array AND content holds zero raw
#         DSML/tool markup. Any leak = the draft-rejection bug: interpose the
#         opencode_compat_proxy shim (Appendix A) or reduce num_speculative_tokens and
#         re-test — do NOT record the harness demo until 5/5 clean.
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

## Appendix B — Rollback + RESULTS template

**Rollback:** Phase 9 teardown + revival *is* the rollback — the fleet returns regardless of gate outcomes (run it even after a mid-run HALT). The staged weights and image persist for the next attempt (~230 GB disk; reclaim with `docker rmi` + HF cache delete only on an explicit abandon decision). **Fallback serving lane:** two-spark runbook Phase 8 (jasl FP8, ~42–44 tok/s) — architecture-identical checkpoint, config carries over.

**RESULTS records:** recipe commit · image digest · weights revision · per-node resident GB at idle/launch/soak · KV pool tokens+GiB · acceptance · decode (structured/code/narrative) · prefill @8k/@100k · soak table · revive diff vs snapshot · deviations.
