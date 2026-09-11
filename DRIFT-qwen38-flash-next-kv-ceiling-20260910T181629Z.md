# Drift report — AutoRound KV ceiling trial, 20260910T181629Z

- **AUTHORIZED policy change:** total effective RAM ceiling raised to 120 decimal GB, with both guard thresholds derived consistently. No hidden 12 GiB available-memory floor remains.
- **OK artifact reuse:** same live baseline image, model/table mounts, source/checkpoint revisions and compiled cache. No build, download, dependency upgrade or new all-file hash pass; retained identity evidence comes from the validated baseline.
- **RECON:** no new upstream scan during this local allocation experiment; same-day pinned-source evidence remains in earlier drift reports. No software/model promotion.
- **PASS 18 GB screening:** startup, tools/JSON and 96K cache correctness/reuse; sampled peak 117.043 GB.
- **FAIL 20 GB memory:** 120.026 GB during growing history; guard stopped the model. No observed CUDA OOM, and no threshold relaxation after the failure.
- **FLAG 20 GB capacity characterization:** two independent 250K contexts returned correct answers but one warm repeat took 136.489 seconds, failing the reuse target. Reported cache capacity is not evidence of fast retention of both contexts. This was not rerun at 19 GB.
- **PASS 19 GB core workloads:** startup/protocol, 250K fixed-prefix, growing 20K/96K/250K, sustained generation at 58.79 tok/s over 139.58 seconds, and normal endpoint transition. Peak 118.534 GB.

**Verdict:** retain 19 GB KV under the user-selected 120 GB guard, with the two-context limitation documented. Factory task quality and multi-day stability were not evaluated. See [results and restoration instructions](./RESULTS-qwen38-flash-next-kv-ceiling-20260910T181629Z.md).
