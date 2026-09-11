# Drift report — AutoRound serving validation, 20260910T165917Z

- **OK, artifact identity:** original serving image reused; recipe, model and PLE revisions unchanged; all 115 files rehashed and control gates passed. No floating model, image or kernel promotion.
- **INFO, recon reuse:** retained the same-day fixed-source recon from the earlier attempts; did not refetch upstream heads during this validation. Earlier cache/kernel issues remain research context, not universally resolved by local smoke tests.
- **AUTHORIZED allocation:** user-approved `12g` KV; original 109 GiB used / 12 GiB available guard cutoffs retained. These are trial cutoffs, not a proven host stability ceiling.
- **CORRECTED local helpers/setup:** named-tool finish reason; cache-reset route enablement on loopback and reset-success check; recoverable prompt sizing at 250K; raw response retention and bounded code-separator handling. Every original failure and correction receipt remains recorded.
- **PASS local measurements:** startup/memory; structured tools/JSON; fixed-prefix correctness and cache speedup through 250,069 tokens; growing tool-history recall/cache hits through 250,167 continuation tokens; sustained generation adjudicated from captured output at 60.78 tok/s over 134.97 seconds.
- **INFO normal-mode transition:** development APIs disabled before binding normal network access. Same image/model configuration verified; equivalent mount entries initially differed only in Docker's list ordering. Hostname-based protocol checks passed on the Spark; remote-client and gateway paths remain untested.

**Verdict:** retain the user-approved 12 GB configuration as serving-ready with the documented validation corrections. This is not a Factory quality or time-to-correct-task result, nor a multi-day stability receipt. See [final results and retained state](./RESULTS-qwen38-flash-next-autoround-seat-20260910T165917Z.md).
