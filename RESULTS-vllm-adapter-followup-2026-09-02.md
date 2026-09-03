# RESULTS: the follow-up — with the adapters finally serving intact, do the seats hold?

**Box:** promaxgb10-41b1 (Dell Pro Max, GB10, aarch64, 121 GB of memory shared between the graphics
processor and the main processor).
**Dates:** the measurements ran early on 2026-09-03; the lane is the follow-up to the previous
evening's controls.
**Related:** [`RESULTS-vllm-adapter-controls-2026-09-02.md`](./RESULTS-vllm-adapter-controls-2026-09-02.md)
(the controls that found and fixed the two defects this work builds on),
[`RESULTS-vllm-multi-adapter-slots-2026-09-02.md`](./RESULTS-vllm-multi-adapter-slots-2026-09-02.md)
and [`RUNBOOK-vllm-lora-adapter-serving-gb10.md`](./RUNBOOK-vllm-lora-adapter-serving-gb10.md).

Three words used throughout. An **adapter** is the small file of extra numbers a fine-tune produces;
it is applied on top of the big base model while the model is answering. **Merged weights** are the
opposite — the same extra numbers baked permanently into a full copy of the model, so nothing is
applied at run time. The **dial** is vLLM's `--gpu-memory-utilization` setting, which tells the server
how much of the machine's memory to claim for itself. The question the whole lane has been asking is
whether one big base model with several adapters on top — one process, several specialist seats — can
replace one whole model per seat.

Every number below names the file it was read from. Nothing here is quoted from a terminal.

---

## Verdict

**The adapter path now works, and the answer to "is the adapter as good as the merged weights"
is yes for both seats that have an exam — but only with vLLM's deterministic-kernel mode switched
off.** Taking those in the order they were asked. **Product owner:** with the corrected export the
product-owner adapter equals or beats its own merged weights — `po-v6` scored 17, 16 and 16 out of 17
and `po-v5` scored 17, 17 and 17, against 16, 16 and 16 for the merged `po-v6` weights under the same
image and the same prompt, and the one check `po-v6` misses twice is the same check the merged weights
miss all three times (`s8b-runaway.json`; `control-A.json`). That result only appeared once the
deterministic mode was off. With the mode on (stage S8) the very same adapter, export, engine, dial
and prompt ran away: all three replies hit the 16,384-token ceiling, wrote one of the four required
files, repeated the same nineteen scenarios about eleven times over, and could not be graded at all
(`s8-followup.json`). Stage S8b changed exactly one thing — it did not set `VLLM_BATCH_INVARIANT` —
and the runaway vanished, so **the runaway belongs to the deterministic-kernel mode meeting the expert
adapters on long generation, not to the runtime expert path**; the price of turning the mode off is
that three runs at temperature zero no longer give byte-identical replies. **Coach:** it passes at
the dial this box can live with, six of six runs green and fifteen of fifteen checks, both with the
mode on and with it off (`s8-followup.json`, `s8b-runaway.json`), so the mode was never what made the
coach pass either. **Planner:** its adapter loads completely and its answer differs from the bare
base model's, and that is all — there is no planner exam, so nothing here grades the plan.
**What the 0.65 dial leaves:** with four adapters resident, 13.94 GiB of working cache — 351,628
tokens, about 10.7 full-length requests — and about 19 GB of machine memory for everything else
(`kv-lines-s8.txt`, `mem-settled-s8.txt`); with three adapters, 16.5 GiB, 416,056 tokens, 12.7
requests' worth and about 20 GB left (`kv-lines-s8b.txt`, `mem-settled-s8b.txt`). Usable, but still
under the 25 GB machine-memory bar the earlier brief set. **Slots at natural reply length:** four
adapters genuinely share one process — throughput rises from 15.0 completion tokens per second for one
request alone to 22.6 across two and 30.9 across four, one per adapter (`slots-natural.csv`) — but at
about 7.4 to 8.3 tokens per second each when four are running this is a batch machine, not an
interactive one, and the same long-prompt test exposed the deterministic mode failing again: whether a
reply ended by itself depended on how many other requests were in flight.

---

## What was run

Two launches on 2026-09-03, one after the other, each in a throwaway diagnostic container. Nothing
was pushed, deployed, restarted or reconfigured.

| Stage | What it did | Main receipt |
|---|---|---|
| S8 | All four corrected exports served together at dial 0.65 with the deterministic-kernel mode **on**: per-module load check, product-owner exam, coach exam, planner load-and-difference check, cache and memory figures, and the parallel-slot test at natural reply length | `~/fine-tuning/output/vllm-followup-2026-09-02/s8-followup.json` |
| S8b | Three of the same exports at the same dial with the deterministic mode **off**, to settle whether the product owner's runaway was the mode or the adapter path: per-module load check, product-owner exam for `po-v6` and `po-v5`, coach exam | `.../s8b-runaway.json` |
| S9 | This write-up | this file |

**Image, base model and snapshot.** Both launches used `vllm/vllm-openai:v0.25.0-aarch64-cu129`,
serving the base model `unsloth/gemma-4-26b-a4b-it`, snapshot
`60941ad6341d0b7af91277ff25c4175f08b56819`, mounted read-only from the host cache
(`launch-s8.sh`, `launch-s8b.sh`; both servers' own "non-default args" lines in `kv-lines-s8.txt` and
`kv-lines-s8b.txt`). The image ships a `torchcodec` built for the wrong CUDA version, which stops vLLM
at import, so both start commands begin `rm -rf /usr/local/lib/python3.12/dist-packages/torchcodec*`.
That is a workaround for a packaging fault in the image, not a change to how adapters are served.
All work ran in a container named `vllm-control` on port 8011 only, never with `--rm`, log saved and
removed by hand.

**The four corrected exports.** Every adapter served in both stages came from
`~/fine-tuning/output/vllm-exports-v3/` — the arithmetic-corrected numbers with the per-expert keys
renamed from `…layers.N.experts.E.*` to `…layers.N.moe.experts.E.*`, which is the name vLLM's Gemma 4
code actually registers the expert block under. Each directory carries a `rename-v3.json` recording
23,040 of 23,450 keys renamed. Both defects, and why they were silent, are written up in the controls
document; this work assumes them fixed and asks what the fixed path scores.

| Name served | Export directory | Served in |
|---|---|---|
| `po-v5` | `vllm-exports-v3/po-gemma4-v5` | S8, S8b |
| `po-v6` | `vllm-exports-v3/po-gemma4-v6` | S8, S8b |
| `coach-ft-v4` | `vllm-exports-v3/coach-gemma4-26b-moe-v4` | S8, S8b |
| `architect-plan-v2` | `vllm-exports-v3/architect-plan-v2` | S8 only |

**Flags and environment, per launch, copied from each server's own "non-default args" line.**

| | S8 | S8b |
|---|---|---|
| Adapters resident | four | three (no planner) |
| Adapter slots | `--max-loras 4 --max-cpu-loras 8` | `--max-loras 3 --max-cpu-loras 6` |
| Dial | 0.65 | 0.65 |
| Deterministic kernels | `VLLM_BATCH_INVARIANT=1` | not set |
| The server's own confirmation | `'VLLM_BATCH_INVARIANT': True` (`kv-lines-s8.txt`) | `'VLLM_BATCH_INVARIANT': False` (`kv-lines-s8b.txt`) |
| Launch script / log | `launch-s8.sh`, `launch-s8.log` | `launch-s8b.sh`, `launch-s8b.log` |
| Full container log | `final-s8.log` (33,573,824 bytes) | `final-s8b.log` (7,691,431 bytes) |

Common to both: `--enable-lora --max-lora-rank 16 --reasoning-parser gemma4 --max-model-len 32768
--max-num-seqs 4 --no-enable-prefix-caching --limit-mm-per-prompt '{"image":0}'`, plus
`VLLM_LOGGING_LEVEL=DEBUG` so the per-module load lines are written. Both servers' own logs record
`'limit_mm_per_prompt': {'image': 0}`.

**Where the receipts live.** Everything is under
`~/fine-tuning/output/vllm-followup-2026-09-02/`, and file names below are relative to that directory
unless a full path is given. Exam runs are under
`~/Projects/appmilla_github/fleet-evals/runs/`, in four run directories created for this work and
never written into afterwards:
`po-heldout-spec/20260902-followup-po-v6-v3-batchinvariant`,
`po-heldout-spec/20260903-followup-po-v6-v3-plain`,
`po-heldout-spec/20260903-followup-po-v5-v3-plain`,
`coach-heldout/coach-ft-v4-v3-followup-2026-09-02` and
`coach-heldout/coach-ft-v4-v3-plain-2026-09-03`.

---

## The per-module load table

vLLM writes one debug line per module every time it switches an adapter into a slot: either
"Successfully loaded LoRA weights for module …" or "No LoRA weights found for module …, skipping",
and a skipped module is set to zero — that is, switched off. Reading those lines back out of each
launch log is what caught the naming defect the night before. Both launches were read the same way
(`lora-module-load-report.json` from `launch-s8.log`; `lora-module-load-report-s8b.json` from
`launch-s8b.log`). The model has 30 layers, so 180 modules per adapter.

| Launch | Adapter | Modules given weights | Of those, expert blocks | Modules zeroed | What was zeroed |
|---|---|---|---|---|---|
| S8 | `po-v5` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |
| S8 | `po-v6` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |
| S8 | `coach-ft-v4` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |
| S8 | `architect-plan-v2` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |
| S8b | `po-v6` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |
| S8b | `po-v5` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |
| S8b | `coach-ft-v4` | 150 | **30 of 30** | 30 | the 30 `router.proj` modules |

The 150 that got weights break down as 60 attention, 60 ordinary feed-forward and 30 expert blocks per
adapter. The only modules still switched off are the 30 `router.proj` ones, which no adapter targets
and which were switched off in the previous evening's working launch too. **Compare the same table in
the controls document, where four of five adapters had 0 of 30 expert blocks loaded.** Warm-up blocks
(12 in S8, 9 in S8b) are excluded and named as excluded in both reports: they are vLLM's own dummy
adapters, synthesised to fit every module, and say nothing about our exports.

---

## Product owner

The exam is `po-held-007-feature-spec`, 17 checks, three repetitions, temperature 0, budget 16,384
tokens. Every repetition in both stages used today's prompt — system prompt hash
`14969fec8dba022d807d276c76db402053f618f57dcd4bd74df0fba0531efb63`, read from each repetition's own
`config.json` — which is the same prompt the merged-weights control used, so the comparison is
like for like.

| Configuration | Scores, read from each `grade.txt` | Did the reply end by itself? | Repeatable? | Files |
|---|---|---|---|---|
| Merged `po-v6` weights under vLLM, no adapter (2026-09-02 control, dial 0.55) | 16, 16, 16 of 17 | yes, 2,782 tokens each time | yes, three byte-identical replies (md5 `acd351b2…`) | `~/fine-tuning/output/vllm-control-2026-09-02/control-A.json` |
| Old export, expert half switched off (the 2026-09-02 lane run) | 16, 11, 17 of 17 | — | no | `fleet-evals/runs/po-heldout-spec/20260902T13{2752,2932,3123}Z-po-v6/` |
| Arithmetic-corrected but wrongly named export, expert half still off | could not be graded, 16, 16 | — | no | `.../20260902-control-po-v6-adapterv2/` |
| Same, with the deterministic mode on | could not be graded, three times | — | yes, all three identical | `.../20260902-control-po-v6-adapter-batchinvariant/` |
| **S8 — corrected export, expert half live, deterministic mode ON** | **could not be graded, three times** | **no — all three ran to the 16,384-token ceiling** | yes, all three byte-identical (md5 `ae27836a…`) | `.../20260902-followup-po-v6-v3-batchinvariant/`; `s8-followup.json` |
| **S8b — `po-v6`, corrected export, deterministic mode OFF** | **17, 16, 16 of 17** | **yes — 2,518 / 2,413 / 2,773 tokens** | no — three different replies | `.../20260903-followup-po-v6-v3-plain/`; `s8b-runaway.json` |
| **S8b — `po-v5`, corrected export, deterministic mode OFF** | **17, 17, 17 of 17** | **yes — 2,415 / 3,065 / 2,799 tokens** | no — three different replies | `.../20260903-followup-po-v5-v3-plain/`; `s8b-runaway.json` |

For comparison, `po-v5` on the old export path on 2026-08-24 — with its expert half switched off by
the converter fault, though nobody knew that at the time — scored 17, 17 and 16, at 2,150 / 2,165 /
2,291 tokens (the three `grade.txt` files under `fleet-evals/runs/po-heldout-spec/20260824T15{3321,3546,3731}Z-po-v5/`,
listed in `s8b-runaway.json`). So on this exam the expert half neither rescues nor ruins the product
owner; what it changed was the interaction with the deterministic kernels.

### The S8 runaway, in numbers

All three S8 repetitions stopped for the same reason: `finish_reason` was `length`, meaning the model
was still writing when its 16,384-token budget ran out, and `completion_tokens` was exactly 16,384 in
each (each repetition's `config.json` under `.../20260902-followup-po-v6-v3-batchinvariant/`). The
task asks for four demarcated FILE blocks; the reply opened one — the `.feature` file — and never
closed it. Counted directly from repetition 1's `response.txt`: **203 `Scenario:` lines of which only
19 are distinct titles**, and **one** `=== FILE:` marker. The same block of nineteen scenarios was
written out about eleven times over. All three `response.txt` files have md5
`ae27836a07e01b3350ae808153bef88a`, so the deterministic mode was doing exactly what it promises —
pinning the answer — and the answer it pinned was a loop. There is no digest file to parse, so the
harness fell back to its simpler slicer, three checks measured nothing, and the run **could not be
graded**. That is not a score of anything, and it must not be quoted as one. Each repetition took
about seventeen minutes (1,018.7 / 1,003.9 / 1,053.3 seconds, from each `config.json`).

### What S8b says about it: the mode, not the path

S8b changed one thing and one thing only — `VLLM_BATCH_INVARIANT` was not set, confirmed by the
server's own line `'VLLM_BATCH_INVARIANT': False` in `kv-lines-s8b.txt`. Same image, same base model,
same corrected exports, same dial, same prompt bytes, same temperature, same token budget. Every one
of the six product-owner repetitions then ended by itself, wrote all four demarcated FILE blocks, and
was assembled by the production post-processor rather than the fallback slicer (`tree_source:
postprocess_feature_spec` in every repetition's `config.json`). Each repetition took about two minutes
instead of seventeen (119.7 to 151.1 seconds, from the `config.json` files). **So the runaway is the
deterministic-kernel mode interacting with the expert adapters on long generation, not the runtime
expert path.**

Two readings follow. First, on this exam the adapter path now equals or beats the merged weights:
`po-v6` at 17/16/16 and `po-v5` at 17/17/17 against the merged weights' 16/16/16, and the check
`po-v6` misses in repetitions 2 and 3 is `test_summary_coherence` — the Integration section not naming
the summary path — which is the identical check the merged weights fail all three times (each
repetition's `grade.txt`; `control-A.json`). Two independent product-owner adapters clearing the exam
on the same working expert path means the clean `po-v6` result is not a fluke of one adapter. Second,
the cost of switching the mode off is repeat-run reproducibility: the three `po-v6` replies have three
different md5 sums and so do the three `po-v5` ones, where S8's three were identical
(`s8b-runaway.json`). We can have an answer that finishes, or an answer that is byte-identical between
runs, but on this evidence not both.

---

## Coach

The coach exam is two held-out bundles, three repetitions each, six runs in all, fifteen checks
between them. A run is green only if every check in the frozen battery passes.

| Configuration | Runs green | Checks green | Files |
|---|---|---|---|
| Merged 8-bit weights under llama.cpp, 25 July baseline | 6 of 6 | — | `fleet-evals/runs/coach-heldout/coach-ft-v4-2026-07-25/` |
| Merged 16-bit weights under vLLM, no adapter (S2, 2026-09-02) | 6 of 6 | — | `.../coach-ft-v4-merged-vllm-temp0-2026-09-02/` |
| Old and wrongly-named exports under vLLM (three separate configurations, 2026-09-02) | 0 of 6 each | — | see the controls document |
| Renamed export, deterministic mode on, dial 0.70, five adapters (S5, 2026-09-02) | 6 of 6 | 15 of 15 | `.../coach-ft-v4-moe-vllm-batchinvariant-temp0-2026-09-02/` |
| **S8 — corrected export, deterministic mode ON, dial 0.65, four adapters** | **6 of 6** | **15 of 15** | `.../coach-ft-v4-v3-followup-2026-09-02/`; `s8-followup.json` |
| **S8b — corrected export, deterministic mode OFF, dial 0.65, three adapters** | **6 of 6** | **15 of 15** | `.../coach-ft-v4-v3-plain-2026-09-03/`; `s8b-runaway.json` |

The grade lines are `2 passed, 2 deselected` on each of three repetitions of the escape-kin bundle and
`3 passed, 3 deselected` on each of three repetitions of the catch-and-green bundle, in both stages —
six `grade.txt` files per stage, all listed by full path in `s8-followup.json` and `s8b-runaway.json`.
Every bundle parsed, and every reply ended by itself (`parse_ok=True`, `finish=stop` throughout, in
`coach-exam-s8.log` and `coach-exam-s8b.log`).

The findings are the specific kind, not the bare-field-name kind that the broken export produced. S8's
were word-for-word identical across all three repetitions and quoted in full in `s8-followup.json`;
they name the file and line (`features/rsvp.feature:41`), the offending argument
(`start_roster_sync() got an unexpected keyword argument 'retry_policy'`), and the manufactured green
(`tests/conftest.py injects a fake gateway into sys.modules before collection`). Against S5, one
finding is classed differently — S5 recorded the first escape-kin finding as defect class DC-14 and
S8 records it as DC-08, naming the same defect at the same file and line — and both wordings pass the
grader. Verdicts match the merged model's on every bundle: reject the four escape-kin bundles, reject
the two dishonest catch-and-green bundles, approve the two honest ones.

Two things this does **not** show. Dropping the dial from 0.70 to 0.65, and serving four adapters
rather than five, changed nothing the grader can see — but that is one launch each, not a sweep. And
the coach passes with the deterministic mode on and with it off, so unlike the product owner it gives
no evidence either way about that mode.

**An inherited receipt defect, in every vLLM coach run including these.** The coach exam runner
`fleet-evals/runs/coach-heldout/coach-ft-v4-2026-07-25/run_coach_heldout.py` hard-codes three strings
into the `serving` block of every `config.json` it writes: line 205 `"lineage": "coach-ft-v3 …
LoRA -> GGUF"`, line 207 `"gguf": "/opt/llama-swap/models/coach-ft-v3/coach-gemma4-26b-moe-v3.Q4_K_M.gguf"`
and line 212 `"served_via": "llama-swap :9000 (on-demand; tutor-set baseline paused for the run)"`.
None of that is true of any vLLM run: nothing was served through llama-swap, no GGUF file was involved,
and the lineage is v4 not v3. The `model_id`, `quant`, `template` and `endpoint` fields in the same
block *are* filled from the command line and are correct — the S8 file reads
`"endpoint": "http://127.0.0.1:8011/v1/chat/completions"` and `"quant": "bf16-base+lora-v3"`. So the
grades and the replies stand; it is the provenance stamp beside them that lies, and it has lied in
every vLLM coach run this lane has made. **Anyone reading a coach `config.json` must ignore its
`gguf`, `served_via` and `lineage` fields and take provenance from the launch script and the server
log instead.** Fixing the runner is a small change and is listed under next steps.

---

## Planner

**What was checked.** That the planner adapter loads completely, and that it changes the base model's
answer. Both hold. Its 30 expert blocks all received weights (`lora-module-load-report.json`), and on
a fixed 609-token planning prompt it produced a different reply from the bare base model — md5
`8b02a3af3be856d950a20f7352207edd` against the base's `3eb6190236fc3c908345e6dbe30d6ba0`, 3,991
characters against 4,014 (`planner/planner-s8.json`, with both replies saved at
`planner/architect-plan-v2.txt` and `planner/gemma4-base.txt`). Both were sent at temperature 0 with a
1,024-token budget and thinking switched off, which is what production sends; both stopped only
because they hit that budget, which is a setting, not a fault. The prompt is
`~/fine-tuning/output/vllm-control2-2026-09-02/determinism-prompt.txt`, md5
`5e353ed0f12b87b86c91801f84597b54`.

**What was not checked.** Anything about quality. There is no planner exam runner and none was
written, so nothing here says the planner's plan is better than the base model's — only that it is
different. The planner adapter was served in S8 only; it was not part of S8b, so it has never been
run with the deterministic mode off, and given what that mode did to the product owner that gap
matters.

**One correction to an earlier draft.** A draft of this write-up said the planner "adds a failure mode
and named test case per section, which the base does not". That is false as written. Both replies do
it: the base reply carries four `Failure Mode:` lines each paired with a `Guard/Test:` line, and the
planner's carries six `Failure Mode:` lines each paired with a `Test Case:` line (counted directly in
`planner/gemma4-base.txt` and `planner/architect-plan-v2.txt`). It is a difference of count and label,
not of presence — and since neither reply is graded, it is not evidence of anything beyond the two
being different.

---

## Cache and memory

The **key-value cache** is the working memory a request needs while it is being answered; the more of
it, the more long requests can be in flight at once.

| Launch | Dial | Adapters resident | Weights loaded (GiB) | Cache (GiB) | Cache (tokens) | Full-length requests' worth | Machine memory left (GB) | Source |
|---|---|---|---|---|---|---|---|---|
| 2026-09-02 S4 (i) | 0.55 | 4 | 53.62 | 1.54 | 38,847 | 1.19× | not recorded | controls document |
| **S8, this work** | **0.65** | **4** | **53.62** | **13.94** | **351,628** | **10.73×** | **19** | `kv-lines-s8.txt`, `mem-settled-s8.txt`, `mem-s8.csv` |
| **S8b, this work** | **0.65** | **3** | **52.37** | **16.50** | **416,056** | **12.70×** | **20** | `kv-lines-s8b.txt`, `mem-settled-s8b.txt` |
| 2026-09-02 S4 (i) | 0.70 | 4 | 53.62 | 20.71 | 522,333 | 15.94× | 14 | controls document |
| 2026-09-02 S5 | 0.70 | 5 | 54.89 | 18.32 | 461,984 | 14.10× | 19 | controls document |

**The caveat that must travel with every one of those cache figures.** They are not a constant of the
configuration on this box. vLLM sizes the cache from whatever memory it finds free when it profiles
itself at start-up, and on a machine where the graphics processor and the main processor share one
pool that varies with whatever else is resident at that moment. The controls document records the
proof: the same merged weights, image, flags and dial reported 17.95 GiB of cache in one launch and
8.84 GiB in another. So read the S8 and S8b rows as one launch's reading each, and treat the
three-adapter row's extra 2.56 GiB as *probably* the fourth adapter's slot given back — the weights
figure did drop by 1.25 GiB, which is about one adapter — rather than as a measured effect of the
kernel mode.

**Reading the memory column.** These are settled values taken after the engine came up, not the trough
during weight loading. For S8 the settled figure is 19 GB available, sampled between 05:56:45Z and
05:57:35Z, every sample between 19.03 and 19.14 GiB (`mem-s8.csv`, 1,209 samples at five-second
intervals; `mem-settled-s8.txt`). For S8b it is 20 GB (`mem-settled-s8b.txt`, `mem-s8b.csv`, 285
samples). The trough during loading was 8,518,756 kB — about 8.1 GiB — at 05:52:04Z in S8 and
8,605,400 kB, about 8.2 GiB, at 07:44:31Z in S8b, both read directly from the sample files. That is
the documented transient the playbook describes, it recovered within about a minute, and neither
container was ever killed by the kernel for running out of memory (`OOMKilled=false` in
`inspect-s8.txt` and `inspect-s8b.json`).

**What 0.65 buys and what it still misses.** Against 0.55 with the same four adapters it turns 1.19
full-length requests' worth of cache into 10.73, so it recovers nearly all of what four resident
adapters cost at the lower dial. Against 0.70 it gives back 5 GB of machine memory (19 rather than 14).
It is still under the 25 GB machine-memory bar the earlier brief set. Startup on this dial took 305
seconds to load the weights and 87 seconds to build the cache in S8, and 312 and 69 seconds in S8b
(`kv-lines-s8.txt`, `kv-lines-s8b.txt`); S8's server first answered a request for its model list 510
seconds — eight and a half minutes — after launch (`s8-followup.json`).

---

## Slots at natural reply length

The controls' slot numbers were all taken with replies capped at a fixed length, which measures the
machine but not the work. This test used a 20,927-token prompt — the product-owner task's own prompt
padded once — with a 4,096-token budget, so replies could end when they were finished, at temperature
0, on the S8 server (dial 0.65, four adapters, four slots). Per-request rows are in
`slots-natural.csv`; the summary is `slots-natural-summary.json`; the script is `slots_natural.py`.

| Scenario | Adapter | Wall clock (s) | Completion tokens | Tokens per second | Ended how? |
|---|---|---|---|---|---|
| one alone | `po-v6` | 273.4 | 4,096 | 14.98 | ran out of budget |
| one alone | `po-v6` | 272.0 | 4,096 | 15.06 | ran out of budget |
| one alone | `po-v6` | 280.0 | 4,096 | 14.63 | ran out of budget |
| two at once | `po-v6` | 240.9 | 2,750 | 11.42 | stopped by itself |
| two at once | `po-v6` | 232.1 | 2,597 | 11.19 | stopped by itself |
| four at once | `po-v5` | 362.3 | 3,002 | 8.29 | stopped by itself |
| four at once | `po-v6` | 317.7 | 2,379 | 7.49 | stopped by itself |
| four at once | `coach-ft-v4` | 339.7 | 2,617 | 7.70 | stopped by itself |
| four at once | `architect-plan-v2` | 283.1 | 2,099 | 7.41 | stopped by itself |

Aggregate throughput: **15.0 tokens per second for one request, 22.6 across two (1.51×), 30.9 across
four (2.06×)**. So four adapters do share one process and one copy of the base model, and adding
callers buys real work: each of four requests runs at about half the speed of one alone rather than
queuing behind it. At 7.4 to 8.3 tokens per second each, though, this is a batch machine.

**Read the tokens-per-second column, not the wall clock.** The replies were different lengths, so the
wall-clock ratios (0.88× for two, 1.33× for four against the single median) compare unlike with unlike
and are recorded here only so nobody recomputes them by hand and believes them.

**And the awkward finding.** The three lone requests all ran to the 4,096-token cap; every batched
request stopped by itself, at 2,099 to 3,002 tokens. Same prompt, same adapter, temperature 0,
deterministic mode on. Whether a reply terminated depended on how many other requests were running.
This is the same runaway the product-owner exam showed and it is the second, independent sighting of
the deterministic mode failing to hold: it held for the sequential exam at 11,802 prompt tokens (three
byte-identical replies in S8) and did not hold here at 20,927. The controls already recorded that the
fused expert kernel sits outside the mode's guarantee when several requests arrive at once; this
extends the doubt to long prompts arriving one at a time.

---

## Estate touches

Every contact with a live service, stated plainly. Nothing was pushed, deployed, restarted or
reconfigured. No configuration file of any live service was edited. Nothing was sent to LiteLLM on
port 4000. No connection was made to NATS or port 4222 of any kind.

| Stage | Contact with the model switchboard (llama-swap, port 9000) | Recorded in |
|---|---|---|
| S8 | one call to `/unload` before graphics-processor work, reply OK; one read of the model list at restore, HTTP 200 | `unload-s8.txt`, `restore-s8.txt`, `restore-s8.json` |
| S8b | one read of the model list; one call to `/unload`, reply OK | `unload-s8b.txt` |

Those are the only two permitted interactions with the switchboard, and seats reload on demand after
an unload, which is the documented estate step. Free memory around the unloads, read from those files:
S8 went from 100 GB available to 111 after the unload; S8b from 102 to 112.

The build queue was checked before and after each stage with
`docker exec forge-prod forge --config /var/forge/forge.yaml status`, and passed every time — the word
BUILD present in the table header, five rows, none running, paused or queued
(`estate-gate-before-s8.txt`, `estate-gate-after-s8.txt`, `estate-gate-before-s8b.txt`,
`estate-gate-after-s8b.txt`; checked again for this write-up by searching all four files for RUNNING,
PAUSED and QUEUED — zero matches in each).

Both diagnostic containers were named `vllm-control`, ran on port 8011 only, were never started with
`--rm`, had their logs saved, and were removed by hand. Neither was killed by the kernel for running
out of memory: `inspect-s8.txt` records `OOMKilled=false ExitCode=0 Restarts=0`, and `inspect-s8b.json`
the same, together with all four of its mounts read-only. Free memory after the containers were
removed: 102 GB available after S8, 104 GB after S8b (`free-after-removal-s8.txt`,
`free-after-removal-s8b.txt`).

The product-owner specialist container was used as the exam harness's tool container, exactly as the
harness normally does; it was not reconfigured or restarted.

---

## Deviations

**The S8 container inspection was saved too thin.** For S8 the only saved inspection is a one-line
text file (`inspect-s8.txt`) recording that the container was not killed and exited cleanly. It does
not record the environment or the mounts. So the evidence that `VLLM_BATCH_INVARIANT` was set for S8,
and that the adapters were mounted read-only from `vllm-exports-v3`, rests on the launch script
(`launch-s8.sh`) and on the server's own log (`'VLLM_BATCH_INVARIANT': True` at
`compilation/backends.py:1111`, and all four adapter paths in the "non-default args" line, both in
`kv-lines-s8.txt`). Both of those hold, and they agree with each other. S8b did save the full
inspection (`inspect-s8b.json`), which independently confirms the environment, the read-only mounts
and the absence of `VLLM_BATCH_INVARIANT` for that stage. Recorded as a receipt defect on S8, not a
measurement defect.

**Every coach `config.json` carries untrue provenance strings.** Described in full in the Coach
section above: three hard-coded fields at lines 205, 207 and 212 of the exam runner claim a GGUF file
and llama-swap serving in runs that used neither. This affects every vLLM coach run this lane has
made, S5 and the July baseline comparison included, and is inherited rather than introduced here.

**A draft claim about the planner was wrong and is corrected above.** The base reply does carry
failure-mode-and-test pairs; the difference is four against six, and a label.

**A product-owner repetition was interrupted before it wrote anything.** A first attempt at S8
repetition 1 was killed by the operator's own ten-minute command limit before producing any file. Its
run directory was empty. It is not counted and not reported as a run; the three S8 repetitions of
record are the three that completed.

**S8b served three adapters, not four.** The planner was not needed to answer S8b's question, so it
was left out, which is why the S8b cache row is not directly comparable with the S8 one. It also means
the planner has never been served with the deterministic mode off.

**Never more than three repetitions of anything**, and no run directory that already existed was
written into; all five run directories used here are new.

**Not done, and worth naming.** No planner exam — none exists, and none was invented. No merged-weights
control was re-run on either of these servers; the merged numbers are quoted from the previous day's
`control-A.json`, which ran at dial 0.55 with no adapters. The v3 exports were not re-verified against
the merged weights in this work; the arithmetic check and the rename manifests were read, not
recomputed. No dial other than 0.65 was measured here. The product owner's runaway was diagnosed as
far as "the deterministic mode causes it" and no further — why that mode makes the expert-adapter path
loop is unknown. The parallel-slot test used the deterministic mode; it was not repeated with the mode
off. Nothing was committed except this document.

---

## What this does and does not license

**It licenses this.** Saying that the adapter path, once the converter's two defects are fixed, serves
the product owner and the coach at least as well as their own merged weights on the exams we have:
`po-v6` 17/16/16, `po-v5` 17/17/17 and the coach 6 of 6 runs and 15 of 15 checks, against merged
`po-v6` at 16/16/16 and merged coach at 6 of 6. It licenses striking the product-owner adapter's
"still unmeasured" status from the controls document — it has now been measured, twice, on two
adapters. It licenses saying that vLLM's deterministic-kernel mode is not safe to leave on for this
work: it caused a seventeen-minute runaway on the product owner that made three exam runs ungradable,
and it failed to hold reply length at long prompts. And it licenses the per-module load check as a
standing gate on every export, since it is what proves an adapter is actually switched on.

**It does not license moving any seat.** Moving a seat onto this path is not a measurement, it is a
deployment: it needs an entry in the model switchboard's configuration fronting a vLLM process, and it
needs Rich's word. Neither exists and neither was sought. Beyond that, the evidence itself is thin in
named ways: two exams, three repetitions each, one box, one or two launches per configuration, two of
the four seats graded at all. The planner has no exam and has never run with the deterministic mode
off. The dial that made these numbers leaves the machine 19 to 20 GB, under the 25 GB bar, so what
this costs on a box that is also building has not been answered. Turning the deterministic mode off is
what made the product owner work, and it also means two identical exam runs no longer give identical
replies — which is a real loss for trustworthy grading and has not been thought through. And the
slot numbers were taken with that same mode on, so they were taken in a configuration this work is
now recommending against.

---

## Next steps — options, not a plan

1. **Fix the coach exam runner's provenance stamp.** Three hard-coded strings write a false serving
   record into every `config.json`. Make them come from the command line like the fields beside them.
   A few minutes' work, and it stops every future coach receipt lying about how it was served.
2. **Re-run the parallel-slot test with the deterministic mode off.** Every slot number in this
   document was taken in the configuration the product-owner result argues against, and reply length
   was demonstrably unstable in it. Same script, one launch.
3. **Decide what to do about the deterministic mode.** It buys byte-identical repeat runs and costs
   a seat that finishes its answer. One option is to keep it for short-generation exams only and never
   in service; another is to drop it and accept that repeat runs vary, as they already do on the
   llama.cpp seat because of its prompt cache. This is a judgement, not a measurement.
4. **Give the planner an exam, or say out loud that it will not have one.** It is the only seat with
   no grading instrument at all, so "the planner works" cannot currently be said or denied.
5. **Find the dial the box can live with while it is building.** 0.65 leaves 19 to 20 GB against a
   25 GB bar. Testing 0.60 and 0.62 with four adapters, recording cache and settled memory, is half a
   day with no exam runs — and, given how much the cache figure varies between launches, it needs two
   or three launches per dial to mean anything.
6. **Make the export gate real.** Add the merged-difference comparison and the per-module load check
   to the converter's own verify step, so an adapter that is silently switched off cannot reach an
   exam again. Both are small scripts and both faults this lane found were invisible without them.
