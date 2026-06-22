# Runbook: Two-Spark Bring-Up — Add Node B → a Networked GB10 Pair (capacity, not speed)

**Status:** Draft (executable companion to the capture spine; conventions in [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md)). Execute once to verify before the second video; the [capture spine](./RUNBOOK-two-spark-video-capture.md) *films* this arc.

**Purpose:** Take an **already-working single Spark** (Node A, stood up by [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md)) and **add a second GB10 (Node B)** over a 200 G ConnectX-7 link, to serve a model **too large for one node** behind a unified front door — *without* disturbing the single-node fleet. The procedure is version-pinned; the gotchas are gates; a Phase 0 recon reports upstream drift first. **This is purely additive: Node A is unchanged.**

> **The one idea (DECISION-DF-004):** *a second node buys **capacity and parallelism, not single-stream speed**.* The 200 G link (~22 GB/s healthy) is the ceiling; a model that fits one node is **faster** on one node. The second node earns its place by running models that **don't fit** (the cross-node TP Proposer), time-shared with the swap pool.

```
clients (agents, Claude Code — OpenAI / Anthropic-compatible)
   │
   ▼
LiteLLM :4000  ← NEW unified front door (router only; NO cloud fallback, DF-001)
   ├── fleet   → llama-swap :9000 on Node A   (the single-Spark baseline, UNCHANGED; becomes a backend)
   ├── embed   → Qwen3-Embedding-0.6B (1024-dim, always-on for fleet-memory)
   └── proposer→ vLLM --tp 2 across Node A <==> Node B   (200 G CX-7; on-demand only; ~158 GB)
                 DeepSeek-V4-Flash class — brought up XOR the full swap pool (memory budget)
Synology NAS — Postgres + pgvector (fleet-memory)                          (LAN / Tailscale)
```

**Machines:** Node A = `promaxgb10-41b1` (proven baseline); Node B = the new DGX Spark. Both Blackwell SM121, 128 GB unified (~121 usable, ceiling 115). 200 G QSFP56 ConnectX-7 single cable.
**Prereq (hard):** Node A is **GREEN** on `RUNBOOK-single-spark-bring-up.md` (llama-swap on `:9000`, gates passed). This runbook does nothing to the Node A config.
**Prior art (re-checked in Phase 0):** [NVIDIA connect-two-sparks playbook](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/connect-two-sparks/README.md) · [NVIDIA NCCL playbook](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/nccl/README.md) · the [DeepSeek-V4-Flash 2× Spark recipe thread](https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309) · [corti "Two Sparks, One Cluster"](https://corti.com/two-sparks-one-cluster-why-stacking-nvidia-dgx-spark-units-unlocks-local-frontier-scale-inference/) · eugr/spark-vllm-docker.
**Source material:** [`RUNBOOK-two-spark-video-capture.md`](./RUNBOOK-two-spark-video-capture.md) + [`two-spark-serving-research-and-references.md`](./two-spark-serving-research-and-references.md) (in this repo); `DECISION-DF-004` lives in the [guardkit repo](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md).
**Expected wall-clock:** ~45–90 min the first time (firmware + cable + NCCL + first TP cold-start dominate); the Proposer cold-start alone is ~6 min.
**Outputs:** `RESULTS-two-spark-bring-up-<YYYY-MM-DD>.md`, committed `DRIFT-two-spark-bring-up-<YYYY-MM-DD>.md`, the live `/opt/litellm/config.yaml` + the vLLM launch command.

---

## PINS (single source of truth)

```
PINS (set 2026-06-22)
  CX-7 firmware     >= 28.45.4028  (UEFI 1.107.26)   fixes the all_gather-halving regression (Apr-2026 throttle)
  DGX OS / driver   7.5.0 / 580.159.03 / CUDA 13.0.2 / UEFI 1.108.20   (both nodes, matched)
  nccl-tests        v2.28.9-1   built make MPI=1, NVCC_GENCODE sm_121
  BUSBW_PASS_GBPS   20          healthy single-cable ~22.1; 25 = theoretical ceiling, NOT the bar; ~15.5 = fw-degraded; ~10.25 = both-ports-miswired
  vLLM              jasl/vllm commit dda4668b   (GB10 validation is commit-specific)
  torch             2.9.1       (2.10.0 breaks CUDA graphs -> one-node-drop hang)
  proposer          DeepSeek-V4-Flash (284B-A13B, FP4+FP8, ~158 GB) + MTP (deepseek_mtp, num_speculative_tokens=2)
  litellm           front door :4000   NO cloud fallback (fallbacks: [] AND context_window_fallbacks: [])
  embed             Qwen3-Embedding-0.6B  (1024-dim, always-on; matches the single-Spark public config — pin ONE dim end-to-end)
  MEM_RULE          swap pool XOR TP proposer  (the ~158 GB proposer + a full pool cannot co-reside across 2x128 GB)
  ENDPOINT          LiteLLM :4000  (clients);  llama-swap :9000 + vLLM :8080 remain direct-port fallbacks (DF-001 §3.3)
  PREREQ            Node A GREEN on RUNBOOK-single-spark-bring-up.md
```

When recon flags drift on a pin, the fix is a **PR editing this block** — never a runtime edit (conventions §6).

---

## What this runbook does NOT cover

- **The single-node fleet.** That is `RUNBOOK-single-spark-bring-up.md` (Node A baseline) — already done; not re-run here.
- **3+ nodes / switch fabric.** Direct-cable link-local only; a third Spark needs a QSFP switch + `--tp 4`/Ray (DF-004 §4.4).
- **Choosing the Proposer engine** (vLLM vs SGLang vs TensorRT-LLM) — decided by the Phase 9 benchmark, not here.
- **The single-node big-brain Player (`gpt-oss-120b`, ~63 GB).** It fits ONE node and stays on-demand on Node A — it is **not** the cross-node TP Proposer.

---

## Phase 0: Recon (read-only, advisory) — emits the drift report

Degrades gracefully (DF-001): network down → `recon: skipped`, proceed on PINS.

### 0.1 Deterministic pin checks

```bash
echo "=== Phase 0.1: two-spark deterministic checks ==="
# CX-7 firmware on THIS node vs the all_gather-halving-fix floor
flint -d $(ibdev2netdev | awk '{print $1; exit}') q 2>/dev/null | grep -i 'FW Version' || echo "[recon] flint unavailable — check FW via DGX Dashboard"
# torch + vLLM commit pins (on the node that will host vLLM)
python3 -c "import torch; print('[info] torch', torch.__version__)" 2>/dev/null || echo "[info] torch not yet installed"
echo "[pin] vLLM commit dda4668b (jasl/vllm); torch 2.9.1; nccl-tests v2.28.9-1"
```

### 0.2 Source scan (fixed list, LLM judgment)

```
RECON SOURCES (fixed)
  - NVIDIA connect-two-sparks + nccl playbooks (GitHub NVIDIA/dgx-spark-playbooks)   topics: cabling, iface naming, all_gather_perf, env pins
  - NVIDIA DGX Spark forum   topics: CX-7 firmware throttle / all_gather halved, mlnx-fw-updater NIC brick, hard power-off under load, torch 2.10 one-node-drop, vLLM #40969 hang
  - DeepSeek-V4-Flash 2x-Spark recipe thread; "best 2026 model for a 2-node cluster" thread (>128 GB candidates, PP-vs-TP)
  - corti two-Spark posts; Spark Arena leaderboard
TASK: "Report only items newer than the PINS date affecting a pinned component or a known gotcha. Emit a drift report. Do NOT propose edited steps. Do NOT change any pin."
```

### 0.3 Emit `DRIFT-two-spark-bring-up-<timestamp>.md` (conventions §5) and commit it. **▶ GATE (advisory):** operator reviews any `[DRIFT]`/`[FLAG]` before promoting pins; the run proceeds on current PINS.

---

## Phase 1: Pre-flight (go/no-go — no side effects)

```bash
# Node A baseline must be green
curl -sf http://localhost:9000/v1/models >/dev/null && echo "PASS: Node A llama-swap :9000 up" || echo "FAIL: stand up Node A first (RUNBOOK-single-spark-bring-up.md). STOP."
uname -m   # aarch64 on both
```
- Both Sparks powered; the **single** 200 G QSFP56 CX-7 cable in hand.
- **Record known-good NIC firmware per node BEFORE cabling** (the brick guard, Phase 2). `flint -d <dev> q | grep -i 'FW Version'` on each; save it.
**Pass:** Node A green; both nodes on a matched DGX OS / driver.

---

## Phase 2: Firmware-first &nbsp;·&nbsp; **▶ GATE: matched, current firmware on BOTH — and don't brick the NIC**

The Apr-2026 firmware introduced aggressive NIC power-saving that **halved** `all_gather_perf` (19 W→1 W on the NIC). The fix is CX-7 FW **28.45.4028+** (UEFI 1.107.26). Update OS + firmware on **both** nodes *before* cabling.

```bash
# Preferred: DGX Dashboard GUI updater on each node. CLI path:
sudo fwupdmgr refresh && sudo fwupdmgr get-updates    # review, then: sudo fwupdmgr update
```
**▶ NIC-BRICK GUARD (load-bearing):** an *unsolicited* `mlnx-fw-updater` flash bricked both CX-7 cards (error -110, Jun 2026). Therefore:
```bash
sudo apt-mark hold mlnx-fw-updater 2>/dev/null || true   # pin; no auto-flash
# Do NOT run unattended `apt upgrade` / `dpkg --configure -a` during bring-up.
```
**Pass:** both nodes report CX-7 FW ≥ 28.45.4028; `mlnx-fw-updater` held; known-good FW recorded. **FAIL → halt** (a degraded NIC silently halves the fabric in Phase 4).

---

## Phase 3: Cable + link-up &nbsp;·&nbsp; **▶ GATE: `ibdev2netdev` shows `(Up)`**

```bash
# Connect the single QSFP cable to ANY QSFP port on each unit (the official
# connect-two-sparks playbook: "using any QSFP interface on each device").
# Same port on both is a Stacking-guide TIDINESS tip, NOT a link-up requirement.
ibdev2netdev                       # expect an enp1s0f1np1-style iface marked (Up)
ip -br addr show | grep -E 'enp1|169.254'   # link-local 169.254.x.x via netplan (40-cx7.yaml) is fine for one cable
```
**Pass:** one CX-7 iface `(Up)` (use the `enp1...` name; ignore the `enP2p...` duplicate — the NIC surfaces 4 names for 2 ports because it's wired as two PCIe Gen5 x4 paths).
**⚠️ WARN:** do **not** cable *both* CX-7 ports unless you IP all four interfaces — the link silently halves to 100 GbE (~10 GB/s busbw).

---

## Phase 4: NCCL fabric &nbsp;·&nbsp; **▶ THE load-bearing GATE: busbw ≥ 20 GB/s AND transport = NET/IB (not TCP)**

`all_gather_perf` busbw alone is a *symptom*; a silent TCP fallback can still post a number while you've lost the RoCE plane (corti lost the data plane this way). The gate is **two-signal**.

### 4.1 Build nccl-tests + pin the iface (per the NCCL playbook)

```bash
git clone https://github.com/NVIDIA/nccl-tests ~/nccl-tests && cd ~/nccl-tests
make MPI=1 MPI_HOME=/usr/lib/aarch64-linux-gnu/openmpi NVCC_GENCODE="-gencode=arch=compute_121,code=sm_121"
# Pin the FABRIC vars to the link iface (resolve the real name per-box via ibdev2netdev):
export NCCL_SOCKET_IFNAME=enp1s0f1np1 UCX_NET_DEVICES=enp1s0f1np1 OMPI_MCA_btl_tcp_if_include=enp1s0f1np1
```

### 4.2 Run the official benchmark + assert both signals

```bash
N1=169.254.x.a; N2=169.254.x.b   # the two link-local IPs
mpirun -np 2 -H ${N1}:1,${N2}:1 --mca plm_rsh_agent 'ssh -o StrictHostKeyChecking=no' \
  -x NCCL_SOCKET_IFNAME -x UCX_NET_DEVICES -x OMPI_MCA_btl_tcp_if_include -x LD_LIBRARY_PATH \
  ~/nccl-tests/build/all_gather_perf -b 16G -e 16G -f 2 | tee /tmp/ag.txt
BUSBW=$(grep -Eo '[0-9]+\.[0-9]+' /tmp/ag.txt | tail -1)
awk -v b="$BUSBW" 'BEGIN{exit !(b>=20)}' && echo "GATE PASS(a): busbw ${BUSBW} GB/s ≥ 20" || echo "GATE FAIL(a): busbw ${BUSBW} GB/s < 20 — firmware-degraded (~15.5) or miswired (~10.25). STOP."
# Signal (b): transport must be RoCE/IB, not socket/TCP
mpirun -np 2 -H ${N1}:1,${N2}:1 --mca plm_rsh_agent 'ssh -o StrictHostKeyChecking=no' \
  -x NCCL_DEBUG=INFO -x NCCL_SOCKET_IFNAME ~/nccl-tests/build/all_gather_perf -b 1G -e 1G 2>&1 | grep -m1 -E 'NET/(IB|Socket)' | tee /tmp/ag-net.txt
grep -q 'NET/IB' /tmp/ag-net.txt && echo "GATE PASS(b): RoCE/IB transport" || echo "GATE FAIL(b): NET/Socket — silent TCP fallback. Re-pin NCCL_IB_HCA + check RoCE. STOP."
```

### 4.3 Raw-RDMA isolation tier (only if the gate fails)

```bash
sudo apt install -y perftest
ib_write_bw -d <roce-dev> --report_gbits     # expect ~92–97 Gb/s/link (~189.85 Gbps dual aggregate)
```
If `ib_write_bw` is healthy but NCCL fails → **NCCL config** (TCP fallback / iface pin). If `ib_write_bw` is also slow → **NIC/firmware** (Phase 2). This separates "fabric bad" from "config bad".

---

## Phase 5: Mesh / passwordless SSH &nbsp;·&nbsp; **▶ GATE: SSH round-trip both directions**

```bash
# discover-sparks (playbook) generates a shared ed25519 key, or use NVIDIA Sync "Cluster Assistant".
ssh ${N2} hostname && ssh -o BatchMode=yes ${N2} 'ssh -o BatchMode=yes '"${N1}"' hostname' \
  && echo "GATE PASS: passwordless SSH both ways" || echo "GATE FAIL: fix keys. STOP."
```

---

## Phase 6: Power-off mitigation &nbsp;·&nbsp; **▶ GATE before any --tp launch**

A GB10 firmware bug **hard powers-off under sustained GPU load** (reproduces in ~60 s of vLLM load; **still open Jun 2026**, not in NVIDIA's Known Issues). TP loads **both** boxes hard — this is the single highest-likelihood failure here and on camera.

```bash
# Stopgap clock clamp on BOTH nodes — LABELLED UNVERIFIED (posted only as a planned test; never confirmed to stop the shutdown):
sudo nvidia-smi -lgc 200,2150
```
**Better-evidenced mitigation (do this if you have a recurring power-off):** thermal — repaste + run case-off (~15 °C drop) with USB-fan airflow ran multi-day TP loops crash-free. Treat `-lgc` as a hopeful stopgap, thermal as the real fix.
**Pass:** clocks clamped on both nodes (and thermal addressed if a power-off has occurred).

---

## Phase 7: LiteLLM `:4000` unified front door &nbsp;·&nbsp; **▶ GATE: NO cloud fallback**

LiteLLM is a *router only* (it does not load models or do TP). Node A's llama-swap `:9000` becomes a **backend**; it keeps running unchanged and remains a direct-port fallback.

```yaml
# /opt/litellm/config.yaml  (excerpt)
model_list:
  - model_name: workhorse        # fleet -> Node A llama-swap
    litellm_params: { model: openai/workhorse, api_base: http://localhost:9000/v1, api_key: "none" }
  - model_name: embed            # Qwen3-Embedding-0.6B, 1024-dim (matches the single-Spark public config)
    litellm_params: { model: openai/embed, api_base: http://localhost:9000/v1, api_key: "none" }
  - model_name: proposer         # cross-node TP=2, brought up on demand (Phase 8)
    litellm_params: { model: openai/deepseek-v4-flash, api_base: http://localhost:8080/v1, api_key: "none" }
  - model_name: claude-opus      # DF-003 ATTENDED path only — never a fallback target
    litellm_params: { model: anthropic/claude-opus-4-7 }
router_settings:
  fallbacks: []                  # NO local->cloud fallback (DF-001)
  context_window_fallbacks: []   # also empty — LiteLLM's documented example escalates to claude-opus on overflow (the exact unattended-spend footgun)
```
**▶ GATE:**
```bash
CFG=/opt/litellm/config.yaml
grep -qE 'fallbacks:\s*\[\]' "$CFG" && grep -qE 'context_window_fallbacks:\s*\[\]' "$CFG" \
  && echo "GATE PASS: no cloud fallback (both fallbacks empty)" \
  || echo "GATE FAIL: a cloud fallback path exists — DF-001 violation. STOP."
```

---

## Phase 8: Memory-budget gate + TP Proposer bring-up &nbsp;·&nbsp; **▶ GATE: pool XOR proposer**

The ~158 GB Proposer shards to ~75–80 GB/node + KV — it claims the large majority of **both** boxes. It and a full swap pool **do not co-reside**. So: **evict/tear down the swap pool before launching the Proposer.**

```bash
# 1. Pause keepalive + drain the Node A pool so it can't revive on top of the proposer:
sudo systemctl stop llama-swap-keepalive.timer        # (system unit, per the single-Spark runbook)
# 2. Launch vLLM --tp 2 across both nodes (mp backend; no Ray at 2 nodes):
#    TP-layer env (distinct from the Phase-4 fabric vars): add the RoCE HCAs explicitly.
export NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_DISABLE=0 \
       GLOO_SOCKET_IFNAME=enp1s0f1np1 TP_SOCKET_IFNAME=enp1s0f1np1
vllm serve deepseek-ai/DeepSeek-V4-Flash \
  --tensor-parallel-size 2 --distributed-executor-backend mp --nnodes 2 \
  --kv-cache-dtype fp8 --enable-expert-parallel --no-ray \
  --speculative-config '{"method":"deepseek_mtp","num_speculative_tokens":2}' \
  --max-num-seqs 2 --port 8080
#    (pin jasl/vllm dda4668b + torch 2.9.1; choose a cudagraph mode that AVOIDS vLLM #40969
#     — FULL_AND_PIECEWISE + chunked prefill silently hangs after ~6–7 requests on GB10.)
```
**▶ GATE:** before the launch, assert the pool is down (`curl -sf localhost:9000/running | jq '.running|length'` → 0 or torn down) so peak memory can't cross the freeze line. After load, `/v1/models` on `:8080` lists the proposer.
**Treat the seat as single-stream:** concurrency=2 collapses decode to ~1 tok/s at 65 K. `--max-num-seqs 2` is a KV-budget cap, not a throughput target.
**Tear down** the Proposer (and `sudo systemctl start llama-swap-keepalive.timer`) to return to daily/pool mode.

---

## Phase 9: Benchmark + record (the capture-spine P3 "number") &nbsp;·&nbsp; **▶ GATE: numbers captured**

```bash
# Same model, both ways — the numbers, not the README, decide whether TP earns its place.
#  (a) Proposer TP=2 decode tok/s + cold-start time (expect ~44 tok/s warm WITH MTP; ~5 without)
#  (b) a fleet model single-node on Node A for contrast
#  (c) PP=2 vs TP=2 for the Proposer — PP wins under concurrency (~555 vs ~252 @batch128),
#      TP wins at batch=1 single-stream (the Proposer's actual regime). Record both.
```
Record decode tok/s (TP=2 / single-node / PP=2), cold-start (~6 min), and TTFT@32K/128K.

## Phase 10: Decision Gate

| Gate | Result | Note |
|---|---|---|
| P0.3 Drift report emitted + reviewed | | committed `DRIFT-*` |
| P2 firmware ≥ 28.45.4028 both nodes + mlnx-fw-updater held | | NIC-brick guard |
| P3 CX-7 link `(Up)` (any port) | | not both ports unless 4× IP'd |
| P4(a) busbw ≥ 20 GB/s | | **record GB/s** |
| P4(b) transport NET/IB (not Socket) | | no silent TCP fallback |
| P5 passwordless SSH both ways | | |
| P6 power-off mitigation on both | | `-lgc` (unverified) + thermal |
| P7 LiteLLM no-cloud guard (both fallbacks empty) | | |
| P8 pool evicted before Proposer (memory XOR) | | |
| P9 TP=2 / single-node / PP=2 numbers | | **record tok/s + cold-start** |

## Phase 11: Evidence → RESULTS

Write `RESULTS-two-spark-bring-up-<YYYY-MM-DD>.md` (gate table filled + recorded numbers + the drift report link). Save the LiteLLM config + the vLLM launch command + the `all_gather_perf` output to `evidence/two-spark-bring-up/`. **Only after the on-hardware Phase 9 benchmark (incl. PP-vs-TP) may DF-004 flip PROPOSED → ACCEPTED.**

---

## Phase 12: Failure modes — fast triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `all_gather_perf` ~15.5 GB/s | CX-7 firmware throttle (Apr-2026) | Phase 2; CX-7 FW ≥ 28.45.4028 |
| busbw ~10 GB/s | both ports cabled, not all IP'd → 100 GbE | use ONE cable / IP all four ifaces |
| busbw fine but `NET/Socket` in logs | silent TCP fallback (lost RoCE) | pin `NCCL_IB_HCA`; Phase 4.3 `ib_write_bw` to isolate |
| Node hard powers-off ~60 s into TP | the open GB10 power-off bug | Phase 6: `-lgc` (unverified) + **thermal** (repaste/airflow) |
| One node drops, other GPU 100 % forever | torch 2.10.0 broke CUDA graphs | pin **torch 2.9.1** |
| Proposer hangs after ~6–7 requests, 0 decode | vLLM #40969 (FULL_AND_PIECEWISE + chunked prefill) | cudagraph mode change / `--enforce-eager` (slower) |
| Proposer decode ~5 tok/s not ~44 | MTP speculative decode off | `--speculative-config deepseek_mtp num_speculative_tokens=2` |
| NIC bricked (pre-init, error -110) | unsolicited `mlnx-fw-updater` flash | Phase 2 hold; `fwupdmgr` downgrade to known-good |
| Unattended run escalated to claude-opus + spend | LiteLLM `context_window_fallbacks` | Phase 7: set it `[]` too |

---

## Appendix: relationship to the other artifacts

- **`RUNBOOK-single-spark-bring-up.md`** — Node A baseline. This runbook is additive on top; it never edits the Node A config.
- **[`RUNBOOK-two-spark-video-capture.md`](./RUNBOOK-two-spark-video-capture.md)** (capture spine, in this repo) — the filming notes; it *films* this executable arc (P2 bring-up war-story = Phases 2–6; P3 number = Phase 9).
- **[`DECISION-DF-004`](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md)** (guardkit repo) — the topology + the memory-budget rule + the "capacity not speed" principle this runbook implements. Stays **PROPOSED** until Phase 9 runs on our own hardware.
