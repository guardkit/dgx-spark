# Drift report — AutoRound seat, 20260910T162007Z

## Pin checks

- **OK:** recipe HEAD `1633d4bc11701c04d7cbd633994421466d1eff1d`, checkpoint `19f9710c8f6600a32e15fb98bc77613ee8ec369b` and PLE `50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14` matched the pins in the saved recon responses.
- **OK:** digest-pinned ARM64 base and all 115 model/table repository files verified again.
- **INFO:** rebuilding the same sources yielded a different image ID. That receipt is preserved; the server explicitly reused the first attempt's image ID. No serving image was promoted.
- **INFO:** blazux `bd60fcb1b492ca920f74df7462f05da7b6d98f73` and Tony `6ad1c8f15cbab1ababd2048e8e5f94094dbfc4a0` were unchanged from the first attempt's recon.

## Source scan and local findings

- **FLAG, existing:** [vLLM #54173](https://github.com/vllm-project/vllm/issues/54173) remained open, last updated September 9. Startup failed before any prefix-cache workload; this run cannot clear that issue.
- **FLAG, existing:** the [long-prefill custom kernel report](https://github.com/jschmied/qwen38-flash-next-gb10/commit/7fede41fc726) remains the reason for selecting exact top-k. The local failure was the RAM guard, before a context test.
- **INFO:** the fixed NVIDIA comparison thread and Arena URL were read and retained in the private recon receipts. No source or model pin changed.
- **FLAG, local:** the actual image's deterministic-kernel loader treats the string `"0"` as enabled and prints `QSADET active`. Its subsequent exact-top-k dispatch still takes precedence with `EXACT_TOPK=1`. Omit the disabled DET environment variable in a future launcher revision; the log line is not evidence that the custom kernel handled selection.
- **FAIL, local gate:** swap deactivation eliminated swap I/O, but startup with explicit `20g` KV exceeded both RAM thresholds. Fleet and swap restoration passed.

**Verdict:** software/model pins unchanged; the selected serving allocation failed the local memory gate. A smaller explicit KV pool is proposed in the [execution results](./RESULTS-qwen38-flash-next-autoround-seat-20260910T162007Z.md), with no third trial performed. Recon responses and the exact executed procedure remain in `/home/richardwoollcott/qwen38-autoround-seat-runs/20260910T162007Z`.
