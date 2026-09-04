# Is there an 8-bit form with the fidelity of the merged seats? What the code in our own image says

Date: 2026-09-04. Written for Rich's decision. Nothing on the box was changed to write this: no model, container or service was started, stopped or reconfigured, no exam was run, and nothing was sent to the switchboard. Every claim below is either a reading of the code inside the image we actually run, with the file and line quoted, or a number from a receipt on this machine, or a public source with the date I read it.

## The question

On 2026-09-04 we established, with receipts, that the coach agent running as an adapter on the **8-bit** shared base misreads a plain true/false value in its own evidence three times out of three, and that the *same* adapter on the **16-bit** base gets it right three times out of three, and that the older merged coach seat under llama.cpp — which stores its weights as 8-bit whole numbers — also gets it right three times out of three. So "8-bit" is not one thing. One kind of 8-bit breaks the coach and another kind does not.

Rich's decision of 2026-09-04 stands: the 8-bit shared host with a deterministic guard is production now. This note asks two follow-on questions:

1. **What is our 8-bit actually doing** that the llama.cpp 8-bit is not, and where does the fidelity loss most plausibly come from?
2. **Is there an 8-bit form on our path** — the vLLM adapter host, on this chip, with runtime adapters — that keeps the memory saving but behaves like the llama.cpp form? And how would we measure the misread rate properly rather than from three sends?

## Short answer

Yes, and it is one flag.

Our `--quantization fp8` is the *coarsest* 8-bit scheme vLLM offers. It squeezes **both** the stored weights **and** the numbers flowing through the model at run time into 8 bits, and it uses a **single** scaling number for an entire weight matrix — for the expert layers, one number for each expert's whole gate-and-up matrix. The llama.cpp form our merged coach uses (called Q8_0) does neither of those things: it leaves the running numbers at full 16-bit precision and it uses a separate scaling number for every block of 32 weights. Those are the two differences, and both push in the direction of the fault we saw.

The pinned image already contains a scheme much closer to the llama.cpp one, reachable from the command line with no new model file, no conversion, and no third party:

```
--quantization int8_per_channel_weight_only --moe-backend triton
```

That stores the expert weights as 8-bit whole numbers with a separate scale for every output row, leaves the running numbers at 16-bit, leaves the dense layers at 16-bit entirely (so the crashing CUTLASS kernel is never reached), and runs on the Triton expert kernel — the same kernel we run today, and one of only three in the whole image that carries the adapter hook. Estimated weight cost: about **30 GiB**, against 28.3 GiB today and 51.04 GiB at 16-bit.

Two others are worth a look and are also one flag each. None of the four needs an offline conversion. The offline routes (llm-compressor, GPTQ, AWQ) all cost hours, need a new checkpoint our adapters were never trained against, and buy nothing the flags do not.

And the measurement: the campaign's 48 real coach turns are all recoverable from receipts. Replaying them on both hosts is roughly a two-hour job with two nine-minute member swaps. Be warned up front what 48 turns can and cannot settle: if the 8-bit host disagrees with the record on none of the 48, that only proves the true rate is under about 7 percent. It cannot prove zero.

## What the words mean

Read this once and the rest reads plainly.

- **16-bit / bf16** — the way weights normally come. Each number takes two bytes.
- **8-bit** — each number takes one byte. Half the memory. There is more than one way to do it.
- **FP8** — one of those ways: an 8-bit *floating point* number. The variant everyone uses, and the one on this chip, is called **e4m3**: 4 bits of exponent, 3 bits of fraction, one of sign. It has wide reach but only about two significant decimal digits of precision.
- **INT8** — the other way: an 8-bit *whole number* from −127 to 127, plus a separate full-precision **scale** that says what "1" means. Same one byte, but the precision is spread evenly instead of concentrated near zero.
- **Q8_0** — llama.cpp's INT8 format, and the one our merged coach seat uses. It splits every weight row into blocks of 32 and gives each block its own scale. ([GGUF format explainer, read 2026-09-04](https://zeroentropy.dev/concepts/gguf/): "Legacy quants stored an FP16 scale per block of 32 weights".)
- **Scale granularity** — how many weights share one scale. **Per-tensor** means one scale for the whole matrix (coarsest). **Per-channel** (also called per-row) means one scale for each output row. **Per-block** means one scale per fixed group, such as Q8_0's 32.
- **Weights** are the stored model. **Activations** are the numbers flowing through it while it answers, which depend on the prompt.
- **W8A8** — weights 8-bit *and* activations 8-bit. **W8A16** — weights 8-bit, activations left at 16-bit. W8A16 is often called "weight-only".
- **Calibration** — running sample prompts through a model beforehand to learn how big its activations get, so fixed scales can be chosen. Needed for "static" schemes; not needed for "dynamic" ones, which measure as they go.
- **Kernel** — the hand-written GPU routine that does the actual multiplication. Different kernels support different combinations of the above.
- **Triton** — a way of writing GPU kernels in Python. vLLM's Triton expert kernel is what we run today.
- **Marlin** — a family of kernels written for weight-only work: they read 8-bit (or 4-bit) weights, expand them back to 16-bit inside the chip, and multiply at 16-bit. Slower than native 8-bit maths, but it never touches the activations.
- **CUTLASS** — NVIDIA's high-performance kernel library. Its dense 8-bit kernel crashes on this chip, which is why our launch line says `--linear-backend torch`.
- **compressed-tensors / llm-compressor** — Red Hat's file format and conversion tool for making pre-quantised model files offline.
- **LoRA adapter** — the small trained file that turns the shared base into "the coach" or "the planner". The **adapter hook** is the code inside an expert kernel that lets the adapter's contribution be added; a kernel without it cannot serve adapters at all.
- **MoE / experts** — this model is a mixture of experts: 128 small expert networks per layer, of which a few fire per token. They are 22.8 of the model's 27 billion weights, so what happens to the experts is what happens to the model.

## 1. What `--quantization fp8` actually does on our path

All file paths below are inside the pinned image `vllm/vllm-openai:v0.25.0-aarch64-cu129`, under `/usr/local/lib/python3.12/dist-packages/`. I read them with `docker exec gemma4-adapters cat`/`grep`/`sed` — read-only, no code run inside the live container.

### It is W8A8, not weight-only

Our checkpoint is a normal 16-bit one, so vLLM takes the "online" road — quantise while loading, rather than read a pre-quantised file:

- `vllm/model_executor/layers/quantization/fp8.py:185-192` — for dense layers, when the checkpoint is not already FP8, it returns `Fp8PerTensorOnlineLinearMethod`.
- `vllm/model_executor/layers/quantization/fp8.py:210-217` — for the expert layers, same test, returns `Fp8PerTensorOnlineMoEMethod`.

For the dense layers, the activations are quantised too:

- `vllm/model_executor/layers/quantization/online/fp8.py:117-122` — the weight scheme is fixed to per-tensor (`kFp8StaticTensorSym`); the activation scheme is set to **per-token FP8** if the chip reports CUTLASS FP8 support, per-tensor FP8 otherwise. Either way, the activations are quantised.
- `vllm/model_executor/kernels/linear/scaled_mm/ScaledMMLinearKernel.py:159-161` — the line that does it: `x_2d_q, x_s = self.quant_fp8(x_2d, x_s, x_s_ub)`. The prompt's own numbers are squeezed into 8 bits immediately before the multiply.

Our own server's start-up log confirms which branch was taken. From `docker logs gemma4-adapters` (the live container, started 2026-09-04 18:25Z):

```
INFO 09-04 18:26:11 [model_executor/.../linear/__init__.py:631]
  Selected ChannelWiseTorchFP8ScaledMMLinearKernel for Fp8PerTensorOnlineLinearMethod
```

`ChannelWise…` is chosen precisely *because* the activation scale is per-token and the weight scale is per-tensor (`vllm/model_executor/kernels/linear/scaled_mm/pytorch.py:177-186`). And the same log's compilation counter reads `'quant_fp8': 120` — 120 activation-quantisation operations compiled into the graph. There is no reading of that line under which the activations stay at 16 bits.

### The weight scales are as coarse as they get

- Dense layers, `online/fp8.py:159`: `ops.scaled_fp8_quant(layer.weight, scale=None)` — **one** scale for the entire weight matrix.
- Expert layers, `online/fp8.py:517-530`: `w13_scale = torch.ones(layer.num_experts, ...)` then a loop that fills one scalar per expert. So for each of the 128 experts in each of the 30 layers there is **one** number covering a 1,408 × 2,816 matrix — 3.96 million weights sharing a single scale.

For comparison, Q8_0 gives 3.96 million weights **123,904** separate scales. That is the size of the gap.

### What the Triton expert kernel does with the expert inputs

- `online/fp8.py:521-522` sets `w13_input_scale = None` and `w2_input_scale = None`, so no fixed activation scale is stored.
- `online/fp8.py:407-408` picks the pair (weights per-tensor, activations **dynamic per-tensor**) for the kernel choice.
- `vllm/model_executor/layers/fused_moe/experts/triton_moe.py:246-250` is where it happens: `moe_kernel_quantize_input(hidden_states, self.a1_scale, ...)`. With `a1_scale` empty, the kernel measures the largest value in the batch of expert inputs on the spot, derives one scale from it, and squeezes every input into 8 bits against that one number. Line 450 does the same again for the second matrix in each expert.

Our log confirms the backend: `Using TRITON Fp8 MoE backend out of potential backends: [...]` (oracle/fp8.py:325), and `Swapping out Fp8PerTensorOnlineMoEMethod` once for each of the 30 expert layers.

### What `--linear-backend torch` does

It restricts the dense-layer kernel choice to three PyTorch-native ones (`vllm/model_executor/kernels/linear/__init__.py:264-268`), of which `ChannelWiseTorchFP8ScaledMMLinearKernel` is the one that fits. That kernel (`scaled_mm/pytorch.py:220-239`) calls `torch._scaled_mm` with dummy scales, gets a raw integer-ish product back, and multiplies the scales in afterwards. **It does not avoid activation quantisation**; it only avoids CUTLASS, which crashes here. The crash is on the record: `RuntimeError: cutlass_gemm_caller, /workspace/csrc/libtorch_stable/quantization/w8a8/cutlass/c3x/cutlass_gemm_caller.cuh:62, Error Internal` (`/home/richardwoollcott/fine-tuning/output/vllm-fp8-exam-2026-09-03/f1-fp8-host.json`).

### So where does the fidelity loss most plausibly come from?

Three suspects, in the order I would bet on them.

**First, the activation quantisation of the expert inputs.** This is the one that best fits the symptom. The coach's fault was not a wobble in its prose — it read the word `false` in its evidence and acted on `true`, three times running, at temperature zero. That is a small, specific piece of the prompt being lost. Expert inputs are quantised *dynamically against the largest value in the batch*: one very large number anywhere in the batch shrinks the scale, and every small number in it loses resolution. Mixture-of-experts models are known to be bad at this; the published diagnosis is that "MoE models exhibit highly heterogeneous activation distributions... direct computation of FP8 activation scaling factors results in underfitting of rare experts, leading to substantial accuracy degradation" (search result summarising the MoE FP8 literature, read 2026-09-04; and vLLM's own bug [#30830, "accuracy issue on MoE online fp8 quantization"](https://github.com/vllm-project/vllm/issues/30830), opened 2025-12-17, still open, reports incoherent output from exactly this online FP8 MoE path on Qwen3-30B-A3B).

**Second, the per-tensor weight scale.** 3.96 million weights on one scale means the small weights in a matrix with any large outlier are stored at a fraction of the precision the format could give them. This is the difference Q8_0's blocks of 32 exist to remove.

**Third, e4m3's shape.** FP8 spends bits on exponent range it does not need for weights that have already been scaled into range, leaving about 3 bits of fraction. INT8 with a good scale spends all 8 bits on the value.

**Why the llama.cpp Q8_0 form shows none of this.** Q8_0 changes only the stored weights. Every number the model computes with while answering stays at 16 bits — llama.cpp expands each block back to 16-bit and multiplies at 16-bit. And the stored weights lose almost nothing, because a scale per 32 weights tracks the local range closely; the community measurement of record is a perplexity change of about 0.01 against full precision ([GGUF quantisation levels, read 2026-09-04](https://tinyweights.dev/posts/gguf-quantization-levels-q4-q5-q8/)). So the merged coach is, for all practical purposes, doing 16-bit arithmetic on very slightly rounded weights. Our FP8 host is doing 8-bit arithmetic on heavily-rounded weights *and* 8-bit arithmetic on the prompt.

That is the whole difference, and it says plainly which lever to pull first: **stop quantising the activations.**

## 2. The candidates

Only three expert kernels in the entire image carry the adapter hook. This is the crux and it constrains everything:

```
vllm/model_executor/layers/fused_moe/experts/triton_moe.py:54
    class TritonExperts(LoRAExpertsMixin, mk.FusedMoEExpertsModular)
vllm/model_executor/layers/fused_moe/experts/marlin_moe.py:701
    class MarlinExperts(LoRAExpertsMixin, MarlinExpertsBase)
vllm/model_executor/layers/fused_moe/experts/gpt_oss_triton_kernels_moe.py:1059
    class UnfusedOAITritonExperts(LoRAExpertsMixin, BaseOAITritonExperts)
```

(grep for `LoRAExpertsMixin` across the image, 2026-09-04.) The third is for a different model family. So every candidate below has to land on **TritonExperts** or **MarlinExperts**, or it cannot serve adapters at all — vLLM asserts on it and refuses to start (`vllm/lora/layers/fused_moe.py:423`).

The pinned image accepts these names on `--quantization`, listed in `vllm/model_executor/layers/quantization/__init__.py:12-46` and defined in `vllm/config/quantization.py:114-137`:

| name | what it sets |
|---|---|
| `fp8` | today's setting: per-tensor FP8 weights, FP8 activations, both dense and experts |
| `fp8_per_tensor` | the same scheme, stated explicitly |
| `fp8_per_channel` | per-output-row FP8 weights, per-token FP8 activations, both dense and experts |
| `fp8_per_block` | FP8 weights with a scale per 128×128 block, activations per 1×128 block |
| `int8_per_channel_weight_only` | INT8 experts with a scale per output row; **activations left at 16-bit**; dense layers untouched |
| `mxfp8` | FP8 with a scale per block of 32, needs SM 100+ for 8-bit activations |

vLLM's own documentation confirms the reading of the important one: for `int8_per_channel_weight_only` it says "Quantizes: weights only" ([vLLM online quantization docs, read 2026-09-04](https://docs.vllm.ai/en/latest/features/quantization/online/)). The same page confirms that dense and expert layers can be given different schemes: "You can apply different quantization schemes to dense linear layers and MoE expert layers via the `linear` and `moe` fields."

### Candidate A — INT8 experts, per-row scales, 16-bit activations (`int8_per_channel_weight_only`)

**This is the closest thing in the image to the llama.cpp form, and it is one flag.**

- **What it quantises.** Only the expert weights, and only the weights. `vllm/model_executor/layers/quantization/online/int8.py:57-88` walks each expert, takes the largest absolute value **in each output row**, divides, rounds and clamps to −127…127, and stores the row's scale. Nothing else in the model is touched: the shorthand sets a `moe` spec and no `linear` spec (`vllm/config/quantization.py:134-136`), so the dense layers keep their 16-bit weights and their 16-bit arithmetic.
- **Are the activations quantised?** No. `online/int8.py:118-128` builds the run-time config without any activation scales, and `vllm/model_executor/layers/fused_moe/oracle/int8.py:207-215` therefore returns `int8_w8a16_moe_quant_config` — "Construct a quant config for 16-bit float activations and int8 weights" (`vllm/model_executor/layers/fused_moe/config.py:943-963`, which leaves the activation descriptors with no data type at all).
- **Scale granularity.** One scale per output row. For this model that is 1,408 scales where FP8 has 1, per expert, per layer — 123,904 scales per layer where FP8 has 128. Coarser than Q8_0's blocks of 32 along the input direction, but roughly a thousand times finer than what we run today.
- **Does the kernel exist on this chip?** Yes, and it is the one we already run. `oracle/int8.py:93-104` maps `--moe-backend triton` to the Triton backend and `oracle/int8.py:62-67` returns `TritonExperts`. `TritonExperts._supports_quant_scheme` (`triton_moe.py:98-120`) admits the INT8 per-channel pair on any chip of capability 7.5 or better; ours is 12.1. The Triton kernel's weight-only INT8 arithmetic path is present and wired: `use_int8_w8a16` is passed through at `triton_moe.py:301, 363, 481, 675, 708` and handled inside the kernel at `fused_moe.py:194, 456, 512, 549`.
- **Adapters?** Yes — `TritonExperts` carries the hook, as quoted above. This is the same class serving our six adapters right now.
- **Offline conversion?** None. It happens during the weight load, like FP8 does today.
- **Expected weight memory.** About **30 GiB**. Arithmetic, from `config.json` in the pinned snapshot (`hidden_size` 2816, `moe_intermediate_size` 704, `num_experts` 128, `num_hidden_layers` 30): the experts are 22.84 billion weights, which is 42.54 GiB at 16-bit and 21.27 GiB at 8-bit. Measured totals are 51.04 GiB at 16-bit and 28.3 GiB at FP8 (`vllm-fp8-exam-2026-09-03/f1-fp8-host.json`; also the 2026-09-04 receipt `coach-misread-lane-2026-09-04/g1c-bf16-adapter-replay.json`, which quotes both server lines). Solving those two measurements gives 2.94 GiB of dense layers and 5.56 GiB of everything the quantiser never touches (the embedding table alone is 1.38 GiB at 262,144 × 2,816 × 2 bytes, and the vision and audio towers are not plain linear layers). Candidate A is then 21.27 + 2.94 + 5.56 = **29.77 GiB**, about 1.5 GiB more than today. The same arithmetic reproduces both measured figures exactly, so I trust it to within a few hundred megabytes.
- **In v0.28.0?** The name is in the released docs, and nothing in the v0.28.0 release notes removes or changes the online INT8 path ([v0.28.0 release, read 2026-09-04](https://github.com/vllm-project/vllm/releases/tag/v0.28.0) — the online-quantization entries there are about MXFP8 and NVFP4).
- **Risk.** Two, both real but modest. First, an inconsistency in vLLM itself: `online/int8.py:42-46` asks the backend selector whether it supports INT8 **W8A8**, then builds a **W8A16** run-time config. The Triton kernel supports both, so it should work, but the support check is not checking the thing that will run — if it fails it will fail loudly at start-up, not silently. Second, someone on the NVIDIA forum hit "illegal memory access" with Triton-compiled INT8 kernels on a GB10, blaming unified memory and TMA descriptors ([DGX Spark INT8 AWQ thread, 2026-05-25/27, read 2026-09-04](https://forums.developer.nvidia.com/t/dgx-spark-int8-awq-w8a16-completely-broken-on-dgx-spark-gb10-blackwell-anyone-got-this-working/371315)). That thread is about a *different* path — the dense-layer W8A16 route through Marlin, exllama and conch, which candidate A never uses, because it leaves the dense layers at 16-bit. And the Triton *expert* machinery is proven on our box today. But it is the closest public warning and it should be in the run card.
- **Speed.** Unknown. Weight-only means the maths happens at 16-bit, so expect to give back some of the roughly 1.4× we gained from FP8 (the figure recorded in `/opt/llama-swap/scripts/gemma4-adapters.sh`). We will not know until we run it.

### Candidate B — FP8 weights with per-row scales, still 8-bit activations (`fp8_per_channel`)

- **What it quantises.** Weights and activations, as today, but the weight scale becomes one per output row instead of one per tensor, for both dense and expert layers. `online/fp8.py:284-293` (dense) and `online/fp8.py:717-748` (experts) — the expert loop calls `scaled_fp8_quant(..., use_per_token_if_dynamic=True)`, giving a scale vector rather than a scalar. The code's own comment says the layout "matches the llmcompressor's FP8_DYNAMIC recipe, so accuracy is comparable but no pre-quantized checkpoint is required" (`online/fp8.py:287-289`).
- **Kernels and adapters.** Triton, so the hook is present (`triton_moe.py:115` lists the per-channel weight / per-token activation pair as supported).
- **Offline conversion?** None.
- **Memory.** 28.3 GiB plus about 65 MB of extra scale tensors. Effectively unchanged.
- **Risk.** Low to try, but it **fixes only the second suspect, not the first**. The activations are still squeezed to 8 bits. If the fault is in the activation path — which is my main suspicion — this will not fix it. It is cheap enough to be worth measuring in the same run, but I would not lead with it.
- **One constraint to know.** This scheme explicitly refuses the Marlin expert backend: `online/fp8.py:705-715` raises rather than run, because Marlin's path "does not implement per-output-channel weight scales". So B and C below cannot be combined.

### Candidate C — FP8 weight-only via Marlin, 16-bit activations

- **What it quantises.** Weights only. Marlin reads the FP8 weights, expands them back to 16-bit inside the chip, and multiplies at 16-bit. `vllm/model_executor/kernels/linear/scaled_mm/marlin.py:34-38` describes the dense kernel as exactly that: "FP8 Marlin kernel for GPUs that lack FP8 hardware support. Leverages the Marlin kernel for fast weight-only FP8 quantization." On the expert side, `vllm/model_executor/layers/fused_moe/oracle/fp8.py:593-604` says "MARLIN and CPU are mixed precision W8A16 config" and routes to `fp8_w8a16_moe_quant_config`; `marlin_moe.py:569-575` asserts that Marlin only ever runs weight-only schemes.
- **How to select it.** `--moe-backend marlin` maps straight to it (`oracle/fp8.py:258`). For the dense layers, `--linear-backend marlin` plus the environment variable `VLLM_TEST_FORCE_FP8_MARLIN=1`, because on any chip of capability 8.9 or above the kernel refuses unless that variable is set (`scaled_mm/marlin.py:51-60`). Ours is 12.1.
- **Adapters?** Yes — `MarlinExperts` carries the hook (`marlin_moe.py:701`).
- **Does Marlin run on sm_121?** Yes, and there is independent evidence: a vLLM bug report from a DGX Spark owner complains that on SM_121 the MXFP8 expert path *falls back* to "MARLIN W8A16: weights are dequantized FP8→BF16, compute in BF16" — the complaint is that it is slow, not that it is broken ([vLLM issue #43906, opened 2026-05-28, read 2026-09-04](https://github.com/vllm-project/vllm/issues/43906)).
- **Offline conversion?** None.
- **Memory.** Same bit-width as today, so about 28.3 GiB plus Marlin's repacked layout and workspace.
- **Risk.** Speed. Marlin is the slow path on this chip by every public account: a Spark benchmark measured Marlin-fallback NVFP4 at 40.8 tokens per second against FP8's 53.8, a 24 percent loss on the same model ([ai-muninn, published 2026-04-21, updated 2026-05-06, read 2026-09-04](https://ai-muninn.com/en/blog/dgx-spark-nvfp4-trap-gb10-fp8-wins)), and the Unsloth card for our own base says to avoid Marlin as "around 2x slower". Those measurements are for 4-bit; 8-bit Marlin should be less bad, but nobody has published a number. Its advantage over candidate A is that it also removes activation quantisation from the *dense* layers, which A leaves at 16-bit anyway — so in practice A and C reach the same place by different routes, and A keeps the fast Triton kernel.

### Candidate D — INT8 W8A8 (SmoothQuant style) via compressed-tensors

- **What it quantises.** Weights and activations, both as 8-bit whole numbers, from a pre-made file. The image has the machinery: `vllm/model_executor/layers/quantization/compressed_tensors/compressed_tensors_moe/compressed_tensors_moe_w8a8_int8.py`.
- **Verdict: skip it.** It keeps the activation quantisation, which is the suspect. It needs an offline conversion with calibration data. It produces a checkpoint our adapters were never trained against. It buys nothing over candidate A. Include it in the table for completeness only.

### Candidate E — INT8 weight-only (W8A16) from a compressed-tensors file

- Same destination as candidate A, reached the expensive way. The image's weight-only INT expert path selects `MarlinExperts` on CUDA (`vllm/model_executor/layers/fused_moe/oracle/int_wna16.py:73`), so adapters would work, but it needs an offline conversion and inherits Marlin's speed cost. Red Hat's own documentation notes that FP8 checkpoints on older chips run "as weight-only W8A16, utilizing FP8 Marlin", which is the same mechanism. **Candidate A is this, for free, at load time, on the fast kernel.** Skip.

### Candidate F — GPTQ or AWQ at 8 bits

- The image supports 8-bit GPTQ for expert layers (`vllm/model_executor/layers/quantization/moe_wna16.py:149`, `num_bits in [4, 8]`), landing on `MarlinExperts`, so adapters would work in principle.
- **Risk is high and the evidence is discouraging.** It needs an offline conversion with calibration. The one public attempt at INT8 weight-only on a GB10 failed on every kernel tried — Marlin "rejected with message about unsupported uint8 type", exllama "only supports float16 activations", AllSpark "doesn't support zero points", and conch-triton crashed ([DGX Spark forum thread, 2026-05-25/27, read 2026-09-04](https://forums.developer.nvidia.com/t/dgx-spark-int8-awq-w8a16-completely-broken-on-dgx-spark-gb10-blackwell-anyone-got-this-working/371315)). Our expert path uses a different scalar type (`uint8b128`, `marlin_moe.py:661-663`) so it is not the identical failure, but there is no reason to spend hours finding out when candidate A is a flag. **Skip.**

### Candidate G — static per-channel FP8 via calibration

- vLLM supports a static activation scheme (`fp8.py:90`, `ACTIVATION_SCHEMES = ["static", "dynamic"]`), but only when reading a pre-quantised checkpoint — the config validator refuses static scales on a 16-bit checkpoint. So this needs llm-compressor, calibration prompts, and a new checkpoint.
- **And it aims at the wrong thing.** A calibrated fixed scale can be *better* than a dynamic one (it is not hostage to one large value in the current batch) but it is still an 8-bit activation. Conversion cost for a model this size is hours: llm-compressor's own published figures run from 10 hours for an 8-billion model to 68 hours for a 70-billion model on eight datacentre GPUs, though data-free FP8 recipes are much faster and a GLM-5.2 MoE checkpoint was reported done "in under 2 hours" ([llm-compressor project, read 2026-09-04](https://github.com/vllm-project/llm-compressor)). On one Spark, budget a day and a repeat of every exam. **Skip unless A, B and C all fail.**

### The non-vLLM comparator — run the merged Q8_0 coach beside the shared host

This is the option that is certain to work, because it is what worked on 2026-09-04. It costs memory instead of risk.

- **The file.** `/home/richardwoollcott/fine-tuning/output/coach-gemma4-26b-moe-v4/gguf_gguf/gemma-4-26b-a4b-it.Q8_0.gguf`, 26,859,844,512 bytes = **25.0 GiB**, plus llama.cpp's own cache and context on top.
- **The room.** With the FP8 adapter host alone and nothing else large resident, the box shows **54.4 GiB** available (`/home/richardwoollcott/fine-tuning/output/vllm-fp8-exam-2026-09-03/f1-fp8-host.json`, `mem-settled-f1.txt` reading: MemAvailable 57,052,012 kB of MemTotal 127,535,220 kB). So the merged coach seat fits, with roughly 29 GiB left.
- **The catch.** The coding model costs about **33.6 GiB** while working. That is the difference between two readings taken the same evening: with the coding model and the FP8 member both resident, 20,135,532 kB available; with the member alone, 55,348,252 kB (`coach-misread-lane-2026-09-04/g1c-bf16-adapter-replay.json`, `memory_readings_kB_MemAvailable`). An earlier note put the coding model at "about 22 GiB"; the 33.6 GiB figure is the more recent and the more conservative, and it is the one to plan against.
- **So the choice is stark:** shared host + merged coach seat leaves no room for the coding model; shared host + coding model leaves no room for the merged coach seat. You can have two of the three. That is the price of buying fidelity with a whole second copy of the weights instead of a flag.

## 3. NVFP4, only as it bears on fidelity

The 2026-09-03 note covers NVFP4 in full and its conclusion has not changed. On fidelity alone, three things are worth restating and one adding.

- Red Hat's own card for this exact base recovers 97 to 103 percent of the 16-bit score on most benchmarks but **91.6 percent on the code benchmark**, its weakest row. Code is what we do.
- Applying our adapters — trained against Google's 16-bit weights — on top of 4-bit expert weights is unreported by anyone. The delta the adapter adds was learned against a different set of numbers.
- The only 4-bit expert kernel with the adapter hook is Marlin, which is the slow path here.
- **New this week, and the reason to close the question:** if we are moving *away* from 8-bit because 8-bit lost information, moving to 4-bit is moving the wrong way. NVFP4 quantises weights *and* activations by default; the W4A16 variants exist but run on Marlin. Everything that makes candidate A attractive makes NVFP4 unattractive. Leave it.

## 4. How to measure the misread rate properly

This is one lane, one approval, and it needs Rich's word before anything is sent, because it posts to the switchboard and it swaps the shared member twice.

### The material exists and I have checked it

The campaign is eight builds. All 48 real coach turns are on disk with their evidence:

| build | coach turns | tasks | evidence bundles |
|---|---|---|---|
| FEAT-9CC1 (2026-09-03 20:44) | 5 | 4 | 5 |
| FEAT-A9AD (2026-09-04 05:41) | 8 | 5 | 8 |
| FEAT-A460 (2026-09-04 07:06) | 4 | 4 | 4 |
| FEAT-99E2 (2026-09-04 08:49) | 9 | 5 | 9 |
| FEAT-F8AC (2026-09-04 10:45) | 6 | 5 | 6 |
| FEAT-11ED (2026-09-04 12:05) | 4 | 4 | 4 |
| FEAT-44A8 (2026-09-04 13:13) | 6 | 4 | 6 |
| FEAT-34A9 (2026-09-04 17:27) | 6 | 5 | 6 |
| **total** | **48** | **36** | **48** |

(counted 2026-09-04 under `/home/richardwoollcott/forge-state/receipts/build-FEAT-*/.guardkit/autobuild-private/*/`.) Every turn has its evidence bundle. Of the 48, 36 are first turns, 8 are second, 3 are third and 1 is fourth.

### What must generalise from `g1b/build_live_prompt.py`, and what I found

The existing driver rebuilds one prompt by calling guardkit's own `AgentInvoker._build_coach_prompt` on four inputs. Generalising it to 48 needs each input checked. I checked all four.

1. **The evidence bundle.** Present for all 48, in the receipts. The driver's fidelity assertion — rebuild the bundle object, serialise it back, require it to match the receipt byte for byte — generalises unchanged. **No work.**
2. **The player's report.** Present for all 48. The original driver read it from the live worktree, and **only one of the eight worktrees still exists** (`/tmp/forge-autobuild-worktrees/build-FEAT-44A8-…`; the other seven are gone). But the receipts carry their own copy of the worktree's autobuild directory — for example `receipts/build-FEAT-99E2-…/worktrees/FEAT-99E2/.guardkit/autobuild/TASK-DEACT-005/player_turn_{1,2,3,4}.json`. Counts match turns in every build. **The driver must be repointed from the worktree to the receipt copy.** This is the one code change that matters.
3. **Turns 2, 3 and 4 — the prior feedback.** Simpler than feared. The turn number itself only appears in the answer template the prompt asks for (`agent_invoker.py`, the `"turn": {turn}` line). The prior feedback reaches the coach through the *player's* report for that turn, because the player wrote it in response to the previous verdict — and that report is file `player_turn_N.json`, already in hand. So a later turn needs no extra reconstruction: same code, later N. **No special case.**
4. **The task file.** **Not in the receipts.** It has to come from the source repository — for the two I checked, `/home/richardwoollcott/Projects/appmilla_github/specialist-agent/output/tasks/backlog/user-list-etag/TASK-44A8-004-update-docs.md` and `.../deactivate-user/TASK-DEACT-005-add-deactivation-docs.md`, both present today. The 2026-09-04 receipt asserts the repo copy was byte-identical to the worktree copy for that one task. **The generalised driver must make that assertion per task and stop on any task whose file has since changed**, rather than quietly replaying a prompt the live run never saw.
5. **The memory context.** This is the one genuine limitation. For **36 of the 48 turns** the memory backend returned nothing and the prompt carried a fixed 47-character placeholder, which the driver can reproduce exactly. For the other **12** it carried real retrieved text of 416 to 1,864 characters, and **that text is not stored in any receipt** — only its length is, in the run logs (`grep "Coach context provided" autobuild-stdout.log` across the eight builds, 2026-09-04). Those 12 turns cannot be rebuilt byte-exactly. Two honest options: report them separately as an "approximate prompt" arm, or drop them and report on 36. I would run all 48, mark the 12, and report both numbers.

### The run

1. **Rebuild all 48 prompts** with the generalised driver, offline, nothing sent. Record each prompt's SHA-256 and character count, and which of the 12 are approximate. Minutes.
2. **Replay on the FP8 host**, which is already live — no swap needed. Three sends per turn at temperature 0, the same wire shape the live run used (one user message, `max_tokens` 16384, the v4 verdict grammar as a top-level body field), exactly as `g1b/send_live_prompt.py` does. 144 requests.
3. **Swap the member to 16-bit** — the script is kept at `/opt/llama-swap/scripts/gemma4-adapters.sh.bak-20260903-bf16-final` and the live 8-bit one at `.bak-20260904-8bit-live`, both present today. Replay the same 144 requests.
4. **Swap back** and confirm the restored file is byte-identical to the backup and that the member answers a live request.
5. **Compare** each of the 288 answers to the decision of record in `coach_turn_N.json`, and count three things separately: decisions that differ from the record; verdicts that quote a value contradicted by their own evidence bundle (the specific fault, machine-checkable); and disagreement between the three repetitions of the same turn on the same host.

### What it costs

- **Model time.** The live campaign's own coach calls ran at a median of **6.0 seconds** across 69 recorded invocations (`events.jsonl` across the eight builds, latency field; mean 69.6 s, skewed by one 600-second timeout). The 2026-09-04 replays took 3.53–6.35 s on the FP8 host and 2.49–9.06 s on the 16-bit host, at 5,937 prompt tokens (`g1b-live-prompt-replay.json`, `g1c-bf16-adapter-replay.json`). The campaign's prompts are on average larger than that one: the median evidence bundle is 13,949 bytes against the reference turn's 6,779, so expect a median prompt nearer 8,000 tokens than 5,937, and a largest around 15,000. 288 requests at a median of 6 seconds is about **29 minutes**; budget **60 to 90 minutes** for the tail.
- **Member swaps.** Two, measured at **515 and 535 seconds** to ready on 2026-09-04 (`g1c-bf16-adapter-replay.json`, `swap_times_local`) — about nine minutes each. The 16-bit member's weight load alone is 319 seconds.
- **Total.** About **two hours**, of which roughly 45 minutes has the factory's shared names answering from a 16-bit base rather than the production 8-bit one.
- **Tokens.** About 2.3 million prompt tokens and roughly 15,000 completion tokens across the 288 requests. If sent straight to the switchboard on port 9000, as the 2026-09-04 replays were, **none of it passes through LiteLLM and no spend row is created**. If routed through the proxy for the record instead, those are the numbers that would appear. Either way there is no money: it is all local.

### What 48 turns can and cannot settle

This matters more than the wall-clock, and it should be on the approval card.

| observed disagreements | rate | 95% confidence interval |
|---|---|---|
| 0 of 48 | 0% | 0% to 7.4% |
| 1 of 48 | 2.1% | 0.4% to 10.9% |
| 3 of 48 | 6.2% | 2.1% to 16.8% |
| 6 of 48 | 12.5% | 5.9% to 24.7% |
| 12 of 48 | 25% | 14.9% to 38.8% |

(Wilson intervals, n = 48.) So: 48 turns will comfortably detect a fault rate of one in five. It will **not** distinguish "never happens" from "happens one time in fifteen". If the answer needs to be finer than that, the set has to grow, and the only way to grow it is to run more builds. The three repetitions per turn measure something different and worth having — whether the host answers the same prompt the same way twice — but they are not 144 independent observations.

### The fences the run must respect

Taken from what the 2026-09-04 lane actually did (`g1c-bf16-adapter-replay.json`, `estate_and_fences`), plus the standing rules:

- **The estate gate before every switchboard action**: `forge status` must show a build table with **no** RUNNING, PAUSED or QUEUED rows. PAUSED is not quiet.
- **No guardkit runner alive.** Check by process, not by ledger — a cancelled build's runner keeps calling the switchboard.
- **The start-order rule.** The adapter host must be resident before any large llama.cpp seat loads. If the coding model is resident, unload it first; it reloads on demand.
- **Back up before editing the live script, and prove the restore.** Byte-compare the restored file to the backup and send one live request through the member before declaring the lane closed.
- **Never restart forge-prod**, never touch NATS or LiteLLM, never leave a member half-loaded.
- **Rich's word is needed** to post to the switchboard at all, and to swap the member.

### How the same harness exams a candidate from section 2

Unchanged. The 48 prompts are the fixed input; the host is the variable. Point the member script at the candidate's flags (for candidate A: `--quantization int8_per_channel_weight_only --moe-backend triton`, and **drop** `--linear-backend torch`, which has nothing to filter once the dense layers are unquantised), wait for ready, replay the same 288 requests, compare against the same decisions of record. Each candidate costs one more member swap — nine minutes — and one more hour of replay. Three candidates measured in one sitting is a long afternoon, not a project.

## 5. The numbers in one place

**Memory, weights only, this model on this box**

| configuration | expert weights | everything else | total | source |
|---|---|---|---|---|
| 16-bit (bf16) | 42.54 GiB | 8.50 GiB | **51.04 GiB** | measured, `g1c-bf16-adapter-replay.json` / `f1-fp8-host.json` |
| FP8 today (`fp8`) | 21.27 GiB | 7.03 GiB | **28.3 GiB** | measured, `f1-fp8-host.json` |
| A: `int8_per_channel_weight_only` | 21.27 GiB | 8.50 GiB | **~29.8 GiB** | arithmetic from `config.json` + the two measurements |
| B: `fp8_per_channel` | 21.27 GiB | 7.03 GiB | **~28.4 GiB** | as FP8 plus ~65 MB of scales |
| C: FP8 weight-only via Marlin | 21.27 GiB | 7.03 GiB | **~28.3 GiB** + Marlin workspace | same bit-width, repacked |
| merged Q8_0 seat under llama.cpp | — | — | **25.0 GiB** (the file) | `coach-gemma4-26b-moe-v4/gguf_gguf/gemma-4-26b-a4b-it.Q8_0.gguf`, 26,859,844,512 bytes |

**Room on the box**

| state | MemAvailable | source |
|---|---|---|
| FP8 member alone | 54.4 GiB | `f1-fp8-host.json`, `mem-settled-f1.txt` |
| 16-bit member alone | 29.4 GiB | `g1c-bf16-adapter-replay.json` |
| FP8 member + coding model | 19.2 GiB | `g1c-bf16-adapter-replay.json` |
| coding model's own cost | ~33.6 GiB | difference of the two rows above |
| nothing large resident | 100.4 GiB | `g1c-bf16-adapter-replay.json` |

**Scale granularity — how many weights share one scaling number**

| scheme | weights per scale (expert matrices) |
|---|---|
| FP8 today | 3,964,928 (one per expert per layer) |
| `fp8_per_channel` / `int8_per_channel_weight_only` | 2,816 (one per output row) |
| Q8_0 under llama.cpp | 32 |

**Fidelity evidence of record, 2026-09-04, one prompt, three sends each**

| arm | decisions | misreads |
|---|---|---|
| coach adapter on FP8 base, vLLM | reject, reject, reject | 3 of 3 |
| coach adapter on 16-bit base, same vLLM | approve, approve, approve | 0 of 3 |
| merged coach Q8_0, llama.cpp | approve, approve, approve | 0 of 3 |

**Speed, for context**

| | figure | source |
|---|---|---|
| FP8 against 16-bit on our host | about 1.4× | `/opt/llama-swap/scripts/gemma4-adapters.sh` comment |
| Marlin fallback against FP8, another Spark, 4-bit | −24% (40.8 vs 53.8 tok/s) | ai-muninn, read 2026-09-04 |
| weight load, FP8 | 312–317 s | `f1-fp8-host.json`, `g1c-bf16-adapter-replay.json` |
| weight load, 16-bit | 319 s | `g1c-bf16-adapter-replay.json` |
| member swap to ready | 515–537 s | `g1c-bf16-adapter-replay.json`, `f1-fp8-host.json` |

## Recommendation

**Try first, and it is one flag:** candidate A, `--quantization int8_per_channel_weight_only --moe-backend triton`, dropping `--linear-backend torch`. It is the only option in the image that removes activation quantisation from the expert path *and* gives the weights a thousand-fold finer scale *and* keeps the fast Triton kernel *and* keeps the adapter hook *and* needs no new model file. It costs about 1.5 GiB more memory than today, which the box has. If the coach's misreading is caused by what I think causes it, this is where it goes away.

**Measure, don't argue.** Approve the 48-turn replay as one lane. Run it three ways in the same sitting — today's FP8, the 16-bit reference, and candidate A — and read the three disagreement rates side by side against the decisions of record. Put the confidence table on the card so nobody over-reads a zero.

**Measure candidate B in the same sitting if there is time**, because it is another single flag and it separates the two suspects: if per-row FP8 weights fix it, the weights were the problem; if they do not and candidate A does, the activations were.

**Leave alone:** every offline conversion route — llm-compressor W8A8, static calibrated FP8, GPTQ and AWQ at 8 bits, compressed-tensors W8A16. Each costs hours, produces a checkpoint the adapters were never trained against, needs every exam re-run, and lands somewhere the flags already reach. And leave NVFP4 alone for this question entirely: it moves further in the direction that hurt us.

**Keep in the back pocket:** the merged Q8_0 coach seat beside the shared host. It is the only option that is *certain* to have the fidelity, because we measured it. It costs 25 GiB and it means the coding model cannot be resident at the same time. If all three flag candidates fail, that is the fallback, and Rich should know the trade before it is needed.

**What Rich physically does:** nothing to read this note. To run the measurement: say go, and be present while the member is swapped twice. **What is at risk:** for about 45 minutes the factory's shared names answer from a 16-bit base instead of the production 8-bit one, and the member is unavailable for about nine minutes at each swap. Nothing else on the box is touched.

## What I could not establish

- **The speed cost of candidates A, B and C.** Nobody has published an 8-bit weight-only number for this chip, and I did not run one. Candidate A gives up native 8-bit expert arithmetic, so expect to lose some of the 1.4× we gained; how much is unknown until it is measured.
- **Whether candidate A starts at all.** The support check in `online/int8.py:42-46` asks about a W8A8 scheme and then builds a W8A16 one. The Triton kernel handles both, so I expect it to work, but I could not prove it without starting a server, which this lane may not do. It will fail loudly at start-up if it fails.
- **Whether the fault is the activations or the weight scales.** The code makes the activation path the better suspect and the published MoE-FP8 literature agrees, but I have not isolated it. Candidates A and B together isolate it in one sitting.
- **How to rebuild the 12 turns whose memory context is not in any receipt.** Only the character counts survive. Those turns can be replayed approximately or excluded, not reproduced.
- **Whether the byte-identity of the task files still holds** for all 36 tasks. I confirmed the files exist for two; the generalised driver must check the rest and stop on any that has drifted.
- **Whether v0.28.0 changes any of this.** Its release notes touch MXFP8 and NVFP4 online quantisation and add Gemma 4 vision-tower LoRA, but say nothing about the online INT8 path or the FP8 per-tensor MoE accuracy question. v0.25.0 remains the proven pin; nothing here argues for moving.

## Sources

**Code inside the pinned image** `vllm/vllm-openai:v0.25.0-aarch64-cu129`, all under `/usr/local/lib/python3.12/dist-packages/`, read 2026-09-04:

- `vllm/model_executor/layers/quantization/fp8.py` — 90 (activation schemes); 98-101 (defaults: not-serialised checkpoint, dynamic activations); 185-192 (dense → `Fp8PerTensorOnlineLinearMethod`); 210-217 (experts → `Fp8PerTensorOnlineMoEMethod`)
- `vllm/model_executor/layers/quantization/online/fp8.py` — 106-122 (per-tensor weights, per-token or per-tensor FP8 activations); 154-167 (`scaled_fp8_quant(weight, scale=None)`); 284-293 (per-channel dense, "matches the llmcompressor's FP8_DYNAMIC recipe"); 372-416 (expert base, weight/activation key pairs); 494-541 (one scale per expert; input scales `None`); 677-715 (per-channel experts; Marlin explicitly refused); 717-748 (per-row expert quantisation)
- `vllm/model_executor/layers/quantization/online/int8.py` — 31-46 (per-channel INT8 experts, Triton selection); 57-93 (per-row quantise to −127…127); 118-128 (run-time config with no activation scales)
- `vllm/model_executor/layers/quantization/online/base.py` — 58-71 (the dispatch tables); 74-116 (the online config)
- `vllm/config/quantization.py` — 24-34 (the scheme names); 114-137 (the `--quantization` shorthands and what each sets); 141-144
- `vllm/model_executor/layers/quantization/__init__.py` — 12-46 (the full list of accepted names)
- `vllm/model_executor/kernels/linear/__init__.py` — 199-207 (`--linear-backend`); 213-268 (backend-to-kernel map); 322-330 (CUDA priority order, Marlin first); 549-573 and 624-646 (selection and the log line at 631)
- `vllm/model_executor/kernels/linear/scaled_mm/ScaledMMLinearKernel.py` — 111-121 and 135-170 (the activation quantisation, line 161)
- `vllm/model_executor/kernels/linear/scaled_mm/pytorch.py` — 24-41 (torch kernels, capability 8.9+); 58-96 (per-tensor); 175-242 (channel-wise, the one we run)
- `vllm/model_executor/kernels/linear/scaled_mm/marlin.py` — 34-38 ("weight-only FP8"); 40-61 (the 8.9 gate and `VLLM_TEST_FORCE_FP8_MARLIN`); 91-110
- `vllm/model_executor/layers/fused_moe/experts/triton_moe.py` — 54 (`TritonExperts(LoRAExpertsMixin, ...)`); 98-120 (supported weight/activation pairs); 246-250 and 450-454 (dynamic quantisation of expert inputs); 301, 363, 481, 675, 708 (`use_int8_w8a16` passed through)
- `vllm/model_executor/layers/fused_moe/experts/marlin_moe.py` — 555, 569-575 (weight-only only); 600-621 (supported weights); 661-663 (`uint8b128` for INT8); 701 (`MarlinExperts(LoRAExpertsMixin, ...)`)
- `vllm/model_executor/layers/fused_moe/experts/lora_experts_mixin.py` — 9 (the hook itself)
- `vllm/model_executor/layers/fused_moe/oracle/int8.py` — 62-67 (Triton → `TritonExperts`); 93-104 (`--moe-backend` mapping); 183-225 (W8A16 when no activation scales)
- `vllm/model_executor/layers/fused_moe/oracle/fp8.py` — 258 (`"marlin"` mapping); 325 (the backend log line); 593-604 ("MARLIN and CPU are mixed precision W8A16")
- `vllm/model_executor/layers/fused_moe/oracle/int_wna16.py` — 47-53 and 73 (weight-only INT → `MarlinExperts`)
- `vllm/model_executor/layers/fused_moe/config.py` — 379-392 (`use_int8_w8a16` / `use_fp8_w8a16`); 634-657 (W8A8 builder); 903 and 943-963 (W8A16 builders, "16-bit float activations and int8 weights")
- `vllm/model_executor/layers/fused_moe/fused_moe.py` — 194, 456, 512, 549 (the Triton kernel's weight-only INT8 arithmetic)
- `vllm/model_executor/layers/quantization/utils/w8a8_utils.py` — 11-18 (`cutlass_fp8_supported`)
- `vllm/lora/layers/fused_moe.py` — 80-95 and 415-425 (the assertion that refuses any expert kernel without the hook)
- `vllm/model_executor/layers/quantization/moe_wna16.py` — 149 (GPTQ at 4 or 8 bits)
- `.../compressed_tensors/compressed_tensors_moe/` — the offline W8A8 INT8, W8A16 and NVFP4 expert methods
- `/hf/hub/models--unsloth--gemma-4-26b-a4b-it/snapshots/60941ad6341d0b7af91277ff25c4175f08b56819/config.json` — `hidden_size` 2816, `moe_intermediate_size` 704, `intermediate_size` 2112, `num_experts` 128, `num_hidden_layers` 30, `vocab_size` 262144, `tie_word_embeddings` true

**Our own receipts on this box**, read 2026-09-04:

- `/home/richardwoollcott/fine-tuning/output/coach-misread-lane-2026-09-04/g1b-live-prompt-replay.json` — the FP8 arm, 3 of 3 misreads, 5,937 prompt tokens, 3.53–6.35 s per send
- `.../coach-misread-lane-2026-09-04/g1c-bf16-adapter-replay.json` — the 16-bit arm, 0 of 3; both weight-load lines; the memory readings; the swap times
- `.../coach-misread-lane-2026-09-04/g1b/build_live_prompt.py` — the prompt rebuilder to generalise
- `/home/richardwoollcott/fine-tuning/output/vllm-fp8-exam-2026-09-03/f1-fp8-host.json` — 28.3 GiB weights, 54.4 GiB free, the CUTLASS crash text, the `--linear-backend torch` finding, 537 s to ready
- `/home/richardwoollcott/fine-tuning/output/coach-gemma4-26b-moe-v4/gguf_gguf/gemma-4-26b-a4b-it.Q8_0.gguf` — 26,859,844,512 bytes
- `/home/richardwoollcott/forge-state/receipts/build-FEAT-{9CC1,A9AD,A460,99E2,F8AC,11ED,44A8,34A9}-*/` — the 48 coach turns, 48 evidence bundles, 48 player reports, and the `events.jsonl` latency figures
- `/opt/llama-swap/scripts/gemma4-adapters.sh` and its backups `.bak-20260903-bf16-final`, `.bak-20260904-8bit-live` — the live launch line and the two swap targets
- `docker logs gemma4-adapters` — the live container's own kernel-selection lines quoted above

**Public sources**, all read 2026-09-04:

- [vLLM online quantization documentation](https://docs.vllm.ai/en/latest/features/quantization/online/) — the shorthand list; `int8_per_channel_weight_only` = "Quantizes: weights only"; separate `linear` and `moe` schemes
- [vLLM issue #30830, "accuracy issue on MoE online fp8 quantization"](https://github.com/vllm-project/vllm/issues/30830) — opened 2025-12-17, still open; incoherent output from this exact online FP8 MoE path
- [vLLM issue #43906, MXFP8 MoE falls back to Marlin on SM_121](https://github.com/vllm-project/vllm/issues/43906) — opened 2026-05-28; confirms Marlin W8A16 runs on the GB10, dequantising FP8 to BF16
- [DGX Spark: INT8 AWQ (W8A16) completely broken](https://forums.developer.nvidia.com/t/dgx-spark-int8-awq-w8a16-completely-broken-on-dgx-spark-gb10-blackwell-anyone-got-this-working/371315) — NVIDIA forum, 2026-05-25/27; Marlin rejects uint8, exllama needs fp16 activations, conch-triton crashes; the dense W8A16 route, not ours
- [NVFP4 is a trap on GB10: FP8 wins by 32%](https://ai-muninn.com/en/blog/dgx-spark-nvfp4-trap-gb10-fp8-wins) — published 2026-04-21, updated 2026-05-06; Marlin fallback costs 24% against FP8
- [vLLM v0.28.0 release notes](https://github.com/vllm-project/vllm/releases/tag/v0.28.0) — no change to the online INT8 path
- [LLM Compressor](https://github.com/vllm-project/llm-compressor) and [its documentation](https://docs.vllm.ai/projects/llm-compressor/en/latest/examples/quantization_w8a8_int8/) — the offline conversion route and its cost
- [GGUF format and k-quants](https://zeroentropy.dev/concepts/gguf/) and [GGUF quantization levels explained](https://tinyweights.dev/posts/gguf-quantization-levels-q4-q5-q8/) — Q8_0 is a scale per block of 32; perplexity change about 0.01 against full precision
- [vLLM on the DGX Spark](https://vllm.ai/blog/2026-06-01-vllm-dgx-spark) — published 2026-06-01; advises using builds validated specifically for sm_121; does not discuss FP8 or INT8
- The 2026-09-03 note in this repo, `RESEARCH-fp8-vs-nvfp4-adapter-host-gb10-2026-09-03.md`, carries the NVFP4 model cards and the DGX Spark forum threads on 4-bit, which are not repeated here
