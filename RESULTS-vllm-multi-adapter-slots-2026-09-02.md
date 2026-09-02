# RESULTS: One vLLM process, four adapters, parallel slots — GB10, 2026-09-02

**Runbook:** [`RUNBOOK-vllm-lora-adapter-serving-gb10.md`](./RUNBOOK-vllm-lora-adapter-serving-gb10.md)
(questions and pass/fail bars pre-registered before this run).
**Previous run:** [`RESULTS-vllm-lora-adapter-serving-2026-08-24.md`](./RESULTS-vllm-lora-adapter-serving-2026-08-24.md)
— one adapter, no parallel test.
**Box:** promaxgb10-41b1 (Dell Pro Max, GB10, aarch64, 121 GB of memory shared between the graphics
processor and the main processor).

Every number below names the file it was read from. Nothing here is quoted from a terminal.

---

## Verdict

**The serving mechanism works and the parallel slots are real; the quality is not yet good enough to
move any seat onto it.** One vLLM process loaded the Gemma 4 base once and served all four of our
tuned adapters at the same time, with no LoRA patches, and it answered a pair of simultaneous
requests in 1.17 times the time one request takes alone — against 2.0 times for the llama.cpp
workhorse we run today, which handles one request at a time (22.7 s for two at once against 11.4 s
for one, `ai-transition/docs/measurements/what-a-build-costs-the-models-2026-09-01.md`, line 59).
The same measurement also gave that workhorse two slots and got 14.9 s for two at once, 1.31 times
one — so most of this parallel win is also reachable from one configuration line on the engine
already running; it was reverted to one slot because a second slot costs context-window memory, the
same trade that caps this run at 1.19 requests' worth of full-length context. That is the thing this lane set out to
find out, and it is answered yes. But the exams say do not ship it yet: the product-owner adapter
scored 44 of 51 checks against a merged seat that scored 17 of 17 (a new failure mode appeared —
one reply's summary file was not valid YAML, which also took three further checks out of
measurement), the coach adapter went 0 of 6 reps green against a baseline of 6 of 6, and the
planner adapter has no machine grader at all so it was served but never marked. Two further facts
limit what the parallel result means: the key-value cache came out at only 1.54 GiB, which is 38,847
tokens — 1.19 requests' worth at the 32,768-token context we serve, so the four slots exist for
short prompts and would not exist at full length; and at temperature zero the adapters do not
repeat themselves, while the plain base model does, so the same question asked twice gets different
answers. The mechanism is proven. The seat move is not licensed by this run. *(See the addendum at the end: the control runs made the same evening show the product-owner slip is not the adapter path's and that the 17 of 17 baseline used an older prompt.)*

---

## What was run

| | |
|---|---|
| Container | `vllm-multi`, id `829d278b73d8` (`exams-2026-09-02.json`), started 2026-09-02 12:25:53Z, removed 13:46Z after its log was saved |
| Image | `vllm/vllm-openai:v0.25.0-aarch64-cu129` — the only release that both loads Gemma 4 and carries the adapter-name fix |
| Base model | `unsloth/gemma-4-26b-a4b-it` snapshot `60941ad6341d0b7af91277ff25c4175f08b56819`, mounted read-only from the host cache |
| Adapters served | `po-v5` (the known-good reference from August), `po-v6` (the live product-owner seat), `coach-ft-v4` (the live coach), `architect-plan-v2` (the live planner) |
| Endpoint | `http://127.0.0.1:8010/v1` |

Exact serve flags, copied from vLLM's own "non-default args" line in
`/home/richardwoollcott/fine-tuning/output/vllm-multi-2026-09-02/launch.log`:

```
--model /hf/hub/models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819
--served-model-name gemma4-base
--enable-lora --max-lora-rank 16
--lora-modules po-v5=/adapters/po-v5 po-v6=/adapters/po-v6
               coach-ft-v4=/adapters/coach-ft-v4 architect-plan-v2=/adapters/architect-plan-v2
--max-loras 4 --max-cpu-loras 8
--reasoning-parser gemma4
--max-model-len 32768 --max-num-seqs 4 --no-enable-prefix-caching
--gpu-memory-utilization 0.55 --limit-mm-per-prompt '{"image":0}'
```

The container's start command was `rm -rf /usr/local/lib/python3.12/dist-packages/torchcodec* &&
exec vllm serve …` — see Deviations.

Each adapter was mounted as its own bind mount at `/adapters/<name>`. A single directory of
symbolic links pointing at host paths does **not** work: inside the container every link dangles.
That was proved and recorded in
`/home/richardwoollcott/fine-tuning/output/vllm-multi-2026-09-02/adapters-mount-check.txt`
(four lines reading `SYMLINK-DANGLING`, followed by the four explicit mounts listing their files).

---

## Q1 to Q4 — the four pre-registered questions

| # | Question | Answer | Number, and the file it came from |
|---|---|---|---|
| **Q1** | Does an unpatched vLLM start with adapters on this mixture-of-experts model, and advertise all of them? | **PASS** | All five names advertised (`gemma4-base`, `po-v5`, `po-v6`, `coach-ft-v4`, `architect-plan-v2`) — `vllm-multi-2026-09-02/models.json`. **0** `get_expert_mapping` errors and **0** "not in the model's supported LoRA target modules" warnings — counted in `vllm-multi-2026-09-02/launch.log`. Time from container start to the model list answering: **494 s** — `vllm-multi-2026-09-02/footprint.txt` |
| **Q2** | Are the adapters actually doing something, or silently inert? | **PASS** | Same prompt, same server, temperature 0, one call per model: **5 different answers, 5 different checksums** (`distinct_md5_count: 5`, `all_identical: false`) — `vllm-multi-2026-09-02/selection.json`. The base and the product-owner adapter overlap on only 4.7% of their wording across three samples each (`base_vs_po_v6_mean: 0.047`) — `vllm-multi-2026-09-02/selection-strength.json`. That same file's own overall verdict is `separated: false`: the adapters' re-runs resemble each other only 0.58 on average while the closest pair of different models scored 0.709, which is the non-repeatability disclosed below, not a sign the adapters are inert. Q2's PASS rests on `selection.json` |
| **Q3** | Quality parity with the merged seats? | **NOT MET** | Product owner 44 of 51 checks (16, 11, 17) against a merged baseline of 17 of 17; coach 0 of 6 reps green against 6 of 6. See the exams table below for the per-rep files |
| **Q4** | Does one process really serve several requests side by side? | **PASS on short requests** | Single request median **11.548 s**; two simultaneous requests to the *same* adapter **13.488 s = 1.168×**; two to *different* adapters **13.641 s = 1.181×**; four at once, one per adapter, **20.295 s = 1.757×** — all from `vllm-multi-2026-09-02/slots-2026-09-02.csv`, totals in `vllm-multi-2026-09-02/summary.json`. The bar was "under 1.5× for a pair"; today's llama.cpp workhorse measured 2.0× with one slot and 1.31× with two slots on 2026-09-01 (`ai-transition/docs/measurements/what-a-build-costs-the-models-2026-09-01.md`, line 59) |

### Two things that qualify Q4, and must travel with it

**The slots are short-prompt slots.** vLLM reported `Available KV cache memory: 1.54 GiB`,
`GPU KV cache size: 38,847 tokens`, `Maximum concurrency for 32,768 tokens per request: 1.19x`
(`vllm-multi-2026-09-02/launch.log`, lines 304–307; repeated in `footprint.txt`). The key-value
cache is the working memory a request needs while it is being answered. The Q4 measurements used a
609-token prompt asking for 256 tokens back
(`prompt_tokens: 609, max_tokens: 256` in `vllm-multi-2026-09-02/summary.json`). Four such requests
fit easily. Four requests at the 32,768-token context this server advertises would not: on vLLM's
own arithmetic there is room for 1.19 of them. **The parallel win shown here has not been shown at
the context length the factory actually uses**, and raising `--gpu-memory-utilization` above 0.55
is the obvious lever but was not tested.

**The adapters are not repeatable at temperature 0.** Three identical calls per model:
the plain base gave the same answer all three times (`distinct_md5: 1, reproducible: true`), while
`po-v5`, `coach-ft-v4` and `architect-plan-v2` gave **three different answers each** and `po-v6`
gave two — `vllm-multi-2026-09-02/determinism-by-model.json`, `all_reproducible: false`. A separate
check found the same thing within one adapter, alone and in a batch
(`vllm-multi-2026-09-02/determinism-check.json`, `sequential_all_identical: false`). Greedy
decoding is supposed to be repeatable. It is repeatable here for the base and not for the adapters,
which points at the adapter path rather than at sampling. This was not chased down today and it is
a live question for any exam run over this server, because a re-run cannot be compared to itself.

### Reasoning text: separated on short answers, not on long ones

The base model's chat template always starts a "thought" section, and `--reasoning-parser gemma4`
is what keeps that text out of the answer. It works: on a short question the server put 631
characters of thinking in a `reasoning` field and the actual 69-character answer in `content`, with
no stray control token in either (`vllm-multi-2026-09-02/reasoning-probe-short-2048.json`,
`PASS_separation_with_text_on_both_sides: true`). On the long planning prompt it did not finish
thinking within the token budget: at 1,536 tokens the answer was 6,202 characters of reasoning and
**0 characters of content**, and at 4,096 tokens 16,251 characters of reasoning and still 0 of
content (`vllm-multi-2026-09-02/reasoning-check.json` `long_probe.PASS: false`, and
`vllm-multi-2026-09-02/reasoning-probe-4096.json`, `finish_reason: length`). The parser is fine.
The planner simply thinks for a very long time on this prompt, and a caller that reads only
`content` would get an empty reply. That is a real integration hazard for the planner seat.

---

## Exams, against their baselines

All product-owner reps were sent with `temperature: 0.0, max_tokens: 16384` — confirmed from each
rep's own `config.json`, not from the command line.

### Product owner — `po-v6` on `po-held-007-feature-spec`, reps 1 to 3 (frozen; the harness refuses rep 4)

| Rep | Read from `grade.txt` | Score | File |
|---|---|---|---|
| 1 | `1 failed, 16 passed` | 16 of 17 | `fleet-evals/runs/po-heldout-spec/20260902T132752Z-po-v6/po-held-007-feature-spec/rep1/grade.txt` |
| 2 | `2 failed, 11 passed, 3 skipped, 1 error` | **11 of 17** | `fleet-evals/runs/po-heldout-spec/20260902T132932Z-po-v6/po-held-007-feature-spec/rep2/grade.txt` |
| 3 | `17 passed` | 17 of 17 | `fleet-evals/runs/po-heldout-spec/20260902T133123Z-po-v6/po-held-007-feature-spec/rep3/grade.txt` |
| **Total** | | **44 of 51** | |

Baselines: the merged `po-ft-v6` seat scored **17 passed** on 2026-08-23
(`fleet-evals/runs/po-heldout-spec/20260823T221337Z-po-ft-v6/po-held-007-feature-spec/rep1/grade.txt`,
one rep only). `po-v5` over vLLM on 2026-08-24 scored **50 of 51** (17, 17, 16). Today is below both.

Rep 1's single failure is the *same* check that failed once on 2026-08-24: the summary's
Integration section must name the feature's own summary file as the `--context` path and did not
(`test_gate_po_held_007.py::test_summary_coherence`, line 191). That one is a known content slip.

**Rep 2 is new and is the reason the total fell.** The model's digest file was not valid YAML, so
the harness's post-processor refused to run, fell back to a simpler slicer, wrote 4 files instead of
6, and never produced the seed file three further checks need. Those three checks therefore
**measured nothing** and are recorded as not passed — the harness says so itself in `grade.txt`
("A skipped bar measures nothing"). The rep is 11 of 17, not 14 of 17. Details, including the exact
parser error and the three unmeasured checks, are in
`/home/richardwoollcott/fine-tuning/output/vllm-multi-2026-09-02/exams-2026-09-02.json`.

### Coach — `coach-ft-v4` on `coach-held-001-escape-kin` and `coach-held-002-catch-and-green`, reps 1 to 3 each

| Task | Rep | Read from `grade.txt` (the frozen "v2" battery) | Green? |
|---|---|---|---|
| coach-held-001-escape-kin | 1 | `1 failed, 1 passed, 2 deselected` | no |
| coach-held-001-escape-kin | 2 | `1 failed, 1 passed, 2 deselected` | no |
| coach-held-001-escape-kin | 3 | `1 failed, 1 passed, 2 deselected` | no |
| coach-held-002-catch-and-green | 1 | `1 failed, 2 passed, 3 deselected` | no |
| coach-held-002-catch-and-green | 2 | `1 failed, 2 passed, 3 deselected` | no |
| coach-held-002-catch-and-green | 3 | `1 failed, 2 passed, 3 deselected` | no |
| **Total** | | | **0 of 6** |

Files: `fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-2026-09-02/<task>/rep<N>/grade.txt`.
Baseline: **6 of 6 green** on 2026-07-25
(`fleet-evals/runs/coach-heldout/coach-ft-v4-2026-07-25/RESULTS-coach-heldout-v2bar-2026-07-25.md`).

**What failed is narrower than the score suggests, and the cause is not established.** The coach's
judgment was intact in all six reps: every bad bundle was rejected and both honest good ones were
approved with no findings. What failed is that its findings do not name the specific piece of
evidence in the bundle, so the grader's anchor match misses. Three differences between this run and
the baseline are untested and must be closed before blaming the adapter or vLLM:

1. **Temperature.** The baseline sent `temperature: 0.0`
   (`fleet-evals/runs/coach-heldout/coach-ft-v4-2026-07-25/coach-held-001-escape-kin/rep-1/config.json`);
   this run sent `0.1` (recorded in `exams-2026-09-02.json`).
2. **Weights and serving stack.** Baseline was a merged Q8_0 GGUF under a pinned llama.cpp; this run
   is the bf16 base plus the adapter under vLLM.
3. **Chat template — a metadata error, now bounded.** The six `config.json` files this run wrote say
   the coach's own template was used. That is wrong: the server had no `--chat-template` and the
   runner sends none, so the base snapshot's template was used
   (`fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-2026-09-02/SERVING-CORRECTION.txt`). The
   coordinator then rendered both templates on identical messages inside the container and got
   **byte-identical prompts** for the system-plus-user chats this runner sends
   (`.../COORDINATOR-template-render-check-2026-09-02.txt`). So this is a wrong metadata string, not
   a wrong prompt — it does not explain the failures, and items 1 and 2 remain the open candidates.

### Planner — `architect-plan-v2`

**Served, loaded, counted in the parallel test, and NOT machine-graded.** The planner's held-out
exam (`po-held-008`) has no runner assembly in this lane, so there is no automatic grader for it.
No grader was invented. Recorded as "not gated".

---

## Memory

All figures are `MemAvailable` from `free -g` — the memory the box could still hand out — read at
three points and saved to files.

| Point | MemAvailable | File |
|---|---|---|
| Before the switchboard was asked to release its seats (12:25:29Z) | 103 GB | `vllm-multi-2026-09-02/mem-before.txt` |
| After release, immediately before launch (12:25:30Z) | **113 GB** | `vllm-multi-2026-09-02/mem-before.txt` |
| Lowest point while weights were loading (12:31:15Z, first of two shards) | **7 GB** | `vllm-multi-2026-09-02/mem-during.txt` |
| Steady state, server answering (12:34:32Z) | **33 GB** | `vllm-multi-2026-09-02/mem-after.txt` |
| After the container was removed (13:46:29Z) | **103 GB** | `vllm-multi-2026-09-02/restore-s5.txt` |

**Footprint at `--gpu-memory-utilization 0.55`: 80 GB** (113 − 33), computed in
`vllm-multi-2026-09-02/footprint.txt`. **Headroom left while serving: 33 GB.** The rest of the
estate needs roughly 30 GB for the workhorse and the small always-on seats, so this fits — but only
just, and with nothing spare for a second large model.

vLLM's own accounting, from `vllm-multi-2026-09-02/launch.log`:
model loading took **53.62 GiB and 315.3 s**; key-value cache **1.54 GiB = 38,847 tokens**;
graph capture 0.17 GiB; engine start-up 67.15 s.

**The dip during loading is a transient, not a shortage.** Available memory fell from 113 GB to
7 GB while the first shard staged, then jumped back to 44–50 GB within about ten seconds of the
second shard landing (`mem-during.txt`, rows 12:31:20 → 12:31:25). The container was never killed by
the kernel (`OOMKilled=false`, no kernel out-of-memory activity). An earlier attempt the same
morning was stopped by hand at 12:06:53Z on a reading taken during that dip; the stop was wrong and
is recorded as such in `vllm-multi-2026-09-02/coordinator-stop-mem.txt`, with the log of that
aborted launch in `coordinator-stop-launch.log`. **0.55 did not fail and needs no change on this
evidence.**

---

## The converted adapters — where they came from and how they were checked

Three adapters had to be converted from the training format into the layout vLLM understands.
The converter is `/home/richardwoollcott/fine-tuning/scripts/convert_moe_lora_to_per_expert.py`.
The fourth, `po-v5`, was the existing reference and was **not touched**.

| Adapter | Source (training output) | Converted to | Converter log | Verification |
|---|---|---|---|---|
| `po-v6` | `~/fine-tuning/output/po-gemma4-v6/lora-adapter` | `.../po-gemma4-v6/lora-adapter-vllm` | `.../po-gemma4-v6/convert-2026-09-02.log` | `.../po-gemma4-v6/convert-verify-2026-09-02.json` and `.../convert-verify-independent-2026-09-02.json` |
| `coach-ft-v4` | `~/fine-tuning/output/coach-gemma4-26b-moe-v4/lora-adapter` | `.../coach-gemma4-26b-moe-v4/lora-adapter-vllm` | `.../coach-gemma4-26b-moe-v4/convert-2026-09-02.log` | `.../coach-gemma4-26b-moe-v4/convert-verify-2026-09-02.json` and `~/fine-tuning/output/convert-verify-independent-coach-gemma4-26b-moe-v4-2026-09-02.json` |
| `architect-plan-v2` | `~/fine-tuning/output/architect-plan-v2/lora-adapter` | `.../architect-plan-v2/lora-adapter-vllm` | `.../architect-plan-v2/convert-2026-09-02.log` | `.../architect-plan-v2/convert-verify-2026-09-02.json` and `.../convert-verify-independent-2026-09-02.json` |
| `po-v5` (reference, untouched) | — | `~/fine-tuning/output/po-gemma4-v5/lora-adapter-vllm` | — | — |

**Shape.** Each conversion produced **23,040 per-expert tensors plus 410 passed straight through =
23,450 total**, which is exactly 30 layers × 128 experts × 3 projections × 2 tensors. Read from each
`convert-2026-09-02.log` and re-counted in each verification file
(`per_expert_matches_expected: true`). Every converted adapter file is 2,673,219,856 bytes, the same
size as the reference (`vllm-multi-2026-09-02/adapters-mount-check.txt`).

**Numerical check — the one the converter itself does not do.** The converter asserts shapes only.
An independent script re-derived the expected slices straight from the documented packing rule
(A for expert *e* is a contiguous block; B for expert *e* is strided, taking every 128th column;
the fused gate/up output is split at 704) and compared them tensor by tensor against what was
written, for layers 0 and 29 and experts 0 and 127 — **24 tensors per adapter, all exactly equal**
(`tensors_checked: 24, all_exactly_equal: true, num_equal: 24` in every
`convert-verify-independent-2026-09-02.json`). This is a spot check at the corners, not an
exhaustive check of all 23,040.

**Reproducibility.** Each adapter was re-converted from scratch into a scratch directory and
compared byte for byte against the copy being served: **all six files identical for all three
adapters**, 18 comparisons, no differences —
`/home/richardwoollcott/fine-tuning/output/convert-repro-byte-identity-2026-09-02.txt`.

**Chat templates carried through unchanged.** `po-v6` and `architect-plan-v2` carry the base
template (md5 `7e2ad1fbf31b`, 18,924 bytes) — the same one the reference `po-v5` carries. The coach
carries its own smaller template (md5 `918d304ab9c6`, 2,466 bytes). Each was confirmed identical to
its source in the verification files. Note that vLLM used the **base** template for every request
in this run regardless (see the coach section).

---

## Deviations, stated rather than hidden

1. **The broken video decoder was deleted at container start.** The `v0.25.0-aarch64-cu129` image
   ships a `torchcodec` built for CUDA 13 inside a CUDA 12.9 image; it raises at `import vllm` and
   kills the server before any model work. An absent one is harmless; a present-but-broken one is
   fatal. The container therefore ran
   `rm -rf /usr/local/lib/python3.12/dist-packages/torchcodec*` before starting the server. **This
   is an image-packaging workaround, not a LoRA patch** — "unpatched" must never be allowed to hide
   it. We decode no video.
2. **No LoRA patches of any kind.** None of the April spike's three patched files were mounted.
3. **The coach exam ran at temperature 0.1, its baseline at 0.0.** Recorded above; it is one of the
   two untested candidate causes of the 0-of-6 result.
4. **The coach run's own `config.json` files carry stale serving metadata.** Besides the wrong
   template string, each of the six files also records a GGUF path (`coach-ft-v3 ... Q4_K_M.gguf`), a
   v3 lineage, `ctx_size 98304`, `np 1` and `served_via llama-swap :9000` — copied through from the
   July runner's defaults. None of it is true of this run: the coach was served as bf16 base plus
   adapter by vLLM on port 8010 with no GGUF and no switchboard. The numbers are unaffected. All of
   these fields are now listed in `SERVING-CORRECTION.txt` beside the run, and the rendered prompts
   were shown to be identical either way.
5. **An earlier launch of the same configuration was stopped by hand at 12:06:53Z** on a
   mid-load memory reading. That was a mistake, is recorded as one in
   `coordinator-stop-mem.txt`, and the run reported here is the clean relaunch.
6. **245 warnings of the form "no matching PunicaWrapper is found; vision_tower… will be ignored"**
   appear in `launch.log`. They concern the image tower, which we do not use (`--limit-mm-per-prompt
   '{"image":0}'`). They are not the "tensors skipped" warning that would signal an inert adapter —
   that warning appears **zero** times.
7. **The switchboard's loaded models were unloaded before the launch.** At 12:25:30Z the lane called
   llama-swap's own unload endpoint (`curl http://127.0.0.1:9000/unload`, runbook Phase 0.5) to free
   memory: available memory went from 103 GB to 113 GB (`vllm-multi-2026-09-02/mem-before.txt`,
   `footprint.txt` line 5). No configuration was edited and nothing was restarted; every seat reloads
   on its next request, so the first call to each seat after this lane paid a cold start. The memory
   table above says "asked to release its seats" — this is what that means. *(Added by the lane
   coordinator on 2026-09-02 after review; the builder's text had said the switchboard was "not touched".)*

---

## What this does and does not license

**Licensed.**
- The mechanism: one resident Gemma 4 base plus four ~2.7 GB adapters in a single vLLM process, on
  this box, on this image, on this snapshot, with no LoRA patches.
- Parallel serving of several requests at once, including requests aimed at *different* adapters,
  **for short prompts** — 1.17× to 1.18× for a pair against 2.0× for today's one-slot workhorse,
  and against 1.31× for the same workhorse given two slots (measured 2026-09-01, reverted for
  memory). vLLM is not the only way to get slots; it is the way that also frees the memory the
  duplicated seats hold.
- The conversion procedure for turning our training-format adapters into vLLM-format ones, now
  reproducible byte for byte and spot-checked numerically.

**NOT licensed.**
- **Moving any seat onto this.** The product-owner exam is below both its baselines and the coach
  exam is 0 of 6. Quality has not been shown.
- **Parallel slots at the context length the factory uses.** Proven at ~600-token prompts only; the
  key-value cache at 0.55 holds 1.19 requests' worth of 32,768-token context.
- **Repeatable answers.** At temperature 0 the adapters do not reproduce themselves; only the base
  does.
- **One adapter set, one box.** These four adapters, this snapshot, this GB10. The Spark boxes are
  untested.
- **No switchboard integration.** No seat entry in the model switchboard (llama-swap, on port 9000)
  points at this process, and none of its configuration was edited. Callers reached vLLM directly on
  port 8010. The switchboard WAS asked, through its own API, to unload its loaded models before the
  launch — see Deviation 7.
- **The planner is ungated.** Served and counted, never marked. And its long answers can come back
  with an empty `content` field because it is still thinking when the token budget runs out.
- **The version pin is deliberately behind current, and stays there.** v0.25.0 is the newest release
  that loads Gemma 4 at all: v0.26 and later ship transformers 5.14+, whose per-layer attention
  guard makes vLLM's head-size lookup raise, and v0.27.1 was proved here on 2026-08-24 to fail with
  and without adapters. v0.28.0 contains the upstream fix and is the candidate replacement, but it
  has been read and not run — it is not licensed until a launch, an adapter start and an
  effectiveness check have actually been executed on it.

---

## Next step candidates

Listed as options, not as a plan. Nothing here is started.

1. **Close the coach question before drawing any conclusion from 0 of 6.** Re-run the two coach
   exams at temperature 0.0 to match the baseline. That is one dial and it removes the cheaper of
   the two remaining candidate causes; if it stays red, the difference is the weights-and-stack
   change (merged Q8_0 under llama.cpp versus bf16 base plus adapter under vLLM), which is a much
   bigger question.
2. **Explain the non-repeatability at temperature 0.** The base repeats and the adapters do not.
   Until that is understood, no exam result over this server can be compared with a re-run of
   itself, which undercuts every quality number above.
3. **Measure the slots at real context.** Repeat the parallel test with prompts near 32,768 tokens,
   and try `--gpu-memory-utilization` above 0.55 to see what the key-value cache can be grown to
   before the rest of the estate is squeezed. The 33 GB of headroom measured here is the budget.
4. **A switchboard entry fronting this process.** The switchboard forwards the requested model name
   through unchanged, so an entry could point at this vLLM process and callers would keep using
   the names they use today. Cheap to add, and it should wait until 1 and 3 are answered.
5. **A runner for the planner exam (`po-held-008`).** Without it the planner cannot be gated, and
   the empty-`content` behaviour on long prompts would go unnoticed.

---

## Receipt index

Run receipts (all under `/home/richardwoollcott/fine-tuning/output/vllm-multi-2026-09-02/`):
`final.log` (the container's complete log), `launch.log`, `models.json`,
`slots-2026-09-02.csv`, `summary.json`, `slots-run.log`, `slots_proof.py`,
`selection.json`, `selection-strength.json`, `selection-*.txt`, `selection-sample-*.txt`,
`determinism-check.json`, `determinism-by-model.json`,
`reasoning-check.json`, `reasoning-plan-v2.json`, `reasoning-plan-v2-long.json`,
`reasoning-probe-4096.json`, `reasoning-probe-short-2048.json`,
`mem-before.txt`, `mem-during.txt`, `mem-after.txt`, `footprint.txt`,
`adapters-mount-check.txt`, `exams-2026-09-02.json`,
`coordinator-stop-mem.txt`, `coordinator-stop-launch.log`,
`estate-gate-s5.txt`, `restore-s5.txt`.

Exam receipts: `fleet-evals/runs/po-heldout-spec/20260902T13{2752,2932,3123}Z-po-v6/` and
`fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-2026-09-02/`.

Conversion receipts: the three `convert-2026-09-02.log`, three `convert-verify-2026-09-02.json`,
three `convert-verify-independent-*.json`, and
`/home/richardwoollcott/fine-tuning/output/convert-repro-byte-identity-2026-09-02.txt`.

## Addendum, 2026-09-02 evening — the control runs (added by the lane coordinator after the results above were committed)

**Product owner: the slip is not the adapter path.** The merged po-v6 weights, served by the same vLLM image with no adapter at all and given today's prompt, scored 16 of 17 on all three greedy runs, failing the same Integration-section check that the adapter path failed, and the three replies were byte-identical (2,782 tokens each). Receipts: `fleet-evals/runs/po-heldout-spec/20260902T145434Z-po-v6-merged/`, `...T145647Z-po-v6-merged/`, `...T145857Z-po-v6-merged/` (each `.../rep<N>/grade.txt`, `config.json`, `response.txt`), and `~/fine-tuning/output/vllm-control-2026-09-02/control-A.json`.

**The 17 of 17 baseline was not like-for-like.** Every vLLM run (24 August, 2 September, and this control) sent a system prompt whose hash is `14969fec…`; the 23 August merged run that scored 17 of 17 (one run) sent `6e4d3014…`. The difference is specialist-agent commit `0161d2d` (24 August 12:53), which added twelve lines to `roles/product-owner/prompts/player_feature_spec.md` about an optional endpoint field. It is also why every vLLM prompt is 226 tokens longer (11,802 against 11,576): the prompt grew, the tokeniser did not change. With today's prompt the merged model omits the Integration section repeatably; the two merged outputs (August under llama.cpp, today under vLLM) are different documents throughout, not the same document minus one section. The exam table above therefore compares against a baseline that no longer exists. A fair baseline needs the merged model under llama.cpp with today's prompt; that run touches a live seat and has not been made.

**Repeatability belongs to the adapter kernels.** Merged weights under vLLM gave three identical greedy replies; the base did the same yesterday; only the adapters did not. That narrows the non-repeatability finding to the LoRA path and leaves it as the adapter path's one confirmed defect, alongside shorter replies (2,040 to 2,467 tokens against 2,782 for the merged weights on the same prompt).

**The adapters cost the cache the slots needed.** With the merged weights and no adapters, the same 0.55 memory dial left a key-value cache of 17.95 GiB, 452,549 tokens, 13.8 requests' worth at full 32,768-token context (`~/fine-tuning/output/vllm-control-2026-09-02/launchA.log`). Yesterday, with four adapters resident, it was 1.54 GiB and 1.19 requests' worth. The two weight files are the same size (48.07 GiB, 1,013 tensors, vision tower included in both), so the whole 16.4 GiB difference is the adapter machinery: the four resident exports are about 10 GiB, and vLLM's load-time accounting shows a further 5 GiB taken during model loading with adapters enabled (53.62 GiB against 48.54 GiB), with the adapter kernels' working buffers making up the rest. So the "short-prompt slots only" limit in Q4 is a cost of how many adapters are kept resident, not of vLLM: fewer adapters per batch, a higher dial, or merged seats each buy it back.

**Coach: temperature was not the cause.** Re-run at temperature 0.0, the baseline's sampling, over the adapter path: 0 of 6 runs green again, the same check failing each time, and the loci the coach wrote are word for word what it wrote at 0.1 yesterday (`bdd.pending[0]`, `plan_audit.variances[0].detail`, `independent_tests.stdout_tail`, `honesty.claims`) against the baseline's specific ones (`plan_audit.variances: tests/conftest.py injects a fake gateway…`). Receipts: `fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-temp0-2026-09-02/<task>/rep<N>/` (`grade.txt`, `config.json` with `temperature: 0.0`, `verdicts/*.json`) and `~/fine-tuning/output/vllm-control-2026-09-02/control-B.json`. Two further facts from those files. On the escape-kin task the three greedy runs were identical; on catch-and-green they were not, and in one run the coach **approved** a bundle it rejected in the other two (CK-02, run 2), so the adapter path's non-repeatability reaches the verdict itself, not only the wording. The coach exam is not prompt-confounded: the 25 July baseline and today share the same instruction version and the same bundle hashes. What remains between the 6 of 6 and the 0 of 6 is the weights path (merged Q8_0 GGUF under llama.cpp against bf16 base plus runtime adapter under vLLM) and the engine; separating those needs a merged coach export served under vLLM, which does not exist yet (a merge is about 49 GB and an hour). The July 6 of 6 itself was re-graded live by the Stage B coach and holds (001: `2 passed, 2 deselected` x3; 002: `3 passed, 3 deselected` x3).

What this changes in the verdict: "quality is not yet good enough to move any seat" stands, but for a different reason than written. The product-owner adapter is not measurably worse than its own merged weights under this engine; the open questions are the prompt-sensitivity of the Integration section (a harness/prompt matter), the adapter kernels' non-repeatability (now shown to flip a coach verdict), and whether the coach's vague loci come from the runtime-adapter path or from vLLM itself, which only a merged coach under vLLM can answer.

**How the controls were run, and two script fixes.** Each stage was an Opus builder driving `~/fine-tuning/output/vllm-control-2026-09-02/control-run.sh` with an independent Opus coach re-grading every rep by hand (workflow `wf_be7516fd-45a`; verdicts pass, tests not green, no blocker). The script needed two fixes before it would run, recorded in `script-changes.txt` beside it with the original kept: the estate gate's header check was anchored at line start and could never pass against forge's box-drawn table (the first attempt aborted having started nothing), and the `--limit-mm-per-prompt` JSON lost its quotes through the inner shell. Diagnostic container `vllm-control` on port 8011 only; the single request to the switchboard was one GET of its model list at each restore; nothing pushed, deployed, reconfigured or restarted.

## Estate restored

Checked after the container was removed, recorded in
`/home/richardwoollcott/fine-tuning/output/vllm-multi-2026-09-02/restore-s5.txt`:
the model switchboard answers on port 9000 (HTTP 200, 29 model names listed);
`forge-prod` is up and healthy; both specialist-agent containers are up; `vllm-multi` no longer
exists; `free -g` shows 103 GB available. The forge build queue was read before and after and had
nothing running, paused or queued (`estate-gate-s5.txt`).
