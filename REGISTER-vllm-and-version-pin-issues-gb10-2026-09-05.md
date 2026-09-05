# Register of vLLM and version-pin issues on the GB10 box

Date: 2026-09-05. Box: promaxgb10-41b1 (Dell Pro Max with a GB10 chip, 121 GiB of memory shared between the graphics processor and the main processor, ARM 64-bit). Nothing was started, stopped or reconfigured to write this. Every claim about our own estate names the receipt file or document it came from. Every claim about a public project names the issue, pull request or file, says what state it was in, and says it was checked on 2026-09-05 with the GitHub interface (`gh api`) unless stated otherwise. One note on units: memory figures in this register are gibibytes (GiB), the unit the receipts themselves record, and a gibibyte is about 7 per cent larger than a gigabyte; sizes on disk are given as their own receipt gives them. One housekeeping note: the entries in the plan of record that this document cites for 2026-09-04 and 2026-09-05 sit in ai-transition commits that have not been pushed yet (`c2afae5`, `4917315`, `1038e79`, `e4228ce`, checked 2026-09-05), so anyone reading from the remote copy will not find them until Rich pushes.

## What this register is for, and how to use it

This is a list of the things in vLLM — the program that serves our models — and in the versions we have pinned around it that have cost us time on this box. It exists because Rich does not want spurious issues raised on other people's projects. We filed a report in August that turned out to have been fixed six weeks earlier, and it went out under Rich's name; the cost of that is the reason this document exists. So each entry carries two things a bare bug list would not: **the bar that would have to be met before filing anything upstream would be justified**, and **the state that upstream was actually in when last checked**. The point is to make a future decision to file — or not to file — cheap, quick and safe, not to file anything now.

To use it: find the symptom you are looking at in the summary table, read that entry's six headings, and note two lines in particular. "Workaround in use" tells you what is already in place and where it lives, so you do not re-solve a solved problem. "Upstream status" tells you whether somebody else has already reported it and whether a newer release fixes it, so you do not report a stale bug. **Standing rule, and it is binding: nothing is filed, commented on, or opened upstream without Rich asking for it in that instance.** Everything upstream goes out under his name and his account. When a finding is genuinely new and would help the project, the right move is to write it down here, offer the filing to Rich once, plainly, and stop there. Where a fact could not be verified today, this document says "unverified" rather than asserting it.

A few words used throughout, explained once. An **adapter** is a small trained file (about 2.5 GiB for us) that turns one shared copy of the base model into a particular role — the checker, the planner, the specification writer. A **kernel** is the hand-written routine that does the actual multiplication on the graphics chip; different kernels support different number formats, and only some of them have the hook that lets an adapter's contribution be added. **CUTLASS**, **Triton** and **Marlin** are the names of three families of those kernels, and three entries below turn on which family runs. CUTLASS is NVIDIA's own library of them, written in C++ and tied closely to each chip generation. Triton is a compiler that generates them from Python-like code, so its kernels are easier to adapt and generally a little slower. Marlin is a family written specially for weights stored at fewer than 16 bits, which unpacks them back to 16 bits inside the chip before multiplying. This model is a **mixture of experts**: each layer holds 128 small sub-networks and only a few fire per word, and they hold most of the model's weights, so what happens to the experts is what happens to the model. **8-bit** means each stored number takes one byte instead of two; there is more than one way to do it, and the differences between those ways are the subject of several entries below. **FP8** is the floating-point way; **INT8** and **Q8_0** are whole-number ways. **sm_121** (also written SM 12.1) is NVIDIA's version label for this chip's instruction set — it is a capability label, not a speed.

---

## Summary

The number in the first column is only a label so entries can be referred to. "Where it bites" is one of: **load** (the server will not start or start-up eats the box), **serve** (it starts but refuses or crashes in use), **quality** (it answers, but worse), **speed**, **tooling** (our own choices of version and pin).

| # | What it is | Where it bites | Workaround in use | Upstream state, verified 2026-09-05 | Filing bar met? |
|---|---|---|---|---|---|
| 1 | The dense 8-bit CUTLASS kernel crashes on this chip (`cutlass_gemm_caller … Error Internal`) | serve (start-up warm-up) | `--linear-backend torch` in the live launch script | The general SM 12.1 gate fix (PR #41215) is **merged and already inside our pinned release**; the thread that was **closed** on the finding that CUDA 13 builds cure it (#43367) is about a *different* kernel — the block-scaled one, not the per-tensor dense one we crash on | **no** — our own kernel has never been run on a CUDA 13 build here |
| 2 | Only two 8-bit expert kernels carry the adapter hook, and which one you get is decided by the number format | serve | `--moe-backend triton` with FP8; `--moe-backend marlin` for integer weight-only | Not a defect — it is how the release is built. Related: #43507 **open** (no CUTLASS grouped-expert kernel on SM 12.x) | **no** |
| 3 | Load-time integer 8-bit quantisation eats the whole memory pool while loading | load | do not use it; quantise offline instead; memory watchdog on every such attempt | No upstream report of this exact path found; nearest is #43969, **open** | **no** — the mechanism was never root-caused |
| 4 | The weight loader orphans 20 MiB blocks on the Marlin integer path, about 150 GiB of waste for this model | load | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` on the container | The 20 MiB cap comes from PR #41268, **merged 2026-04-30, present in v0.25.0 and unchanged in v0.28.0**; #43969 **open** (same class, different model); PR #51096 **open, unmerged** | **yes** — the measurement is complete; only a public reproduction is missing |
| 5 | Marlin weight preparation crashes when the checkpoint has one scale per row (`marlin_utils.py:343`, group width unset) | load | quantise with one scale per 64 weights instead | Issue #52713 **open**, its fix PR #53163 **open and unmerged**; the code is **unchanged in v0.28.0** | **no** — already reported by someone else, with a better reproduction than ours |
| 6 | No tuned expert-kernel table for this chip at our shape, and none at all for integer weight-only | speed | none; accept about 20% less speed on the Marlin path | PR #52502 **merged 2026-08-17, in v0.28.0 only**; it adds exactly two tables, both floating-point, neither our shape | **no** — a gap in tuning data, not a defect |
| 7 | The FP8 base misreads a plain true/false field that every other form reads correctly | quality | a deterministic guard in guardkit (commit `1447819d`) that voids the specific wrong finding | Nothing upstream matches. Issue #30830 (online FP8 mixture-of-experts accuracy) is **closed as completed 2025-12-22** and is not our path | **no** — one prompt, three sends, no minimal reproduction |
| 8 | The vLLM version pin itself: why v0.25.0 and not the current release | tooling | pinned to `vllm/vllm-openai:v0.25.0-aarch64-cu129` | v0.28.0 is the **latest release** (published 2026-08-26) and does contain PR #49797, the Gemma 4 fix; untested here beyond an import probe. v0.25.1 (published 2026-07-14) is a one-patch step from our pin that would retire entry 13, also untested here | not a defect |
| 9 | The transformers library pin inside the image | load | comes with the pinned image: transformers **5.13.0** | transformers PR #47384 **merged 2026-07-23, first released in 5.15.0** (2026-08-10) — so the break that stops later vLLM images is dated and understood | not a defect |
| 10 | The llama.cpp / GGUF findings that constrain what we may compare against | quality | the merged Q8_0 checker is the comparator; never serve this family at 4-bit | our own measurements only | not a defect |
| 11 | The memory dial does not give a fixed footprint | load | `--kv-cache-memory-bytes 8589934592` in the live launch script | documented behaviour of the flag, not a bug | **no** |
| 12 | `NVRM … NV_ERR_NO_MEMORY` lines in the kernel log during a load | note only | none; record, do not act | n/a | **no** |
| 13 | The pinned image ships a video decoder built for the wrong CUDA version, which kills the server at start-up | load | delete it in the container's start command | Issue #48592 **closed as completed 2026-07-15** because the fix shipped in **v0.25.1**; the wider "installed but unloadable" problem is #54097, **open** | **no** — already reported and closed |
| 14 | Per-expert adapter weights are skipped in silence when their names do not match, and the repair the image already contains is not applied on the adapter path | quality | our converter (version 3) writes the path vLLM looks under; a per-module load check reads the server's own debug lines | PR #50252 **open, unmerged** (same silent-no-op on Gemma 4 expert adapters); PR #55310 **open, unmerged** (reject adapters that match nothing); issue #39815 **closed as stale 2026-09-02**, its PR #39816 **open, unmerged** | **partly** — the "no warning at all" half is arguably new; the mapping half is already reported |
| 15 | Greedy answers are not repeatable on the adapter path, and the deterministic mode makes long answers run away | quality | deterministic mode stays off for the gated roles | no upstream report found for either half | **no** — not isolated to a minimal case |
| 16 | The base snapshot pin: serving a different revision of the same model looks exactly like a bad adapter | quality | snapshot `60941ad6…` pinned in the launch script and the runbook | not a defect | not a defect |

---

## 1. The dense 8-bit CUTLASS kernel crashes on this chip

**Symptom.** With `--quantization fp8` and nothing else, the server loads all the weights correctly and then dies in its warm-up pass, six minutes and fifty-two seconds after start, with:

```
RuntimeError: cutlass_gemm_caller,
  /workspace/csrc/libtorch_stable/quantization/w8a8/cutlass/c3x/cutlass_gemm_caller.cuh:62,
  Error Internal
```

The line that chose the failing kernel, from the same log: `Selected CutlassFP8ScaledMMLinearKernel for Fp8PerTensorOnlineLinearMethod`. This is the **dense** kernel — the attention and ordinary feed-forward layers — not the expert kernel, which had already been chosen correctly as Triton. It is not a memory problem: the container's own record says it was not killed for memory, and it exited with code 1. Receipt: `/home/richardwoollcott/fine-tuning/output/vllm-fp8-exam-2026-09-03/f1-fp8-host.json`, section `the_two_failed_attempts.attempt_1_the_brief_as_written`, with the whole 13,497-line log kept beside it as `launch-fp8-attempt1.log`. Date: 2026-09-03.

**Root cause as far as known.** Not established by us from source. The public diagnosis for the same error string on the same chip is that the per-tensor FP8 dispatch guards on `__CUDA_ARCH__==1200` (SM 12.0) while the GB10 reports 12.1, so the guard fails inside the kernel and surfaces as a generic internal error ([vLLM issue #40758, comment by j9smith, 2026-04-30](https://github.com/vllm-project/vllm/issues/40758)). We did not read the CUDA source in our own image to confirm that this is still the mechanism, because the fix for that exact gate is already in our release (see below), so something else or something residual is at work.

**Workaround in use.** The flag `--linear-backend torch`, in the live launch script `/opt/llama-swap/scripts/gemma4-adapters.sh`, on the `vllm serve` line. It restricts the dense-layer kernel choice to PyTorch's own, and the server then logs `Selected ChannelWiseTorchFP8ScaledMMLinearKernel`. Two other things were tried and are recorded: `--linear-backend triton` is refused outright in 21 seconds (`ValueError: --linear-backend=triton was requested but no 'triton' kernel exists for this layer type`), and the unmodified command is the one that crashes. The workaround does **not** avoid squeezing the running numbers to 8 bits; it only avoids CUTLASS. That is spelled out in `RESEARCH-8bit-fidelity-adapter-host-gb10-2026-09-04.md`, section 1.

**Upstream status.**
- [Issue #40758](https://github.com/vllm-project/vllm/issues/40758), "`Qwen3.6-35B-A3B-FP8` fails on `NVIDIA GB10` with `cutlass_scaled_mm` / `cutlass_gemm_caller Error Internal` **under vLLM nightly + CUDA 13.0**" — opened 2026-04-24, **closed as completed 2026-05-01**. Same error string, same chip, a different model. The last four words of that title matter and an earlier draft of this register left them off: the reporter who confirmed it (amuin-2hz, 2026-05-01) was running torch 2.11.0+cu130, which is a **CUDA 13** build. So the per-tensor crash has been seen on CUDA 13 by someone else.
- [PR #41215](https://github.com/vllm-project/vllm/pull/41215), "Use enable_sm120_family for per-tensor FP8 CUTLASS kernels on SM12.1" — **merged 2026-05-20**. Checked by comparing its merge commit `644b2a28e7eb3b11191f157416cfedebd2da995b` against the tags: it is **contained in v0.25.0 and in v0.28.0**. So the fix that closed #40758 is already inside the image we run, and we crashed anyway.
- [Issue #43367](https://github.com/vllm-project/vllm/issues/43367), "SM12.1 / GB10 still fails in CutlassFp8BlockScaledMMKernel after #41215" — opened 2026-05-21, **closed as completed 2026-06-23**, with the closing conclusion in its own comments that the failure belongs to builds made against **CUDA 12.9** and disappears on **CUDA 13** builds of the same code, confirmed independently by two reporters. **Read the title carefully: that thread is about the block-scaled kernel, not the per-tensor dense kernel we crash on.** The CUDA-13 cure was therefore established on a different kernel from ours.
- Still open and adjacent, both about the *block-scaled* rather than the per-tensor path: [#47990](https://github.com/vllm-project/vllm/issues/47990) (SM120 blockwise FP8 rejects widths not divisible by 128), [PR #48588](https://github.com/vllm-project/vllm/pull/48588) and [PR #55180](https://github.com/vllm-project/vllm/pull/55180) — all **open**.
- What changed between v0.25.0 and v0.28.0 for this item: nothing we could identify. #41215 is in both. The open block-scaled work is unmerged in both.

**What would justify filing.** The minimal reproduction is: `vllm serve <this Gemma 4 snapshot> --quantization fp8 --moe-backend triton` with no `--linear-backend` flag, on a GB10, using a **CUDA 13** build of a **current** release, showing the same crash. We already have the crash, the exact line, the kernel-selection line, the full log and the negative control (the same command with one flag added, which works). **What is missing is the only thing that matters: nobody has run our kernel, on this box, on a CUDA 13 build of any release.** Be precise about what the CUDA-13 finding covers. The consensus recorded on #43367 — CUDA 12.9 builds fail, CUDA 13 builds do not — was reached on the **block-scaled** kernel. Ours is the **per-tensor dense** kernel (`Selected CutlassFP8ScaledMMLinearKernel for Fp8PerTensorOnlineLinearMethod`), and on that path nobody has shown a CUDA 13 build to be safe: #40758 names CUDA 13.0 in its own title, and the reporter who confirmed it on 2026-05-01 was on torch 2.11.0+cu130. That sighting predates the #41215 fix which is in our release, so it does not prove our kernel still fails on CUDA 13 — but it does mean there is no established cure for our kernel to point at, and no test of our kernel on CUDA 13 either. Filing on the strength of a thread about a different kernel, or filing without first running a CUDA 13 image ourselves, would repeat the August mistake in a new costume. There is no CUDA 13 aarch64 image of v0.25.0 or v0.28.0 on this box today (`docker images` lists only `-cu129` variants of v0.22.0, v0.25.0, v0.27.1 and v0.28.0, plus the abandoned `cu130-nightly` from 2026-04-23).

**Notes for later research.** If the pin ever moves to v0.28.0, retry the plain FP8 command once without `--linear-backend torch` and record the result either way; it is a two-minute check inside a start that we would be doing anyway. Also worth knowing whether the PyTorch dense kernel costs speed against CUTLASS — that was never measured (`f1-fp8-host.json` says so explicitly).

---

## 2. Only two 8-bit expert kernels carry the adapter hook

**Symptom.** Not a failure so much as a constraint that decides every other choice. In the pinned image, exactly three expert kernels carry the hook that lets an adapter's contribution be added, and one of the three is for a different model family:

```
vllm/model_executor/layers/fused_moe/experts/triton_moe.py:54
    class TritonExperts(LoRAExpertsMixin, mk.FusedMoEExpertsModular)
vllm/model_executor/layers/fused_moe/experts/marlin_moe.py:701
    class MarlinExperts(LoRAExpertsMixin, MarlinExpertsBase)
vllm/model_executor/layers/fused_moe/experts/gpt_oss_triton_kernels_moe.py:1059
    class UnfusedOAITritonExperts(LoRAExpertsMixin, BaseOAITritonExperts)
```

Anything that lands on a fourth kernel cannot serve adapters at all: vLLM asserts and refuses to start (`vllm/lora/layers/fused_moe.py:423`). All read inside the pinned image on 2026-09-04 and recorded in `RESEARCH-8bit-fidelity-adapter-host-gb10-2026-09-04.md`, section 2.

The practical consequence is a fork. For **floating-point 8-bit** the adapter-capable kernel is Triton, and `--moe-backend triton` is what selects it. For **integer 8-bit weights with 16-bit arithmetic** there is **no Triton kernel at all** — the backend chooser accepts only `marlin`, `humming` and `flashinfer_trtllm`, so passing `--moe-backend triton` on that path is fatal, and the kernel that runs is Marlin. That was read out of the image before anything was run, and recorded in `~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/q0-format.json`, section `a_method_class`, on 2026-09-04, then confirmed on the wire the same night: `Using 'MARLIN' WNA16 MoE backend.` ("WNA16" is vLLM's name for weights at N bits with 16-bit arithmetic; here N is 8.)

**Root cause as far as known.** By design. Marlin's own class asserts it only ever runs weight-only schemes (`marlin_moe.py:569-575`), and the per-row floating-point scheme explicitly refuses Marlin (`online/fp8.py:705-715`, because Marlin "does not implement per-output-channel weight scales"). So the combinations are genuinely constrained, not accidentally so.

**Workaround in use.** Both flags live in the same place, `/opt/llama-swap/scripts/gemma4-adapters.sh`: the production line carries `--quantization fp8 --moe-backend triton --linear-backend torch`. The experimental integer container used `--moe-backend marlin` instead, and never touched production (`~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/s1/start_exam_container4.sh`).

**Upstream status.** Nothing to report — this is the shape of the release, not a bug. The nearest open report explaining *why* the CUTLASS expert kernels are not available on this chip is [issue #43507](https://github.com/vllm-project/vllm/issues/43507), "CUTLASS MoE backend unavailable on SM_120/SM_121 (consumer Blackwell / DGX Spark) for tensor/token-scaled FP8 models" — opened 2026-05-23, **open**, no maintainer reply. Its own account is that CUTLASS 4.5 ships no grouped-expert kernel for SM 12.0/12.1. Between v0.25.0 and v0.28.0 we found no change to which expert classes carry the hook.

**What would justify filing.** Nothing. There is no defect here to file. If we ever wanted a Triton integer weight-only expert kernel that carries the hook, that is a feature request, and it would need a stated need and a measurement showing what it would buy — which entry 6 suggests would be speed, and entry 7 suggests would not be fidelity.

**Notes for later research.** The Triton kernel's own comment names the combination "adapter on top of weight-only quantisation" as a case it handles (`triton_moe.py:316-318`), which is why candidate A in the fidelity research looked promising before it hit the memory wall in entry 3. If a Triton integer weight-only expert path ever appears upstream, that is the one change that would reopen the whole question.

---

## 3. Load-time integer 8-bit quantisation exhausts the shared memory pool

**Symptom.** On 2026-09-04 at 21:03Z, on Rich's word, the production entry was switched from floating-point 8-bit to integer 8-bit quantised while loading (`--quantization int8_per_channel_weight_only --moe-backend triton`, with `--linear-backend torch` removed). The flag was accepted — the log read `Using TRITON Int8 MoE backend out of potential backends: ['TRITON', 'HUMMING', 'CPU']` — and then the expert load kept taking memory: free memory went 101 → 52 → 28 → 21 → 15 → 5 → 0.2 GiB with 15 GiB of swap in use, and the experts were still loading five minutes in. The equivalent floating-point load of the same model never drops below about 35 GiB free. The attempt was stopped and the entry unloaded at about 21:07Z, but the kernel had already killed three processes: the proxy that fronts the models (restarted by the system a minute later), a Claude Code session belonging to another window, and the text-embedding server. Everything was restored and answering by 21:19Z. **No exam ran, so nothing here says anything about that scheme's answer quality or speed.** Receipts: `~/fine-tuning/output/candidate-a-int8-exam-2026-09-04/c1-abort/` — `abort-utc.txt` (2026-09-04T21:08:07Z), `kernel-kills.txt` (the kernel's own kill lines), `candidate-container.log` (the full container log), `candidate-script-as-run.sh`. Written up in `ai-transition/docs/software-factory-plan-of-record.md`, entry "2026-09-04, 21:03–21:19Z".

**Root cause as far as known. Not root-caused, and this entry deliberately does not pretend otherwise.** What we can say is what we saw: the loader's peak memory while quantising the experts online exceeds the 121 GiB shared pool for this model, where the floating-point online path fits comfortably. The plausible explanation written down at the time — that this path holds the 16-bit experts and the 8-bit copy at once, on a machine where graphics and main memory are one pool — is a hypothesis, not a reading of the code. Nobody has read the online integer loader's allocation pattern the way the Marlin path was read in entry 4. Note carefully that entry 4's cause (orphaned 20 MiB allocator blocks) was established for the **offline compressed-tensors Marlin** path and **may or may not** be the same mechanism here; the online path was never retried after the allocator fix was found, so the connection is untested.

**Workaround in use.** Do not use this scheme as a load-time path on this box. Two rules were made standing that night and are recorded in the memory note `lesson-online-quant-load-memory-watchdog.md`: never test a new quantisation scheme, loader path or model on the production entry — use a separate container on port 8011 on an otherwise quiet box; and every such attempt runs a memory watchdog that stops the container when free memory falls below a floor and records the peak. The watchdog exists and works. `~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/watchdog.log` records both of that night's trips at the **14 GiB** floor: at 21:51:25Z on swap (`TRIP: swap used 9935 MiB > 8 GiB`) and at 22:09:46Z on free memory (`TRIP: MemAvailable 13697 MiB < 14 GiB`), each followed within seconds by the target container stopped and the pool back above 100 GiB. Every later arming used a **12 GiB** floor, from 22:58:40Z onwards, and every one of those ended `targets gone, exiting clean` — none of them tripped. Read again from the log on 2026-09-05.

**Upstream status.** No upstream report of this exact path (online `int8_per_channel_weight_only` on unified memory) was found in a search of the vLLM tracker on 2026-09-05. The nearest is [issue #43969](https://github.com/vllm-project/vllm/issues/43969), "gpt-oss-120b MXFP4 MoE init OOM-killed on unified-memory ARM (DGX Spark / Jetson Thor)" — opened 2026-05-29, **open**, with GB10 confirmations in its comments; that is the same *class* of failure (host memory exhausted during expert-layer quantisation-method setup on a unified-memory ARM box) but a different model and a different number format. Worth knowing in the other direction: vLLM's own recipe recommends this exact flag for this exact model — [`vllm-project/recipes`, `Google/Gemma4.md`](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md), fetched again 2026-09-05, line 1098: "For the MoE model, use `--quantization int8_per_channel_weight_only` (online, no checkpoint needed) which provides ~47% memory savings with negligible quality impact." The recipe carries no numbers and was not written for this box, and it says nothing about loading on a shared memory pool.

**What would justify filing.** A minimal reproduction would be: this model, this flag, a current release, on a GB10, with a memory trace showing the peak, run in a container that harms nothing, plus a control showing the floating-point path on the same box fits. We already have the memory trace and the control. **What is missing is the mechanism.** Filing "it uses too much memory" against a scheme the project's own recipe recommends, without being able to say what is holding the memory, invites exactly the response we got in August. The honest sequence is: read the online integer loader in the pinned image the way the Marlin path was read; retry it once in a watched container with the allocator variable from entry 4 set, since that is a one-variable test and it might simply be the same bug; and only then decide.

**Notes for later research.** The retry described above is cheap and has never been done. If it succeeds, entries 3 and 4 collapse into one finding, and the case for a single, well-evidenced upstream report gets much stronger.

---

## 4. The weight loader orphans 20 MiB blocks on the Marlin integer path

**Symptom.** Loading a pre-made integer 8-bit checkpoint (compressed-tensors, weights only) in a separate container on a quiet box: free memory fell from 102 GiB to 9.6 GiB in about forty seconds, by which time only 2 of the file's 7 shards had loaded. The watchdog stopped the container at its 14 GiB floor. The checkpoint on disk is 26.83 GiB, as vLLM's own start-up line measures it; the load had already consumed about 92 GiB. Nothing else was harmed and the kernel killed nothing. Receipt: `~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/q2-exam.json` — the ten-second memory samples are in the file, the trip line reads `2026-09-04T22:09:46Z TRIP: MemAvailable 13697 MiB < 14 GiB`, and the container log is `q2/exam-container.log`. Date: 2026-09-04.

**Root cause as far as known.** Established from the pinned image's own source, with the arithmetic matching the measurement, on 2026-09-04 (recorded in the memory note `adapter-serving-durable-facts-2026-09-02.md` under "2026-09-04 22:35Z ROOT CAUSE", and summarised in the plan of record entry "2026-09-04, ~22:40Z"). In four steps:

1. Marlin's integer weight-only expert parameters are stored the other way round from the file's layout (`compressed_tensors_moe_wna16_marlin.py:118-135, 218-222` mark them transposed).
2. The expert weight loader narrows its destination on the **last** dimension (`routed_experts.py:485` and `:489`, both confirmed in the running image on 2026-09-05), which makes the destination non-contiguous, so every per-expert copy needs a staging buffer of about 1.9 MiB on the graphics chip (`routed_experts.py:497`).
3. During weight loading vLLM caps the memory allocator's block size at 20 MiB: in the pinned image, `vllm/v1/worker/gpu_worker.py:406-411`, read on 2026-09-05 —
   ```
   def load_model(self, *, load_dummy_weights: bool = False) -> None:
       with (
           self._maybe_get_memory_pool_context(tag="weights"),
           set_current_vllm_config(self.vllm_config),
           # 20 MiB is the minimum PyTorch allows for max_split_size_mb.
           self._scoped_allocator_max_split(max_split_size_mb=20),
       ):
   ```
   With that cap, each small staging buffer takes a fresh 20 MiB segment which the allocator will not then reuse: 256 orphaned segments per expert layer, about 5 GiB a layer, roughly 150 GiB across thirty layers, on top of the 27 GiB of weights.
4. On a discrete graphics card a failed allocation flushes that cache and it recovers. On a box where graphics and main memory are one pool, nothing triggers the flush, so the whole machine is consumed.

Predicted consumption 2.6 GiB a second against 2.39 measured. The floating-point path is unaffected because its layout is not transposed.

**Workaround in use.** One environment variable on the container: `-e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, which tells the allocator to grow one pool instead of hoarding fixed blocks. **Confirmed to fix it outright**: the same checkpoint then loaded 7 of 7 shards in 52.7 seconds with the box flat at about 67 GiB free (recorded in `adapter-serving-durable-facts-2026-09-02.md`, "2026-09-04 23:00Z"), and the later group-64 checkpoint loaded 8 of 8 shards in 48 seconds at a peak of 54.2 GiB used, watchdog untroubled (`~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/s1-load.json`). The variable lives in `s1/start_exam_container4.sh`; **it is not in the production launch script, and does not need to be**, because production runs the floating-point path, which never had the problem.

**Upstream status.**
- [PR #41268](https://github.com/vllm-project/vllm/pull/41268), "[UX][Bugfix] Fix OOM by setting PyTorch `max_split_size_mb` during model loading" — **merged 2026-04-30**. This is the *source* of the 20 MiB cap; it was itself a fix for a different out-of-memory problem. Checked today by comparing its merge commit `f03d82efdd88fbd85ddf7a5475e237ae3abaf01e` against the tags: **contained in v0.25.0, v0.27.1 and v0.28.0**.
- **What changed between v0.25.0 and v0.28.0 for this item: nothing.** The same code stands in v0.28.0 at `vllm/v1/worker/gpu_worker.py:454-455`, fetched from the tag on 2026-09-05 and compared line for line with the pinned image's `:410-411`. The wording of the comment is identical.
- [Issue #43969](https://github.com/vllm-project/vllm/issues/43969) — **open**, opened 2026-05-29, "gpt-oss-120b MXFP4 MoE init OOM-killed on unified-memory ARM (DGX Spark / Jetson Thor)". The reporter bisects the onset to two days in May 2026 and confirms it on both a Thor and a GB10; a commenter on 2026-06-12 confirms on a GB10 that when the load survives, the format resolves to the Marlin expert backend and total use reaches about 118 GB on a 128 GB box. That is the same class of failure and the same kernel family. **Our root-cause analysis is not in that issue.**
- [PR #51096](https://github.com/vllm-project/vllm/pull/51096), "Preserve user PYTORCH_CUDA_ALLOC_CONF keys in `_scoped_allocator_max_split`" — **open, unmerged**. Relevant because the helper in our image (`gpu_worker.py:255-276`, read 2026-09-05) resets the allocator settings by writing only `max_split_size_mb`, which is why the state of a user's other allocator keys during loading is worth watching. In our case the workaround survived and worked; that is a measurement, not a guarantee.

**What would justify filing.** This is the one entry where the bar is **met on evidence**. The minimal reproduction is: any compressed-tensors weight-only integer checkpoint of a mixture-of-experts model, on a unified-memory box, loaded with a current vLLM release, showing free memory falling at about 2.4 GiB a second and the load never completing; then the same load with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` completing in under a minute at a flat memory profile. We have: both runs with ten-second memory samples, both container logs, the four source citations above, the predicted-versus-measured slope, and confirmation that the code is unchanged in the latest release. What is **missing** is a reproduction somebody else could run without our 27 GiB checkpoint — that is, either a public checkpoint that shows the same thing, or a small synthetic case. Adding our analysis as a comment on the already-open #43969 would be lower-cost and lower-risk than opening anything new. **Rich declined to file this on 2026-09-04**, in his words "a bit hesitant to raise issues after the false alarms raised previously", and that decision stands until he says otherwise.

**Notes for later research.** Two loose ends. Whether `--load-format fastsafetensors` also avoids it (the tensors would go straight to the chip with no staging copy) was never tried and would need that package in the image. And whether the same orphaning explains entry 3 — see the cheap retry suggested there.

---

## 5. Marlin weight preparation crashes when the checkpoint has one scale per row

**Symptom.** With the allocator fixed, the same integer checkpoint loaded all its weights and then crashed while preparing them for the kernel:

```
TypeError: '>' not supported between instances of 'NoneType' and 'int'
  vllm/model_executor/layers/quantization/utils/marlin_utils.py:343
  group = group_size if group_size > 0 else 1
```

Call chain, read from the log: `compressed_tensors_moe_wna16_marlin.py:419 process_weights_after_loading` → `oracle/int_wna16.py:1127 convert_to_wna16_moe_kernel_format` → `int_wna16.py:514 _process_weights_marlin` → `marlin_utils.py:343`. Receipt: `~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/r1/exam2-container.log`, lines 595–607, read again on 2026-09-05; the analysis is in `s0/format-g64.json`. Date: 2026-09-04, about 23:00Z.

**Root cause as far as known.** Read out of the pinned image and recorded in `s0/format-g64.json`. A compressed-tensors checkpoint that scales weights one row at a time leaves the "group width" field unset — it is `None`, and nothing fills it in for that strategy (`compressed_tensors/quantization/quant_args.py:196`). vLLM's Marlin method does set its own copy to −1 when it sees that strategy (`compressed_tensors_moe_wna16_marlin.py:262-264` — the test `if self.strategy == "channel":` is line 262 and the assignment `self.group_size = -1` is line 264, read at the v0.25.0 tag on 2026-09-05, which is the source the pinned image is built from), but only on the method object; the weight-preparation step re-reads the value straight off the checkpoint (`oracle/int_wna16.py:1117-1119`, `group_size = quant_config.group_size`) and hands `None` to a helper that compares it to a number.

**Workaround in use.** Quantise with **one scale per 64 input values** instead of one per row. The same code path is taken, Marlin is still chosen, no padding is needed for our widths, and the adapter hook is untouched — all four checked in source before the run and written down in `s0/format-g64.json`, `same_code_path_confirmed`. The resulting checkpoint is `~/fine-tuning/output/gemma4-26b-a4b-it-int8-w8a16-g64-ct`; it loaded in 48 seconds, served all six adapters, and was examined (entry 7 and the plan-of-record entry "2026-09-05, ~00:20Z"). This is an experiment-only workaround; production does not use this path at all.

**Upstream status.**
- [Issue #52713](https://github.com/vllm-project/vllm/issues/52713), "Marlin MoE support probe raises TypeError instead of returning a verdict for unset group_size" — opened 2026-08-18, **open** on 2026-09-05. It names three sites that compare an unset group width to a number, and the second of the three is exactly ours (its wording: "`oracle/int_wna16.py:1512` (weight prep re-reads `weight_quant.group_size`) → `marlin_utils.py:344`"). It even names an affected checkpoint of this very model family, `lokeshe09/gemma-4-26B-A4B-it-INT4-W4A16-channelwise`.
- Its fix, [PR #53163](https://github.com/vllm-project/vllm/pull/53163), "Normalise an unset group_size on the compressed-tensors WNA16 MoE path" — opened 2026-08-20, **open and unmerged** on 2026-09-05.
- **What changed between v0.25.0 and v0.28.0 for this item.** The crash site is unchanged: `marlin_moe_padded_intermediate` still reads `group = group_size if group_size > 0 else 1` at `marlin_utils.py:344` in v0.28.0 (fetched from the tag 2026-09-05), and the caller still reads the value straight off the checkpoint (`int_wna16.py:1500` in v0.28.0). One thing *did* change: #52713 says its first of three sites was introduced by [PR #44570](https://github.com/vllm-project/vllm/pull/44570), **merged 2026-07-31**, which is **not** in v0.25.0 (verified by comparing its merge commit `454ea5b52611c933e00581723e2db56f0144cea7` against the tags: diverged from v0.25.0, contained in v0.27.1 and v0.28.0). So on our pinned release only the weight-preparation site exists — which is precisely where our traceback lands. Consistent, and worth recording as an example of a report and an observation matching without being identical.

**What would justify filing.** Nothing more. It is already reported, by someone with a five-line reproduction that needs no checkpoint at all, and a fix is open. The only thing worth doing is watching #53163: if it merges, the group-64 workaround stops being necessary on whatever release carries it. If we ever wanted to help, the useful contribution would be a comment confirming the weight-preparation site is reachable on v0.25.0 without #44570 — small, factual, and still needs Rich's word.

**Notes for later research.** Our quantiser rounds with scale = largest absolute value ÷ 127 and clamps to −127…127, where the compressed-tensors reference divides by 127.5 and clamps to −128…127. Harmless for serving, because dequantising multiplies back by the stored scale, but it should be stated in any write-up and in any upstream comment (recorded in `adapter-serving-durable-facts-2026-09-02.md`, in the note the reviewing agent left on that lane on 2026-09-04).

---

## 6. No tuned expert-kernel table for this chip at our shape

**Symptom.** Every start of an integer 8-bit expert path logs, once:

```
Using default MoE config. Performance might be sub-optimal! Config file not found at
  .../configs/E=128,N=11264,device_name=NVIDIA_GB10.json
```

(`~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/s1-load.json`, `lora.warnings_seen`, 2026-09-04.) The measured cost, from the exams the next hour: **20.0 tokens a second on the checker exam and 21.3 on the specification-writer exam, against the production floating-point host's 25.3 and 28.4** — roughly a fifth slower (`~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/s2-exams.json`). That is about where the plain 16-bit path sits, which is consistent with Marlin expanding 8-bit weights back to 16 bits inside the chip and multiplying at 16 bits.

**Root cause as far as known.** No mystery. vLLM ships hand-tuned kernel settings as small files named by expert count, width, chip and number format, and there is no file for our combination, so generic settings are used. Additionally the Marlin design does the arithmetic at 16 bits by construction, so some of the loss is the scheme, not the tuning.

**Workaround in use.** None. The production path does not use Marlin, so this does not bite production today.

**Upstream status.**
- [PR #52502](https://github.com/vllm-project/vllm/pull/52502), "[Hardware][NVIDIA] Add GB10 fused-MoE fp8 tuning configs (E=256, E=512)" — **merged 2026-08-17**. Verified today by listing the files it added: exactly two, `E=256,N=512,device_name=NVIDIA_GB10,dtype=fp8_w8a8,block_shape=[128,128].json` and `E=512,N=512,…`. Both are **floating-point** and **block-scaled**; neither is our shape (128 experts, width 11,264 as vLLM names it) and neither is an integer weight-only table.
- **What changed between v0.25.0 and v0.28.0 for this item.** Everything, in the sense that v0.25.0 has **zero** GB10 tuning tables and v0.28.0 has **two** — checked on 2026-09-05 by listing `vllm/model_executor/layers/fused_moe/configs` at each tag (331 files at v0.28.0, two of them GB10; none at v0.25.0). Neither of the two would apply to our model.
- A GitHub code search for `NVIDIA_GB10` across the repository returned 0 results through the API today; the directory listing above is the stronger evidence and is what this entry rests on.

**What would justify filing.** Nothing to file — a missing tuning table is not a defect. The *contribution* shape would be to tune our own and offer it upstream, which means running vLLM's tuning script for this expert count, width and format on this box, producing a file, and measuring the gain. That is real work with an unknown payoff, and it only matters if we ever move production onto an integer weight-only path — which entry 7 argues against.

**Notes for later research.** If somebody does tune it, the same run should produce a floating-point table for our shape too, since production runs a shape that has no table either. Whether that would recover any of the production speed is unmeasured.

---

## 7. The FP8 base misreads a field that every other form reads correctly

**Symptom.** This one is about answers, not crashes, and it is the reason the whole 8-bit fidelity question was opened. On 2026-09-04, the checker role — served as an adapter on the floating-point 8-bit base — read a plain true/false value in its own evidence backwards, three times out of three, at temperature zero. The evidence said a test run had been deliberately skipped for a documentation task (`independent_tests.signal_absent = false`); the model reported it as absent (`true`) and rejected the work. Measured four ways on the same prompt, same wire shape, three sends each:

| what was serving | result | receipt |
|---|---|---|
| the adapter on the **floating-point 8-bit** base, vLLM | **3 of 3 misreads** (reject each time) | `~/fine-tuning/output/coach-misread-lane-2026-09-04/g1b-live-prompt-replay.json` |
| the same adapter on the **16-bit** base, same vLLM | 0 of 3 (approve, no findings) | `~/fine-tuning/output/coach-misread-lane-2026-09-04/g1c-bf16-adapter-replay.json` |
| the **merged Q8_0** checker under llama.cpp (integer 8-bit) | 0 of 3 (approve) | same file |
| the **integer 8-bit group-64** checkpoint, vLLM, Marlin | 0 of 3, replies byte-identical to the 16-bit ones | `~/fine-tuning/output/int8-offline-checkpoint-2026-09-04/s2-exams.json`, section `a_live_prompt` |

So "8-bit" is not one thing: the floating-point form is the odd one out, confirmed twice, and integer 8-bit is clean on this prompt.

**Two honesty notes that must travel with those numbers.** First, three sends of one prompt establish a **direction, not a rate**; how often the floating-point base misreads across the real workload is not measured. Second, the receipt `s2-exams.json` states this result **backwards** in its headline and summary — it calls the correct behaviour a failure. The counts in it are right and the narrative is wrong. The correction sits beside it as `s2-INTERPRETATION-CORRECTION.txt` (2026-09-05, ~00:45 local) and the plan of record carries the polarity of record. Anyone reading that receipt must read the correction with it.

And the integer form is not a free win: in the checker's own exam it passed **4 of 6 repetitions** against 6 of 6 for both the floating-point and the 16-bit hosts, and both losses were the same shape — it approved a bundle carrying a real defect, which is the failure that matters most here. The specification-writer role was unharmed (16, 17, 17 out of 17, no runaway). Both from `s2-exams.json`.

**Root cause as far as known.** Not established. What the code says, read inside the pinned image on 2026-09-04 and written up in `RESEARCH-8bit-fidelity-adapter-host-gb10-2026-09-04.md`, section 1, is that our floating-point setting is the coarsest 8-bit scheme vLLM offers, and it differs from the integer form in two ways at once. It squeezes the **numbers flowing through the model** to 8 bits as well as the stored weights (`ScaledMMLinearKernel.py:159-161` for the dense layers; `prepare_finalize/no_dp_ep.py:14-37` for the expert inputs, which are scaled against the largest value in the current batch). And it gives an **entire expert matrix one scaling number** (`online/fp8.py:517-530`) where llama.cpp's Q8_0 gives one per 32 weights. Which of the two loses the word `false` is the open question; the research note's own conclusion is that it is not settled and that only running the two candidates apart would settle it.

**Workaround in use.** A deterministic guard in guardkit, commit `1447819d`: when the record says the signal is present and the test was skipped by profile, a checker finding claiming the signal is absent is dropped. It voids this specific wrong finding rather than fixing the model. Rich's decision of 2026-09-04 is that the floating-point shared host with that guard is the production arrangement; the plan of record carries it under "2026-09-04, ~18:55Z".

**Upstream status.** Nothing upstream matches this. The one report that looked relevant, [issue #30830](https://github.com/vllm-project/vllm/issues/30830) "accuracy issue on MoE online fp8 quantization", was **closed as completed on 2025-12-22** — seven months before our pinned release was published — by two merged changes, [#30831](https://github.com/vllm-project/vllm/pull/30831) (an Intel graphics fix) and [#30900](https://github.com/vllm-project/vllm/pull/30900) (a fix for streaming when a model is split across several graphics cards). We run one card with no split, so neither is our path, and the reporter's own diagnosis blamed weight loading. State re-confirmed 2026-09-05. Nothing in v0.28.0's changes touches the per-tensor floating-point expert accuracy question, so far as we could tell.

**What would justify filing. It is not close, and this entry exists partly to say so.** A filing would need a **minimal reproduction**: a public model, a short prompt, and a demonstration that the floating-point online path returns a different and demonstrably wrong answer where the 16-bit path does not — ideally reduced to something smaller than a 6,000-token checker prompt with a private adapter on a privately fine-tuned model. What we have is one prompt, three sends, on a private adapter, with a fine-tune in the loop, on a pinned old release. What is missing is: a rate rather than a direction; the same effect on a public model with no adapter; and a separation of the two mechanisms (running numbers versus weight scales), which the research note's candidates A and B were designed to do and which the memory wall in entry 3 prevented. Until all three exist, this is our fidelity finding and nobody else's business.

**Notes for later research.** The measurement that would turn a direction into a rate already exists on paper: the campaign's 48 real checker turns are all recoverable from receipts, and replaying them across hosts is about a two-hour job with two nine-minute swaps of the shared entry. The design, the confidence table (48 turns can detect a fault rate of one in five; it cannot distinguish "never" from "one in fifteen"), and the fences are in `RESEARCH-8bit-fidelity-adapter-host-gb10-2026-09-04.md`, section 4. It needs Rich's word because it posts to the shared entry and swaps it twice. Also outstanding: the third held-out checker case was never run on any base, and the research note names that as the next honest step before concluding anything more about the integer form.

---

## 8. The vLLM version pin itself

**Symptom.** Not a symptom — a choice, and the most consequential one here. We run `vllm/vllm-openai:v0.25.0-aarch64-cu129`, an image built 2026-07-11, while the latest release is v0.28.0. Anything read from newer documentation may not apply to us, and our drift check correctly reports the gap.

**Why v0.25.0, in order of how it was learned.**

- **August 23.** Adapter serving on this mixture-of-experts model was first made to work on a build from 23 April, and it needed **four fixes stacked**: our own patch to expose the expert mapping, our own converter to unpack the adapter per expert, an unmerged upstream change to stop the adapter being zeroed, and serving the exact base revision the adapter was trained on (worth 15 out of 17 → 17 out of 17). Recorded in `ai-transition/docs/software-factory-plan-of-record.md` around line 2190 and in the memory note `multi-lora-adapter-serving-path-2026-08-23.md`.
- **August 24, correction.** Three of those four turned out not to be needed on a current release. The expert-mapping failure had already been fixed **in v0.25.0, published 2026-07-11**, six weeks before we filed it upstream; we had been running a four-month-old binary from an image tagged `cu130-nightly`, because **a tag called "nightly" is not a nightly build**. Our issue [#53470](https://github.com/vllm-project/vllm/issues/53470) was **closed as not planned** and our [PR #53482](https://github.com/vllm-project/vllm/pull/53482) **closed unmerged** — both states re-confirmed 2026-09-05. That episode is the origin of the standing rule at the top of this document.
- **August 24, the run that set the pin.** On v0.25.0, unpatched, adapter serving scored **50 of 51** graded checks against a merged comparator that scored 17 of 17 three times; the one loss was a content slip, not a serving fault. `RESULTS-vllm-lora-adapter-serving-2026-08-24.md`.
- **August 24, the blocker.** **v0.27.1 cannot load this model at all**, proved by execution here, with and without adapters: `AmbiguousGlobalPerLayerAttributeError: 'head_dim' is a per-layer attribute and may vary across layers`, raised in vLLM's `get_head_size()`. `--hf-overrides` does not help, because the guard fires on *access*, not on the value. Same document.

**Workaround in use.** The pin, stated with its reasons in `RUNBOOK-vllm-lora-adapter-serving-gb10.md` under "PINS", and in the live launch script `/opt/llama-swap/scripts/gemma4-adapters.sh` as `IMAGE="vllm/vllm-openai:v0.25.0-aarch64-cu129"`.

**Upstream status — what v0.27.1 and v0.28.0 offer, and what is unproven.** All states checked 2026-09-05; containment checked by comparing each merge commit against the release tags.

| reference | what it is | state | in v0.25.0? | in v0.27.1? | in v0.28.0? |
|---|---|---|---|---|---|
| [PR #49797](https://github.com/vllm-project/vllm/pull/49797) "Fix Gemma 4 for upcoming Transformers version" | the fix for the loading failure above | **merged 2026-08-10** | no | **no** | **yes** |
| [PR #42662](https://github.com/vllm-project/vllm/pull/42662) "[LoRA][Gemma4] Support vision tower LoRA" | adapters on the image half of the model | **merged 2026-08-13** | no | no | **yes** |
| [PR #50833](https://github.com/vllm-project/vllm/pull/50833) "Fix dynamic INT8 W8A8 MoE config being built as W8A16" | changes the online integer expert path | **merged 2026-08-07** | no | no | **yes** |
| [PR #52502](https://github.com/vllm-project/vllm/pull/52502) GB10 expert tuning tables | speed only, floating-point only | **merged 2026-08-17** | no | no | **yes** |
| the recursive expert-mapping walk (the "adapter resolver" fix) | what makes adapters start at all on this model | in the release line | **yes** | yes | yes |

Release dates, from the GitHub releases interface today: v0.25.0 **2026-07-11**, v0.25.1 **2026-07-14**, v0.26.0 **2026-07-27**, v0.27.0 **2026-08-10**, v0.27.1 **2026-08-11**, v0.28.0 **2026-08-26**, and **v0.28.0 is the latest release**. Our images on disk were built 2026-07-11 (v0.25.0), 2026-08-11 (v0.27.1) and 2026-08-25 (v0.28.0) by `docker images`.

**v0.25.1, the small step nobody here has taken.** There is one release between our pin and everything above, and this register missed it until an independent review found it on 2026-09-05: **v0.25.1, published 2026-07-14**, three days after the image we run. It carries the one fix that would retire entry 13 — the video decoder that kills the server at start-up. Checked today at both tags: `vllm/multimodal/video.py` line 36 reads `except ImportError:` at v0.25.0 and `except (ImportError, RuntimeError):` at v0.25.1, which is exactly the widening that lets a broken decoder fall back to a placeholder instead of taking the process down, and exactly why issue #48592 was closed (its answering comment: "#47888 fixed this back on 2026-07-08 ... It is in v0.25.1 though (released today)"). So v0.25.1 is the cheapest candidate for dropping the removal step from our start scripts. **It is untested here, and nothing should be inferred beyond the two things checked above: the release date, and the widened guard in that one file.** An ARM image does exist to try — `docker manifest inspect vllm/vllm-openai:v0.25.1-aarch64-cu129` returned a manifest on 2026-09-05 (a read-only registry query; nothing was pulled, and the image is not on this box) — but no model has been loaded on it, and which transformers version it ships is **unverified**. By date it predates transformers 5.14.0 (2026-07-15), which would put it clear of the Gemma 4 break of entry 9, but that is an inference from dates, and inferences from dates are what entry 9 exists to warn about.

**What is unproven about v0.28.0, and it is the important half.** The image was probed on 2026-09-02 by importing the library only, no model and no graphics work (recorded in `multi-lora-adapter-serving-path-2026-08-23.md`): the import succeeds **without** the video-decoder removal of entry 13, it carries transformers **5.15.1** and torch **2.13.0+cu129**, and the Gemma 4 fix from #49797 is present in its model file. **Nobody has loaded or served this model on it.** Unknown until run: whether it loads and serves Gemma 4 here; whether an adapter is effective on it; whether the CUTLASS crash of entry 1 recurs; and whether its speed and answer quality match. The runbook's condition for moving the pin is explicit and unchanged: run the no-adapter control launch, the adapter start, and the effectiveness check on the v0.28.0 image first. Two upstream issues corroborating the loading failure remain **open** on 2026-09-05: [#51744](https://github.com/vllm-project/vllm/issues/51744) "vllm-openai:latest fails to start Gemma4 with Transformers 5.15.0" and [#53836](https://github.com/vllm-project/vllm/issues/53836) "NVIDIA DGX Spark vllms and gemma 4 26B won't work".

**What would justify filing.** Nothing about the pin itself. The loading failure that pins us is already fixed upstream and already reported by others. Note that #51744 and #53836 are both still open even though #49797 is merged and released — if we ever wanted to be useful upstream at zero risk, confirming on one of them that v0.28.0 resolves it would be a one-line factual comment, and it still needs Rich's word.

**Notes for later research.** There are now two pin moves worth separating: the small one to **v0.25.1**, which would retire entry 13 alone and changes almost nothing else, and the large one to **v0.28.0**, which is the single change that would retire entries 1 (possibly), 13 (probably) and part of 5. It costs a controlled run of about an hour and it must not be done during factory work. Whether the v0.28.0 image also fixes the video decoder is already answered yes by the import probe; whether it fixes anything else here is unmeasured.

---

## 9. The transformers library pin inside the image

**Symptom.** The version of the transformers library baked into the vLLM image decides whether this model loads at all — a coupling that is invisible from the vLLM version number.

**What the pinned image carries.** Read on 2026-09-05 from the running container's installed-package folders (`docker exec gemma4-adapters ls /usr/local/lib/python3.12/dist-packages/`): **transformers 5.13.0**, torch **2.11.0+cu129**, vllm **0.25.0+cu129**, compressed-tensors **0.17.0**.

**The break history, as the documents record it and as verified today.**
- transformers **5.13.0** released 2026-07-03; the v0.25.0 image was built 2026-07-11 and carries it.
- transformers **5.14.0** released 2026-07-15. `RESULTS-vllm-lora-adapter-serving-2026-08-24.md` records that this release introduced the machinery for models whose layers differ from each other (`integrations/heterogeneity/`), absent in 5.12.0 and present in 5.14.0. Not independently re-verified today.
- transformers **5.15.0** released 2026-08-10, and this is the release that actually breaks Gemma 4: [PR #47384](https://github.com/huggingface/transformers/pull/47384), "Use new `per_layer_config` for Gemma 4 so that heterogeneous attention config is explicit", **merged 2026-07-23**, checked today against the tags — **not in 5.14.0, contained in 5.15.0**. After it, a plain attribute read on such a configuration raises, and vLLM's head-size lookup does exactly a plain attribute read.
- transformers **5.15.1** released 2026-08-19 and is what the v0.28.0 image carries (probe of 2026-09-02). The latest transformers release today is **5.16.1** (2026-08-26).

**One correction to our own record, made honestly here.** Our August table listed v0.26.0 (2026-07-27, expected to ship transformers 5.14.x) as "expected no — untested". On the dates verified today, the Gemma-4-specific change reached transformers only in **5.15.0**, so v0.26.0 might in fact load this model. **That is an inference from dates, not a measurement — v0.26.0 has never been run here, and no image of it is on the box.** It is recorded because it is the kind of unverified assumption that costs a day.

**Workaround in use.** None needed: the pin in entry 8 carries the right library version with it. The coupling is documented in the runbook's PINS block.

**Upstream status.** transformers #47384 is **merged and released**, as above; it is a deliberate change, not a bug. The vLLM side of it is #49797, merged and in v0.28.0 (entry 8). Nothing to watch.

**What would justify filing.** Nothing. Both halves are resolved upstream.

**Notes for later research.** If the pin ever needs to move but v0.28.0 fails for some other reason, v0.26.0 is an untested intermediate worth ten minutes rather than a day.

---

## 10. The llama.cpp, GGUF and quantisation-aware-training findings that constrain our choices

**Symptom.** Not a defect — a set of measured limits that decide what we are allowed to compare against and what we may never serve. They belong in this register because they are the reason several entries above are framed the way they are.

**What was measured, and where.**
- **The comparator of record is a merged Q8_0 model file under llama.cpp** — integer 8-bit, one scale per block of 32 weights, arithmetic at 16 bits. File: `~/fine-tuning/output/coach-gemma4-26b-moe-v4/gguf_gguf/gemma-4-26b-a4b-it.Q8_0.gguf`, 26,859,844,512 bytes = 25.0 GiB. It answers the disputed prompt correctly 3 of 3 (entry 7). One correction that matters and is easy to get wrong: **that comparator is itself 8-bit, not 16-bit** — the only checker file on disk is the Q8_0 one. The plan of record records that correction at "Correction, 2026-09-04 ~16:30Z".
- **Post-training 4-bit destroys this tune.** One variable, greedy decoding, the identical 11,576-token prompt: the 8-bit form stopped cleanly at 2,756 tokens with 4 complete blocks and 9 scenarios; the 4-bit form ran to the 16,384-token ceiling with one unclosed block and 206 scenarios of which 25 were unique, three repeated 27 times each. `ai-transition/docs/software-factory-plan-of-record.md`, around line 2182.
- **Quantisation-aware training is worse, not better.** Three arms on the untuned base at the length that matters: the 8-bit form stopped with 4 blocks; post-training 4-bit looped 90 times but escaped; the quantisation-aware 4-bit base **never escaped**, produced 0 blocks and hit the ceiling. The premise — that a base trained for 4-bit tolerates the rounding — fails exactly where it was needed. Same plan-of-record entry, and the memory note `multi-lora-adapter-serving-path-2026-08-23.md`. Caveat recorded at the time: provenance was not perfectly controlled (Google's build versus our conversion), and the same build scored 6 of 6 on short prompts.
- **The standing rule that follows:** never serve this model family at 4-bit here, 4-bit "Q4_0" included.
- **Speed, for context:** single-stream, 16-bit under vLLM about 21 tokens a second against about 38 for the Q8_0 file under llama.cpp; vLLM's advantage is serving several requests at once, not single-stream speed (`adapter-serving-durable-facts-2026-09-02.md`).
- **One difference that must be stated whenever the two are compared:** llama.cpp can force the model's answer into a required shape, and vLLM ignores that request, so the comparison is not perfectly like for like. The record notes the shape permits both possible verdicts, so it cannot have forced the result (plan of record, "Correction, 2026-09-04 ~16:30Z").

**Workaround in use.** Not applicable; these are constraints, kept by rule.

**Upstream status.** Nothing. These are our own measurements of model files, not defects in anyone's code.

**What would justify filing.** Nothing.

**Notes for later research.** The interesting open question is why the integer 8-bit forms behave so differently from the floating-point one, which is entry 7's question and remains unsettled.

---

## 11. The memory dial does not give a fixed footprint

**Symptom.** The same `--gpu-memory-utilization 0.60` gave the adapter host 10.7 GiB of working cache (269,516 tokens) in one launch and 21.08 GiB (531,460 tokens) in another on 2026-09-03. vLLM sizes the cache from what is **free at the moment it measures**, up to the dial's target, so the process's total footprint changes with whatever else the box happens to be holding. On a clean box the process took 73 GiB, and loading a second model of about 26 GB on disk beside it drove free memory to zero and the kernel killed the model-routing proxy twice. Recorded in the memory note `gb10-vllm-kv-budget-not-deterministic.md`, with the kernel's own kill lines in `~/fine-tuning/output/vllm-switchboard2-2026-09-03/kernel-oom-tail.txt`.

**Root cause as far as known.** Documented behaviour of the dial, not a bug. It is a *ceiling expressed as a fraction*, measured against free memory at profile time — which on a box where graphics and main memory are one pool is a moving target.

**Workaround in use.** Set the cache in **bytes**, not as a fraction: `--kv-cache-memory-bytes 8589934592` (8 GiB) in `/opt/llama-swap/scripts/gemma4-adapters.sh`. The flag exists in the pinned release at `vllm/config/cache.py:173` (verified in the image 2026-09-05), and its own documentation says that when set it ignores the fraction. Measured effect — and it matters which arrangement it was measured on. On 2026-09-03, serving the **16-bit** base, the process cost about **73.9 GiB** of free memory whatever else was resident (51 GiB of weights, the 8 GiB cache, the graphics context, the shared-memory segment and the host-side adapter copies); the server logged that it had reserved exactly 8 GiB and skipped its memory profiling, and the profiling lines disappeared from the log. **That number is not today's.** Production has served the 8-bit floating-point base since 2026-09-03 by Rich's decision of 2026-09-04 (plan of record); the production start-up script of record is the dated backup `/opt/llama-swap/scripts/gemma4-adapters.sh.bak-20260904-8bit-live`, which carries `--quantization fp8`. Readers on 2026-09-05 should know the live script was temporarily swapped to its 16-bit backup from about 07:44Z for the coach-rate measurement lane, which restores it byte-identical and proves the restore, so the live file was not the FP8 one while this register was being corrected. The same memory note records that arrangement at **28.3 GiB of weights**, with the host alone leaving about **54.5 GiB** free where the 16-bit one left 32.4 GiB. Budget today's box from the 8-bit figures; the 73.9 GiB figure is kept here because it is where the flag's behaviour was measured, not because it describes what is running now. The script keeps the old fraction on the command line as a written record of the previous ceiling, with a comment saying it no longer decides anything.

**Upstream status.** Nothing to report — this is the flag working as documented, and the fix is to use the other flag. No upstream search was made because there is no defect to search for.

**What would justify filing.** Nothing.

**Notes for later research.** The practical sizing rule from our measurements: this model costs roughly 43 KiB of cache per token, so 8 GiB is about 200,000 tokens, and one full-length request at our 131,072-token ceiling fits inside that with room to spare.

---

## 12. Driver out-of-memory lines in the kernel log during a load

**Symptom.** During heavy loads the kernel log carries lines of the form `NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] … @ mem_desc.c`. They look alarming and are not, by themselves, a kill.

**Counts, measured today from the kernel log with `journalctl -k` (times are the box's local time, which is one hour ahead of UTC):**

| window | what was happening | `NV_ERR_NO_MEMORY` lines |
|---|---|---|
| 2026-09-04 19:20–19:40 local | ordinary floating-point 8-bit host running | **0** |
| 2026-09-04 22:00–22:15 local (21:00–21:15Z) | the aborted load-time integer attempt of entry 3 | **223** |
| 2026-09-04 23:05–23:12 local | the watchdog-stopped Marlin load of entry 4 | **0** |
| 2026-09-05 00:20–00:35 local (2026-09-04 23:20–23:35Z) | the successful group-64 integer load | **247** |

By way of a baseline, counted again on 2026-09-05 across everything the kernel log holds — it starts at the boot of 2026-08-13, so "since August" means since the 13th — **most hours carry none of these lines at all**: 68 of the roughly 600 hours in the log carry any, and the ordinary ones among those carry between one and seventeen. Two hours outside the four windows above carry a load-sized burst of their own: 2026-08-21 18:00 local (128 lines) and 2026-09-05 08:00 local (200 lines and still rising as this was written, while another window's experiment was loading on the box). A single line was also recorded during a floating-point exam on 2026-09-03 while a second model was loading, and was written up then exactly as it should be: "It is not a process kill and nothing was killed; the load finished and answered 25 seconds later. Recorded, not acted on" (`~/fine-tuning/output/vllm-fp8-exam-2026-09-03/f3-memory.json`, with the raw lines in `kernel-f3.txt`).

**One correction to the brief this register was written from.** It expected "about 5 on floating-point loads, about 200 on the integer group-64 load". The second figure checks out (247). The first does not: the floating-point load window measured **zero**, and the "handful" figure is not a per-load count at all — it is a background rate, and a thin one, since most hours of the log carry nothing.

**Root cause as far as known.** The driver failing an internal allocation and retrying. On a shared memory pool it is an ordinary consequence of being near the limit.

**Workaround in use.** None, and none wanted. The rule is: **only a kernel "Killed process" line or a container reporting it was killed for memory counts as an event.** A driver warning is an early-warning signal to watch, never a thing to act on. That rule is recorded in `gb10-vllm-kv-budget-not-deterministic.md` and was applied correctly on 2026-09-03.

**Upstream status.** Not applicable — this is the NVIDIA driver, not vLLM, and it is not a defect report.

**What would justify filing.** Nothing.

**Notes for later research.** The counts above are a usable rule of thumb: a load that produces two hundred of these lines is a load that is straining the pool, even if nothing dies. That makes it a cheap health signal for any future experiment, alongside the memory watchdog.

---

## 13. The pinned image ships a video decoder built for the wrong CUDA version

**Symptom.** The `v0.25.0-aarch64-cu129` image contains a `torchcodec` built against CUDA 13 (`libnvrtc.so.13`) inside a CUDA 12.9 image with torch 2.11.0+cu129. It fails when vLLM imports it, **before any model work**, and kills the server. vLLM guards that import against a missing package but not against a broken one, so an **absent** decoder degrades gracefully and a **present-but-broken** one is fatal. Recorded in `RESULTS-vllm-lora-adapter-serving-2026-08-24.md` and repeated in every later results document.

**Root cause as far as known.** An image packaging mismatch: a component built for one CUDA version shipped inside an image built for another. Not a vLLM logic error, though the narrow exception handling turns a packaging slip into a fatal one.

**Workaround in use.** The container start command begins by deleting it: `rm -rf /usr/local/lib/python3.12/dist-packages/torchcodec* && exec vllm serve …`. It is in the live launch script `/opt/llama-swap/scripts/gemma4-adapters.sh` and in every experimental start script. We decode no video, so nothing is lost. The runbook is emphatic that this must always be said out loud, so that "unpatched" never quietly covers it.

**Upstream status.**
- [Issue #48592](https://github.com/vllm-project/vllm/issues/48592), "v0.25.0 torchcodec not compatible with cu129 wheel" — opened 2026-07-14, **closed as completed 2026-07-15**. Verified 2026-09-05. Same release, same mismatch, reported by someone else within three days of us needing it. It was closed because the fix had already shipped: the issue's answering comment reads "#47888 fixed this back on 2026-07-08 by widening the except to (ImportError, RuntimeError) ... It is in v0.25.1 though (released today)".
- [Issue #54097](https://github.com/vllm-project/vllm/issues/54097), "installed-but-unloadable torchcodec breaks video requests — OSError escapes the guards" — opened 2026-08-27, **open**. This is the wider version of the problem: the guards catch a missing package but not an unusable one.
- **The fix is one patch release away, and this register missed it until an independent review on 2026-09-05 found it.** [v0.25.1](https://github.com/vllm-project/vllm/releases/tag/v0.25.1) was published **2026-07-14**, three days after the image we run. Verified today by fetching `vllm/multimodal/video.py` at both tags: line 36 reads `except ImportError:` at v0.25.0 and `except (ImportError, RuntimeError):` at v0.25.1, so a broken decoder falls back to a placeholder there instead of killing the server. **v0.25.1 is the cheapest candidate for retiring the removal step, and it is untested here.** An ARM image exists to try — `docker manifest inspect vllm/vllm-openai:v0.25.1-aarch64-cu129` returned a manifest on 2026-09-05, a read-only registry query with nothing pulled and the image not on this box — but nothing has been loaded on it and the transformers version it carries is unverified. See entry 8.
- **What changed between v0.25.0 and v0.28.0 for this item.** The v0.28.0 image imports cleanly **without** the removal step (probe of 2026-09-02, no graphics work), so the packaging defect appears not to be present there. Whether the narrow exception handling of #54097 was also changed is **unverified**.

**What would justify filing.** Nothing. It is reported and closed for our release, and the general case is reported and open.

**Notes for later research.** Keep the removal step in every start script until a real model load — on v0.25.1 or on v0.28.0 — proves it unnecessary in practice, not only on import. v0.25.1 is the smaller of the two tests and would settle this entry on its own.

---

## 14. Per-expert adapter weights are skipped in silence when their names do not match

**Symptom.** The most expensive defect in this register, because it fails without a single error message. On 2026-09-02, four of five adapters were serving with **the whole expert half of the adapter switched off**, and every symptom pointed at model quality instead. Corrected adapter numbers changed nothing; seven, six and seven of the eight answers in three repetitions were textually identical before and after the correction. The server's own debug log, once turned on, told the truth:

| adapter served | export version | expert blocks that got weights | expert blocks reset to zero |
|---|---|---|---|
| four of the five | version 2 | **0 of 30** | 30 |
| the checker, renamed | **version 3** | **30 of 30** | **0** |

Receipt: `RESULTS-vllm-adapter-controls-2026-09-02.md`, "The adapter path's two defects, in series", with the per-module report at `~/fine-tuning/output/vllm-control2-2026-09-02/lora-module-load-report.json`. The renamed export then scored **6 of 6** where the same numbers under the old names scored **0 of 6** on the same server in the same launch.

**Root cause as far as known.** Two things, one ours and one vLLM's.

Ours: our first converter packed one factor of each expert by striding rather than contiguously, which produced numerical noise (measured against the merged model's own before-and-after difference: 0.038 and 0.068 on a similarity scale where a true match scores 0.80 to 0.94). Fixed in converter version 2.

vLLM's: the key it builds for a per-expert adapter comes from the module's real path, which for this model is `…layers.N.moe.experts.E.{gate_proj, up_proj, down_proj}`. Our exports wrote `…layers.N.experts.E.*` without the `.moe.`. **vLLM finds nothing, skips the module without printing a warning, resets it to zero, and serves the attention half only.** And the image already contains the exact repair — `_remap_gemma4_expert_weight_name`, confirmed today at `gemma4.py:88` in the running container, with its **single** call site at `gemma4.py:1661` inside the base model's weight loader. It is never called from the adapter loader.

**Workaround in use.** Converter version 3 writes the path vLLM looks under by default (`~/fine-tuning/scripts/convert_moe_lora_to_per_expert.py`, with `--legacy-expert-path` to reproduce the old names), and every export carries a `rename-v3.json` recording what it renamed — 23,040 of 23,450 keys. The exports in use are under `~/fine-tuning/output/vllm-exports-v3/`. The durable rule that came out of it, recorded in `adapter-serving-durable-facts-2026-09-02.md`: an export is verified only when its per-expert reconstruction matches the merged model's difference at about 0.8 or better, **and** the server's debug log shows every expert module loaded for that adapter, **and** an exam matches. Shape equality proves nothing.

**Upstream status.**
- [PR #50252](https://github.com/vllm-project/vllm/pull/50252), "[Bugfix][Gemma4] Map stacked expert LoRA tensors onto the MoE parent module" — opened 2026-07-29, **open and unmerged** on 2026-09-05. Its own opening sentence is our symptom exactly: "Stacked ('3D') expert LoRA adapters for Gemma-4 MoE load without error and then apply **no expert deltas at all** — silently." It concerns the adapter format our training tool exports, and it names the same name-rewriting helper.
- [PR #55310](https://github.com/vllm-project/vllm/pull/55310), "[Bugfix][LoRA] Reject adapters with no matching target modules" — opened 2026-09-04, **open and unmerged**. It makes an adapter that matches nothing fail loudly instead of silently serving the base model. It fixes issue #55193.
- [Issue #39815](https://github.com/vllm-project/vllm/issues/39815), "Gemma4 LoRA adapters zeroed out" — **closed as not planned on 2026-09-02, by the inactivity robot**, not by a fix. Its fix, [PR #39816](https://github.com/vllm-project/vllm/pull/39816), is **open and unmerged**. Note the standing puzzle, recorded and never explained: on v0.25.0 the adapter is demonstrably effective even though that fix is unmerged. Do not infer why.
- **What changed between v0.25.0 and v0.28.0 for this item: nothing merged.** All three of the above are open.

**What would justify filing.** This is the entry where our finding is closest to being genuinely new, and it is still not clean. Two halves:
- The **mapping** half — that the expert path needs the `.moe.` inserted — is already reported in #50252 by someone with a fuller analysis than ours.
- The **silence** half — that vLLM skips an unmatched per-expert module, resets it to zero, and logs nothing above debug level — is only partly covered by #55310, which rejects adapters where *nothing* matches. Ours matched the attention modules, so it would still slip through: the adapter is half-applied and nobody is told. A warning on any per-expert module that finds no weights would have saved us a week.
- The minimal reproduction would be: a public Gemma 4 mixture-of-experts adapter exported with the legacy names, loaded on a current release, with the server showing 30 expert modules reset to zero and no warning above debug. We have all of that except on a **public** adapter and on a **current** release: our evidence is a private adapter on v0.25.0. Since #50252 already sits open and unmerged, the cheap and low-risk move is to add our per-module load-report evidence there rather than open anything — and that, like everything else, waits for Rich.

**Notes for later research.** Our own open item from 2026-09-02 was recorded as "report vLLM's silent expert-adapter skip upstream". It has not been done and should not be done without Rich's word. If the pin moves to v0.28.0, re-check whether the debug-only silence still holds — that is a five-minute check during a start we would be doing anyway.

---

## 15. Greedy answers are not repeatable, and the deterministic mode makes long answers run away

**Symptom.** Two related surprises about repeatability, both measured.

First: at temperature zero — which is supposed to be deterministic — the plain base model gives the same answer three times, while none of the four adapters repeats itself: in three sends each, the product-owner version 5 export, the checker and the plan-writer each gave **three different answers**, and the product-owner version 6 export gave **two** — one answer twice and a different one once (`~/fine-tuning/output/vllm-multi-2026-09-02/determinism-by-model.json`, read again 2026-09-05: `distinct_md5` 3, 3, 3 and 2 against the base's 1, `all_reproducible: false`; also written up in `RESULTS-vllm-multi-adapter-slots-2026-09-02.md`). Base repeatable, adapters not, which points at the adapter path rather than at sampling. It means an exam re-run cannot be compared to itself byte for byte.

Second: vLLM has a mode that makes results repeat exactly regardless of what else is being answered at the same time (`VLLM_BATCH_INVARIANT=1`). Turning it on **fixed** the repeatability, at about 1.3 times the compute per word — and **broke long generation on the adapter path**: the specification-writer role ran away to the 16,384-token ceiling producing 203 scenarios of which 19 were distinct, one tag repeated 196 times, where the merged comparator was clean. With the mode **off**, the same role on the same export scored 17 of 17 and stopped on its own. Recorded in `adapter-serving-durable-facts-2026-09-02.md` ("2026-09-03 S8b — THE RUNAWAY WAS THE MODE") and in `RESULTS-vllm-adapter-followup-2026-09-02.md`.

A further limit on that mode: it held for one exam at 11,802 prompt tokens (three byte-identical replies) but **not** at 20,927 tokens, where the same request stopped early whenever other requests were in flight. Treat determinism as bounded by sequence length on this build.

**Root cause as far as known.** Neither half is root-caused. Both are recorded as measured behaviour of this release on this chip with this adapter path.

**Workaround in use.** The deterministic mode stays **off** for the gated roles, and non-byte-exact repeatability is accepted — llama.cpp never gave us byte-exactness either. The rule and its reason are in the live launch script's comments (`NO VLLM_BATCH_INVARIANT: deterministic kernels made the product-owner seat run away`) and in `adapter-serving-durable-facts-2026-09-02.md`.

**Upstream status.** No upstream report was found for either half in searches of the vLLM tracker on 2026-09-05. That is a weak negative: the searches were by keyword, not exhaustive.

**What would justify filing.** For the non-repeatability: a minimal case on a **public** adapter and a public base showing the base repeatable and the adapter not, at temperature zero, on a current release. For the runaway: the same, with the deterministic mode on and off, on a long generation. We have neither on public material, and both are entangled with our own export path (entry 14) — which is precisely the sort of entanglement that produced our stale August report. Not close.

**Notes for later research.** The two are probably related — a deterministic-kernel path that changes behaviour with sequence length and an adapter path that is not deterministic when it should be are both about how the adapter's contribution is accumulated. Nobody has looked.

---

## 16. The base snapshot pin

**Symptom.** Serving a different revision of the same base model, with the same adapter, scored **15 of 17** where the correct revision scored **17 of 17**. A revision mismatch looks exactly like a bad adapter, and it is silent. `RESULTS-vllm-lora-adapter-serving-2026-08-24.md`, "Reproduce", and the runbook's PINS block.

**Root cause as far as known.** Expected behaviour, not a defect: an adapter learns a difference against a particular set of numbers, and a different revision is a different set of numbers. It is in this register only because the failure is silent and looks like something else.

**Workaround in use.** The revision is pinned in the launch script: `SNAP=".../models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819"`, mounted read-only. It is the revision the adapters were trained on. The runbook states it as load-bearing.

**Upstream status.** Not applicable.

**What would justify filing.** Nothing.

**Notes for later research.** Any future retrain must record the revision it trained against, in the same place the adapter is stored.

---

## What is NOT in this register

Things deliberately left out, and why, so that their absence is not read as an oversight.

- **Our own bugs.** The converter's striding error (entry 14) and the exam harness's field-name mismatches were ours, are fixed, and are recorded in the results documents. Only the vLLM half of entry 14 is registered here.
- **Operating rules that are not defects.** The start-order rule (the adapter process must be resident before any large llama.cpp model loads, kernel-proven 2026-09-03), the check that no build is running before anything shared on the box is touched (the build service must show nothing running, paused or queued), the memory watchdog, and the "never restart the build service unless every build has finished" rule. These are how we run the box, not faults in anyone's software. They live in `adapter-serving-durable-facts-2026-09-02.md` and the runbook.
- **The 4-bit NVFP4 question.** Closed for this purpose on 2026-09-03 and again in the 2026-09-04 research note: it moves further in the direction that hurt us, its only adapter-capable kernel here is the slow one, and it needs a third-party checkpoint our adapters were never trained against. `RESEARCH-fp8-vs-nvfp4-adapter-host-gb10-2026-09-03.md` carries the model cards and the forum measurements. Not a defect register item.
- **Offline conversion routes we chose not to take** — calibrated static schemes, GPTQ and AWQ at 8 bits, and integer weight-and-activation schemes. Each needs a conversion run of unmeasured length here, produces a checkpoint the adapters were never trained on, and lands somewhere a flag already reaches. Reasons in the research note, section 2, candidates D through G.
- **Speed differences that are the scheme working as designed.** Marlin doing 16-bit arithmetic on 8-bit weights is slower on purpose; that is entry 6's context, not a bug.
- **Other people's reports we merely read.** The NVIDIA developer-forum threads on integer 8-bit on this chip, on 4-bit throughput, and on toolchain rebuilds are cited in the research notes as leads. They are not our observations and none is registered as our defect.
- **Anything filed upstream.** Nothing in this register has been filed, and nothing will be without Rich asking for it in that instance. The two things we did file in August (#53470 and #53482) were both closed without being merged, and the lesson from that is the first paragraph of this document.
