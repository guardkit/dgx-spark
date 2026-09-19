# AutoRound KV allocation after the kernel fix — 20260919T090408Z

**Disposition, 2026-09-19 12:40 UTC:** retain **22 GB KV** at `http://spark-fcf6.local:8888/v1`, model `qwen3.8-flash-next-autoround`, under the unchanged 120 decimal GB total-RAM guard. The owner chose this size for the larger pool of cached conversation it gives a local coding-agent harness, accepting a thinner margin. If problems appear, fall back to 19 GB or to an untested 20 or 21 GB (see [Fallback](#fallback)). This is not a multi-day soak result.

## Why the allocation was revisited

On 2026-09-15 the Spark booted into kernel `7.0.0-1019-nvidia`, which turns on Kexec HandOver and reserves about 9.3 GiB at boot. On 2026-09-17 the seat ran out of memory and went into swap, and the owner cut the cache from 19 GB to 14 GB. On 2026-09-19 NVIDIA's `nvidia-spark-grub-kho` 1.0-1 package (`kho=off`) was installed and the Spark rebooted. The kernel's boot log went from `117722720K/133828484K available … 16079992K reserved` to `127473180K/133828484K available … 6329464K reserved`. `MemTotal` was unchanged at 127,598,544 kB. The research note [RESEARCH-local-coding-agent-model-gb10-2026-09-19.md](./RESEARCH-local-coding-agent-model-gb10-2026-09-19.md) has the background.

Guard thresholds were not changed: maximum used **120,000,000,000 bytes = 111.758709 GiB**, minimum available **9.930851 GiB**, swap disabled, no swap-counter increase permitted.

## How this run differed from the 2026-09-10 ladder

- **The production seat was tested in place**, with development APIs off and the normal `0.0.0.0:8888` bind. The factory was idle; the seat was confirmed to have no running or waiting requests before each relaunch.
- **No cache reset was available** (`POST /reset_prefix_cache` returns 404 in normal mode). The repo's probes were run unmodified through wrappers that skip only that call. Every probe ran against a freshly started container that had never been sent its prompts, so each first pass was cold. The cold timings below confirm it.
- **Each size was launched from the live container's own configuration.** `relaunch.py` reads `docker inspect`, keeps the image ID, mounts, the 20 environment settings and every argument, and changes only `--kv-cache-memory-bytes`. Each earlier container was renamed and kept, stopped.
- **Test clients.** The protocol, generation, growing-history and fixed-prefix probes ran from the Dell (`promaxgb10-41b1`) over `spark-fcf6.local:8888`. The two-conversation probes ran on the Spark against `127.0.0.1:8888`, as on 2026-09-10. On 2026-09-10 every client ran on the Spark, so peak totals are not strictly comparable between the two dates.
- **One probe is new:** a copy of the concurrent probe with both prompts sized to 130,000 tokens and different filler seeds (`run-concurrent-130k.py`), to test the factory's conversation size.
- The memory guard ran throughout with the same script (`sha256 535b4795f26f7701…`), command and thresholds as before the reboot.

## Allocation ladder

| KV allocation | Reported cache-token capacity | Sampled peak total RAM | Least available | Outcome |
|---:|---:|---:|---:|---|
| 14 GB | 450,604 (1.72×) | 105.36 GB, idle plus the generation probe only | 23.56 GiB | The setting in use from 2026-09-17; restored unchanged after the reboot as the starting point |
| 19 GB | 612,141 (2.34×) | **113.90 GB** | 15.61 GiB | All core checks passed; kept as the first fallback |
| **22 GB** | **708,497 (2.70×)** | **117.09 GB** | 12.64 GiB | All core checks passed; **retained** |

For reference, two days of factory traffic at 14 GB on the unfixed kernel (2026-09-17 to 2026-09-19, 86,060 guard samples) peaked at 100.67 GiB = 108.09 GB with no swap.

The 22 GB peak left **2.91 GB below the ceiling** and **2.71 GiB above the available-memory floor**. After the tests the idle seat held 116.75 GB: GPU memory rises to a high-water mark as long prompts arrive (90.97 GiB after loading, 94.97 GiB after the 250K tests) and is not handed back.

## Workload evidence

| Check | 19 GB | 22 GB |
|---|---|---|
| Startup / identity | PASS; same image ID and settings; healthy in about 180 s | PASS; healthy in about 150 s |
| Protocol | not run | PASS; automatic, required and named tool calls, arguments, all continuations, standalone JSON, thinking off |
| Fixed-prefix cache, **250,069 prompt tokens** | PASS, including changed-question and unrelated-prefix correctness | PASS, same checks |
| Cold / warm first output at 250K | **159.613 s / 2.141 s**; changed question 2.477 s | **159.615 s / 2.325 s**; changed question **16.115 s** |
| Growing tool history | PASS at 20K, 64K, 94K, 96K, 110K, 120K and 250K, with correct tool call and earlier-result recall at every stage | PASS, same stages |
| Final growing stage | 250,072-token tool turn in 88.02 s; recall on the cached conversation in 2.13 s | 88.74 s; 2.36 s |
| Sustained generation, 8,192 tokens | **54.93 tok/s** over 149.9 s | **38.38 tok/s** first run; see below |
| Memory / swap | PASS; maximum 113.90 GB, unchanged swap counters, no guard stop | PASS; maximum 117.09 GB, unchanged swap counters, no guard stop |
| Runtime log review | No pre-emption, out-of-memory, CUDA error or state-copy guard line | Same |
| Hostname-based checks from another machine | PASS from the Dell | PASS from the Dell |
| Gateway / Factory | NOT TESTED / NOT RUN | NOT TESTED / NOT RUN |

All generation streams ended at their token cap (`finish_reason=length`). These are serving receipts, not coding-task results.

### Generation speed at 22 GB

| Run | Result |
|---|---|
| First 8,192-token run, about three minutes after loading | 38.38 tok/s |
| Repeat straight after the 250K tests | 40.15 tok/s |
| Repeat after that | 59.17 tok/s |
| Three prompts the seat had never been sent, 3,000 tokens each | 56.3, 57.7 and 55.9 tok/s, with 21,373, 15,717 and 21,101 major page faults |

During the two repeats the Spark took 83,090 major page faults and read 0.34 GB from NVMe. At 14 GB the page cache held about 22.5 GiB, almost all of it rows of the 48 GB PLE lookup table; at 22 GB it holds about 11 to 12 GiB. Steady generation speed is unchanged. The cost of the smaller page cache is a slow patch of about 40 tok/s for a few minutes after loading and after a very large prompt displaces the table's rows. The 16.1-second changed-question turn at 22 GB, against 2.5 seconds at 19 GB, is consistent with the same effect. Real factory traffic has not yet been measured at this size; at 14 GB it averaged 44.6 tok/s.

## Two-conversation tests: limitation, improved but not removed

Two independent prompts were submitted together, then repeated together. All answers were correct in every run. The probe requires each warm first output to be at most half its cold time.

| Test | Size | Cold first output | Warm first output | Probe verdict |
|---|---|---:|---:|---|
| Two 250K conversations (250,054 and 250,096 tokens) | 19 GB | 158.18 s / 316.03 s | **149.58 s / 301.23 s** | FAIL; neither reused |
| Two 250K conversations | 22 GB | 165.05 s / 315.05 s | **88.66 s** / 6.61 s | FAIL; one reused, the other about half re-read |
| Two 130K conversations (130,057 and 130,093 tokens) | 19 GB | 161.54 s / 92.37 s | 3.35 s / 3.02 s | PASS |
| Two 130K conversations | 22 GB | 158.59 s / 84.34 s | 3.40 s / 3.35 s | PASS |

Two 250K conversations total about 500K tokens, which is smaller than either pool, so reported capacity still does not guarantee that two full-length conversations stay cached. The cause was not identified. Two conversations at the factory's 131K window size do stay cached at either size.

## Identity, evidence and retained state

- Host: `spark-fcf6`, NVIDIA GB10 / ARM64, kernel `7.0.0-1019-nvidia` with `kho=off`, driver `580.173.02`, Docker `29.6.2` (was `29.2.1` on 2026-09-10).
- Serving image: `sha256:3acf22132d7b912450570e32d9c1696385b731e26f590b0d34c332822ccd245a`, unchanged. vLLM `0.1.dev20073+g8e685d198`, torch `2.13.0+cu130`. No rebuild, download, package upgrade inside the image, or change to model, table, template or serving flags other than the cache size.
- Model mount `…/qwen38-autoround/19f9710c8f6600a32e15fb98bc77613ee8ec369b`, PLE mount `…/qwen38-ple-fp8/50511b0a41aa1d34b8beb7e5d4bb06a0b650dc14`, compiled cache `…/qwen38-autoround-seat-runs/20260910T165917Z/cache`, all unchanged.
- Repository HEAD `db70ff565826ff9fb79d92f8185934027c4c622f` when the probes ran.

Evidence directory on the Spark: `/home/richardwoollcott/api-factory-resume-20260919T090408Z`. It holds `memory.jsonl` (two-second guard samples for the whole session), `observations.jsonl`, `windows-22g.log` (test start and end times), `container-inspect-prereboot.json` and `state-prereboot.txt` (the 14 GB seat's full configuration before the reboot, secrets masked), `relaunch.py` (`sha256 f98248de813dc849…`), `probes/` (the repo probes as run, plus `run-concurrent-noreset.py` and `run-concurrent-130k.py`), `concurrent-19g/`, `concurrent-19g-130k/`, `concurrent-22g/`, `concurrent-22g-130k/`, and `dell-run-probes/` (the receipts from the probes run on the Dell, with the wrapper and chain scripts). See [drift](./DRIFT-qwen38-flash-next-kv-ceiling-20260919T090408Z.md).

The retained normal container is `qwen38-autoround-seat`, restart policy `no`, bind `0.0.0.0:8888`, development APIs disabled, started 2026-09-19T10:55:56Z. The memory guard is active as the transient user unit `qwen38-autoround-memory-guard`. `llama-swap.service` and `litellm.service` on the Spark are masked through `$XDG_RUNTIME_DIR/systemd/user.control/` and inactive, and swap is off. The Dell's gateway routes `flash-next` and `flash-next-t06` were not changed.

A reboot of the Spark undoes the masks, the guard and the swap setting, and the seat does not restart by itself. Put the masks, swap-off and guard back first, as the runbook describes, and then `docker start qwen38-autoround-seat`.

## Fallback

Two stopped containers are kept on the Spark: `qwen38-autoround-seat-19g` (tested today) and `qwen38-autoround-seat-14g` (the 2026-09-17 configuration). To fall back to one of them, with the guard left running:

```bash
docker stop -t 90 qwen38-autoround-seat
docker rename qwen38-autoround-seat qwen38-autoround-seat-22g
docker rename qwen38-autoround-seat-19g qwen38-autoround-seat
docker start qwen38-autoround-seat
```

For an in-between size, generate the launch from the 22 GB container instead of the last two lines:

```bash
python3 ~/api-factory-resume-20260919T090408Z/relaunch.py qwen38-autoround-seat-22g qwen38-autoround-seat 21g --go
```

Neither 20 GB nor 21 GB was tested in this run. Each gigabyte of cache added about 32,100 tokens to the pool and about 1.06 GB to the peak between 19 and 22 GB, so 20 GB should give about 644,000 tokens and peak near 115.0 GB, and 21 GB about 676,000 tokens and near 116.0 GB. The 2026-09-10 run did test 20 GB, and the guard stopped it at 120.026 GB; that run's totals ran about 4.6 GB higher than today's at the same 19 GB setting. Run the probes again at whichever size is chosen and record it here.

Signs that a fallback is needed: the guard stops the seat (`memory.failed` appears in the evidence directory and the container exits), swap counters move, or generation on real traffic stays well under the 44.6 tok/s measured at 14 GB rather than dipping briefly.

Not done in this run: a soak under factory traffic, a keyed request through the Dell's gateway with a spend record, any Factory task, and a recon of upstream changes.
