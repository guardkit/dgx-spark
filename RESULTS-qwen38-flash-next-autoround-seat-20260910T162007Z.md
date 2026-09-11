# AutoRound seat execution — 20260910T162007Z

**Disposition:** startup stopped by the RAM guard; original fleet and swap restored. **Not serving-ready.** No responses were generated, and no throughput, context/cache, protocol, application canary or Factory comparison result is available.

## Artifact and procedure identity

- Machine: `spark-fcf6`, ARM64 / NVIDIA GB10, 121.690 GiB OS-visible memory; driver `580.173.02`, Docker `29.2.1`.
- Source: Saren `1633d4bc11701c04d7cbd633994421466d1eff1d`; base `vllm/vllm-openai:qwen38-flash-next@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`; external kernel `e0ef69d4f5575dad00d34e05479eaf4c6547bace`.
- **Serving image reused from the first attempt:** `sha256:3acf22132d7b912450570e32d9c1696385b731e26f590b0d34c332822ccd245a`. vLLM `0.1.dev20073+g8e685d198`, torch `2.13.0+cu130`, transformers `5.15.1`, fastsafetensors `0.3.3`.
- The repeat source build produced `sha256:fd5c8268b79061100fe386b73d371b34d9d2337759d0b2b6b52ce57244587b9a`. It was used only for CPU artifact staging/checksums; its separate build receipt is retained. It was not the serving image.
- Checkpoint: `Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN@19f9710c8f6600a32e15fb98bc77613ee8ec369b`.
- PLE: `Saren/Qwen3.8-Flash-Next-ple-table-fp8@50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14`.
- All **115 repository files** reverified against upstream identity: 68 indexed model shards, 33 PLE files and 128 logical PLE partitions validated. Existing downloads reused.
- Repository HEAD `fb8395e0b0f020e6dd30de413ce681bf15c988cf`, with uncommitted procedure files. Executed runbook SHA-256 `0bbbf03bcf0105713ae2ccc6202d9a9864d08d91a1c3fd4b2b7106c80c018eaa`; immutable copy in the evidence directory. Later status-only documentation is not the executed procedure.
- Serving settings unchanged from the first attempt: MTP3, private 65,536-token draft vocabulary, ten routed experts, exact top-k, prefix cache, native 262144 context, BF16/auto KV, eight sequences, 8192-token prefill chunks, explicit `20g` KV, local-NVMe PLE and prewarming.

## Gate outcomes

| Gate | Result | Evidence |
|---|---|---|
| Preflight/base snapshot | PASS | Original fleet/catalog/config and swap state saved |
| Artifacts | PASS | ARM64 image identity and all-file hashes reverified |
| Isolation/headroom | PASS | Effective runtime mask; GPU fleet drained; 110.950 GiB available after settling |
| Swap preparation | PASS | Only the recorded `/swap.img` temporarily disabled; no fstab or sysctl changes |
| Startup | FAIL / interrupted | Weights loaded; guard stopped engine during cache/warmup preparation, before API readiness |
| Memory | FAIL | 110.789 GiB effective used, 10.901 GiB available; limits 109 GiB / 12 GiB |
| No-swap during startup | PASS for observed interval | Zero swap occupancy and unchanged swap-in/out counters across 141 samples |
| Context/cache, MTP acceptance, tools/JSON, decode/long stream | NOT RUN | API never became ready |
| Gateway | N/A | No route or key changes |
| Recovery | PASS | Swap identity/priority restored; fleet catalog/config matched; embedding, speech and tutor checks passed |

The loader reported **67.92 GiB** for model loading in **105.344 seconds**. vLLM then reserved **20,000,000,000 bytes (18.63 GiB)** for KV and reported **644,732 cache tokens**, or 2.46 full native-context requests. Explicit KV sizing bypassed its automatic memory budget calculation: `gpu_memory_utilization=0.01` did not cap that reservation.

At **2026-09-10 16:30:00 UTC**, the guard observed **110.7890548706 GiB used / 10.9005050659 GiB available**. These are also the maximum/minimum in the 141 recorded two-second samples, not an instantaneous peak claim. Swap occupancy remained zero; `pswpin=2456334` and `pswpout=6298985` were unchanged from the post-swapoff baseline. Both RAM limits were breached, so the guard stopped the container. This demonstrates that the selected configuration did not fit the runbook's memory envelope on this host; it is not an observed CUDA OOM or proof that the model cannot run with a smaller cache.

The [first attempt](./RESULTS-qwen38-flash-next-autoround-seat-20260910T145550Z.md) stopped for small swap activity while RAM remained within limits. This retry intentionally disabled the recorded swap file before baselining the guard, without changing model settings or loosening RAM limits. The retry therefore establishes a separate RAM failure.

## Startup diagnostic and next trial

The log printed `QSADET active` despite `VLLM_QSA_DET_TOPK=0`. Inspection of the **actual serving image's** `qsa.py` explains the message: the library-loading condition tests a nonempty environment string, so the string `"0"` loads the extension. The subsequent dispatch independently checks `_QSA_TOPK_MODE == "1"` and calls `_qsa_exact_topk`; the custom `topk_op` is only called in the other branches. Container inspection confirmed `VLLM_QSA_EXACT_TOPK=1`. Thus the message alone does **not** establish use of the custom selection kernel or defeat the exact fallback. This is source/dispatch evidence, not a completed long-context test. A future launcher should omit `VLLM_QSA_DET_TOPK` when disabled, matching the upstream shell wrapper and avoiding unnecessary library loading.

**Recommended next configuration, not executed or promoted:** keep the same image, checkpoint, MTP3, BF16 KV, exact top-k and native context, but reduce explicit KV from `20g` to **`12g`**. That reduces the requested pool by **7.45 GiB**. This is a capacity hypothesis: allocation sizes and remaining startup/workload peaks must be measured. The current reported cache capacity suggests room to reduce the pool, but does not prove that the smaller pool supports a 250K request with the required headroom. Require engine admission of native context, the existing memory guard, and all original serving gates. Keep the 109 GiB used / 12 GiB available limits unchanged. The failed `20g` pins remain in the runbook for traceability; no third launch was attempted.

## Evidence and final state

Private evidence: `/home/richardwoollcott/qwen38-autoround-seat-runs/20260910T162007Z`. Key receipts: `runbook-executed.md`, `procedure.sha256`, `artifacts.sha256.json`, `image.json`, `image-selection.txt`, `rebuild-image.json`, `failed-start.log`, `failed-container.json`, `memory.jsonl`, `memory.failed`, `patched-qsa.py`, `swaps-before.txt`, `swaps-drained.txt`, `swaps-after.txt`, `rollback.log`, `restoration-checks.json` and `execution-state.json`.

The Qwen container was removed, its memory guard stopped, and both runtime fleet masks removed. `/swap.img` is active again with its original size and priority `-2`. The original llama-swap unit is loaded and active; its configuration hash and catalog match the saved baseline. A real embedding request returned 1024 finite values; Parakeet, Qwen TTS and both tutor health endpoints returned HTTP 200. Existing model files and built images remain available for reuse. Gateway configuration and Factory execution were untouched. See the [drift report](./DRIFT-qwen38-flash-next-autoround-20260910T162007Z.md).
