# AutoRound seat execution — 20260910T145550Z

**Disposition:** startup stopped by the memory guard; fleet restored. **Not serving-ready.** No application canary or Factory comparison was run. The built image and verified model/table files are retained for reuse.

## Artifact and procedure identity

- Machine: `spark-fcf6`, ARM64 / NVIDIA GB10; driver `580.173.02`, Docker `29.2.1`.
- Source: Saren `1633d4bc11701c04d7cbd633994421466d1eff1d`; base `vllm/vllm-openai:qwen38-flash-next@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`.
- Built image: `sha256:3acf22132d7b912450570e32d9c1696385b731e26f590b0d34c332822ccd245a`. vLLM `0.1.dev20073+g8e685d198`, torch `2.13.0+cu130`, transformers `5.15.1`, fastsafetensors `0.3.3`.
- Checkpoint: `Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN@19f9710c8f6600a32e15fb98bc77613ee8ec369b`.
- PLE: `Saren/Qwen3.8-Flash-Next-ple-table-fp8@50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14`.
- All **115 repository files** passed upstream identity checks; 68 indexed model shards, 33 PLE files and all 128 logical PLE partitions passed validation.
- Repository HEAD: `fb8395e0b0f020e6dd30de413ce681bf15c988cf`, with uncommitted procedure files. Executed runbook SHA-256: `0d3e4b6c6d6a52e7676c88b8c18ae473a9db2caea26339a01f9d72597a916ee4`. The immutable executed copy and original/corrected hashes are in the private evidence directory.
- Serving settings: MTP3, reduced draft vocabulary, full ten routed experts, exact top-k, prefix cache, native 262144 context, BF16/auto KV, eight sequences, explicit `20g` KV, local-NVMe PLE, prewarm on. No model or serving parameter was changed during the attempt.

## Gate outcomes

| Gate | Result | Evidence |
|---|---|---|
| Preflight/base recovery snapshot | PASS | ARM64, Docker/sudo, local NVMe, free port, base catalog/config snapshot |
| Artifacts | PASS | Image build/identity and every checkpoint/table file verified |
| Isolation | PASS after procedure correction | Higher-precedence runtime user-unit mask; no remaining GPU workloads |
| Prelaunch headroom | PASS after settling correction | Initial immediate assertion failed during asynchronous GPU release; subsequently 110.938 GiB available across three consecutive samples |
| Startup | FAIL / interrupted | Guard stopped container before API readiness; two checkpoint shards had loaded and PLE prewarming had begun |
| Memory/no-swap | FAIL | Swap activity with RAM still inside both limits |
| Context/cache, tools/JSON, decode/long stream, accepted MTP tokens | NOT RUN | Startup did not complete |
| Gateway | N/A | No routes or keys changed |
| Recovery | PASS | Original fleet catalog/config restored; embedding inference (1024 dimensions), speech and tutor health checks passed |

At the guard trip, effective used memory was **86.821 GiB** and available memory **34.869 GiB**. Both were inside the 109 GiB used / 12 GiB available limits. Swap occupancy grew **286,720 bytes (280 KiB)** and the swap-out counter grew **69 pages**. Swap-in did not increase. These are sampled values, not a claim about an unobserved instantaneous peak. The guard enforced the no-swap rule and prevented further startup.

The host had `/swap.img` active and `vm.swappiness=60`. This result establishes a swap-gate failure; it does not establish that the model exceeds physical memory capacity. A subsequent procedure revision adds temporary swap-file deactivation before the guard baseline, preserving the same RAM limits and restoring swap during teardown. That revision has its own execution evidence.

The first execution also exposed two host-control issues: ordinary runtime masks lose precedence to this user-configured unit, and GPU memory can release after service stop returns. Both corrections were recorded before launch, with prior procedure copies retained. The failed immediate headroom assertion was preserved, not counted as an uninterrupted pass.

## Evidence and final state

Private evidence: `/home/richardwoollcott/qwen38-autoround-seat-runs/20260910T145550Z`. Key files: `artifacts.sha256.json`, `image.json`, `build.log`, `failed-start.log`, `failed-container.json`, `memory.jsonl`, `memory.failed`, `drain-first-attempt.log`, `drain-settled.log`, `procedure-correction.txt`, `rollback.log`, `restoration-checks.json` and `runbook-executed.md`.

The failed model container was removed, both runtime masks removed and the guard stopped. Swap configuration was unchanged in this attempt. The fleet was restored; health checks also warmed the tutor and coach models. No model weights, images, fleet configuration, gateway routes or keys were deleted or replaced. See [recon drift](DRIFT-qwen38-flash-next-autoround-20260910T145550Z.md).
