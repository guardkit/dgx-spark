# RESULTS: The adapter host goes behind the model switchboard — GB10, 2026-09-03

**Previous runs:** [`RESULTS-vllm-multi-adapter-slots-2026-09-02.md`](./RESULTS-vllm-multi-adapter-slots-2026-09-02.md)
(one process, four adapters, parallel slots proven; exams not) ·
[`RESULTS-vllm-adapter-followup-2026-09-02.md`](./RESULTS-vllm-adapter-followup-2026-09-02.md)
(the corrected exports served together).
**Box:** promaxgb10-41b1 (Dell Pro Max, GB10, aarch64, 121 GB of memory shared between the graphics
processor and the main processor; `MemTotal` 127,535,220 kB, `s11-dial.json`).
**Receipts folder:** `~/fine-tuning/output/vllm-switchboard-2026-09-03/` (stage S11) and
`~/fine-tuning/output/vllm-switchboard2-2026-09-03/` (stages S12 and S12b).

Every number below names the file it was read from. Nothing here is quoted from a terminal without
its receipt. No model was called and no live service was changed to write this document.

Three words used throughout, in plain English:

- **The switchboard** is `llama-swap` on port 9000. It holds a list of model entries, starts the
  right process when a name is asked for, and stops it when it goes idle.
- **The adapter host** is one vLLM process that holds the Gemma 4 26B base model once, at 16-bit
  precision, and serves our four fine-tuned adapters (small trained add-ons) from named slots on
  top of it. Its switchboard entry is called `gemma4-adapters`.
- **The cache** (vLLM's logs call it the KV cache) is the working memory a served model needs for
  each request in flight. Its size is quoted in tokens: 131,072 tokens is four requests at the
  32,768-token context we serve, which is what the eight-sentence campaign needs.

---

## Verdict

**The adapter host is now a member of the switchboard under the names the factory already sends,
and the coding model runs beside it — but only because the cache stopped being sized by a
percentage dial and started being a fixed number of bytes.** With the dial alone, vLLM measures how
much memory is free at the moment it starts and takes a share of that, so on a clean box it claimed
531,460 tokens of cache (`s12-switchboard.json`) and left the 26 GB coding model nowhere to go; the
Linux kernel's out-of-memory killer then killed the LiteLLM proxy twice (`s12-switchboard.json`,
12:10:48Z and 12:12:46Z). Pinning the cache to exactly 8 GiB with `--kv-cache-memory-bytes` gave
201,733 tokens — comfortably over the 131,072 the eight-sentence campaign needs — the coding model
loaded beside it in about 31 seconds, nothing was killed, and all three factory names plus the
coding model answered through LiteLLM with both resident (`s12b-kvcap.json`).

---

## What was run

### S11 — two memory dials, with the coding model resident

Source: `~/fine-tuning/output/vllm-switchboard-2026-09-03/s11-dial.json`.

The question S11 asked was whether the adapter host and the `qwen36-workhorse` coding seat can both
be resident, and in which order they must start. Both tests below started the adapter host first,
with the switchboard's large seats unloaded, and then loaded the coding model beside it.

| | Dial 0.55 (test T1) | Dial 0.60 (test T2) |
|---|---|---|
| Weights loaded | 51.04 GiB | 51.04 GiB |
| Cache claimed | 5.08 GiB — 128,193 tokens | 10.69 GiB — 269,516 tokens |
| Free memory, adapter host alone | 32.1 GiB | 26.1 GiB |
| Coding model loaded beside it | yes, HTTP 200 in 39.0 s | yes, HTTP 200 in 34.5 s |
| Free memory, both resident | 9.7 GiB | 4.2 GiB |
| Swap left, both resident | 82 MB of 16,383 MB | 203 MB of 16,383 MB |
| All four seats answered | yes | yes |

Two failures in the same stage set the start-order rule. At dial 0.50 vLLM could not start at all —
its own line reads `Available KV cache memory: -2.35 GiB`, a negative budget. And started in the
reverse order, beside a resident coding model, it failed in two different ways on the same day: once
loudly (`torch.AcceleratorError: CUDA error: out of memory`, 09:32:59) and once silently and worse —
the kernel killed the coding model's `llama-server` process (pid 2341714) four minutes into the
adapter host's weight load, at 10:20:19Z, and the adapter host then profiled against the memory it
had just been handed and took 39.3 GiB of cache.

S11's own recommendation was that S12 **must not proceed as briefed**: the rule for the stage was
15 GB of free memory left with both resident, and neither dial reached it. It named the reason
plainly, and this is the finding the rest of the day turns on:

> "vLLM sizes its cache from the memory that is FREE when it profiles, not from a fixed share of the
> box." (`s11-dial.json`, cross-cutting finding)

### S12 — the switchboard entry, and the two proxy kills

Sources: `s12-switchboard.json`, `config.diff`, `litellm-check.json`.

**The member.** A new script `/opt/llama-swap/scripts/gemma4-adapters.sh` (mode 755, modelled on the
existing `audio-parakeet.sh`) starts image `vllm/vllm-openai:v0.25.0-aarch64-cu129` on the
`unsloth/gemma-4-26b-a4b-it` snapshot `60941ad6341d0b7af91277ff25c4175f08b56819`, served as
`gemma4-base`, with four adapters from `vllm-exports-v3`: `product-owner-agent` (po-gemma4-v6),
`architect-agent` (architect-plan-v2), `coach-ft-v4` (coach-gemma4-26b-moe-v4) and `po-v5-adapter`
(po-gemma4-v5). Serve flags: `--enable-lora --max-lora-rank 16 --max-loras 2 --max-cpu-loras 4
--gpu-memory-utilization 0.60 --reasoning-parser gemma4 --max-model-len 32768 --max-num-seqs 4
--no-enable-prefix-caching --limit-mm-per-prompt '{"image":0}'`. The start line uses
`docker rm -f` rather than `--rm`, so a stopped container's log survives until the next start — the
campaign needs it as proof of which adapter answered. `VLLM_BATCH_INVARIANT` is deliberately **not**
set (deterministic kernels made the product-owner seat run away on 2026-09-03 morning).

**The names moved.** From `config.diff`: a new entry `gemma4-adapters` (`checkEndpoint /v1/models`,
`ttl: 0`, `concurrencyLimit: 4`) took ten aliases — `product-owner-agent`, `product-owner-v6`,
`po-v6`, `po-ft-v6`, `architect-agent`, `software-architect`, `ddd-architect`, `architect-plan-v2`,
`coach-ft-v4`, `po-v5-adapter`. The three seats that used to own those names — each with
its own merged copy of the model, in the file format llama.cpp uses — were
renamed `po-ft-v6-llamacpp`, `architect-plan-v2-llamacpp` and `coach-ft-v4-llamacpp` and their alias
lists removed, with dated comments; their commands and time-to-live are untouched, so they are one
file-copy away from service.

**The matrix sets.** A new variable `gv4: gemma4-adapters`; `all`, `po` and `shadow` now name it;
`all_llamacpp` and `po_llamacpp` were added carrying the previous membership for rollback. The
edited file was parsed with `yaml.safe_load` before it was moved into place, and checked for alias
collisions: 30 entries, zero collisions.

**Preload.** `hooks.on_startup.preload` became `[embed, gemma4-adapters]`, with a dated comment that
order matters on this box.

**Time to ready.** The config landed in one move at 12:00:28Z and the new names were visible on
`:9000/v1/models` five seconds later. The starting request (32-token prompt to
`product-owner-agent`) was fired at 12:00:41Z; the container came up at 12:00:32Z and the member was
ready at 12:09:13Z — **8 minutes 32 seconds**, and the request itself returned HTTP 200 after
511.8 s having waited for the load. The switchboard's patience setting (`healthCheckTimeout`) was
600 s at the time, so this left 88 seconds of margin.

**The three checks through LiteLLM** (`litellm-check.json`), each made from inside a container that
already held the key, so no key touched a shell:

| Name asked | Called from | Result | Tokens |
|---|---|---|---|
| `coach` | forge-prod, `http://localhost:4000` | 200 in 2.9 s | 24 prompt / 22 completion |
| `product-owner-agent` | the product-owner specialist container | 200 in 1.2 s | 24 / 21 |
| `architect-agent` | the architect specialist container | 200 in 1.2 s | 24 / 22 |

All three are in LiteLLM's own spend log at 12:14:04.848, 12:14:12.676 and 12:14:13.926, and each
is matched in the vLLM log by a batch of 30 `Successfully loaded LoRA weights for module …
moe.experts` lines — one per layer — showing that adapter being pulled into a graphics slot.

**And then the coding model was asked for, and the proxy died twice.** One small completion for
model `workhorse` was sent at 12:10:10Z from inside the product-owner specialist container. The
switchboard began loading `qwen36-workhorse` beside the resident adapter host. Between 12:10:23Z and
12:10:43Z the NVIDIA driver logged repeated `Out of memory [NV_ERR_NO_MEMORY]`. At 12:10:48Z the
kernel killed the LiteLLM proxy (pid 935633); its systemd user unit restarted it; at 12:12:46Z the
kernel killed the replacement (pid 2642376) with free memory at zero and swap exhausted, the coding
model still in state `starting`. At 12:12:47Z the builder unloaded the coding model
(`POST :9000/api/models/unload/qwen36-workhorse` → HTTP 200 `OK`) and about 21 GB came back within
five seconds. The proxy was answering again on its own at 12:13:33Z; nobody restarted it. The
adapter host itself survived both kills untouched (`OOMKilled=false`).

**The root cause, stated once.** vLLM sizes its cache from whatever memory is free at the moment it
profiles. The switchboard preloads the member first, from a clean box — exactly the condition that
maximises the claim — so the same 0.60 dial that gave 269,516 tokens in S11 gave **531,460 tokens**
here, which at the measured 42.6 KB per token is **21.08 GiB** of cache. Added to 51.04 GiB of
weights that is the **72.98 GiB** member recorded in the script's own comment block
(`s12b-kvcap.json`, step 1); measured on the box's free-memory figure the member cost about **82
GiB** (102 GiB before it started, 20–21 GiB settled). Either way there was nothing left for a 26 GB
seat, and the kernel picked the proxy.

### S12b — a fixed cache budget, and both processes resident

Source: `s12b-kvcap.json`.

**The flag exists in this build.** `vllm serve --help=all` in the running image documents
`--kv-cache-memory-bytes` as "Size of KV Cache per GPU in bytes … Note that kv_cache_memory_bytes
(when not-None) ignores gpu_memory_utilization", confirmed against `vllm/config/cache.py` in the
image.

**Two edits, both backed up first (`cmp` confirmed identical before either was touched).** The
member script gained `--kv-cache-memory-bytes 8589934592` (8 GiB) immediately above the dial, plus a
15-line dated comment explaining why — the flag now sits on **line 72 of
`/opt/llama-swap/scripts/gemma4-adapters.sh`**, read directly for this document. The dial
`--gpu-memory-utilization 0.60` was deliberately left in place as a record of the old ceiling.
The switchboard config's `healthCheckTimeout` went from **600 to 900 seconds**, because S12's cold
start used 512 of the 600 allowed. `config.diff` against `config.yaml.bak-20260903-pre-s12b` is
exactly those four lines plus dated comments, and the edited file was parsed with `yaml.safe_load`
(30 entries, `gemma4-adapters` present) before it moved into place at 12:23:02Z.

**Restart through the switchboard.** Unload at 12:23:46Z (HTTP 200, `OK`), confirmed gone by
12:23:59Z, with 102.99 GiB free. Starting request fired 12:24:08Z; ready 12:32:37Z — **509 seconds**,
against the 900 now allowed, so 391 seconds of margin instead of 88.

**What the log says now.** The server's own arguments line at 12:24:17 carries
`'kv_cache_memory_bytes': 8589934592`. Weights: 51.04 GiB in 326.5 s (`gpu_model_runner.py:5306`),
identical to every previous run. And in place of the usual profiling lines,
`gpu_worker.py:459` at 12:30:56:

> "Initial free memory 99.75 GiB, reserved 8.0 GiB memory for KV Cache as specified by
> kv_cache_memory_bytes config and skipped memory profiling. This does not respect the
> gpu_memory_utilization config."

Cache: **201,733 tokens** (`kv_cache_utils.py:2146`) against the campaign's bar of 131,072 — a
margin of 70,661 tokens, and 6.16 full-length requests' worth at the 32,768-token context we serve.
8 GiB over 201,733 tokens is 42.6 KB per token, against a prediction of about 43 KB.

**The coding model beside it.** Fired at 12:39:28Z, HTTP 200 in 28.0 s, and the five-second memory
trace shows the whole event: 29.04 GiB free at 12:39:25Z, 23.80 at 12:39:30Z, a trough of 7.95 at
12:39:35Z, 6.35 at 12:39:56Z, and **ready at 12:40:01Z with 5.88 GiB free** — about **31 seconds**
from absent to ready. The lowest sample was 5.88 GiB. Nothing was killed:
`journalctl -k --since 13:13:00 | grep -c 'Killed process'` returned **0**, the container reports
`OOMKilled=false, Running=true, RestartCount=0`, and the LiteLLM proxy is still process 2643145 —
the same one it was before the stage.

**The three names again, plus the coding model, with both resident:**

| Name asked | Called from | Result | Tokens |
|---|---|---|---|
| `product-owner-agent` | product-owner specialist container | 200 in 4.5 s | 23 / 49 |
| `architect-agent` | architect specialist container | 200 in 2.9 s | 28 / 59 |
| `coach` | forge-prod | 200 in 2.8 s | 26 / 54 |
| `workhorse` | product-owner specialist container | 200 in 3.4 s | 25 / 164 — asked 17 plus 25, answered 42 |

All four are in LiteLLM's spend log (12:39:28.97, 12:41:52.862, 12:42:01.438, 12:42:14.303), and the
vLLM log shows the adapter swaps: the product owner was already in a slot from the starting request
(which is why it needed no reload), the architect was pulled in at 12:42:01 and the coach at
12:42:14, displacing one of the others — correct behaviour with only two graphics slots
(`--max-loras 2`). `po-v5-adapter` was never activated, because it was never called.

**Driven again independently.** An independent coach re-drove every check rather than reading them:
all three factory names plus the coding model answered through the proxy again at 12:48:11–12:48:27Z
(product-owner-agent 200 in 1.6 s, 23/31 tokens; architect-agent 200 in 1.7 s, 23/35; coach 200 in
1.3 s from forge-prod, 26/25; workhorse 200 in 3.2 s, 25/164), each in the spend log, each with its
adapter's 30 expert-load lines in the container log.

---

## Memory, with both resident

- **The member costs 73.9 GiB** of the box's available-memory figure — 102.99 GiB before it started,
  29.05 GiB with it settled (`s12b-kvcap.json`). The prediction going in was about 60 GiB (51 GiB of
  weights plus 8 GiB of cache); the extra roughly 15 GiB is the graphics context, activation
  buffers, the 10 GB shared-memory segment the container holds, and four processor-side copies of
  the adapters from `--max-cpu-loras 4`. **Anyone planning from this should use 74, not 60.**
- **The box settles at about 5.4 GiB available with 3 GB of swap free** (5.90 GiB at 12:41:26Z,
  5.38 GiB at 12:43:53Z, `s12b-kvcap.json`; the coach recorded `MemAvailable` 5,468,280 kB). For
  comparison, S11's two successful runs settled at 9.7 GiB and 4.2 GiB and both had swap completely
  exhausted; this one sits between them and still has swap left.
- **At the time of writing** (this document, 2026-09-03 afternoon, read directly) the switchboard's
  `/running` lists `embed`, `gemma4-adapters` and `qwen36-workhorse` all `ready`, LiteLLM is still
  process 2643145, and `MemAvailable` reads 4,415,640 kB — about 4.2 GiB, lower than the coach's
  5.4 GiB an hour earlier. The band is real and it is narrow.
- **The early-warning sign.** One NVIDIA driver line exists after the S12 cascade:
  `NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned
  from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359`, at 13:39:30 local = 12:39:30Z — the exact
  second the coding model began loading, at the bottom of the trough. Nothing was killed and nothing
  failed. It is reported because it is the same driver signature that preceded the S12 cascade, and
  because it is the honest sign that this box is being asked for very nearly everything it has.

**There is no room for a third large thing.** The start order still matters and has not changed: the
adapter host must be resident before the coding model loads.

---

## What this does and does not license

**A seat has moved.** This is the plain fact and it should not be buried. Since 12:00:28Z today,
`product-owner-agent`, `architect-agent` and `coach-ft-v4` — the names the factory's own containers
send — resolve to `gemma4-adapters`, the shared vLLM process, and no longer to the three separate
merged model files that served them before (`config.diff`). Every factory call to the spec writer,
the plan writer or the build checker now goes to an adapter slot. That is a live change to how the
factory's seats are served, made for the campaign, and it is reversible in one file copy.

**Also true, and each one matters:**

- **Time-to-live is 0 for the campaign.** The member never idles out, because its cold start is
  about 8.5 minutes and the factory does not wait that long. **Revert it to `ttl: 1800` after the
  campaign** — the dated comment in the config says so too.
- **The planner is ungraded.** No exam runner exists for the plan seat's output. The 2026-09-02
  follow-up recorded that the planner adapter loads whole and changes the base's answer, but nothing
  scores whether the answer is right. Any claim about plan quality on this path has to come from the
  campaign's own plan-checker scores, not from a prior exam.
- **Repeated runs are not byte-identical.** Deterministic mode (`VLLM_BATCH_INVARIANT`) is off by
  design, because with it on the product-owner adapter ran away on long generation (2026-09-03
  morning). So the same sentence sent twice will not produce identical text. This was never true on
  the llama.cpp path either.
- **The keepalive will not revive the member.** `/usr/local/bin/llama-swap-keepalive.sh` was not
  changed (`s12-switchboard.json`). A switchboard restart will preload `gemma4-adapters`, but if the
  member ever stops on its own, nothing brings it back automatically — someone has to send a request
  to one of its names and wait about 8.5 minutes.

**What this does not license:** it is not a decision that any seat stays on this path. It is not a
quality result — no exam was run in these three stages; every measurement here is about memory,
readiness and routing. It does not license loading anything else large on this box while both are
resident. And it does not license running the campaign unattended: the pre-flight and abort rules
are in the run card (`ai-transition/docs/bakeoff-arm-V-adapters-run-card-2026-09-03.md`).

---

## Rollback

Both stages left verified backups (`cmp` confirmed each identical to the original before any edit).

**Undo S12b only** — back to the dial deciding the cache size, patience back to 600 s
(`s12b-kvcap.json`):

```
cp /opt/llama-swap/scripts/gemma4-adapters.sh.bak-20260903-s12 /opt/llama-swap/scripts/gemma4-adapters.sh && \
cp /opt/llama-swap/config/config.yaml.bak-20260903-pre-s12b /opt/llama-swap/config/config.yaml
curl -s -X POST http://127.0.0.1:9000/api/models/unload/gemma4-adapters
```

then re-start it with any request to `product-owner-agent`. **Warning:** this re-creates the S12
condition in which the coding model cannot load beside the member.

**Undo the whole thing** — the three merged seats come back under their old names and the adapter
host stops (`s12-switchboard.json`):

```
cp /opt/llama-swap/config/config.yaml.bak-20260903-pre-gemma4-adapters /opt/llama-swap/config/config.yaml
```

The switchboard watches the file and reloads within about five seconds; `gemma4-adapters` stops via
its own stop command (`docker stop gemma4-adapters`); the fleet bounces for about a minute. The
member script can be left in place — nothing references it once the config is restored.

**The backups exist**, all four of them, named in the receipts:
`/opt/llama-swap/config/config.yaml.bak-20260903-pre-gemma4-adapters`,
`/opt/llama-swap/config/config.yaml.bak-20260903-pre-s12b`,
`/opt/llama-swap/scripts/gemma4-adapters.sh.bak-20260903-s12`, and the copy of the member script
kept beside the receipts as `gemma4-adapters.sh.copy`.

---

## Deviations, disclosed

Four, all recorded by the builders in their own receipts rather than found afterwards.

1. **The 30 GB gate was read in decimal gigabytes.** The brief said to load the coding model only if
   available memory was at least 30 GB. It settled at 30,421,032 kB — which is 30.4 GB counted in
   billions of bytes, or **29.0 GiB** as `free -g` prints it. The figure sat on both sides of the
   bar depending on the unit, and the bar did not say which. The builder proceeded on arithmetic
   from two runs that had already worked (the coding model costs about 22 GiB of available memory;
   S11's second test loaded it successfully from a *lower* starting point), and recorded the call
   plainly so it can be overruled. If GiB was intended, this was a deviation.
2. **A stricter abort trigger than briefed.** The brief said abort if available memory drops below
   3 GB at any five-second sample; the builder armed **5 GiB** instead, because S12's own trace
   shows memory falling at about 1.6 GB per second — one ten-second sample went from 16.9 GB to
   0.87 GB — so a 3 GB trigger on a five-second poll can be overtaken between samples. Stricter,
   never looser. It never fired; the lowest sample was 5.88 GiB.
3. **The config move restarted the member by itself, once.** The switchboard watches its config
   file, so moving the edited file into place triggered a reload that restarted `gemma4-adapters`
   before the deliberate unload had been issued. The builder confirmed by `docker inspect` that the
   restarted container already carried the new flag, then did the briefed unload and restart anyway
   — which is why the 509-second time-to-ready and the cache figure come from a clean start.
4. **Two log lines the brief asked for do not exist any more.** `Available KV cache memory` and
   `Free memory on device … Actual usage` are memory-profiling lines, and the new flag skips
   profiling entirely — vLLM says so itself in the `gpu_worker.py:459` line quoted above. This is
   the intended consequence of the change, not a fault. What to read instead: `gpu_worker.py:459`
   for the reservation and `kv_cache_utils.py:2146` for the token count.

Two further honest notes from the receipts: the prediction that the member would cost about 60 GiB
was low (73.9 GiB measured), and the builder made two mistakes of its own that never touched the box
— a `docker exec` without `-i` so a load probe never fired, and a `pkill -f` that matched the shell
running it — both caught by checking state afterwards and both redone correctly.

---

## What was not done

- No exam was run and no quality was measured in S11, S12 or S12b. These stages measure memory,
  readiness and routing only.
- The coding model was not left resident beside the member at the end of S12 — it was unloaded to
  stop the cascade, and only S12b put both back.
- The keepalive script was not touched.
- `/opt/litellm/config.yaml` was read for routing names in S12 and not opened at all in S12b; it was
  never edited (its modification time is still 2026-09-01 18:03:40).
- Nothing else on the box was restarted: not forge-prod, not the specialist containers, not the
  LiteLLM proxy (it restarted itself twice in S12 and was not touched in S12b), not the factory
  dashboard.
- NATS and port 4222 were not touched.
- The 8 GiB cache budget was not tuned further; it cleared the campaign bar on the first attempt, so
  no second value was tried.
- No secret was printed, saved, diffed or read from a process environment at any stage; every call
  that needed the LiteLLM key ran inside a container that already held it. All 56 receipt files are
  mode 600 and the secret scan returned zero.
- The switchboard config is not in a repository; the receipts named above are its record.
- This document was written from receipts and read-only checks. Nothing was pushed.
