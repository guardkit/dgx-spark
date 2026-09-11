# AutoRound 12 GB KV serving validation — 20260910T165917Z

**Disposition, 2026-09-10 17:39:22 UTC:** serving-ready at the normal direct API, retained on `spark-fcf6`. Validation required documented helper/setup corrections; original failed receipts are preserved. **No Factory evaluation or correctly-completed-task comparison ran.**

- Endpoint: `http://spark-fcf6.local:8888/v1`
- Model ID: `qwen3.8-flash-next-autoround`
- Container: `qwen38-autoround-seat`, restart policy `no`; development APIs disabled, bind `0.0.0.0:8888`.
- Original llama-swap fleet remains **runtime-masked and inactive**; `/swap.img` remains **inactive**. The memory guard remains **active**. Existing LiteLLM stays active; no gateway route or key changed.

## What the KV reduction established

Reducing the explicit pool from **20 GB to 12 GB** allowed startup and the tested workloads to remain inside the original conservative guard limits. The engine resolved `12g` to **12,000,000,000 bytes / 11.18 GiB**, providing **386,839 cache tokens**, or **1.48 native-context requests**. Native context stayed **262144**; the main model, full ten routed experts, MTP3, private draft vocabulary, BF16 KV and prefix caching were unchanged.

The guard uses `MemTotal - MemAvailable`, stopping above **109 GiB used (117.038 decimal GB)** or below **12 GiB available (12.885 GB)**. These are trial cutoffs, not an established hardware ceiling. The operator reports stable multi-day operation at 120 GB; that observation is compatible with the earlier **118.959 GB guard stop**, which was not an observed OOM. Compare units and reclaimable-cache accounting before comparing monitoring tools.

Across the retained two-second samples through disposition, maximum effective used memory was **103.908 GiB** and minimum available memory **17.781 GiB**. Swap occupancy stayed zero, and `pswpin=2659653` / `pswpout=6504603` remained unchanged after swapoff and the guard baseline. These are sampled extrema, not instantaneous peaks or a multi-day soak result. The separate [first 12 GB attempt](./RESULTS-qwen38-flash-next-autoround-seat-20260910T164735Z.md) also passed startup/memory, peaking at 104.006 GiB before its probe expectation failure.

## Gate outcomes

| Gate | Result and scope |
|---|---|
| Preflight/base recovery snapshot | PASS; original catalog/config, units and swap identity preserved |
| Artifact identity | PASS; original ARM64 serving image reused; all 115 model/table files rehashed and control gates rechecked |
| Isolation and startup | PASS; fleet masked, no competing GPU model; native API and SM121 verified |
| Model/caches | PASS; full external FP8 PLE, hybrid/Marlin load, BF16 KV, MTP3/private draft vocabulary; 1600-token attention blocks |
| Protocol | PASS; automatic, required and named tool calls, correct arguments, all continuations, standalone JSON, thinking off |
| Fixed-prefix correctness/cache | PASS at seven lengths through 250,069 actual prompt tokens; correct cold/warm, changed suffix and unrelated prefix |
| Growing tool history | PASS through 250,167 continuation prompt tokens, with older tool-result recall and positive prefix-hit increments at every stage |
| MTP/state | Accepted proposals observed; no Mamba state-copy guard hit, CUDA error or traceback in validation logs |
| Long generation | PASS after captured-response adjudication of a separator false positive; 8192 native completion tokens, 134.97 seconds, 60.78 tok/s approximate decode |
| Memory/no-swap | PASS throughout the observed startup, validation and normal-mode transition |
| Normal endpoint | PASS; same serving image/settings, development APIs disabled; hostname-based tool/JSON calls passed |
| Remote client / gateway | NOT TESTED / N/A; hostname calls originated on the Spark, no gateway changes |
| Recovery/retention | RETAINED; original fleet displaced, swap inactive, guard active; original configuration hash still matches |

### Fixed-prefix measurements

| Actual prompt tokens | Cold first output (s) | Warm first output (s) |
|---:|---:|---:|
| 20,099 | 13.125 | 1.609 |
| 64,173 | 37.767 | 1.324 |
| 94,142 | 56.287 | 2.130 |
| 96,178 | 57.586 | 1.428 |
| 110,143 | 66.602 | 2.185 |
| 120,116 | 72.943 | 1.419 |
| 250,069 | 169.752 | 2.065 |

Each row passed the warm/cold ratio gate and answer checks. Short recall outputs are unsuitable for sustained decode measurements: MTP and SSE batching make their apparent decode rates misleading. These synthetic smokes demonstrate useful caching and basic state correctness, not general long-context reasoning or Factory completion time.

The growing conversation used successive targets of 20K, 64K, 94K, 96K, 110K, 120K and 250K **without resetting between turns**. Observed continuation cache-hit increments were **17,600; 62,400; 91,200; 94,400; 107,200; 118,400; 248,000 tokens** respectively. It recalled prior tool results correctly while changing the expected answer. The final expansion from about 120K to 250K took 90.927 seconds to first tool output; its following recall took 2.129 seconds.

### Sustained generation and limits of the result

The retained diagnostic response used a 75-token code-generation prompt and returned **8192 completion tokens**. First output arrived at **0.199 seconds**; total duration was **134.969 seconds**. Approximate decode rate was **60.778 tok/s**, calculated as `(8192 - 1) / (last_delta - first_delta)`; whole-request rate was **60.695 tok/s**. Finish reason was `length`, with zero reasoning tokens.

The output hit its token cap partway through the requested module. This is a throughput/stream-stability receipt, **not a correctly completed coding task**. It does not establish superiority over Qwen3.6-35B-A3B in AutoBuild. That comparison still needs the [Factory evaluation](./QWEN38-software-factory-evaluation.md).

The validation metrics snapshot, including both long generations and short probes, contained **4519 drafts**, **13,557 proposed tokens** and **12,506 accepted tokens** (about **92.25%** acceptance). Accepted counts by proposal position were **4351 / 4176 / 3979**. It also recorded **3,776,951 prefix-query tokens** and **2,708,800 prefix-hit tokens**. These are aggregate counters for the validation process, not task-level latency attribution; restarting into normal mode reset the process counters.

## Corrections and preserved failures

This was not an uninterrupted run of the original helper. None of these corrections changed model weights, the serving image, KV allocation, context, MTP or memory thresholds:

1. **Named-tool finish reason:** the earlier 12 GB attempt's probe expected `tool_calls` for named requests. The actual pinned vLLM implementation deliberately returns `stop` with a structured named call. Corrected before this run; all tool structure, arguments and continuations remain checked. Full live protocol checks then passed.
2. **Cache-reset route:** the first cache invocation returned 404 before inference. Inspection found the route gated behind `VLLM_SERVER_DEV_MODE`. The engine was restarted with development APIs enabled **on loopback only**, retaining the guard and recovery snapshots. Helpers now check the reset's returned `success` value as well as HTTP status. Original container/startup and failed cache receipts were preserved.
3. **250K prompt sizing:** the old proportional algorithm destructively sliced its source and could not grow it after an undershoot. This failed before inference. Bounded binary search over the original source fixed it; the resumed request measured 250,069 actual tokens. Earlier passing length receipts remained valid.
4. **Long-output heuristic and evidence:** the first long stream was rejected for repeated characters before its content was saved. Raw capture was added before assertions and the one diagnostic generation repeated. Its ten flagged runs were ordinary Python `# ===...` section comments. The detector now permits bounded `=`/`-` comment separators while still rejecting repetitive prose, exclamation loops and oversized separators. The captured response passed the corrected content check and all timing/usage assertions in `decode-adjudicated.json`; the original live `FAIL` receipts remain intact. No third generation was fabricated or claimed.
5. **Normal-mode identity check:** Docker reordered equivalent bind-mount entries. An initial order-sensitive comparison failed; comparing the same entries without list-order significance passed, preserving every source, destination and mount mode.

The image still prints `QSADET active` with `VLLM_QSA_DET_TOPK=0`, because its extension loader tests a nonempty string. Source inspection establishes that `VLLM_QSA_EXACT_TOPK=1` subsequently dispatches to the exact fallback. The environment was unchanged for this controlled trial. The long-context receipts provide actual execution evidence beyond the earlier source-only diagnosis.

After validation, the server restarted into normal mode. Image, mounts and model/serving arguments matched the validation container; only the bind address and development-API environment differed. The normal endpoint passed all protocol checks through `spark-fcf6.local`, and `POST /reset_prefix_cache` returned 404 as required. The long-stream measurement was taken in isolated validation mode; it was not repeated after the normal-mode restart.

## Immutable artifacts and evidence

- Host: `spark-fcf6`, GB10 / ARM64, driver `580.173.02`, Docker `29.2.1`, 121.690 GiB OS-visible RAM.
- Serving image: `sha256:3acf22132d7b912450570e32d9c1696385b731e26f590b0d34c332822ccd245a`; reused without rebuild.
- Saren recipe: `1633d4bc11701c04d7cbd633994421466d1eff1d`; base `vllm/vllm-openai:qwen38-flash-next@sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`; kernel `e0ef69d4f5575dad00d34e05479eaf4c6547bace`.
- Checkpoint: `Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN@19f9710c8f6600a32e15fb98bc77613ee8ec369b`.
- PLE: `Saren/Qwen3.8-Flash-Next-ple-table-fp8@50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14`; full 128 partitions and scale checked.
- Runtime: vLLM `0.1.dev20073+g8e685d198`, torch `2.13.0+cu130`, transformers `5.15.1`, fastsafetensors `0.3.3`.
- Repository HEAD: `fb8395e0b0f020e6dd30de413ce681bf15c988cf`, with uncommitted procedure/helper changes. Initial executed v1.3 runbook hash: `a1770e32957c14f395bfa1ae9685462f31792535ea38ed10392ab6dba6d5a7aa`. Later correction snapshots/hashes are distinct; the final documentation is not represented as an uninterrupted original procedure.

Private run directory: `/home/richardwoollcott/qwen38-autoround-seat-runs/20260910T165917Z`. It contains original and corrected procedure snapshots/hashes; all-file artifact manifest and image identity; every original failed/passed probe receipt; `cache-admin-source.txt`; validation and normal container inspections/logs; `decode-diagnostic/code-decode-raw-1789061515015519695.json` (SHA-256 `c7b48f205f935dc578ddb7d849a4530779ea5d16245beb71bcc1d39da8428f70`); `decode-adjudicated.json`; growing-history receipts; metrics; `memory-at-disposition.jsonl`; and `execution-state.json`. The active `memory.jsonl` continues after the fixed disposition snapshot. See [drift](./DRIFT-qwen38-flash-next-autoround-20260910T165917Z.md).

## Retention and restoration

The endpoint is retained for subsequent use. The normal container does not auto-restart; its dedicated memory guard remains active. Both runtime fleet masks and the temporary swap deactivation remain owned by this run. The original fleet configuration hash is unchanged; gateway configuration and Factory code were not modified.

To end the seat and restore the saved fleet/swap state, use Appendix A of the runbook with this run's original pins and recovery snapshot. The extracted, executed rollback is also retained privately:

```bash
cd /home/richardwoollcott/Projects/appmilla_github/dgx-spark
source /home/richardwoollcott/qwen38-autoround-seat-runs/20260910T165917Z/pins.sh
source "$RUN_DIR/block-8.sh"
```

Then repeat the original embedding, speech and tutor health checks. No cleanup was performed at this final disposition because the Qwen seat is deliberately retained; the preceding 12 GB run already demonstrated fleet/swap restoration.
