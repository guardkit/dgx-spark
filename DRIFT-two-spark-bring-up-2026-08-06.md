# DRIFT REPORT — RUNBOOK-two-spark-bring-up, run 2026-08-06

Mode: **fresh** — first execution of the two-spark bring-up. Node A = `promaxgb10-41b1` (single-spark GREEN, public config, LiteLLM :4000 authenticated per the dashboard overlay), Node B = `spark-fcf6`. Executed by agent (Claude Code / Fable 5). Recon per CONVENTIONS §4; no step edited, no pin changed.

## PIN CHECKS (deterministic)

```
[OK]    CX-7 firmware     28.45.4028 on all 4 ports, BOTH nodes == the gate floor exactly (boot-log method;
                          cards power-gated off the PCIe bus pre-cable, as the runbook predicts)
[DRIFT] DGX OS / driver   both nodes matched at DGX OS 7.2.3 / driver 580.173.02 vs pinned 7.5.0 / 580.159.03
                          — the matched-pair requirement is satisfied; driver is NEWER than the pin
                          (drift already known from the 2026-08-04 Node B access check)
[OK]    CUDA              13.0 (nvidia-smi major.minor; pin 13.0.2)
[INFO]  UEFI              vendor-scheme BIOS strings (Node A Dell FCM1253: 5.36_4.0.0; Node B: 5.36_0ACUM018)
                          — not comparable to the pinned NVIDIA UEFI 1.108.20; same 5.36 base on both
[DRIFT] eugr/spark-vllm-docker  pinned f7d6e3b5 (2026-08-02); HEAD 42b3a793 (2026-08-05)
                          "Replaced loader with instanttensor in more recipes"
[OK]    jasl/vllm         reference pin dda4668b exists upstream (2026-05-13)
[OK]    litellm           latest release v1.95.0 == the validated 2026-08-04 baseline (floated dep, CONVENTIONS §3)
[INFO]  nccl-tests        releases API returned empty this run — recon degraded on this source;
                          pin v2.28.9-1 unverified vs latest (build-from-source pin, gate-protected anyway)
[OK]    DeepSpec          deepseek-ai/DeepSpec repo live, NO releases/tags yet — no SM121/aarch64 path to watch-adopt
[INFO]  torch             not installed on either node — expected pre-Phase 8 (the Docker lane carries its own;
                          the jasl reference lane installs 2.9.1 into its venv)
```

## SOURCE SCAN (advisory — fixed sources, items newer than PINS date 2026-06-22)

```
[FLAG] GB10 hard power-off STILL REPRODUCES on the July-2026 platform firmware (OTA2607) — forum thread
       "Hard power-off under sustained GPU load at ~90W, persists after full platform firmware update"
       — the July EC/UEFI release does NOT clear the Phase 6 gotcha; the mitigation stays load-bearing
       https://forums.developer.nvidia.com/t/hard-power-off-under-sustained-gpu-load-at-90w-persists-after-full-platform-firmware-update/378315
[INFO] July-2026 DGX Spark software release exists (EC + UEFI device firmware updates) — post-PINS platform
       FW is available; given the flag above it is NOT a reason to flash mid-run
       https://forums.developer.nvidia.com/t/dgx-spark-software-updates-july-2026-release/376736
[FLAG] connect-two-sparks playbook updated 2026-07-21 ("network configuration updates") — now documents
       persistent netplan /24 subnets (192.168.100.x / 192.168.101.x) as the primary path; this runbook's
       Phase 3 assumes link-local 169.254 via 40-cx7.yaml (still works; the playbook itself notes full
       bandwidth with one cable). Playbook still advises same-port-on-both to "prevent NCCL test issues"
       — stronger wording than the runbook's tidiness-tip framing.
       https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/connect-two-sparks/README.md
[FLAG] DeepSeek recipe space moved past the pins: community recipes now serve DeepSeek-V4-Flash-0731-DSpark
       (DSpark speculative decoding + nvfp4_ds_mla KV) at ~67.6 tok/s mean / 84.3 peak single-stream on
       2x Spark (tonyd2wild repo, updated ~2026-08-03); shipped MTP defaults moved k=3→5; a newer vLLM
       0.25.2 runtime measured SLOWER than the older one on the same HW. Touches the DeepSeek + MTP +
       vLLM pins. Adoption = PR; the repo already carries RUNBOOK-deepseek-v4-flash-0731-two-spark.md
       as the follow-on artifact for exactly this.
       https://github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark
[INFO] CX-7 hotplug: "ConnectX-7 network cards disappear after DGX Spark system update (cx7-pcie-hotplug)"
       — matches the hotplug gotcha Phase 3 already gates (stability mini-gate + hotplug-disable decision rule)
       https://forums.developer.nvidia.com/t/connectx-7-network-cards-disappear-after-dgx-spark-system-update-due-to-cx7-pcie-hotplug-driver-issue/374275
[INFO] 4x Spark TP=4 recipe (jasl fork, RDMA, MTP, 49–54 tok/s) — beyond 2-node scope (DF-004 §4.4)
       https://forums.developer.nvidia.com/t/deepseek-v4-flash-on-4x-dgx-spark-via-vllm-jasl-fork-tp-4-rdma-mtp-49-54-tok-s-single-stream-full-recipe-the-traps/373808
```

## VERDICT

**2 drift, 3 flags. Procedure unchanged — the run proceeds on current PINS.** The two drifts are benign for this run (matched driver pair newer than pin; eugr HEAD moved but we clone AT the pin). The DeepSeek-0731/DSpark flag is the one worth a promotion PR after this run — it is the follow-on runbook's territory, not a mid-run change. Review before promoting pins (CONVENTIONS §6).
