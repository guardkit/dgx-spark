# Runbook: Two-Spark Bring-Up — Add Node B → a Networked GB10 Pair (capacity, not speed)

**Status:** **Verified** — first execution GREEN 2026-08-06→07 ([`RESULTS-two-spark-bring-up-2026-08-06.md`](./RESULTS-two-spark-bring-up-2026-08-06.md)); that run's 12 execution-caught findings are folded in below. Conventions in [`RUNBOOK-CONVENTIONS.md`](./RUNBOOK-CONVENTIONS.md).

**Purpose:** Take an **already-working single Spark** (Node A, stood up by [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md)) and **add a second GB10 (Node B)** over a 200 G ConnectX-7 link, to serve a model **too large for one node** behind a unified front door — *without* disturbing the single-node fleet. The procedure is version-pinned; the gotchas are gates; a Phase 0 recon reports upstream drift first. **This is purely additive: Node A is unchanged.**

> **The one idea (DECISION-DF-004):** *a second node buys **capacity and parallelism, not single-stream speed worth stacking for**.* A model that fits one node gains only ~1.3–1.5× from TP=2 — per-layer sync latency + the unsharded remainder eat the rest (the 200 G link's ~22 GB/s healthy busbw binds at prefill/concurrency, not batch-1 decode) — at 2× the hardware with both fleets drained; leaderboard near-2× rows are concurrency throughput. The second node earns its place by running models that **don't fit** (the cross-node two-box DeepSeek), time-shared with the swap pool.

```
clients (agents, Claude Code — OpenAI / Anthropic-compatible)
   │
   ▼
LiteLLM :4000  ← NEW unified front door (router only; NO cloud fallback, DF-001)
   ├── fleet   → llama-swap :9000 on Node A   (the single-Spark baseline, UNCHANGED; becomes a backend)
   ├── embed   → Qwen3-Embedding-0.6B (1024-dim, always-on for fleet-memory)
   └── DeepSeek→ vLLM --tp 2 across Node A <==> Node B   (200 G CX-7; on-demand only; ~158 GB)
                 DeepSeek-V4-Flash class — brought up XOR the full swap pool (memory budget)
Synology NAS — Postgres + pgvector (fleet-memory)                          (LAN / Tailscale)
```

**Machines:** Node A = `promaxgb10-41b1` (proven baseline); Node B = the new DGX Spark. Both Blackwell SM121, 128 GB unified (~121 usable, ceiling 115). 200 G QSFP56 ConnectX-7 single cable.
**Prereq (hard):** Node A is **GREEN** on `RUNBOOK-single-spark-bring-up.md` (llama-swap on `:9000`, gates passed). This runbook does nothing to the Node A config.
**One-time box setup:** passwordless sudo on **both** nodes (run the agent as that user, not root) **+ LAN SSH Node A → Node B** (the agent drives every Node B step over SSH from Node A; Phases 0–2 run pre-cable, so this is the ordinary LAN/Tailscale path — the CX-7 link-local mesh is Phase 5's job) — see [README → One-time box setup](./README.md#one-time-box-setup-passwordless-sudo). The only physically-manual inputs are the CX-7 cable + any firmware reboot (operator steps, conventions §2.3).
**Prior art (re-checked in Phase 0):** [NVIDIA connect-two-sparks playbook](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/connect-two-sparks/README.md) · [NVIDIA NCCL playbook](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/nccl/README.md) · the [DeepSeek-V4-Flash 2× Spark recipe thread](https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309) · [corti "Two Sparks, One Cluster"](https://corti.com/two-sparks-one-cluster-why-stacking-nvidia-dgx-spark-units-unlocks-local-frontier-scale-inference/) · eugr/spark-vllm-docker.
**Source material:** [`two-spark-serving-research-and-references.md`](./two-spark-serving-research-and-references.md) (in this repo); `DECISION-DF-004` lives in the [guardkit repo](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md).
**Expected wall-clock:** ~45–90 min with weights pre-staged and the hotplug-off reboot (Phase 3) already done; the first-ever run measured ~2.5 h active execution plus ~1 h weight pre-stage and the operator steps. DeepSeek seat cold-start: **230 s** first load, **~114 s** warm relaunch (InstantTensor ~9 GB/s off NVMe cache).
**Outputs:** `RESULTS-two-spark-bring-up-<YYYY-MM-DD>.md`, committed `DRIFT-two-spark-bring-up-<YYYY-MM-DD>.md`, the live `/opt/litellm/config.yaml` + the vLLM launch command.

---

## PINS (single source of truth)

```
PINS (set 2026-06-22)
  CX-7 firmware     >= 28.45.4028  (UEFI 1.107.26)   fixes the all_gather-halving regression (Apr-2026 throttle)
  DGX OS / driver   7.5.0 / 580.159.03 / CUDA 13.0.2 / UEFI 1.108.20   (both nodes, matched)
  NCCL              libnccl2/-dev 2.28.9-1+cuda13.0 (deb, NOT preinstalled — install exactly); nccl-tests built
                    from upstream HEAD (no 2.28.x tag exists; 717b683 validated) make MPI=1, NVCC_GENCODE sm_121
  BUSBW_PASS_GBPS   20          healthy single-cable ~22.1; 25 = theoretical ceiling, NOT the bar; ~15.5 = fw-degraded; ~10.25 = both-ports-miswired
  vLLM              eugr/spark-vllm-docker @ f7d6e3b5   (PINNED DEFAULT for the V4-Flash TP build — Docker, recipe deepseek-v4-flash, --no-ray --port 8080; pinned 2026-08-02. Reference build for A/B: jasl/vllm @ dda4668b + torch 2.9.1 — the canonical thread's validated commit — Phase 8)
  torch             2.9.1       (2.10.0 breaks CUDA graphs -> one-node-drop hang)
  DeepSeek          DeepSeek-V4-Flash (284B-A13B, FP4+FP8, ~158 GB) + MTP (deepseek_mtp, num_speculative_tokens=2)
  SEAT_DIALS        --gpu-memory-utilization 0.76 --max-model-len 98304   (validated 2026-08-07; the recipe
                    defaults 0.8/500K put a front-door host at ~113 GB used — OVER the 115 ceiling; Node A FROZE there.
                    NOT 0.75: the 96K KV requirement has a ~6.9 GiB floor that barely moves with max-model-len,
                    and 0.75's available KV wobbles 6.83–6.97 GiB run-to-run → intermittent startup ValueError;
                    0.76 measures 8.2 GiB available — real margin at ~109 GB used, still ~6 GB under the ceiling)
  litellm           litellm[proxy] (latest)   front door :4000; NO cloud fallback (fallbacks: [] AND context_window_fallbacks: []); floated not frozen (CONVENTIONS §3); validated at 1.89.4 on GB10
  embed             Qwen3-Embedding-0.6B  (1024-dim, always-on; matches the single-Spark public config — pin ONE dim end-to-end)
  MEM_RULE          swap pool XOR two-box DeepSeek  (the ~158 GB DeepSeek + a full pool cannot co-reside across 2x128 GB)
  ENDPOINT          LiteLLM :4000  (clients);  llama-swap :9000 + vLLM :8080 remain direct-port fallbacks (DF-001 §3.3)
  PREREQ            Node A GREEN on RUNBOOK-single-spark-bring-up.md
```

When recon flags drift on a pin, the fix is a **PR editing this block** — never a runtime edit (conventions §6).

---

## Node roles & prerequisites — no factory reset, ever

This runbook is **purely additive** — it assumes one box already works and layers the second node + the CX-7 interconnect + LiteLLM + the on-demand two-box DeepSeek on top. **Nothing here wipes or conflicts with a single-Spark setup;** the engines coexist on distinct ports (llama-swap `:9000`, vLLM `:8080`, LiteLLM `:4000`). **No factory reset is ever required.**

- **Both nodes may be single-Spark boxes.** Running `RUNBOOK-single-spark-bring-up.md` on a box first is fine and recommended — you validate it and get an independently-useful node. It is *not* something to undo.
- **Node A** = the llama-swap pool host (the always-on fleet, fronted by LiteLLM `:4000`). **An existing single-Spark box already IS Node A** — its llama.cpp SM121 build, llama-swap, user unit + linger, and keepalive timer are exactly the single-Spark software baseline (the model config aside). **Do NOT re-run `RUNBOOK-single-spark-bring-up.md` on it** — that would overwrite its config (and `-watch-config` would reload the fleet on the spot). Run **only this** runbook on Node A; its fleet config is otherwise zero-change.
- **Node B** = cross-node TP compute. This is the box you *do* run `RUNBOOK-single-spark-bring-up.md` on first (validate it + build llama.cpp + get an independently-useful fleet). During a TP run its fleet just sits **dormant** — you **stop** it, you don't uninstall it (`systemctl --user stop llama-swap`; `start` to revive after). A single GB10 can't hold both its ~65 GB fleet *and* a ~75–80 GB DeepSeek shard, so the fleet and the DeepSeek seat **time-share** the box (the DF-004 memory rule).
- **What each node needs:** *both* need firmware (Phase 2), the CX-7 fabric (Phases 3–5), and vLLM + the DeepSeek seat weights (Phase 8). Node B does **not** need its own always-on fleet for TP — but having one (from single-Spark) is harmless.
- **The only first-run risks are hardware/fabric** (cable link-up, NCCL `NET/IB`, firmware, the TP launch) — never the single-Spark software underneath.

**Three operating modes (time-shared — the DF-004 memory rule):**

1. **Day-to-day fleet (default).** Node A serves its always-on fleet to your agents via LiteLLM `:4000`; Node B runs its own fleet or sits idle. No TP, no cabling exercised in this mode — the two boxes are just two independent single-Spark setups.
2. **Cross-node DeepSeek (on demand).** To run a model too big for one box (DeepSeek-V4-Flash, ~158 GB → ~79 GB/node), **drain the fleet on BOTH nodes** (stop the keepalive + `systemctl --user stop llama-swap` on each), launch vLLM `--tp 2` across the pair (Phase 8), then tear it down and revive both fleets. The shard **cannot** co-reside with a full fleet (~79 GB DeepSeek + a ~65–81 GB fleet blows the 115 GB ceiling) — so this is **time-shared with mode 1, never concurrent**: you pause day-to-day serving, run the big model, then resume.
3. **Standalone long-run on one node.** Use **Node B alone** for a long job (e.g. the agentic dataset factory, 50+ hrs) — stop its fleet to free memory, run the job; **Node A is untouched and keeps serving day-to-day.** This mode does **not** use this runbook (no TP, no cabling, no draining Node A) — the two boxes simply operate independently.

---

## What this runbook does NOT cover

- **The single-node fleet.** That is `RUNBOOK-single-spark-bring-up.md` (Node A baseline) — already done; not re-run here.
- **3+ nodes / switch fabric.** Direct-cable link-local only; a third Spark needs a QSFP switch + `--tp 4`/Ray (DF-004 §4.4).
- **Choosing the DeepSeek seat engine** (vLLM vs SGLang vs TensorRT-LLM) — decided by the Phase 9 benchmark, not here.
- **The single-node big-brain Player (`gpt-oss-120b`, ~63 GB).** It fits ONE node and stays on-demand on Node A — it is **not** the cross-node two-box DeepSeek.

---

## Phase 0: Recon (read-only, advisory) — emits the drift report

Degrades gracefully (DF-001): network down → `recon: skipped`, proceed on PINS.

### 0.1 Deterministic pin checks

```bash
echo "=== Phase 0.1: two-spark deterministic checks ==="
# CX-7 firmware on THIS node vs the all_gather-halving-fix floor
mstflint -d $(ibdev2netdev | awk '{print $1; exit}') q 2>/dev/null | grep -i 'FW Version' || echo "[recon] mstflint unavailable — check FW via DGX Dashboard"   # DGX OS ships mstflint, not legacy flint
# torch + vLLM commit pins (on the node that will host vLLM)
python3 -c "import torch; print('[info] torch', torch.__version__)" 2>/dev/null || echo "[info] torch not yet installed"
echo "[pin] eugr/spark-vllm-docker f7d6e3b5 (recipe deepseek-v4-flash); reference build jasl/vllm dda4668b + torch 2.9.1; nccl-tests v2.28.9-1"
```

### 0.2 Source scan (fixed list, LLM judgment)

```
RECON SOURCES (fixed)
  - NVIDIA connect-two-sparks + nccl playbooks (GitHub NVIDIA/dgx-spark-playbooks)   topics: cabling, iface naming, all_gather_perf, env pins
  - NVIDIA DGX Spark forum   topics: CX-7 firmware throttle / all_gather halved, mlnx-fw-updater NIC brick, hard power-off under load, torch 2.10 one-node-drop, vLLM #40969 hang
  - DeepSeek-V4-Flash 2x-Spark recipe thread; "best 2026 model for a 2-node cluster" thread (>128 GB candidates, PP-vs-TP)
  - DSpark spec-decoding (DeepSeek): github.com/deepseek-ai/DeepSpec releases + vLLM issue #46910 — watch for an SM121/aarch64 path (evolution of the deepseek_mtp we already run; not yet on the jasl fork)
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
- **Management LAN should be wired.** If a node's LAN is Wi-Fi, set `sudo nmcli connection modify <profile> connection.autoconnect-retries 0` (= retry forever) — NM's default gives up after 4 attempts, and one AP auth blip then strands the box unattended (80-min outage observed 2026-08-07; the box was healthy underneath).
- **Record known-good NIC firmware per node BEFORE cabling** (the brick guard, Phase 2). `mstflint -d <dev> q | grep -i 'FW Version'` on each (DGX OS ships `mstflint`, not the legacy Mellanox-OFED `flint`); save it.
**Pass:** Node A green; both nodes on a matched DGX OS / driver.

---

## Phase 2: Firmware-first &nbsp;·&nbsp; **▶ GATE: matched, current firmware on BOTH — and don't brick the NIC**

The Apr-2026 firmware introduced aggressive NIC power-saving that **halved** `all_gather_perf` (19 W→1 W on the NIC). The fix is CX-7 FW **28.45.4028+** (UEFI 1.107.26). Update OS + firmware on **both** nodes *before* cabling.

> **✅ VERIFIED 2026-08-02 (both estate boxes, from boot logs): FW = 28.45.4028 on every port — the gate floor exactly. No flash required; this phase is a pure verification pass here.**
> **The card is deliberately ABSENT from `lspci` while uncabled** — since DGX OS Jan-2026, `dgx-spark-mlnx-hotplug` power-gates the idle CX-7 clean off the PCIe bus (~18 W saved; flag file `/etc/nvidia/cx7-hotplug-enabled`). So with no cable in, `mstflint` cannot see the device — **read the firmware from the boot log instead**:
> ```bash
> journalctl -k -b --no-pager | grep 'mlx5_core.*firmware version'   # expect 28.45.4028+
> # healthy-but-gated signature: mlx5_core probe + "Port module event: Cable unplugged"
> # + a cx7-pcie-hotplug removal ~20s after boot. NO mlx5/MTKP lines at all since boot
> # = real fault territory (cold boot, then fieldiag/RMA path).
> ```

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

**✋ OPERATOR STEP (conventions §2.3):** connect the single QSFP cable to the **same-position** QSFP port on each unit (a Phase-8 harness requirement — see below) — the agent prompts, then polls `ibdev2netdev` / mlx5 module events and continues into the gate below. No cable yet is a *pending input*, not a FAIL — wait for the operator. **Zero `Cable plugged` module events after insertion = not seated** (upside-down or short of the click — observed 2026-08-06; the event fires instantly on a good seat): prompt a firm reseat, don't diagnose the NIC.

```bash
# Connect the single QSFP cable to the SAME-POSITION QSFP port on each unit.
# Any port LINKS UP (the official playbook allows it) — but the eugr Phase-8
# harness pushes ONE global iface name to every node, so asymmetric ports kill
# rank 1 (gloo: "Unable to find address for: enp1s0f1np1"). Same port on both
# is a REQUIREMENT for the TP lane, not a tidiness tip (2026-08-07: B's cable
# had to be moved mid-run to match A).
ibdev2netdev                       # expect an enp1s0f1np1-style iface marked (Up)
ip -br addr show | grep -E 'enp1|169.254'   # link-local 169.254.x.x via netplan (40-cx7.yaml below)
```
**Pass:** one CX-7 iface `(Up)` (use the `enp1...` name; ignore the `enP2p...` duplicate — the NIC surfaces 4 names for 2 ports because it's wired as two PCIe Gen5 x4 paths).
**⚠️ WARN:** do **not** cable *both* CX-7 ports unless you IP all four interfaces — the link silently halves to 100 GbE (~10 GB/s busbw).

**IP + MTU — the exact `40-cx7.yaml` validated 2026-08-07 (write on each node, `netplan apply`):**
```yaml
# /etc/netplan/40-cx7.yaml   (Node A shown; Node B: 169.254.207.2/16 — same iface names, same port both boxes)
network:
  version: 2
  ethernets:
    enp1s0f1np1:            # primary PCIe path — carries the IP
      addresses: [169.254.207.1/16]
      mtu: 9000
    enP2p1s0f1np1:          # secondary PCIe path — NO IP, but the MTU is load-bearing:
      dhcp4: false          # NCCL stripes across BOTH paths; leaving this netdev at 1500
      link-local: [ipv6]    # costs ~6 GB/s busbw (17.85 vs 23.85 measured 2026-08-06)
      mtu: 9000
```
**▶ NM-ZEROCONF GUARD (load-bearing, recurs):** netplan's NM backend renders the secondary iface with `ipv4.method=link-local` regardless of the yaml above — a random 169.254 zeroconf lands on `enP2p…` at boot/cable events, the two nodes' GID tables go asymmetric (one side gains an IPv4 GID), and NCCL dies with `ibv_modify_qp … Invalid argument` on the P2 device. Pin it after **every** `netplan apply` and re-check after **every** reboot (both nodes):
```bash
sudo nmcli connection modify netplan-enP2p1s0f1np1 ipv4.method disabled ipv6.method link-local
sudo nmcli device reapply enP2p1s0f1np1
# assert: ONLY fe80 GIDs on the P2 device, symmetric on both nodes
grep -H . /sys/class/infiniband/roceP2p1s0f1/ports/1/gids/* | grep -v ':0000:0000:0000:0000:0000:0000:0000:0000'
```

**Hot-plug notes (post-Jan-2026 DGX OS — the card is off the bus until the cable wakes it):**
- **▶ POWER-CAP GUARD (found 2026-08-06 — supersedes the flap-only decision rule below): a runtime hotplug attach leaves the NIC power-capped.** The hotplugged slot never advertises power capability (`mlx5_pcie_event: PCIe slot power capability was not advertised`), and the fabric caps at ~13–14 Gb/s raw `ib_write_bw` / ~2.8 GB/s busbw — *below every classic failure signature, with transport correctly NET/IB and the wire at 200 G*. The default path is therefore **disable hotplug + boot with the cable in**: `sudo mv /etc/nvidia/cx7-hotplug-enabled{,.off}` on BOTH nodes, reboot both — the boot-time attach initializes at full power (23.85 GB/s measured; ~18 W idle cost, the documented trade). Runtime insertion remains fine for link-up + the stability watch; do the hotplug-off reboot **before Phase 4**.
- On cable insertion the hotplug driver re-attaches the NIC and the netdevs appear. If they don't within ~30 s: force it (`sudo /opt/nvidia/dgx-spark-mlnx-hotplug/mtk-hotplug-handler.sh plug-in`), then re-check; a reboot with the cable in also works.
- **QSFP56 cable caveat:** a June-2026 forum report (same FW 28.45.4028) saw a third-party **QSFP56** DAC trigger FALSE "Cable removal" events — NICs vanish ~20 s after boot *with the cable inserted*. NVIDIA's approved list is **QSFP112** DACs (Amphenol NJAAKK-N911/0006, Luxshare LMTQF022-SD-R). A 200G QSFP56 DAC is electrically fine for the link; only the hotplug *presence detection* may be picky. **If the link flaps: disable hot-plug** (`/etc/nvidia/cx7-hotplug-enabled` — remove/rename the flag, reboot; costs ~18 W idle) and it will hold.
- **THE ESTATE'S CABLE (identified 2026-08-02): FS.COM 0.5 m 200G QSFP56 passive DAC, P/N `QSFP-200G-PC005`, NV/ME-coded — the same vendor/form-factor/length class as the June report's suspect part.** Decision rule, pre-made so cable day never stalls:
  ```
  Cable in → netdevs appear → ▶ STABILITY MINI-GATE: watch 2 minutes
    (journalctl -kf | grep -E 'mlx5|cx7-pcie-hotplug' — no removal events, iface stays Up)
  HOLDS  → proceed to Phase 4; hotplug stays enabled. Done.
  FLAPS  (~20 s vanish, "Cable removal" with cable seated) →
    sudo mv /etc/nvidia/cx7-hotplug-enabled /etc/nvidia/cx7-hotplug-enabled.off
    reboot BOTH nodes with the cable in → re-run this phase (link will hold; ~18 W idle cost;
    restore the flag after the session if wanted). Order an approved QSFP112 DAC only if
    living hotplug-disabled long-term is unwanted — the session itself never blocks on it.
  ```

---

## Phase 4: NCCL fabric &nbsp;·&nbsp; **▶ THE load-bearing GATE: busbw ≥ 20 GB/s AND transport = NET/IB (not TCP)**

`all_gather_perf` busbw alone is a *symptom*; a silent TCP fallback can still post a number while you've lost the RoCE plane (corti lost the data plane this way). The gate is **two-signal**.

### 4.1 Build nccl-tests + pin the iface (per the NCCL playbook)

```bash
sudo apt install -y libopenmpi-dev openmpi-bin build-essential   # OpenMPI is NOT preinstalled; `make MPI=1` needs it (both nodes)
sudo apt install -y libnccl2=2.28.9-1+cuda13.0 libnccl-dev=2.28.9-1+cuda13.0   # NCCL is NOT preinstalled either (nccl.h missing = build fails); install the PIN exactly (both nodes)
git clone https://github.com/NVIDIA/nccl-tests ~/nccl-tests && cd ~/nccl-tests   # build from HEAD — upstream has no 2.28.x tag (717b683 validated 2026-08-06)
# Resolve the real MPI prefix per-box — do NOT hardcode (the path varies by install):
MPI_HOME=$(dirname "$(mpicc --showme:incdirs 2>/dev/null | awk '{print $1}')"); : "${MPI_HOME:=/usr/lib/aarch64-linux-gnu/openmpi}"
make MPI=1 MPI_HOME="$MPI_HOME" NVCC_GENCODE="-gencode=arch=compute_121,code=sm_121"
# Pin the FABRIC vars (same iface name on both boxes now that same-port is required; the OMPI include
# takes the CIDR, which resolves per-node). Export ALL THREE for EVERY mpirun — including the debug run:
# dropping OMPI_MCA_btl_tcp_if_include lets OMPI wander onto docker/tailscale ifaces and HANG (hit 2026-08-07).
export NCCL_SOCKET_IFNAME=enp1s0f1np1 UCX_NET_DEVICES=enp1s0f1np1 OMPI_MCA_btl_tcp_if_include=169.254.0.0/16
```

### 4.2 Run the official benchmark + assert both signals

```bash
N1=169.254.x.a; N2=169.254.x.b   # the two link-local IPs
mpirun -np 2 -H ${N1}:1,${N2}:1 --mca plm_rsh_agent 'ssh -o StrictHostKeyChecking=no' \
  -x NCCL_SOCKET_IFNAME -x UCX_NET_DEVICES -x OMPI_MCA_btl_tcp_if_include -x LD_LIBRARY_PATH \
  ~/nccl-tests/build/all_gather_perf -b 16G -e 16G -f 2 | tee /tmp/ag.txt
BUSBW=$(awk '/Avg bus bandwidth/{print $NF}' /tmp/ag.txt)   # parse the named line (robust to integer values + column drift)
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

A GB10 firmware bug **hard powers-off under sustained GPU load** (reproduces in ~60 s of vLLM load; **still open Jun 2026**, not in NVIDIA's Known Issues). TP loads **both** boxes hard — this is the single highest-likelihood failure here.

```bash
# Stopgap clock clamp on BOTH nodes — LABELLED UNVERIFIED (posted only as a planned test; never confirmed to stop the shutdown):
sudo nvidia-smi -lgc 200,2150
```
**Better-evidenced mitigation (do this if you have a recurring power-off):** thermal — repaste + run case-off (~15 °C drop) with USB-fan airflow ran multi-day TP loops crash-free. Treat `-lgc` as a hopeful stopgap, thermal as the real fix.
**⚠️ `-lgc` does NOT persist across reboot** — re-apply on both nodes after every boot, before any TP launch (candidate amendment: a systemd oneshot). **And it does NOT prevent the memory-ceiling freeze**: 2026-08-07, Node A froze under the seat (nvidia-smi blocked >368 s + NVRM `NV_ERR_NO_MEMORY`) *with the clamp applied* — that failure is fixed by the Phase 8 `SEAT_DIALS`, not here. Treat the clamp as power-off-specific.
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
  - model_name: deepseek-fp8     # cross-node TP=2 FP8 lane, brought up on demand (Phase 8)
    litellm_params: { model: openai/deepseek-ai/DeepSeek-V4-Flash, api_base: http://localhost:8080/v1, api_key: "none" }
    # ^ the segment after openai/ must be the id vLLM actually SERVES — the full HF repo id
    #   (assert via :8080/v1/models once the seat is up); a bare "deepseek-v4-flash" 404s upstream
    # NAMING (2026-08-08): renamed from `deepseek` -> `deepseek-fp8`. The BARE `deepseek` alias names
    # the pinned PRIMARY seat and is owned by the 0731 overlay (RUNBOOK-deepseek-v4-flash-0731 Phase 6
    # -> :8888) — never re-create a bare `deepseek` row here: two rows sharing one model_name form a
    # LiteLLM load-balance group that round-robins traffic into the down lane.
router_settings:
  fallbacks: []                  # NO local->cloud fallback (DF-001)
  context_window_fallbacks: []   # also empty — LiteLLM's documented example escalates to claude-opus on overflow (the exact unattended-spend footgun)
```
> **If Node A runs a personal / non-public fleet** (different aliases than the public `workhorse`/`coach`/`chat`/`embed` — e.g. the reference box serves `qwen36-workhorse`, `coach-ft-v3`, `embed`, …), **adapt this `model_list` to Node A's actual `:9000` aliases** before deploying. Each row is `model_name:` (the name your *agents* call, left side) → `model: openai/<llama-swap-alias>` (what it routes to on Node A, right side); `api_base` stays the llama-swap proxy port `:9000`. So map `workhorse` → `openai/qwen36-workhorse`, add a `coach` → `openai/coach-ft-v3` row, etc. `embed` usually matches as-is. Confirm Node A's aliases with `curl -s localhost:9000/v1/models | jq -r '.data[].id'`. The `deepseek-fp8` row is unchanged.

**▶ GATE — no cloud fallback (DF-001):** the robust invariant is *no cloud model is named anywhere in this config, fallback or otherwise*. Frontier planning happens on a Claude **subscription** (Claude Code / claude.ai), never through the front door — LiteLLM's anthropic backend is API-key per-token billing only, which this estate does not use. (An earlier revision carried a named `claude-opus` "DF-003 attended" row here; removed 2026-08-07 — subscription auth cannot be routed through LiteLLM, so the row was unusable by design.)
```bash
CFG=/opt/litellm/config.yaml
grep -qE '^\s*fallbacks:\s*\[\]' "$CFG" && grep -qE '^\s*context_window_fallbacks:\s*\[\]' "$CFG" \
  && echo "GATE PASS: no cloud fallback (both fallbacks empty)" \
  || echo "GATE FAIL: a cloud fallback path exists — DF-001 violation. STOP."
# NOTE: the leading `^\s*` anchor is load-bearing — without it, an empty `context_window_fallbacks: []`
# line satisfies the first grep's `fallbacks: []` substring even when `fallbacks:` is POPULATED (false-pass).
! sed 's/#.*//' "$CFG" | grep -qiE 'anthropic/|vertex|bedrock|gemini|openai/gpt-[0-9]' \
  && echo "GATE PASS: no cloud model named anywhere in YAML values" \
  || echo "GATE FAIL: a cloud model is named in the config — DF-001 violation. STOP."
# `sed 's/#.*//'` strips comments first so the in-file "…escalates to claude-opus on overflow" note
# can't false-FAIL the gate — it asserts YAML values only.
```

**▶ GATE — CPU-pin LiteLLM disjoint from llama-swap on Node A (WARN, not STOP):** Node A runs *both* the LiteLLM front door and the llama-swap pool, so under concurrent multi-model load they must not share a core (symptom: LiteLLM 504s + flaky llama-swap health). Set non-overlapping `CPUAffinity=` on the two user units; the GB10 CPU is **20 cores** (10× Cortex-X925 + 10× Cortex-A725) — e.g. litellm `0-3`, llama-swap `4-19`. WARN on overlap (the disjointness check is sound; the 504s rationale is community-sourced — see DF-005's verification note). Identical mechanism + gate as the single-Spark front-door overlay [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) Phase 4.2:
```bash
LSW=$(systemctl --user show llama-swap.service -p CPUAffinity --value 2>/dev/null)
LIT=$(systemctl --user show litellm.service   -p CPUAffinity --value 2>/dev/null)
python3 - "$LSW" "$LIT" <<'PY'
import sys
def expand(s):
    out=set()
    for t in (s or "").replace(',',' ').split():
        if '-' in t: a,b=t.split('-'); out|=set(range(int(a),int(b)+1))
        elif t.isdigit(): out.add(int(t))
    return out
a,b=expand(sys.argv[1]),expand(sys.argv[2])
print("GATE WARN: CPUAffinity not set on both units — pin disjoint (litellm 0-3 / llama-swap 4-19 on 20 cores)." if not a or not b
      else f"GATE WARN: CPUAffinity overlaps on {sorted(a&b)} — make disjoint." if a&b
      else "GATE PASS: litellm and llama-swap CPUAffinity disjoint.")
PY
```

**▶ GATE — front door answers (route to a local model):** a smoke request to `:4000` for `workhorse` returns a local completion (front door up + routing to llama-swap). The cloud-safety invariant is the no-cloud gate above; this just proves `:4000` is live and demuxing.
```bash
curl -sf http://localhost:4000/v1/models | jq -r '.data[].id' | sort
RESP=$(curl -s http://localhost:4000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"workhorse","max_tokens":16,"messages":[{"role":"user","content":"reply: pong"}]}')
echo "$RESP" | jq -e '.choices[0].message.content' >/dev/null \
  && echo "GATE PASS: :4000 front door answers from a local model" \
  || { echo "GATE FAIL: no local completion via :4000 — check LiteLLM + the llama-swap :9000 backend. STOP."; echo "$RESP" | head -c 400; }
```

**Install + run it (agent steps — not a pre-install):** the agent runs `pip install --user --break-system-packages 'litellm[proxy]'` (latest; validated baseline 1.89.4 on GB10 — floated not frozen, CONVENTIONS §3), then deploys **`examples/litellm-config.public.yaml` — the canonical model_list; the block above is an excerpt, not the source** — to `/opt/litellm/config.yaml` (adapt fleet aliases per the personal-fleet note; on a box running the dashboard overlay, edit the examples pair and mirror per the deployed file's header instead of overwriting — a blind heredoc here would clobber rows owned by later overlays, e.g. the 0731 runbook's bare `deepseek` row). Then run it as a **CPU-pinned user systemd unit** — the same unit as the single-Spark front-door overlay [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md) Phase 3 (`CPUAffinity=0-3`, llama-swap drop-in `4-19`), which is where the single-node LiteLLM front door (DECISION-DF-005, the precursor to this decision) is specified. Direct ad-hoc start for a quick test: `litellm --config /opt/litellm/config.yaml --port 4000 --host 0.0.0.0`.

---

## Phase 8: Memory-budget gate + two-box DeepSeek bring-up &nbsp;·&nbsp; **▶ GATE: pool XOR DeepSeek**

The ~158 GB DeepSeek shards to ~75–80 GB/node + KV — it claims the large majority of **both** boxes. It and a full swap pool **do not co-reside**. So: **evict the swap pool on EVERY participating node before launching the DeepSeek seat** (Node A always; Node B too if it ran single-Spark — stop, don't uninstall).

```bash
# 0. One-time: stand up the pinned vLLM runtime (agent step — heavy build, edit out the wait).
#    PINNED DEFAULT = eugr/spark-vllm-docker @ f7d6e3b5 (pinned 2026-08-02) — the community-standard Docker
#    harness (~1.9k★; --no-ray, fastsafetensors, GB-based gpu-mem-util, DeepGEMM nv_dev baked in).
#    Clone at the pin, build + distribute the vllm-node image from the head:
#      git clone https://github.com/eugr/spark-vllm-docker ~/spark-vllm-docker \
#        && git -C ~/spark-vllm-docker checkout f7d6e3b5db44ba19e1129d03793223692458929d
#      cd ~/spark-vllm-docker && ./build-and-copy.sh   # then assert BOTH nodes: docker image inspect vllm-node
#    (a dev clone may already exist at ~/Projects/spark-vllm-docker — fetch + checkout the pin there instead.
#     eugr tracks its own vLLM version — record the image's embedded vLLM commit in RESULTS on first build.)
#    REFERENCE BUILD (A/B escape hatch, venv not Docker) = jasl/vllm @ dda4668b + torch 2.9.1 — the exact
#    commit the canonical thread's 42–44 tok/s numbers validate against (torch 2.10 breaks CUDA graphs):
#      python3 -m venv ~/vllm-tp && ~/vllm-tp/bin/pip install -U pip torch==2.9.1 \
#        && ~/vllm-tp/bin/pip install 'vllm @ git+https://github.com/jasl/vllm@dda4668b'
#    (Separately, eugr is still credited for the 121a-real llama.cpp build flag. The granite-vision seat no
#     longer uses eugr images — it runs upstream vllm/vllm-openai:v0.22.0-aarch64-cu129-ubuntu2404 directly.)
# 0b. The DeepSeek weights (~158 GB) load LOCALLY PER NODE for mp/no-ray TP — vLLM pulls them to EACH
#     node's HF cache on first launch (so it downloads on BOTH A and B). Pre-stage to avoid inline waits:
#     hf download deepseek-ai/DeepSeek-V4-Flash   (run on each node)  — or point --model at a shared NFS dir.
# 1. Drain the fleet on EVERY participating node so it can't revive on top of the DeepSeek seat.
#    On Node A always (and Node B too, if it ran single-Spark): stop the keepalive timer + the fleet.
sudo systemctl stop llama-swap-keepalive.timer        # (system unit, per the single-Spark runbook)
systemctl --user stop llama-swap                      # fleet goes dormant during TP; `start` to revive after
# 2. Pre-launch: assert :8080 is FREE — an open-webui container squatted it 2026-08-07 → vLLM EADDRINUSE:
ss -ltnp | grep -E ':8080\b' && echo "FAIL: port squatted — stop/re-port the owner first" || echo "PASS: 8080 free"
#    Launch TP=2 across both nodes — DEFAULT (eugr recipe: MTP k=2, fp8 KV, deepseek_v4 tool parsers included).
#    The SEAT_DIALS (PINS) are MANDATORY on a front-door host: recipe defaults (0.8 util / 500K ctx) put
#    Node A at ~113 GB used — over the 115 ceiling — and Node A FROZE there (the registry's ~114 GB gotcha,
#    reproduced 2026-08-07: nvidia-smi blocked + NVRM NV_ERR_NO_MEMORY). 0.76/96K fits with margin:
#    ~109 GB used, KV 8.2 GiB available vs the ~6.9 GiB the 96K config needs (vLLM's startup ValueError
#    prints the exact arithmetic when a combination doesn't fit — trust it over hand-estimates: the
#    requirement has a ~6.9 GiB floor that barely moves with max-model-len).
#    -n pins the cluster + rendezvous to the CX-7 link IPs (never let it default to the LAN).
cd ~/spark-vllm-docker && ./run-recipe.sh deepseek-v4-flash --no-ray --port 8080 \
  -n ${N1},${N2} --gpu-memory-utilization 0.76 --max-model-len 98304
#    --no-ray is MANDATORY (the recipe yaml defaults to the ray backend; mp/no-ray is the 2-node way);
#    --port 8080 holds the estate port contract (recipe default is 8000). The harness autodiscovers the
#    NCCL env — ASSERT it picked the direct link (NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1), never trust it blind.
#    REFERENCE LANE (jasl venv, manual launch — only when A/B-ing against the validated reference build):
export NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1 NCCL_IB_DISABLE=0 \
       GLOO_SOCKET_IFNAME=enp1s0f1np1 TP_SOCKET_IFNAME=enp1s0f1np1
~/vllm-tp/bin/vllm serve deepseek-ai/DeepSeek-V4-Flash \
  --tensor-parallel-size 2 --distributed-executor-backend mp --nnodes 2 \
  --kv-cache-dtype fp8 --enable-expert-parallel --no-ray \
  --speculative-config '{"method":"deepseek_mtp","num_speculative_tokens":2}' \
  --max-num-seqs 2 --port 8080
#    (reference lane: jasl/vllm dda4668b + torch 2.9.1; choose a cudagraph mode that AVOIDS vLLM #40969
#     — FULL_AND_PIECEWISE + chunked prefill silently hangs after ~6–7 requests on GB10. The eugr recipe
#     ships VLLM_USE_BREAKABLE_CUDAGRAPH=0 in its env — confirm the hang doesn't reproduce during Phase 9.)
```
**▶ GATE:** before the launch, assert the pool is down (`curl -sf localhost:9000/running | jq '.running|length'` → 0 or torn down) so peak memory can't cross the freeze line. After load, `/v1/models` on `:8080` lists the DeepSeek seat. *(Endpoint shape verified on llama-swap v245, 2026-08-06: `/running` returns `{running:[...]}`. Note the fleet returns **429** while models are cold-loading after a revive — wait for `state:"ready"`.)*
**Treat the seat as single-stream:** concurrency=2 collapses decode to ~1 tok/s at 65 K. `--max-num-seqs 2` is a KV-budget cap, not a throughput target.
**Tear down** the DeepSeek seat, then revive each node you drained: `systemctl --user start llama-swap` + `sudo systemctl start llama-swap-keepalive.timer` — back to daily/pool mode.

---

## Phase 9: Benchmark + record &nbsp;·&nbsp; **▶ GATE: numbers captured**

```bash
# Same model, both ways — the numbers, not the README, decide whether TP earns its place.
#  (a) DeepSeek TP=2 decode tok/s + cold-start time (expect ~44 tok/s warm WITH MTP; ~5 without —
#      expectation from the jasl reference build; the first eugr-lane run RE-BASELINES it here)
#  (b) a fleet model single-node on Node A for contrast
#  (c) PP=2 vs TP=2 for the DeepSeek seat — PP wins under concurrency (~555 vs ~252 @batch128),
#      TP wins at batch=1 single-stream (the DeepSeek seat's actual regime). Record both.
```
Record decode tok/s (TP=2 / single-node / PP=2), cold-start, and TTFT@32K/128K.
**First-run baselines (2026-08-07, eugr lane, SEAT_DIALS 0.75/96K, clocks clamped 2150):** TP=2 warm single-stream **32.9 tok/s** (usage-counted; MTP k=2 — chunk-counting undercounts ~2×, MTP packs ~2 tok/chunk) · TTFT 0.36 s short / 28.9 s @ ~32K · cold 230 s, warm relaunch 114 s · single-node contrast (workhorse 35B) **62.1 tok/s** — capacity-not-speed measured. **PP=2: resolved by amendment** — the pinned eugr recipe exposes no pipeline-parallel knob, and the estate's regime is single-operator batch-1 (where TP wins; PP's advantage is concurrency-only). The operator amended DF-004's acceptance condition on 2026-08-07 and **DF-004 is ACCEPTED** on the TP + single-node measurements; PP-vs-TP is a revisit trigger in DF-004 §4.4 if a multi-stream workload ever materialises.

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
| P7 LiteLLM no-cloud guard (both fallbacks empty + no cloud model named) | | config is local-only, no cloud rows |
| P7 LiteLLM ↔ llama-swap CPUAffinity disjoint on Node A | | **WARN** (not hard-gated) |
| P7 front door `:4000` answers from a local model | | proves routing to llama-swap :9000 |
| P8 pool evicted before DeepSeek (memory XOR) | | |
| P9 TP=2 / single-node / PP=2 numbers | | **record tok/s + cold-start** |

## Phase 11: Evidence → RESULTS

Write `RESULTS-two-spark-bring-up-<YYYY-MM-DD>.md` (gate table filled + recorded numbers + the drift report link). Save the LiteLLM config + the vLLM launch command + the `all_gather_perf` output to `evidence/two-spark-bring-up/`. **DF-004 flipped PROPOSED → ACCEPTED 2026-08-07** on the on-hardware TP=2 + single-node measurements, with the PP-vs-TP leg removed from the acceptance condition by operator amendment (single-operator batch-1 regime; see DF-004's status line + §4.4 revisit trigger).

---

## Phase 12: Failure modes — fast triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `all_gather_perf` ~15.5 GB/s | CX-7 firmware throttle (Apr-2026) | Phase 2; CX-7 FW ≥ 28.45.4028 |
| busbw ~10 GB/s | both ports cabled, not all IP'd → 100 GbE | use ONE cable / IP all four ifaces |
| busbw fine but `NET/Socket` in logs | silent TCP fallback (lost RoCE) | pin `NCCL_IB_HCA`; Phase 4.3 `ib_write_bw` to isolate |
| Node hard powers-off ~60 s into TP | the open GB10 power-off bug | Phase 6: `-lgc` (unverified) + **thermal** (repaste/airflow) |
| One node drops, other GPU 100 % forever | torch 2.10.0 broke CUDA graphs | pin **torch 2.9.1** |
| DeepSeek hangs after ~6–7 requests, 0 decode | vLLM #40969 (FULL_AND_PIECEWISE + chunked prefill) | cudagraph mode change / `--enforce-eager` (slower) |
| DeepSeek decode ~5 tok/s not ~44 | MTP speculative decode off | `--speculative-config deepseek_mtp num_speculative_tokens=2` |
| NIC bricked (pre-init, error -110) | unsolicited `mlnx-fw-updater` flash | Phase 2 hold; `fwupdmgr` downgrade to known-good |
| Unattended run escalated to a cloud model + spend | LiteLLM `context_window_fallbacks` | Phase 7: set it `[]` too |
| Fleet models preload while the DeepSeek seat is up | live edit of the llama-swap config — `-watch-config` re-runs the `hooks.on_startup.preload` list on every reload, no service restart needed | `curl localhost:9000/unload` immediately (unloads all); edit the fleet config only while the seat is down (MEM_RULE) |
| LiteLLM 504s / flaky health on Node A under load | LiteLLM & llama-swap sharing a CPU core | Phase 7: disjoint `CPUAffinity=` (litellm 0-3 / llama-swap 4-19; 20-core GB10) |
| busbw ~2.8 GB/s, NET/IB correct, raw `ib_write_bw` ~13 Gb/s | runtime hotplug attach — slot power never advertised, NIC power-capped | Phase 3 power-cap guard: hotplug flag off + reboot BOTH with cable in |
| busbw ~17–18 GB/s (below 20, above the fw-degraded ~15.5) | secondary-path netdev (`enP2p…`) still MTU 1500 | Phase 3: `mtu: 9000` on BOTH PCIe paths, both nodes |
| NCCL `ibv_modify_qp … Invalid argument` on the P2 device | NM zeroconf IPv4 on one node's `enP2p…` → asymmetric GID tables | Phase 3 NM-zeroconf guard (`ipv4.method disabled` + reapply) |
| rank 1 dies: gloo `Unable to find address for <iface>` | cable in different port positions — eugr pushes ONE global iface name | move the cable: SAME port position both boxes (Phase 3) |
| vLLM API `OSError: [Errno 98] Address already in use` | something squats `:8080` (an open-webui container did) | Phase 8 pre-launch `ss` check; stop/re-port the squatter |
| Box FREEZES (nvidia-smi blocked, NVRM `NV_ERR_NO_MEMORY`) — not a power-off | unified-memory ceiling (~114 GB used); recipe defaults 0.8/500K | Phase 8 `SEAT_DIALS` 0.75/96K — the `-lgc` clamp does NOT prevent this |
| Box unreachable but alive; NM `no secrets: no agents`; Wi-Fi down | Wi-Fi LAN + NM autoconnect gave up after 4 retries | Phase 1: `autoconnect-retries 0` (infinite); prefer wired |
| mpirun warns `cannot find a corresponding process entry` / hangs | ghost `orted` from an aborted earlier run | `pkill -x orted` on both nodes, re-run |

---

## Appendix: relationship to the other artifacts

- **`RUNBOOK-single-spark-bring-up.md`** — Node A baseline. This runbook is additive on top; it never edits the Node A config.
- **[`DECISION-DF-004`](https://github.com/guardkit/guardkit/blob/main/docs/decisions/DECISION-DF-004-two-spark-serving-topology-unified-front-door.md)** (guardkit repo) — the topology + the memory-budget rule + the "capacity not speed" principle this runbook implements. **ACCEPTED 2026-08-07** on this runbook's first-run measurements (acceptance condition amended by the operator: PP leg dropped for the single-operator batch-1 regime).
- **[`DECISION-DF-005`](./DECISION-DF-005-single-spark-serving-topology-litellm-front-door.md)** (this repo) — the **single-node precursor**: the same LiteLLM `:4000` front door + no-cloud-fallback gate + disjoint-`CPUAffinity` gate, on one Spark. This two-node fabric is its **superset**; the LiteLLM Phase here re-uses the single-Spark front-door overlay [`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md)'s install/unit/gates (same mechanism, divergent config — this adds the cross-node `deepseek` backend; a `claude-opus` DF-003 row was briefly carried here and removed 2026-08-07: subscription auth cannot route through LiteLLM, so it was unusable by design).
