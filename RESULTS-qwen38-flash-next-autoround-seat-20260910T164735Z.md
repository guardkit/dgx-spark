# AutoRound 12 GB KV trial — 20260910T164735Z

**Disposition:** startup and observed memory gates passed. The original protocol probe halted on a named-tool finish-reason expectation; fleet and swap were restored. Subsequent inspection identified an incorrect probe expectation, and a separate corrected-probe rerun follows. This receipt preserves the original outcome; it is not a completed serving validation.

## Configuration and memory accounting

The user authorized reducing explicit KV allocation from `20g` to **`12g`**, and reported sustaining 120 GB RAM usage for days. The runbook's guard actually measures `MemTotal - MemAvailable` in **GiB**, stopping above **109 GiB (117.038 GB)** used or below **12 GiB (12.885 GB)** available. These are conservative test cutoffs, not an established hardware stability ceiling. The preceding `20g` run stopped at **118.959 decimal GB**, without an observed OOM. Its guard result does not contradict the operator's 120 GB observation; monitoring units and cache accounting must be matched for a direct comparison.

This trial kept the original guard thresholds to isolate the cache-size change. `12g` resolves to **12,000,000,000 bytes / 11.18 GiB**, a 7.451 GiB reduction from `20g`. Native context, eight sequences, MTP3, private 65,536-token draft vocabulary, exact top-k, full ten routed experts, BF16 KV, prefix caching, local-NVMe FP8 PLE and swap preparation were unchanged.

- Serving image: `sha256:3acf22132d7b912450570e32d9c1696385b731e26f590b0d34c332822ccd245a`, reused without rebuilding.
- Recipe `1633d4bc11701c04d7cbd633994421466d1eff1d`; base digest `sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`; kernel `e0ef69d4f5575dad00d34e05479eaf4c6547bace`.
- Checkpoint `Saren/Qwen3.8-Flash-Next-W4A16-AutoRound-hybrid-MTP_int4RTN@19f9710c8f6600a32e15fb98bc77613ee8ec369b`; PLE `Saren/Qwen3.8-Flash-Next-ple-table-fp8@50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14`. All 115 files rehashed and control-file gates passed.
- Host `spark-fcf6`, GB10 / ARM64, 121.690 GiB OS-visible memory, driver `580.173.02`; vLLM `0.1.dev20073+g8e685d198`, torch `2.13.0+cu130`, CUDA 13.0.
- Repository HEAD `fb8395e0b0f020e6dd30de413ce681bf15c988cf`, uncommitted procedure files. Executed v1.2 runbook SHA-256 `134497dfcbce062a09edf478f319fc897a4316e92475333d5ddb04c665640ba7`. Original probe SHA-256 `25ae9eb754243cfabb5849fad4a206bf4785b1cd409e218d93ee00181cdab4ba`.

## Gate results

| Gate | Result |
|---|---|
| Preflight, base snapshot, artifact identity | PASS |
| Fleet isolation, headroom and temporary swap deactivation | PASS; drained available RAM 110.990 GiB |
| Startup and GPU identity | PASS; API ready at 16:56:23 UTC; SM121 confirmed |
| Native context admission | PASS; API advertises 262144; KV capacity 386,839 tokens / 1.48 full-context requests |
| Memory during startup and five short requests | PASS; sampled maximum used 104.006 GiB / minimum available 17.683 GiB |
| Swap during observed interval | PASS; zero occupancy, counters unchanged at pswpin 2537511 / pswpout 6381338 |
| Automatic and required tool calls + continuations | PASS; correct structured calls, arguments and `cobalt-731` continuation |
| Named tool | Original probe FAIL on `finish_reason=stop`; captured call itself has correct name, ID and JSON arguments |
| Named continuation, standalone JSON, context/cache, growing history, sustained decode | NOT RUN after probe failure |
| MTP activity | Observed 25 drafts, 75 proposed tokens, 75 accepted tokens; 25 accepted at each of three positions |
| Gateway / Factory | N/A / NOT RUN |
| Recovery | PASS; fleet configuration/catalog, embedding, speech and tutor checks passed; swap restored |

Memory extrema come from 177 samples at two-second intervals, not an instantaneous peak measurement. The loader reported 67.92 GiB and 103.894 seconds. No Mamba guard hit or fatal CUDA error was observed in this short interval; long-context correctness remains untested. Prefix metrics showed 1610 queried tokens and zero hits; these 300–355-token prompts are below the reported 1600-token attention block size and do not validate useful caching. Short, highly speculative responses are **not a sustained throughput benchmark**.

## Probe diagnosis

The named request produced an empty text response plus one structured `lookup_test_key` call, with `{"key":"gate-alpha"}` and a nonempty call ID. The only failing assertion was its final reason: `stop` rather than `tool_calls`.

Read-only inspection of the actual image's vLLM chat-serving implementation found explicit logic selecting `tool_calls` for automatic/required calls and leaving `stop` for named calls. The original helper incorrectly required `tool_calls` for all three modes. The corrected helper permits either `stop` or `tool_calls` only for named requests; all name, ID, argument, continuation and other assertions remain. A replay test accepted the captured named response and rejected automatic `stop`, wrong named arguments and missing named calls. Synthetic fixtures supplied the two not-yet-generated responses for that helper test; they are not model validation receipts. No serving software or model pin was changed to address this probe error.

## Evidence and final state

Private evidence: `/home/richardwoollcott/qwen38-autoround-seat-runs/20260910T164735Z`. Includes immutable `runbook-executed.md`, `procedure.sha256`, artifact manifest/image identity, startup and gate logs, original `direct/protocols-1789059417728615048.json`, memory samples, before/after metrics, `serving-source-excerpts.txt`, `probe-correction-test.txt`, rollback and restoration checks.

Container removed, guard stopped, both runtime masks removed, original swap file/priority restored. Embedding inference returned 1024 finite values; both speech and tutor health checks passed. No gateway route or Factory change. The original failed receipt is retained; see [drift](./DRIFT-qwen38-flash-next-autoround-20260910T164735Z.md).
