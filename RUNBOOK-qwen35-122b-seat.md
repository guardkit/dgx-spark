# Runbook: qwen3.5-122b single-Spark seat (spark-fcf6)

**Purpose:** stand up **Qwen3.5-122B-A10B** as a *standing* strong-tier seat on `spark-fcf6` at the full native 262,144-token context — the DGX-Spark half of the DF-031 two-box router experiment (weak/plan tiers stay on the Dell ProMax's always-on fleet; this seat is the strong tier the router escalates to).
**Machine:** `spark-fcf6` (DGX Spark GB10, 128 GB unified; this repo's "Node B").
**Predecessors:** `RUNBOOK-two-spark-bring-up.md` Node B green (fcf6 fleet on `:9000`, LiteLLM door on `:4000`). The DeepSeek two-box seat must be **down** (Mode 1) — seat-XOR applies on this box too.
**Execution-results link:** `RESULTS-qwen35-122b-seat.md` (written once, at the final phase of the first run).
**Expected duration:** ~90 min first run (the ~64 GB weight pull dominates) + ~15 min gates.
**Research of record:** `ai-transition/docs/two-box-router-research-2026-08-16.md` (all figures cited there; this runbook pins the fastest *fully-pinned* community recipe — DFlash speculative decoding over AutoRound INT4, 53.7–59 tok/s measured, ~81 tok/s on tool-call-heavy agent work).

> **DISPLACEMENT — read before running (Rich's decision, taken at launch):** this is a **dedicated** seat in the OPERATOR doc's Mode-3 shape. The fcf6 llama-swap fleet (embed, gemma4-tutor, parakeet, qwen3-tts, tutor-coach — the study-tutor stack) is **drained while the seat stands** and revived at teardown (Appendix A). A shared-mode variant exists only as an unmeasured option (Appendix B) and is not executable from this runbook.

**Target architecture:**

```
Mac (Switchyard :4100)                    spark-fcf6
  strong tier ──────────────▶ LiteLLM :4000 ── row qwen35-122b ──▶ vLLM (Docker) :8888
                                    │                                Qwen3.5-122B-A10B INT4-AutoRound
                                    ▼                                + DFlash 0.8B drafter (speculative)
                          llama-swap :9000 fleet                     ctx 262,144 · util 0.82 · bf16 KV
                          (DRAINED while seat stands)
Dell ProMax (untouched): workhorse + architect always-on behind its keyed :4000
```

```
Execution modes:
  fresh    — run top to bottom (first stand-up of the seat)
  re-run   — same file on a built box; idempotent phases no-op, gates re-verify
  update   — Phase 0 recon reports drift; re-run affected phases; new baselines in RESULTS
```

---

## PINS (runbook v1, set 2026-08-16)

```
target model        Intel/Qwen3.5-122B-A10B-int4-AutoRound     (~64 GB; HF revision: RESOLVE-AT-RECON, freeze in RESULTS)
drafter             z-lab/Qwen3.5-122B-A10B-DFlash             (0.8B; HF revision: RESOLVE-AT-RECON, freeze in RESULTS)
engine image        AEON-7 sm121 vLLM 0.23 image               (EXACT TAG: RESOLVE-AT-RECON from t/374328; freeze digest in RESULTS)
SERVED_ID           qwen35-122b
SEAT_PORT           8888
CTX                 262144
GB10_UTIL           0.82        (swap onset measured at 0.87+; a freeze at 0.84 with fastsafetensors — never raise past 0.85)
KV_TYPE             bf16        (per t/374328; the fp8-KV / int8-lm-head expansion is Appendix B, not this lane)
SPEC_TOKENS         7           (t/378167 config; DFlash acceptance 6.5–8.3 measured)
MEM_USED_MAX_GB     109         (the community stability envelope for THIS stack — do not substitute the fleet's 120 GB experience)
MEM_FREE_MIN_GiB    15          (free under peak load, t/374328)
DECODE_FLOOR        35 tok/s    (structured; recipes measure 46–59 — 35 is the halt line)
COLD_START_MAX      900 s       (first load; LiteLLM row timeout must exceed this)
```

**Float-with-baseline / RESOLVE-AT-RECON note (CONVENTIONS §3):** three pins above cannot be honestly frozen from off-box research — the two HF revisions and the exact engine-image tag. Recon resolves them from the fixed sources below, the run freezes what actually ran into `RESULTS`, and a follow-up commit to this PINS block ratifies them (§6 promotion — a reviewed commit, never a mid-run edit). The gates prove the resolved versions serve correctly regardless.

---

## Phase 0: Recon (read-only; emits a drift report; degrade gracefully if sources are down)

```
RECON SOURCES (fixed)
  - forums.developer.nvidia.com t/374328   (DFlash on 1× Spark — the recipe of record: exact image tag + launch flags)
  - forums.developer.nvidia.com t/378167   (fp8-KV/int8-lm-head variant + SPEC_TOKENS config)
  - forums.developer.nvidia.com t/365639   (AutoRound INT4 quick-start; the torch-pin crash-class fix)
  - huggingface.co/Intel/Qwen3.5-122B-A10B-int4-AutoRound   (revision)
  - huggingface.co/z-lab/Qwen3.5-122B-A10B-DFlash           (revision)
  - huggingface.co/Qwen/Qwen3.5-122B-A10B                   (card: native ctx 262,144 — assert unchanged)
RECON TASK
  Resolve the three RESOLVE-AT-RECON pins (exact image tag; both HF revisions; the verbatim
  vLLM launch flags incl. the speculative-config syntax from t/374328's quick-start).
  Report only items newer than 2026-08-16 that affect a pin or a known gotcha.
  Output a drift report. Do NOT propose edited steps. Do NOT change any pin.
```

## Phase 0.5: Pre-flight (no side effects)

```bash
df -h /home | awk 'NR==2 {print ($4+0 >= 80) ? "PASS disk" : "FAIL disk <80G free"}'
ss -ltn | grep -q ":8888 " && echo "FAIL port 8888 taken" || echo "PASS port free"
docker info >/dev/null 2>&1 && echo PASS docker || echo FAIL docker
curl -s -m 3 localhost:9000/v1/models >/dev/null && echo PASS fleet-alive || echo FAIL fleet
curl -s -m 3 localhost:4000/v1/models >/dev/null && echo PASS door-alive || echo FAIL door
free -g | awk '/Mem:/ {print "baseline free:", $7, "GB"}'   # snapshot only, no gate yet
docker ps --format '{{.Names}}' | grep -qi deepseek && echo "FAIL deepseek seat active (seat XOR)" || echo "PASS no deepseek seat"
```

## Phase 1: Precondition gate (overlay rule — halt if the base is not green)

▶ **GATE:** `curl -s -m 5 localhost:9000/v1/models | grep -q workhorse && echo PASS || echo FAIL` — Node B's fleet is the proven base state this overlay stands on. FAIL → STOP (fix the fleet first; never build a seat on an unknown box state).

## Phase 2: Stage weights (idempotent; no serving change yet)

```bash
hf download Intel/Qwen3.5-122B-A10B-int4-AutoRound --revision <RECON>   # ~64 GB
hf download z-lab/Qwen3.5-122B-A10B-DFlash        --revision <RECON>   # ~1.6 GB
```

▶ **GATE:** both snapshots present at the recon-resolved revisions (`hf scan-cache | grep -c …` == 2) → PASS; else STOP.

## Phase 3: Drain the fleet (Mode-3 ritual — the displacement the header names)

```bash
systemctl --user stop llama-swap        # tutor stack, tts, parakeet, embed go down HERE
systemctl --user status llama-swap --no-pager | grep -q inactive && echo PASS drained || echo FAIL
```

▶ **GATE — memory headroom:** `free -g | awk '/Mem:/ {print ($7 >= 110) ? "PASS" : "FAIL free<110G"}'` — projected seat residency (~100 GB at util 0.82) needs a clean box. FAIL → find the squatter (`docker ps`, `nvidia-smi`), never launch over it. *(Registry: the 121 GB-ceiling row, adapted to this stack's envelope.)*

## Phase 4: Launch the seat

Run the recon-resolved image with the recon-resolved flags from t/374328's quick-start — the shape (values from PINS):

```bash
docker run -d --name qwen122b-seat --gpus all --restart unless-stopped -p 8888:8888 \
  <IMAGE:RECON> vllm serve Intel/Qwen3.5-122B-A10B-int4-AutoRound \
  --served-model-name qwen35-122b --port 8888 \
  --max-model-len 262144 --gpu-memory-utilization 0.82 \
  <SPECULATIVE-CONFIG FLAGS: RECON — DFlash drafter, num_speculative_tokens 7>
```

▶ **GATE — comes up within the cold window:** `/health` returns 200 within `COLD_START_MAX` (poll; ~9 min cold starts are normal for seats this size on this box). FAIL → `docker logs qwen122b-seat`, STOP.
▶ **GATE — memory envelope:** used ≤ `MEM_USED_MAX_GB` **and** free ≥ `MEM_FREE_MIN_GiB` **and** swap delta == 0 (`free -g`, gate on **total** unified memory, not compute-apps). Any breach → STOP and tear down; do not "just lower util a little" mid-run (§6: that is a PINS change).

## Phase 5: Serving gates (the seat proves itself)

▶ **5.1 smoke:** a completion returns from `:8888` (`.choices[0].message.content` non-empty, model id `qwen35-122b`). FAIL → STOP.
▶ **5.2 context:** `/v1/models` reports `max_model_len == 262144`, and a ~30K-token prompt completes without truncation error. FAIL → STOP.
▶ **5.3 throughput:** structured-task decode ≥ `DECODE_FLOOR` tok/s (measure as the DeepSeek runbook does: `stream:false`, tokens/duration). Below floor → STOP; the recipes measure 46–59, so a floor miss means a wrong pin resolved, not "GB10 slowness".
▶ **5.4 long generation:** one request generating ≥ 90 s wall-clock completes through `:8888` — the router-timeout trap probe (a 60 s router default upstream is a known community failure against 120B-class models).

## Phase 6: Front-door row (the ONLY serving-config edit this runbook makes)

Add to fcf6's LiteLLM config (backup first, as `config.yaml.bak-122b-seat`):

```yaml
- model_name: qwen35-122b
  litellm_params: { model: openai/qwen35-122b, api_base: "http://localhost:8888/v1", timeout: 900 }
```

▶ **GATE — exactly one row:** `grep -c 'model_name: qwen35-122b' config == 1` (two same-named rows load-balance into a dead lane — the DeepSeek bare-row invariant).
▶ **GATE — no cloud fallback (DF-001, re-run after ANY door edit):** `fallbacks: []` and `context_window_fallbacks: []` hold; no cloud model named anywhere post-edit.
▶ **GATE — the restart trap:** restart litellm, then **re-assert the drain** — on Node A, `litellm.service` carries `Wants=llama-swap.service`, so a door restart silently revives the drained fleet and memory-crashes the box (caught live on the 0731 run: 2 GB free, 10 GB swap). Check the unit here: `systemctl --user cat litellm | grep -i wants`; after restart: `systemctl --user is-active llama-swap` must be `inactive` — if not, stop it again and record the unit dependency in RESULTS as a fix-me.
▶ **GATE — through the door:** a completion for `qwen35-122b` via `:4000` returns; the request appears in the door's log/spend view (else something bypassed the door).

## Phase 7: Decision Gate

| # | Gate | Result |
|---|---|---|
| 1 | Precondition: fleet green before drain | |
| 2 | Weights staged at pinned revisions | |
| 3 | Drain + ≥110 GB free before launch | |
| 4 | Seat healthy within cold window | |
| 5 | Memory envelope (≤109 used / ≥15 GiB free / swap 0) | |
| 6 | Smoke + 262K ctx + ≥35 tok/s + 90 s long-gen | |
| 7 | Door row ×1 · no-cloud re-proved · drain re-asserted post-restart · served via :4000 | |

All PASS → the seat stands. Write `RESULTS-qwen35-122b-seat.md` (versions actually run, image digest, HF revisions, all measured numbers, the drift report) — **once, here, never a partial write-up mid-run**. Then, as reviewed follow-up commits: freeze the three RESOLVE-AT-RECON pins in this file's PINS block; add the seat to `ARCHITECTURE-current.md` (on-demand table + a matrix-set note that this seat is Mode-3/whole-box); point the Mac's Switchyard strong tier at `http://spark-fcf6.local:4000/v1` → `qwen35-122b`.

## Appendix A: Rollback / teardown (also the experiment-over ritual)

```bash
docker rm -f qwen122b-seat
mv /opt/litellm/config.yaml.bak-122b-seat /opt/litellm/config.yaml && systemctl --user restart litellm
systemctl --user start llama-swap
curl -s localhost:9000/v1/models   # assert the 5-model revive set matches the pre-drain snapshot
```

Weights stay cached (~66 GB disk; reclaim only if the seat is retired for good). Verify the revive is snapshot-identical — the 0731 precedent.

## Appendix B: shared-mode variant (NOT executable — recorded so nobody improvises it)

Running the seat beside the tutor stack means a much smaller KV pool (lower util, reduced ctx) — **no public measurements exist** for that configuration, and the fp8-KV/int8-lm-head expansion (t/378167: 1.37M-token KV pool, vLLM main@318b527) is pinned to a moving main build. Either becomes its own runbook revision after this lane is green and RESULTS gives a local baseline — promotion by PR per §6, not a mid-run swap.
