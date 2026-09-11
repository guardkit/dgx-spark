# Drift report — AutoRound 12 GB trial, 20260910T164735Z

- **OK, artifact identity:** same serving image, recipe/checkpoint/PLE revisions and all 115 file hashes verified. No build or model promotion.
- **INFO, recon reuse:** same-day fixed-source recon from the preceding attempt was retained, not fetched again. See [prior drift](./DRIFT-qwen38-flash-next-autoround-20260910T162007Z.md).
- **AUTHORIZED configuration change:** explicit KV reduced from 20 to 12 decimal GB; all other serving settings and guard cutoffs retained.
- **CORRECTION, interpretation:** 109 GiB used / 12 GiB available are trial cutoffs, not demonstrated hardware limits. The operator reports stable multi-day use at 120 GB; the earlier RAM guard cutoff did not establish instability or an OOM.
- **FLAG, local probe:** named-tool `finish_reason=stop` is deliberate in the actual pinned vLLM serving code. The helper's universal `tool_calls` assertion was too strict. Correction and replay checks recorded for the next execution; original failed receipt preserved.

**Verdict:** the smaller KV pool passed startup and observed memory gates. Protocol validation halted on a helper error, now diagnosed; no long-context or sustained-generation claim follows. See [results](./RESULTS-qwen38-flash-next-autoround-seat-20260910T164735Z.md).
