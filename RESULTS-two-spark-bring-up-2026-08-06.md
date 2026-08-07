# RESULTS — Two-Spark Bring-Up (executed 2026-08-06 → 2026-08-07)

**Runbook:** [`RUNBOOK-two-spark-bring-up.md`](./RUNBOOK-two-spark-bring-up.md) (Draft → this is the first execution) · **Drift report:** [`DRIFT-two-spark-bring-up-2026-08-06.md`](./DRIFT-two-spark-bring-up-2026-08-06.md) (2 drift, 3 flags; run proceeded on PINS) · **Mode:** fresh
**Node A:** `promaxgb10-41b1` (Dell Pro Max GB10; single-spark GREEN baseline: llama-swap v245 `:9000` public config + authenticated LiteLLM 1.95.0 `:4000` dashboard) · **Node B:** `spark-fcf6` (single-spark box, fleet time-shared)
**Executed by:** agent (Claude Code / Fable 5) with operator physical steps; wall-clock ~11 h elapsed including two operator power-cycles and an overnight pause (active agent time ~2.5 h)

## The one idea, on hardware

DECISION-DF-004 said a second node buys **capacity, not speed**. Measured: the 35B workhorse on ONE node decodes **62.1 tok/s**; DeepSeek-V4-Flash (284B-A13B, ~150 GB — fits on NO single node) decodes **32.9 tok/s** across the pair. The second node's value is that the big model runs *at all*, behind the same front door, time-shared with the day-to-day fleet — not that anything got faster.

## Gate table (Phase 10)

| Gate | Result | Note |
|---|---|---|
| P0.3 Drift report emitted + committed | **PASS** | `a674fec`; power-off persists on July FW; DeepSeek-0731/DSpark flagged for promotion PR |
| P2 firmware ≥ 28.45.4028 both nodes | **PASS** | 28.45.4028 on all 4 ports of both (boot-log method); `mlnx-fw-updater` not installed on either — brick vector absent |
| P3 CX-7 link `(Up)` | **PASS** | 200G negotiated; 2-min stability mini-gate clean (0 removal events); hotplug **disabled** (see findings) |
| P4(a) busbw ≥ 20 GB/s | **PASS — 23.85 GB/s** (initial), **23.89** (final topology) | healthy reference ~22.1; evidence `all_gather_perf-16G-*.txt` |
| P4(b) transport NET/IB | **PASS** | `NET/IB : Using [0]rocep1s0f1 [1]roceP2p1s0f1` both nodes; no Socket fallback |
| P5 passwordless SSH both ways | **PASS** | over the link IPs (169.254.207.1 ⇄ .2) |
| P6 power-off mitigation both nodes | **PASS** (clamp applied; **insufficient alone** — see findings) | `-lgc 200,2150`; NOT persistent across reboot |
| P7 no-cloud guard (both fallbacks empty + no cloud fallback target) | **PASS** (initial + re-check after row edit) | claude-opus attended-only, exact-name; claude-* still → local workhorse |
| P7 CPUAffinity disjoint (litellm/llama-swap) | **PASS** | 0-3 / 4-19 |
| P7 front door `:4000` answers local | **PASS** | authenticated (keyless 401 preserved); all 7 rows live |
| P8 pool evicted before DeepSeek (memory XOR) | **PASS** | both nodes drained + asserted; revived after teardown |
| P8 NCCL env asserted on launch | **PASS** | harness autodiscovered `NCCL_IB_HCA=rocep1s0f1,roceP2p1s0f1` — the direct link, exactly as the runbook demands |
| P8 `:8080` serves the seat | **PASS** | `deepseek-ai/DeepSeek-V4-Flash`; full path `:4000`→`:8080`→TP=2 proven (`-tp2-` fingerprint) |
| P9 numbers captured | **PASS (TP + single-node; PP deferred)** | see below |

## Recorded numbers (Phase 9)

| Measure | Value | Conditions |
|---|---|---|
| TP=2 decode, warm single-stream | **32.9 tok/s** (usage-counted; MTP k=2 on) | eugr lane, util 0.75 / 96K ctx, clocks clamped 2150; **re-baselines the eugr lane** (jasl-thread reference was ~44 unclamped @0.90 util) |
| TP=2 TTFT, short prompt | **0.36 s** warm | |
| TP=2 TTFT @ ~32K-token prompt | **28.9 s** (~1.1K tok/s effective prefill) | clamped clocks |
| Cold start | **230 s** first load; **114 s** warm relaunch | InstantTensor ~9 GB/s off NVMe cache |
| Single-node contrast (workhorse 35B-A3B, llama.cpp) | **62.1 tok/s**, TTFT 0.09 s | Node A `:9000`, fleet mode |
| PP=2 vs TP=2 | **DEFERRED** — the pinned eugr recipe exposes no pipeline-parallel knob; an on-hardware PP run needs a harness change (= PR) | carried from the canonical thread: PP wins under concurrency (~555 vs ~252 @batch128), TP wins batch-1 |
| all_gather busbw | **23.85 / 23.89 GB/s** + NET/IB | 16 GiB, nccl-tests @ NCCL 2.28.9-1+cuda13.0 |

**Consequence for DF-004:** the topology + memory rule + capacity-not-speed principle are **validated on hardware**, but the runbook's own promotion condition ("incl. PP-vs-TP") is only partially met — **DF-004 stays PROPOSED** until a PP lane exists (follow-on PR) or the condition is amended.
*(Addendum 2026-08-07: the condition **was** amended — the operator dropped the PP leg as inapplicable to the estate's single-operator batch-1 regime; **DF-004 is now ACCEPTED** on the TP + single-node measurements. PP-vs-TP became a revisit trigger in DF-004 §4.4.)*

## Execution-caught findings (amendments backlog — fold into the runbook by PR)

1. **CX-7 runtime hotplug attach power-caps the NIC.** With `dgx-spark-mlnx-hotplug` active, cable insertion after boot attaches the card with *"PCIe slot power capability was not advertised"* and raw RDMA caps at ~13–14 Gb/s (busbw 2.84 — below every documented failure signature). The fix is the runbook's own decision rule applied for a new reason: **disable the hotplug flag + reboot both nodes with the cable in** (boot-time attach = full power; 23.85 GB/s). The flags now live at `/etc/nvidia/cx7-hotplug-enabled.off` on both nodes (~18 W idle cost, documented trade).
2. **MTU must be raised on BOTH PCIe paths.** The runbook's netplan only IPs the primary netdev; NCCL stripes across both paths, and the secondary (`enP2p…`) at default 1500 drags busbw to 17.85. `mtu: 9000` on both paths → 23.85. (Netplan `40-cx7.yaml` on both nodes now carries both ifaces.)
3. **Same physical port on both boxes is a REQUIREMENT for the eugr harness, not a tidiness tip.** `launch-cluster.sh` pushes one global `ETH_IF`/`IB_IF` to every node; with asymmetric ports rank 1 dies (`gloo … Unable to find address for: enp1s0f1np1`). Operator moved B's cable to match A (port f1 both). The runbook's Phase 3 wording should be upgraded for the eugr lane.
4. **NetworkManager zeroconf poisons the secondary path's GID table.** On (re)boot/cable-move, NM's rendered profile (`ipv4.method=link-local`) gives the address-less `enP2p…` netdev a random 169.254 IPv4 → asymmetric GID tables → NCCL `ibv_modify_qp … EINVAL`. Fix applied on both nodes: `nmcli connection modify netplan-enP2p1s0f1np1 ipv4.method disabled` + `ipv6.method link-local` (netplan's `link-local: [ipv6]` does NOT render this correctly via the NM backend). **Recurs after netplan regeneration — must be folded into the runbook.**
5. **The recipe's memory defaults are over the freeze line on a front-door host.** eugr defaults (util 0.8, 500K ctx) put Node A at ~113 G used / 7 G free — and Node A **froze** there (nvidia-smi blocked >368 s + NVRM `NV_ERR_NO_MEMORY` spam; the registry's ~114 G freeze gotcha, reproduced). The `-lgc` clamp did not prevent it. Fitted operating point, verified: **`--gpu-memory-utilization 0.75 --max-model-len 98304`** → A ~107 G used, KV 6.97 GiB (96K needs ~5.3). vLLM's startup error message provides the exact arithmetic when a combination doesn't fit.
6. **`-lgc` clamp is not persistent** — it resets on every reboot and must be re-applied before any TP launch (candidate for a systemd oneshot in the runbook).
7. **Port 8080 squatting:** an `open-webui` container (host-bound `0.0.0.0:8080`) collided with the estate port contract; stopped for the session and **left stopped** — re-port it before restarting (`docker start open-webui`).
8. **Node A's LAN is Wi-Fi and it strands the box.** An AP auth blip at 07:04 exhausted NM's default 4 autoconnect retries; the box sat healthy-but-unreachable for 80 min (the second "disconnect" — NOT the GB10 bug). Fixed: `connection.autoconnect-retries 0` (infinite) on `whitestocks`. **Recommend wired Ethernet for Node A.**
9. **Cable seating:** the first insertion was upside-down (operator-corrected); zero module-detect events is the signature. The QSFP56/FS.COM false-removal gotcha did NOT occur — link held every stability watch.
10. **LiteLLM deepseek row must use the served id:** vLLM serves `deepseek-ai/DeepSeek-V4-Flash`, so the row is `model: openai/deepseek-ai/DeepSeek-V4-Flash` (runbook excerpt says `openai/deepseek-v4-flash` — would 404). Fixed in both example files + live (`642e258` + follow-up commit this run).
11. **PINS decode note:** `nccl-tests v2.28.9-1` is the **NCCL library deb version** (`libnccl2/-dev 2.28.9-1+cuda13.0`, installed exactly); nccl-tests itself has no 2.28.x tag — built at upstream HEAD `717b683`, MPI=1, sm_121.
12. **First launch failure mode worth a triage row:** vLLM `EADDRINUSE` on :8080 → check for squatters before launch (`ss -ltnp | grep :8080`).

## Box-state deltas this run leaves behind

- Both nodes: CX-7 hotplug flag **off** (`…/cx7-hotplug-enabled.off`), netplan `40-cx7.yaml` (A: `169.254.207.1/16`, B: `.2/16`, mtu 9000 both paths), NM P2 profiles v6-LL-only, NCCL 2.28.9-1+cuda13.0 + nccl-tests built, `perftest` installed, cable in port **f1 on both**.
- Node A: LiteLLM live config = dashboard twin + `deepseek` + `claude-opus` rows (backup: `/opt/litellm/config.yaml.bak-20260806-twospark`); wifi autoconnect-retries infinite; `open-webui` stopped; clock clamp applied (non-persistent).
- Node B: A's key + B→A SSH mesh; fleet revived (mode 1).
- Weights: `deepseek-ai/DeepSeek-V4-Flash` (~149 G) in both HF caches (alongside the `-0731` staged for the follow-on runbook). Image `vllm-node` (eugr @ f7d6e3b5; embedded vLLM `0.26.1rc1.dev439+g7b9f2dad8`, flashinfer 0.6.17) on both nodes.
- End state: **mode 1 (day-to-day)** — both fleets serving, front door green, DeepSeek seat torn down (on-demand per the runbook's Phase 8 launch/teardown).

## Evidence

[`evidence/two-spark-bring-up/`](./evidence/two-spark-bring-up/): known-good NIC FW · all_gather 16G (initial + final topology) · NCCL transport signal · deployed LiteLLM config · vLLM launch command + env · TP=2 decode + 32K-TTFT benches · single-node contrast bench.
