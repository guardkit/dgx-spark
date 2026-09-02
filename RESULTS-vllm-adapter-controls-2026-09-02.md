# RESULTS: the adapter controls — why the fine-tuned adapters were serving badly, and what fixed it

**Box:** promaxgb10-41b1 (Dell Pro Max, GB10, aarch64, 121 GB of memory shared between the
graphics processor and the main processor).
**Date:** 2026-09-02, evening, seven stages run back to back.
**Related:** [`RESULTS-vllm-multi-adapter-slots-2026-09-02.md`](./RESULTS-vllm-multi-adapter-slots-2026-09-02.md)
(the lane run these controls were built to explain) and its addendum;
[`RUNBOOK-vllm-lora-adapter-serving-gb10.md`](./RUNBOOK-vllm-lora-adapter-serving-gb10.md).

Two words used throughout. An **adapter** is the small file of extra numbers a fine-tune produces;
it is applied on top of the big base model while the model is answering. **Merged weights** are the
opposite: the same extra numbers baked permanently into a full copy of the model, so nothing is
applied at run time. The question this whole lane has been asking is whether we can serve one big
base model with several adapters on top — one process, several specialist seats — instead of one
whole model per seat.

Every number below names the file it was read from. Nothing here is quoted from a terminal.

---

## Verdict

The converter that turns our fine-tuned adapters into the layout vLLM wants had two separate faults,
one on top of the other, and together they had been switching off most of every adapter we served.
The first was arithmetic: the converter split the trained numbers across the model's 128 expert
sub-networks the wrong way round, so what it wrote was noise. It was found by comparing the exported
adapter against the merged weights' own before-and-after difference — the exports scored 0.004 to 0.07
on a similarity scale where a true match scores about 0.80 to 0.94 — and fixed by writing the
numbers contiguously per expert instead of strided
(receipts `~/fine-tuning/output/vllm-exports-v2/converter-v2-verify.json` and `.txt`, the CORRECTION
block at the top of `~/fine-tuning/scripts/convert_moe_lora_to_per_expert.py`, with the faulty version
kept beside it as `convert_moe_lora_to_per_expert.py.v1-strided-B-2026-08-23`).
The second fault was a name: vLLM looks for expert adapter weights under the module path
`…layers.N.moe.experts.E.*`, our exports wrote `…layers.N.experts.E.*` without the `.moe.`, and vLLM
skipped them without a word — which is why fixing the arithmetic changed nothing at the server and
why the corrected export gave byte-identical answers to the broken one. Turned to the questions the
lane pre-registered: **the adapter path was measurably worse than the merged weights on the same
engine, and for the coach it is no longer worse once the names are right** — the coach served from
the renamed export scored 6 of 6 runs green (15 of 15 checks), the same as its own merged weights, on every rep of
both tasks (`s5-batchinvariant.json`), where the same numbers under the old names scored 0 of 6;
the product-owner adapter has never been served with its expert half loaded, so its gap is still
open. **The product owner's slip is not the adapter's fault at all**: the merged product-owner
weights under the same vLLM image score 16 of 17 three times over, where the adapter's runs were 16, 11 and 17 (old export) and could-not-be-graded, 16, 16 (corrected packing), so the adapter is no worse than its merged weights on the runs that could be graded, and the one check
they fail — a missing Integration section — appears only where today's prompt and vLLM meet
(`s3-po-2x2.json`); the 17 of 17 it was being measured against was a single August run that does not
reproduce — re-run today with the same prompt bytes on the switchboard seat (August used a hand-started server, see below), one of the three runs could not
be graded at all and the other two scored 16 of 17. **The coach's vague findings — bare field names like `plan_audit.variances[0].detail` instead
of the sentence naming the actual defect — came from the broken export and nothing else**: with the
expert weights actually loaded it writes the specific sentence every time. **The non-repeatability is
fixed** by vLLM's deterministic-kernel mode (`VLLM_BATCH_INVARIANT=1`): every adapter that gave two or
three different answers to the same question at temperature 0 now gives one, sequentially and when
three requests are fired at once — the single exception being the renamed coach export, whose expert
kernels are the only ones actually running, where one of three simultaneous calls still differed.
It costs about a third more compute per token generated (0.0625 seconds per token against 0.0483 on
the same path without it), Running the expert adapters for real does not add cost per token: per completion token the renamed export is
cheaper than the old one under the same mode (0.0626 against 0.0691 seconds); its bundles take longer in
wall clock because its replies are longer (a mean of 53.9 completion tokens against 33.8), and the extra
tokens are the evidence it now cites. **Four resident adapters added about 5 GiB to what the server
loaded (48.54 GiB to 53.62 GiB) and, at the 0.55 dial, cost 16.4 GiB of the working cache (17.95 GiB
down to 1.54 GiB) — and you buy that back with the memory dial, not by dropping adapters**: turning
the dial to 0.70 with the same four adapters took the cache from 1.54 GiB, which is 1.19 requests'
worth of full-length context, to 20.71 GiB and 15.94 requests' worth (`s4-cache-slots.json`). But 0.70 leaves the box only 14 GB of memory for everything
else, so on a machine that also runs the workhorse the practical dial is somewhere around 0.62 to
0.65, and that has not been measured.

---

## What was run

Seven stages, run back to back on 2026-09-02, each by a builder with an independent reviewing agent
re-grading its receipts. Stages S1 to S5 made measurements; S6 is this document; S7 records the
result in the plan of record.

| Stage | What it did | Main receipt |
|---|---|---|
| S1 | Merged the coach adapter into the base model, so the coach could be tested without any adapter at run time | `~/fine-tuning/output/vllm-control2-2026-09-02/s1-merge.json` |
| S2 | Served those merged coach weights under vLLM with no adapter, and re-ran the coach exam | `.../s2-merged-coach.json` |
| S3 | Completed the product-owner grid: August's prompt against today's, crossed with vLLM against the live llama.cpp seat | `.../s3-po-2x2.json` |
| S4 | Measured what adapters cost in cache and in parallel slots at full prompt length, and re-ran both exams on the arithmetic-corrected exports | `.../s4-cache-slots.json` |
| S5 | Turned on vLLM's deterministic-kernel mode, and served a renamed export to test the module-name theory | `.../s5-batchinvariant.json` |
| S6 | This write-up | this file |
| S7 | The plan-of-record entry | — |

**Image, base model and snapshot.** Every vLLM stage used `vllm/vllm-openai:v0.25.0-aarch64-cu129`,
serving the base model `unsloth/gemma-4-26b-a4b-it`, snapshot
`60941ad6341d0b7af91277ff25c4175f08b56819`, mounted read-only from the host cache. The image ships a
`torchcodec` built for the wrong CUDA version, which stops vLLM at import, so every container's start
command begins `rm -rf /usr/local/lib/python3.12/dist-packages/torchcodec* && exec vllm serve …`.
That is a workaround for a packaging fault in the image, not a change to how adapters are served.
All diagnostic work ran in a container named `vllm-control` on port 8011 only.

**Serve flags, per launch, copied from each server's own "non-default args" line.**

| Launch | Model served | Adapters | Distinctive flags | Log |
|---|---|---|---|---|
| S2 | merged coach weights, `coach-ft-v4-merged` | none (`--enable-lora` not passed) | dial 0.55 | `launch-s2.log` |
| S3 cell A | merged product-owner v6 weights, `po-v6-merged` | none | dial 0.55 | `launchA.log` |
| S4 (i) | base, `gemma4-base` | four, arithmetic-corrected | dial 0.70, `--max-loras 4 --max-cpu-loras 8` | `launch-s4i.log` |
| S4 (ii) | base, `gemma4-base` | same four | dial 0.70, `--max-loras 2 --max-cpu-loras 4` | `launch-s4ii.log` |
| S5 | base, `gemma4-base` | the same four plus the renamed coach export | dial 0.70, `--max-loras 5 --max-cpu-loras 10`, `VLLM_BATCH_INVARIANT=1`, `VLLM_LOGGING_LEVEL=DEBUG` | `launch-s5.log` |

Common to all of them: `--reasoning-parser gemma4 --max-model-len 32768 --max-num-seqs 4
--no-enable-prefix-caching --limit-mm-per-prompt '{"image":0}'`, and where adapters were served,
`--enable-lora --max-lora-rank 16`. Each server's own log confirms `limit_mm_per_prompt: {'image': 0}`.

**Adapters and where they were mounted from.** In S4 and S5 the four arithmetic-corrected exports
came from `~/fine-tuning/output/vllm-exports-v2/{po-gemma4-v5, po-gemma4-v6,
coach-gemma4-26b-moe-v4, architect-plan-v2}`, and in S5 the renamed coach export came from
`~/fine-tuning/output/vllm-exports-v3/coach-gemma4-26b-moe-v4`. Those source paths are read from the
launch scripts `launch-s4.sh` and `launch-s5.sh`, not from the server log — vLLM records only the
in-container paths (`/adapters/po-v5` and so on), so the mapping back to the host directory is
corroborated from the scripts.

**The merge recipe (S1).** The merge block of `~/fine-tuning/scripts/run_po_export.sh`, unchanged
except for the container name (`coach-merge`), no `--rm`, and the coach's own adapter and output
paths. Container image `nvcr.io/nvidia/pytorch:25.11-py3`, sequence length 22,528 (the value the
product-owner v6 export used; it does not change the merged weights). It ran 897 seconds — 14 minutes
57 seconds — and exited 0. The merge is real, and was checked twice: the sampled check reports 12
tensors checked, 0 identical to the base, 12 merged
(`~/fine-tuning/output/coach-gemma4-26b-moe-v4/merged-16bit/merge-applied-check.json`), and the
exhaustive check reports 265 modules checked, 265 merged, 0 identical and 0 unresolved
(`.../vllm-control2-2026-09-02/coach-merge-exhaustive-check.json`). The merged directory is ten files totalling 51,644,301,065 bytes, of which the two weight files are 51,612,009,916 (`s1-merge.json`).

---

## The adapter path's two defects, in series

### Defect one — the converter packed the experts wrong

This model routes each token through 128 small expert sub-networks per layer, and our training tool
(Unsloth via PEFT) stores the trained adapter as one packed block per layer rather than one per
expert. The converter's job is to unpack that block into the 128 per-expert pieces vLLM wants.

The v1 converter took the "B" factor of each expert by striding through the packed block
(`lb[:, e::num_experts]`). That was wrong. It was found by a test that had not been applied before:
compare each exported expert against the *merged* weights' own before-and-after difference — that is,
against merged-minus-base, which is the ground truth for what the adapter should do. The attention
projections calibrate the test, because they need no repacking at all and so show what a true match
scores under the merged file's rounding: 0.8029 to 0.9385 on a cosine similarity (a measure of how alike two sets of numbers are: 1.0 identical, 0 unrelated) scale
(`converter-v2-verify.json`, `control_attention_q_proj_cos`). Against that, the v1 export scored
**0.0378 and 0.0681** on the coach's layer 0 expert 0, with the best other expert at 0.002 — the
right magnitude of noise everywhere. The v2 converter takes each expert's B factor contiguously
(`lb[:, e*r:(e+1)*r]`) and scores **0.8274 / 0.8714** on that same check, and 0.9138 / 0.9183 on
layer 15 expert 5, 0.8468 / 0.8777 on the product owner's layer 0 expert 0, and 0.9769 / 0.9398 on
its layer 29 expert 64 — the same band as the calibration.

Swept across whole layers rather than sampled experts (`converter-v2-verify.txt`): coach layer 0,
**126 of 128** experts score above 0.5; coach layer 29, **109 of 128**. Of the 19 that do not, 17 have a merged difference below 0.001, which is at the merged file's own rounding floor — too small for the instrument to see — and two (non-tiny) are unexplained by any receipt. Layer 29 expert 127 is the clearest case — its merged
difference is 4.4e-4 against a reconstruction of 1.2e-3, so the cosine of 0.278 is measuring rounding
error. **The merge itself loses the tiniest per-expert differences**, so an expert whose trained
change is that small cannot be verified this way at all; the check confirms the converter on every
expert whose trained change is large enough to see. The magnitudes also agree: the reconstruction is
within about 3% of the merged difference on every expert with a meaningful change, which confirms the
adapter's scaling factor is 1.0.

The v1 exports are kept untouched as evidence at `~/fine-tuning/output/<run>/lora-adapter-vllm`.

### Defect two — the module name vLLM actually looks under

Fixing the arithmetic changed nothing at the server. In S4, the corrected coach export produced the
same grades, the same failing check and the same vague findings as the old one — and comparing the
two runs' raw replies, **seven, six and seven of the eight bundles across the three reps have exactly the same answer text in both**
(run directories `fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-temp0-2026-09-02` and
`.../coach-ft-v4-vllm-adapterv2-temp0-2026-09-02`, noted in `s5-batchinvariant.json`). State it
plainly: **for four of the five adapters, the expert half of the adapter was never reaching the
model, so correcting the numbers in it could not possibly change an answer.**

The reason is a name. vLLM v0.25.0 builds the key it expects for a per-expert adapter from the
module's real path in the model, which for Gemma 4 is `…layers.N.moe.experts.E.{gate_proj, up_proj,
down_proj}`. Our exports wrote `…layers.N.experts.E.*` with no `.moe.`. vLLM finds nothing, skips the
module without printing a warning, resets it to zero, and serves the attention adapters only. The
image even contains a repair for exactly this — `_remap_gemma4_expert_weight_name` at `gemma4.py`
line 89 inserts the missing `.moe.` — but it is called only from the base model's weight loader, never
from the adapter loader. The converter's CORRECTION 2 block records this, and v3 writes the `.moe.`
path by default with `--legacy-expert-path` to reproduce the old names.

S5 is the runtime proof, and it is the server's own words. With debug logging on, vLLM reports per
adapter and per layer whether each module got weights or was reset. Read back into
`lora-module-load-report.json`:

| Adapter served | Export | Expert blocks with weights | Expert blocks reset to zero |
|---|---|---|---|
| `po-v5` | v2 | 0 of 30 | 30 |
| `po-v6` | v2 | 0 of 30 | 30 |
| `coach-ft-v4` | v2 | 0 of 30 | 30 |
| `architect-plan-v2` | v2 | 0 of 30 | 30 |
| `coach-ft-v4-moe` | **v3, renamed** | **30 of 30** | **0** |

The renamed exports are at `~/fine-tuning/output/vllm-exports-v3/<run>`, each carrying a
`rename-v3.json` recording 23,040 of 23,450 keys renamed by the rule
`.layers.N.experts.E. → .layers.N.moe.experts.E.`. The v2 and v3 files contain the same numbers;
only the labels differ.

**And the rename works.** Reported exactly as measured: the coach served from the v3 export scored
**6 of 6 runs green** — escape-kin `2 passed, 2 deselected` on each of three reps, catch-and-green
`3 passed, 3 deselected` on each of three reps — where the same numbers under the v2 names scored
0 of 6 on the same server in the same launch (`s5-batchinvariant.json`, run directories
`fleet-evals/runs/coach-heldout/coach-ft-v4-moe-vllm-batchinvariant-temp0-2026-09-02` and
`.../coach-ft-v4-vllm-batchinvariant-temp0-2026-09-02`).

---

## The coach: merged weights, the old adapter, the fixed adapter, the renamed adapter, and July

The coach exam is two held-out bundles, three reps each, six runs in all. A run is green only if
every check in the frozen battery passes.

| Configuration | Green | What its findings looked like | Files |
|---|---|---|---|
| Merged Q8_0 (the 8-bit quantised form the switchboard seat serves) weights under llama.cpp, 25 July baseline | **6 of 6** | specific: `plan_audit.variances: tests/conftest.py injects a fake gateway…` | `fleet-evals/runs/coach-heldout/coach-ft-v4-2026-07-25/`; re-graded live on 2026-09-02 (`001: 2 passed, 2 deselected` ×3; `002: 3 passed, 3 deselected` ×3) |
| Merged bf16 (16-bit floating point, the precision the merged weights are stored in) weights under vLLM, no adapter (S2) | **6 of 6** | specific, and byte-identical across all three reps | `fleet-evals/runs/coach-heldout/coach-ft-v4-merged-vllm-temp0-2026-09-02/`; `s2-merged-coach.json` |
| Old v1 adapter under vLLM, temperature 0 | 0 of 6 | bare field names: `bdd.pending[0]`, `plan_audit.variances[0].detail`, `independent_tests.stdout_tail`, `honesty.claims` | `fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-temp0-2026-09-02/`; `~/fine-tuning/output/vllm-control-2026-09-02/control-B.json` |
| Arithmetic-corrected v2 adapter under vLLM (S4) | 0 of 6 | the same bare field names | `fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-adapterv2-temp0-2026-09-02/`; `s4-cache-slots.json` |
| v2 adapter with deterministic kernels on (S5) | 0 of 6 | the same bare field names, now identical across reps | `fleet-evals/runs/coach-heldout/coach-ft-v4-vllm-batchinvariant-temp0-2026-09-02/`; `s5-batchinvariant.json` |
| **v3 renamed adapter, deterministic kernels on (S5)** | **6 of 6** | specific, e.g. `plan_audit.variances: tests/conftest.py injects a fake gateway into sys.modules before collection… the claimed 'gateway path' green is a manufactured signal on a stubbed module` | `fleet-evals/runs/coach-heldout/coach-ft-v4-moe-vllm-batchinvariant-temp0-2026-09-02/`; `s5-batchinvariant.json` |

S2 is what made the diagnosis possible: the merged coach, on the engine that was under suspicion,
gave July's answer — 6 of 6, specific findings, three byte-identical replies. That ruled out vLLM
itself and ruled out bf16-against-Q8_0 numbers, and pointed at the run-time adapter path. S5 then
found which part of that path.

The renamed adapter's verdicts match the merged model's on every bundle: reject on all four
escape-kin bundles, reject the two dishonest catch-and-green bundles, approve the two honest ones,
identical across all three reps, no verdict flipped. It is not word-for-word the merged model — it
names two call sites where the merged one named none — but it is the same judgement and the same
quality of evidence (`s5-batchinvariant.json`).

---

## The product owner: prompt against engine, and the adapter variants

The exam is `po-held-007-feature-spec`, 17 checks, three reps, temperature 0. Two prompts are in
play: August's (hash beginning `6e4d3014`) and today's (`14969fec`), which differs by exactly twelve
added lines about an optional `endpoint` field, and nothing else
(`old-vs-live-prompt.diff`, `old-prompt-sha256.txt`). Every rep's prompt hash was read from that
rep's own `config.json`, not from the command line.

### The grid: which prompt, which engine

|  | August's prompt (`6e4d3014`) | Today's prompt (`14969fec`) |
|---|---|---|
| **vLLM, merged product-owner weights** | 16, 16, 16 of 17. Integration section **present**. Three byte-identical replies. (S3 cell A) | 16, 16, 16 of 17. Integration section **absent**. Three byte-identical replies. (S3 cell D, measured earlier the same day) |
| **The live llama.cpp seat `po-ft-v6`** | today: one run could not be graded, then 16 and 16 of 17. Integration section present. (S3 cell C) — August, one rep: 17 of 17 | **17, 17, 17 of 17.** Integration section present. (S3 cell B) |

Files, in the same order: `fleet-evals/runs/po-heldout-spec/20260902-control-po-v6-merged-vllm-oldprompt/`;
`.../20260902T145434Z-po-v6-merged/`, `...T145647Z-`, `...T145857Z-` plus
`~/fine-tuning/output/vllm-control-2026-09-02/control-A.json`;
`.../20260902-control-po-ft-v6-llamaswap-oldprompt/`; `.../20260823T221337Z-po-ft-v6/`;
`.../20260902-control-po-ft-v6-llamaswap-todayprompt/`.

Two readings come out of that grid.

**The missing Integration section is an interaction, not a fault in either half.** It is present in
three of the four cells and missing only where today's prompt and vLLM meet. The live llama.cpp seat
writes the section with either prompt; vLLM writes it with August's prompt and drops it with today's.
So the twelve extra lines push the section out of the answer only under vLLM. That is a prompt and
engine matter, and it is not evidence about adapters at all.

**The 17 of 17 baseline does not reproduce, and should not be quoted again.** Re-running the
August cell today — the same prompt bytes and greedy settings, on the switchboard seat rather than August's hand-started server — gave three replies, none of
which matches August's (md5 `8171ce00e54f37e7747b165eba70587a`), and two grades of 16 out of 17.
Correcting the builder here, who reported the third as "10 of 17": **that run could not be graded.**
Its digest file was not valid YAML, the production post-processor refused to run, three checks
measured nothing (they were skipped), three failed and ten passed. It is recorded as not a pass, not
as a score. The same class of slip happened to a vLLM adapter rep the same day, so it is not specific
to one engine.

Also correcting the builder on the August comparison. It was **not** "the same seat, same engine".
The 2026-08-23 run that scored 17 of 17 talked to `http://127.0.0.1:9310/v1`, and port 9310 is not a
switchboard port — the switchboard's own configuration starts at 5800, and
`~/fine-tuning/scripts/serve_po_v4.sh` says in as many words that it serves "on a SCRATCH port for
grading — deliberately NOT through llama-swap". The honest wording is: **the same weights file, very
probably, served by llama.cpp both times — a hand-started server in August, the switchboard seat
today; the launch flags may differ and were not recovered for August.** "Very probably" because the
two copies of the weights file were compared at nine sampled one-megabyte windows and matched, and
are the same size (26,859,860,864 bytes), but they were not compared in full.

### The product-owner adapter variants, against those cells

| Configuration | Reps, read from each `grade.txt` | Repeatable? | Files |
|---|---|---|---|
| Merged weights under vLLM, today's prompt | 16, 16, 16 | yes, three byte-identical replies (md5 `acd351b2…`) | `control-A.json` |
| Old v1 adapter under vLLM (the lane run) | 16, 11, 17 | no | `fleet-evals/runs/po-heldout-spec/20260902T13{2752,2932,3123}Z-po-v6/` |
| Arithmetic-corrected v2 adapter (S4) | could not be graded, 16, 16 | no — three different replies at temperature 0 (`po-adapterv2-md5.txt`) | `.../20260902-control-po-v6-adapterv2/`; `s4-cache-slots.json` |
| Corrected v2 adapter, deterministic kernels on (S5) | could not be graded, three times | yes — all three md5 `1ca83a3b…` | `.../20260902-control-po-v6-adapter-batchinvariant/`; `s5-batchinvariant.json` |

The reps that could not be graded are the same failure mode as cell C rep 1: the reply's digest was not valid YAML,
production's post-processor refused it, the harness fell back to its simpler slicer, and three checks
were left unmeasured. A skipped check measures nothing, so 11 of 17 overstates rather than understates
the gap.

The plain reading: pinning the adapter to one answer did not improve the answer, it just stopped it
varying, and the answer it settled on is the weak one. And **every one of these product-owner adapter
runs was made with the adapter's expert half switched off** — the naming defect above applies to all
of them. Whether the product-owner adapter is actually worse than its merged weights is therefore
still unknown; it has never been served intact.

---

## Repeatability

Three identical calls at temperature 0, then three fired at the same moment, on a fixed 609-token
prompt (`determinism-prompt.txt`). "Distinct answers" counts different replies to the same question.

| Model served | Distinct answers before, 3 calls (2026-09-02 lane run) | Sequential, deterministic kernels on | Three at once, deterministic kernels on |
|---|---|---|---|
| `gemma4-base` (no adapter) | 1 — already repeatable | 1 | 1 |
| `po-v5` | 3 | 1 | 1 |
| `po-v6` | 2 | 1 | 1 |
| `coach-ft-v4` | 3 | 1 | 1 |
| `architect-plan-v2` | 3 | 1 | 1 |
| `coach-ft-v4-moe` (renamed, expert kernels live) | did not exist | 1 | **2** |

Before: `~/fine-tuning/output/vllm-multi-2026-09-02/determinism-by-model.json`.
After: `~/fine-tuning/output/vllm-control2-2026-09-02/determinism-batchinvariant.json`.

What the mode changes, read from the image itself
(`/usr/local/lib/python3.12/dist-packages/vllm/lora/ops/triton_ops/utils.py`): the adapter's first
matrix multiply normally splits its sum into 64 pieces computed in parallel and added together, and
floating-point addition is not exactly associative, so the order they happen to finish in changes the
last bits. With the flag on, that split is set to 1 — one piece, one order, the same answer every
time. The mode also replaces some of PyTorch's own kernels; the server printed warnings that this is
experimental, and no line said the mode was refused or only partly applied.

The one hole: the renamed coach export, the only adapter whose expert kernels actually run, repeats
itself when called one at a time but gave a different answer on one of three simultaneous calls. The
fused expert adapter kernel is outside the guarantee in this release. On the exams it did not matter,
because the exams send one request at a time.

**What it costs.** Product-owner reps, wall clock from each rep's `config.json`: 135.8 / 137.6 / 137.3
seconds with the mode on, against 112.1 / 100.8 / 114.2 on the same adapter path without it, and
132.7 / 128.8 / 128.6 for the merged weights. Because the replies are different lengths the fairer
number is per token generated: **0.0625 seconds with the mode, 0.0483 without, 0.0467 for merged
weights** — so the mode costs about 1.29 times the compute per token, and the adapter path with it
runs at about 1.34 times the merged weights' cost per token. Actually running the expert adapters does not cost more per token: on the renamed export a coach bundle
took 3.37 seconds against 2.33 on the v2 export in the same launch, but per completion token the renamed export
is the cheaper of the two (0.0626 against 0.0691 seconds, from the same `per_bundle` usage records) — its replies
are longer (a mean of 53.9 tokens against 33.8) because they now name the evidence. The mode itself made the v2
bundle 1.25 times S4's 1.87 seconds (`s5-batchinvariant.json`).

---

## Cache and slots

The **key-value cache** is the working memory a request needs while it is being answered; the more of
it, the more long requests can be in flight at once. `--gpu-memory-utilization` (called "the dial"
below) is what tells vLLM how much of the machine's memory to claim.

| Dial | Adapters resident | `--max-loras` | Weights loaded (GiB) | Cache (GiB) | Cache (tokens) | Full-length requests' worth | Memory left for the rest of the box (GB) | Source |
|---|---|---|---|---|---|---|---|---|
| 0.55 | 0 (merged product-owner weights) | — | 48.54 | 17.95 | 452,549 | 13.81× | 28 | `vllm-control-2026-09-02/launchA.log`, `memA-serve.txt` |
| 0.55 | 0 (merged coach weights, S2) | — | 48.54 | 7.22 | 182,155 | 5.56× | 41 | `launch-s2.log`, `s2-merged-coach.json` |
| 0.55 | 2 (v1 exports) | 2 | 51.04 | 14.97 | 377,532 | 11.52× | not recorded | `vllm-control-2026-09-02/launchB.log` |
| 0.55 | 4 (v1 exports) | 4 | 53.62 | 1.54 | 38,847 | 1.19× | not recorded | `RESULTS-vllm-multi-adapter-slots-2026-09-02.md`, lines 86–87 and 216 |
| 0.70 | 4 (v2 exports) | 4 | 53.62 | 20.71 | 522,333 | 15.94× | **14** | `launch-s4i.log`, `mem-s4i-serve.txt` |
| 0.70 | 4 (v2 exports) | 2 | 51.04 | 32.23 | 812,674 | 24.80× | **7** | `launch-s4ii.log`, `mem-s4ii-serve.txt` |
| 0.70 | 5 (four v2 plus the renamed coach) | 5 | 54.89 | 18.32 | 461,984 | 14.10× | **19** | `launch-s5.log`, `mem-s5-serve.txt` |

*Note on the S2 row, and on the cache budget itself:* the merged coach at the same 0.55 dial reported far less cache (7.22 GiB) than the merged product-owner run's 17.95 GiB, and the S3 cell A launch — the SAME merged product-owner weights, image, flags and dial as that 17.95 GiB run — reported 8.84 GiB, 223,034 tokens and 6.81 requests' worth (`launchA.log` in `vllm-control2-2026-09-02`, lines 60–63; also in `s3-po-2x2.json` under cell A). So the cache figure at a given dial is not a constant of the configuration on this box: vLLM sizes the cache from the memory it finds free when it profiles, and on unified memory that varies with what else is resident at that moment. Treat every cache figure here as one launch's reading, and read the dial's effect from launches made minutes apart under the same conditions (the 0.55-to-0.70 comparison with four adapters was).

**How to read the memory column, and one correction to the S4 write-up.** Those "memory left" figures
are the settled values, taken 70 to 90 seconds after the engine came up, not the trough during weight
loading (the trough is a transient the playbook already describes). At the 0.70 dial the box is left
with 14 GB free with four adapter slots and 7 GB with two — against 28 GB at the 0.55 dial with no
adapters, and against the 25 GB bar this work was briefed to hold. **0.70 is too high a dial for a
box that also runs the workhorse.** The practical dial is somewhere around 0.62 to 0.65, and that
was not measured — no dial between 0.55 and 0.70 was tested at all.

**What the adapters cost, and how to buy it back.** The 1.19-requests'-worth figure from the lane run
was a dial problem, not an adapter problem: the same four adapters at 0.70 give 15.94 requests' worth.
Halving how many adapters may be in one batch bought a further 11.5 GiB of cache, about 2.6 GiB of
which is the two fewer adapter copies held on the graphics processor and the rest their working
buffers. So: fewer adapters per batch, or a higher dial, both buy cache back — but the dial takes it
from the same pot as everything else on the machine.

**Parallel slots at real prompt length.** Prompt of 20,927 tokens, asking for 256 tokens back, at the
0.70 dial with four adapters and four slots: one request alone took a median 19.52 s; two at once
took 29.28 s (**1.50×**); four at once, one per adapter, took at worst 50.55 s (**2.59×**). With only
two adapter slots, four at once behaved exactly as expected — two ran, two were deferred, and the
slowest finished at 58.21 s (**2.99×**). Files `slots-realctx-summary.json`,
`slots-realctx-launchii-summary.json`.

Two things must travel with those ratios. First, **every one of those replies stopped at the 256-token
cap** (`finish_reason: length`), so these are wall-time ratios for fixed-length generation, not for
natural, variable-length replies. Second, **the queue is not the cache, it is the compute.** The
server's own scheduler lines show `Running: 1 reqs, Waiting: 3 reqs` as the burst was admitted one
prefill at a time, while peak cache use during that burst was 11.6% of 522,333 tokens — about 61,000
tokens for four 21,000-token requests. The cache had room. Reading a 21,000-token prompt costs about
ten seconds at roughly 2,092 tokens per second, and the server does those one at a time. No adapter
setting changes that. Against the lane run's 1.17× for two short requests, the honest figure for real
work is about one and a half requests' worth of throughput for two callers and two and a half for
four.

One more correction to the S4 write-up: the base model id was never called in S4 — only the four
adapters were — so nothing in that stage licenses a claim that five model names were served and
answered. S5's launch does advertise five adapter names, and its debug log accounts for all five.

---

## Estate touches

Every contact with a live service, stated plainly. Nothing was pushed, deployed, restarted or
reconfigured. Nothing was sent to LiteLLM on port 4000. No connection was ever made to NATS or port
4222. No configuration file of any live service was edited.

| Stage | Contact with the model switchboard (llama-swap, port 9000) | Recorded in |
|---|---|---|
| S1 | one read of the model list; one call to `/unload` to release loaded seats before graphics-processor work (reply OK) | `mem-s1-before.txt`, `s1-merge.json` |
| S2 | one call to `/unload` (reply OK); one read of the model list at restore | `llama-swap-unload-s2.txt`, `restore-s2.txt` |
| S3 | one read of the model list before the work; one call to `/unload`; **six exam requests** to `http://127.0.0.1:9000/v1` for model id `po-ft-v6` (three for cell B, three for cell C); one read of the model list at the end | `llamaswap-models-before-s3a.json`, `cellB-rep{1,2,3}.log`, `cellC-rep{1,2,3}.log` |
| S4 | one call to `/unload` (reply OK); one read of the model list after restore | `unload-s4i.txt` |
| S5 | one call to `/unload` (reply OK); one read of the model list after restore (HTTP 200) | `unload-s5.txt`, `restore-s5.txt` |

S3 made **nine exam requests in all: six to the switchboard on port 9000** (three for cell B, three
for cell C) and three to the diagnostic container on port 8011 (cell A). The S3 receipt originally
said eighteen requests to the switchboard; that overstated it, and the count above is the corrected
one. Seats reload on demand after an unload, which is the documented estate step.

The build queue was checked before and after every stage that touched the graphics processor, using
`docker exec forge-prod forge --config /var/forge/forge.yaml status`. It passed every time — the word
BUILD present in the table, five rows, none running, paused or queued. Files:
`estate-gate-after-s1.txt`, `estate-gate-before-s2.txt`, `estate-gate-after-s2.txt`,
`estate-gate-s3-before.txt`, `estate-gate-s3-after.txt`, `estate-gate-before-s4.txt`,
`estate-gate-mid-s4.txt`, `estate-gate-after-s4.txt`, `estate-gate-before-s5.txt`,
`estate-gate-after-s5.txt`, `estate-gate-final-s5.txt`.

Every diagnostic container was named (`vllm-control` or `coach-merge`), never started with `--rm`,
had its log saved, and was removed by hand. None was killed by the kernel for running out of memory
(`OOMKilled=false` in every `docker inspect`).

---

## Deviations

**The first coach merge was killed by our own watchdog, wrongly.** Twelve minutes in, during the
write of the first 49.9 GB file, available memory dipped to 6 GB for about ten seconds and the export
script's default 8 GB watchdog killed the container. The kernel's own out-of-memory killer never
fired, so the dip was the transient the playbook describes, not a real shortage. The attempt was
discarded — it left both weight files but no merge-applied check, and structurally complete is not
semantically merged — and everything from it was saved
(`coach-merge-attempt1-state.txt`, `coach-merge-attempt1-container.log`, `coach-merge-attempt1.log`,
`coach-merge-mem-trace-attempt1.txt`, `coach-merge-attempt1-merged-listing.txt`). The second attempt
lowered the watchdog to 4 GB and completed; its trough was 6.5 GB and the watchdog did not fire.

**S3's reviewing agent blocked, and the coordinator overrode the block.** The reviewer reproduced all
nine grades and every checksum, prompt hash, token count and temperature, and found the fences clean.
Its three objections were about how the builder *described* the results, not about any measurement:
the August comparison was not the same server, cell C rep 1 could not be graded rather than scoring
10 of 17, and the request count to the switchboard was overstated. All three corrections are carried
in this document and the measurements stand, so the coordinator overrode the block and the lane
continued; stages S4 to S7 kept their stop-on-fail rule. The adjudication is written down in
`~/fine-tuning/output/vllm-control2-2026-09-02/S3-COACH-BLOCKER-adjudication-2026-09-02.txt`.

**The reviewer's under-claim, which the builder had missed.** The first-rep difference on the
llama.cpp seat is explained by the server's prompt cache, and the receipts say so themselves: the
number of cached prompt tokens each request reported
(`usage.prompt_tokens_details.cached_tokens`) was 0 on cell B rep 1 and 11,794 on reps 2 and 3, and
1,770 on cell C rep 1 against 11,571 on reps 2 and 3. Decoding with a cached prefix changes the
numbers enough to change the reply. The vLLM cells record no cached tokens at all, because prefix
caching was switched off there. So greedy decoding is not repeatable on the llama.cpp seat either —
the finding is not vLLM's alone.

**S4's reviewing agent did not block but made four corrections**, all carried above: the memory
figures are settled values rather than troughs and 0.70 is too high a dial; the slot ratios are for
fixed 256-token replies; the base model was not exercised in S4; and the adapter source paths come
from the launch script rather than the server log.

**The repeatability probe kept hashes, not replies.** The S5 determinism script hashed each of the 36 replies and
discarded the text, although the brief asked for the replies to be saved. The distinct-answer counts stand (the
reviewer recomputed them from the recorded hashes), but the one divergent reply — the renamed coach export's odd
answer out of three simultaneous calls — cannot be inspected by anyone. A receipt defect, recorded as one.

**Renamed exports exist for all four adapters, but only the coach's was served.** The directories
`vllm-exports-v3/{po-gemma4-v5, po-gemma4-v6, architect-plan-v2}` each carry a `rename-v3.json`
recording the same 23,040-key rename, and three further diagnostic exports
(`diag-coach-attn-only`, `diag-coach-experts-only`, `diag-coach-experts-only-v2names`) exist with a
`diag.json` describing an identity test. None of those six was served or graded in any stage covered
by these receipts.

**Not done, and worth naming.** No dial between 0.55 and 0.70 was tested. The renamed coach export
was never run with the deterministic mode off, so this work cannot say on its own whether its 6 of 6
needs that mode — the indirect evidence is that the v2 export scored 0 of 6 both with the mode off
and with it on, so the mode is not what changed the score. No merged product-owner or merged coach run
was repeated on the S4 or S5 servers; those merged numbers are quoted from S2 and from yesterday's
control. The July baseline was read and quoted, not re-run. No fourth rep was taken anywhere. No
product-owner or planner adapter was ever served with its expert half loaded.

---

## What this does and does not license

**It licenses this.** The converter is now correct on both counts and there is a test that would have
caught either fault — compare the export against the merged weights' own difference, and read the
server's debug log for "successfully loaded" against "skipping" per module. That test should be a
gate on every future export, because both faults were silent: vLLM started, advertised the adapter,
answered every request, and served an adapter that was mostly switched off. It also licenses striking
the 17 of 17 product-owner baseline from every comparison table: it was one run, on a hand-started
server, with a prompt that no longer exists, and it does not reproduce. And it licenses saying that
the coach's failure since 25 July was an export defect, not a fine-tune defect, not temperature, not
llama.cpp against vLLM.

**It does not license moving any seat.** The renamed coach adapter has been graded on two held-out
tasks, three reps each, on one box, in one launch, against one baseline. There is no renamed
product-owner or planner export that has been served, so three of the four seats are still unmeasured
on a working adapter path. The memory and cache figures were all taken at a dial the box cannot live
with while it is also building, so the honest answer to "what does this cost on a working machine" is
that we do not know yet. Nothing here says the parallel-slot win survives at real prompt lengths on a
dial we can afford — at the dial we did test, four full-length requests took 2.59 times one alone, and
the limit was reading the prompts, not the adapters.

---

## Next steps — options, not a plan

1. **Grade the renamed exports that already exist for the product owner and the planner.** The converter already
   does it; the exports for `po-gemma4-v5`, `po-gemma4-v6` and `architect-plan-v2` are already on
   disk. That is the single measurement that would tell us whether the product-owner gap is real.
   It needs one launch and three reps per seat.
2. **Find the dial the box can actually live with.** Test 0.60, 0.62 and 0.65 with four adapters, and
   record the cache, the requests'-worth figure and the settled memory left. Half a day, no exam runs.
3. **Make the two silent faults loud.** Add the merged-difference comparison to the converter's own
   verify step, and add a check that reads the server's debug log after launch and fails if any
   adapter has expert modules reset to zero. Both are small scripts.
4. **Decide what to do about the deterministic-kernel mode.** It removes the non-repeatability we
   need for trustworthy exams, at about a third more compute per token, and it does not cover the
   fused expert kernel when several requests arrive at once. One option is to use it for exams only
   and not in service.
5. **Re-measure the parallel slots on the fixed path.** Every slot number here was taken with the
   expert adapters switched off, so they understate the real cost of serving adapters that work.

*Coordinator's amendment, 2026-09-02 late. The S6 reviewer blocked this document on two unlicensed claims (the per-token cost of running the expert adapters, and "exactly as the adapter does") and four smaller points (the cache figure's run-to-run variation, the merged directory's byte count, two unexplained experts in layer 29, "checks" for "runs"), plus the unsaved repeatability replies and the identical-answer counts the coordinator's notes had asked for. All are corrected above, together with the wording of the August comparison and the ungradable-run notation; four terms are glossed for a non-specialist. No measurement changed. The block was resolved by correcting the document, not by overriding the reviewer.*
