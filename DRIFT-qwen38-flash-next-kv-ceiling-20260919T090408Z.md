# Drift report — AutoRound KV allocation after the kernel fix, 20260919T090408Z

- **AUTHORIZED allocation change:** the owner asked for 22 GB KV to be tried and then pinned, with 19 GB or an in-between 20 to 21 GB as the fallback. The 120 decimal GB ceiling and both guard thresholds are unchanged.
- **HOST change, outside the runbook:** NVIDIA's `nvidia-spark-grub-kho` 1.0-1 (`kho=off`) installed and the Spark rebooted. Boot-time available memory rose from 117,722,720K to 127,473,180K; `MemTotal` unchanged. Docker is now `29.6.2` (was `29.2.1`). Kernel `7.0.0-1019-nvidia`, driver `580.173.02`.
- **OK artifact reuse:** same image ID, model and PLE mounts, compiled cache, template and serving flags. Only `--kv-cache-memory-bytes` changed. Launches were generated from the live container's `docker inspect`, not from the runbook's PINS block.
- **DEVIATION, validation mode:** the runbook validates on a loopback seat with development APIs on and resets the prefix cache between checks. This run tested the normal-mode production seat with those APIs off, skipping only the reset call. Each probe ran against a freshly started container that had never been sent its prompts; cold timings confirm cold starts. The factory was idle and the seat had no requests in flight at each relaunch.
- **DEVIATION, client location:** four probes ran from the Dell; the two-conversation probes ran on the Spark. On 2026-09-10 all ran on the Spark, so peak totals are not strictly comparable across the two dates.
- **RECON:** no upstream scan. No software or model promotion.
- **PASS 19 GB:** fixed-prefix 250K, growing history to 250K, sustained generation 54.93 tok/s. Peak 113.90 GB. Protocol gate not run at this size.
- **PASS 22 GB core workloads:** protocol, fixed-prefix 250K, growing history to 250K, sustained generation. Peak 117.09 GB, least available 12.64 GiB, no swap, no guard stop.
- **FLAG 22 GB generation speed:** 38.38 and 40.15 tok/s on the runs that followed loading and the 250K tests, then 59.17 tok/s, and 55.9 to 57.7 tok/s on three unseen prompts. Consistent with the PLE table's page cache, now about 11 to 12 GiB, being displaced and refilled. Not yet measured on factory traffic.
- **FLAG two-conversation reuse:** two 250K conversations failed the reuse target at 19 GB (neither reused) and at 22 GB (one reused, one about half re-read). Two 130K conversations passed at both sizes. Reported cache capacity is still not evidence that two full-length conversations stay cached.
- **NOT RUN:** soak under factory traffic, keyed gateway request with spend record, Factory task, 20 GB and 21 GB.

**Verdict:** retain 22 GB KV under the unchanged 120 GB guard, with 2.91 GB of margin at the sampled peak. Fall back to 19 GB, or to a newly tested 20 or 21 GB, if the guard stops the seat, swap counters move, or generation on real traffic stays low. See [results and fallback instructions](./RESULTS-qwen38-flash-next-kv-ceiling-20260919T090408Z.md).
