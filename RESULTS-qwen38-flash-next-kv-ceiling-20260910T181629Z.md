# AutoRound KV allocation under a 120 GB ceiling — 20260910T181629Z

**Disposition, 2026-09-10 18:57:07 UTC:** retain **19 GB KV** at `http://spark-fcf6.local:8888/v1`, model `qwen3.8-flash-next-autoround`. This is the highest whole-GB allocation tested here that completed the selected core workloads below the user-selected ceiling. It is not a claim about the absolute maximum allocation or multi-day stability.

## Policy and controlled change

The user authorized increasing KV allocation and treating **120 decimal GB total RAM usage** as the safe ceiling. The guard measures effective used RAM as `MemTotal - MemAvailable`. Both thresholds were changed together:

- Maximum used: **120,000,000,000 bytes = 111.758708954 GiB**.
- Minimum available on this host: **9.930850983 GiB**, derived from `MemTotal=130,663,170,048 bytes`.
- Swap remained disabled, and no swap-counter increase was permitted.

This replaces the earlier 109 GiB used / 12 GiB available trial cutoffs. The user's operational observation informed the ceiling; these attended tests do not establish a multi-day soak result. All totals below include the host-local test clients and other remaining host processes. Two-second guard samples are not instantaneous peak measurements.

The live, validated 12 GB image, model/table mounts and compiled cache were reused. No rebuild, package upgrade, new quantization, fresh download or all-file rehash occurred during this allocation ladder. The same pinned model, exact top-k, MTP3/private 65,536-token draft vocabulary, BF16 KV, native 262144 context, eight sequences and 8192-token prefill chunks remained in use. Development APIs were enabled only on loopback during cache tests, then disabled before normal network exposure.

## Allocation ladder

| KV allocation | Reported cache-token capacity | Sampled peak total RAM | Outcome |
|---:|---:|---:|---|
| 12 GB | 386,839 | 111.571 GB in the prior final validation | Previously validated baseline; not rebenchmarked in this ladder |
| 18 GB | 579,550 | **117.043 GB** | Startup, tools/JSON and 96K cache checks passed; proceeded upward |
| 20 GB | 644,732 | **120.026 GB** | Guard stopped the model during growing history; rejected |
| **19 GB** | **612,141** | **118.534 GB** | Core single-conversation workload checks and normal endpoint passed; retained |

The 19 GB pool adds 7 GB of requested KV allocation and roughly **58% more reported cache tokens** than 12 GB. Its measured peak left **1.466 GB below the selected ceiling**, with at least **11.296 GiB available RAM**. Both its validation and normal-mode startup remained within that envelope.

At 20 GB, startup and a fixed-prefix 250K test passed, but a later growing-history run reached **120,025,714,688 bytes** effective used—about **25.7 MB above the ceiling**. The guard stopped the container. This was a guard-enforced limit, not an observed CUDA OOM. The failed sample and interrupted request are retained; lowering the pool did not retroactively turn that attempt into a pass.

## Retained 19 GB workload evidence

| Check | Result |
|---|---|
| Startup / identity | PASS; same ARM64 image and model settings, GPU/SM121 and native context verified |
| Protocol | PASS; automatic, required and named tool calls, arguments, all continuations, standalone JSON, thinking off |
| Fixed-prefix cache | PASS at **250,069 prompt tokens**, including changed-question and unrelated-prefix correctness |
| Cold / warm first output | **162.326 s / 2.097 s** at 250K |
| Growing tool history | PASS at targets **20K, 96K and 250K**, with correct earlier-tool-result recall |
| Growing continuation cache hits | Increments of **17,600 / 94,400 / 248,000 tokens**; final continuation prompt **250,145 tokens** |
| Sustained generation | PASS; **8192 completion tokens**, **139.584 s**, **58.791 tok/s approximate decode** |
| Whole-request generation rate | **58.689 tok/s**; first output **0.261 s** |
| Memory / swap | PASS; maximum **118.534 GB used**, unchanged swap counters, no guard stop |
| Runtime log review | No Mamba state-copy guard hit, CUDA error or traceback observed in the validation logs |
| Normal-mode transition | PASS; same image/settings/mount entries; only bind address and development-API flag changed |
| Hostname-based protocol checks | PASS through `spark-fcf6.local:8888`, originating on the Spark |
| External client / gateway / Factory | NOT TESTED / unchanged / NOT RUN |

The code stream ended at its 8192-token cap (`finish_reason=length`). This is a serving-performance receipt, not a completed coding-task result. The prior 12 GB capture measured 60.78 tok/s; these single runs do not establish a statistically meaningful performance difference or a speedup from larger KV. The broader seven-length smoke series remains in the [12 GB validation](./RESULTS-qwen38-flash-next-autoround-seat-20260910T165917Z.md); this allocation trial used the lengths listed above.

Validation MTP counters recorded **2258 drafts**, **6774 proposed tokens**, and **6213 accepted tokens** (about 91.72%). Accepted counts by position were **2164 / 2073 / 1976**. Prefix counters recorded **1,485,179 queried tokens / 968,000 hit tokens**, with zero scheduler preemptions. These counters cover the listed 19 GB validation process and reset on the normal-mode restart.

## Additional two-context test: limitation, not a passed capacity claim

At **20 GB**, two independent requests of **250,054 and 250,096 tokens** were submitted together, then repeated together. All four answers were correct, but the requirement that both warm first-output times be at most half their cold times **failed**:

| Context | Cold first output | Warm first output |
|---|---:|---:|
| A | 161.052 s | **136.489 s** |
| B | 322.025 s | 6.039 s |

The cold timings and live scheduler observations are consistent with mostly sequential cold prefilling. One older context required substantial prefill again on its repeat. The advertised cache capacity therefore did not translate into fast reuse of both full contexts in this test. This does not identify the underlying cache-management cause. No scheduler preemption was reported in the captured metrics.

This was additional capacity characterization, separate from the core single-conversation checks. Its failure remains recorded. It was **not repeated at 19 GB**, and no claim that 19 GB fixes it is made. The next independent growing-history check at 20 GB then failed the RAM ceiling. The [concurrent probe](./scripts/qwen38-concurrent-cache-probe.py) is included for reproduction; its executable AST matches the private script that ran. Use it only on an isolated loopback validation server with the reset API enabled.

## Identity, evidence and retained state

- Host: `spark-fcf6`, NVIDIA GB10 / ARM64, driver `580.173.02`, Docker `29.2.1`.
- Serving image: `sha256:3acf22132d7b912450570e32d9c1696385b731e26f590b0d34c332822ccd245a`.
- Recipe `1633d4bc11701c04d7cbd633994421466d1eff1d`; base digest `sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`; kernel `e0ef69d4f5575dad00d34e05479eaf4c6547bace`.
- Checkpoint `Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN@19f9710c8f6600a32e15fb98bc77613ee8ec369b`; PLE `Saren/Qwen3.8-Flash-Next-ple-table-fp8@50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14`.
- vLLM `0.1.dev20073+g8e685d198`, torch `2.13.0+cu130`; model/template and all-file identity receipts inherited from the validated baseline.
- Repository HEAD `fb8395e0b0f020e6dd30de413ce681bf15c988cf`, with uncommitted working-tree procedure changes. Private execution scripts, helper snapshots and hashes record the allocation overlay; final runbook v1.7 documents the selected defaults rather than claiming to be the unchanged pre-trial procedure.

Private ladder directory: `/home/richardwoollcott/qwen38-autoround-kv-runs/20260910T181629Z`. Each of `18g`, `20g`, `19g` and `19g-normal` contains its actual pins, container/startup evidence and memory samples. In particular, retain `20g/memory.failed`, concurrent cold/warm responses and `concurrent-assessment.json`, `19g/stage-result.json`, decode and growing receipts, and `19g-normal/normal-mode-checks.json`. The root contains the baseline container, limits, executed scripts/helper snapshots, procedure hashes, original recovery-owner pointer and final `execution-state.json`. See [drift](./DRIFT-qwen38-flash-next-kv-ceiling-20260910T181629Z.md).

The retained normal container is `qwen38-autoround-seat`, restart policy `no`, bind `0.0.0.0:8888`, development APIs disabled. `POST /reset_prefix_cache` returns 404. The 120 GB memory guard remains active. Original llama-swap services remain runtime-masked/inactive and swap remains disabled. LiteLLM stays active, with no gateway route or key changes. No remote-client connectivity or Factory task claim follows from the local hostname check.

The original fleet recovery snapshot still belongs to `/home/richardwoollcott/qwen38-autoround-seat-runs/20260910T165917Z`; copies needed for teardown are retained in the current run, and the original fleet configuration hash still matches. To stop the Qwen seat and restore fleet/swap:

```bash
cd /home/richardwoollcott/Projects/appmilla_github/dgx-spark
source /home/richardwoollcott/qwen38-autoround-kv-runs/20260910T181629Z/19g-normal/pins.sh
source "$RUN_DIR/block-8.sh"
```

Then verify embedding, speech and tutor health as described in the runbook. Teardown was not performed at this disposition because the 19 GB seat is deliberately retained.
