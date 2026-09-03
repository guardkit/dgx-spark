# FP8 or NVFP4 for the adapter host on the GB10: what the forum, the model cards and the code say

Date: 2026-09-03. Written for Rich's decision. Nothing in here has been run on our box yet; every number below is somebody else's measurement or a reading of the vLLM code we ship, and each is attributed.

## The question

Everything we have served so far uses 16-bit weights. The 26B mixture-of-experts base takes 53.6 GiB before any adapter or cache, and on 2026-09-03 the memory budget did not close beside the resident coding model: at the 0.55 memory dial the four-adapter process left 9.7 GB for everything else and swap was exhausted. Rich asked whether an 8-bit (FP8) base is the right fix, whether the 4-bit NVIDIA format (NVFP4) would give the same quality with an even larger cache, and what real GB10 users report.

## Short answer

Measure FP8 first. NVFP4 is real and works on the GB10, but for adapter serving on this chip it would cost us three things we do not want to pay: a third-party base checkpoint our adapters were never trained against, the slow Marlin kernel (the only 4-bit expert kernel that carries the adapter hook), and a measurable quality dip on code in Red Hat's own table. FP8 quantises our own 16-bit checkpoint on load, halves the weights, and uses the Triton expert kernel that carries the adapter hook. The cache room FP8 frees is already several times what the eight-sentence campaign needs, so NVFP4's extra 11 GB buys nothing we need.

## What FP8 would do

- Weights halve: about 27 GB instead of 53.6 GiB, quantised from our own checkpoint at start-up (`--quantization fp8`). No new model file, no third party.
- Speed on the Spark: the forum's careful measurement on a 30B mixture model found 8-bit decodes at 55 tok/s against 31.7 tok/s at 16-bit, so roughly 1.7 times faster. Their summary line: "Use FP8 when the model fits."
- Adapters: in vLLM v0.25.0 only three expert kernels carry the adapter hook (Triton, Marlin, and the gpt-oss Triton variant). The FP8 path can be pinned to Triton with `--moe-backend triton`. This combination is unmeasured on our exams; that is exactly what the staged measurement lane is for.

## What NVFP4 would do

- Weights shrink to about 16 GB (the community checkpoints report 15.3 to 16.5 GB). That is roughly 11 GB less than FP8.
- Speed on the Spark: 20 to 35 percent faster than FP8, not the doubling the bit count suggests. One forum thread measured NVFP4 at 65 to 68 tok/s against FP8 at 55 on the same 30B mixture model; another measured a 27B dense model at 29 to 34 percent more throughput than FP8 across three workloads. The reason is the chip: the GB10 lacks the datacenter FP4 tensor instructions and has 99 KB of on-chip shared memory against 228 KB on the datacenter part, so 4-bit weights are unpacked to 8-bit before the maths and the kernels run smaller tiles. The thread's own words: "FP4 + small shared memory is the worst combo."
- Our adapters on a 4-bit base: unproven anywhere. The adapters were trained against Google's 16-bit base. Applying that delta on top of 4-bit expert weights has not been reported by anyone we found, and in our vLLM release the only 4-bit expert kernel with the adapter hook is Marlin, which Unsloth's card says to avoid ("around 2x slower; let vLLM auto-select the NVFP4 kernel"). So adapter serving on NVFP4 would give up most of the speed advantage.
- Making our own NVFP4 checkpoints: not straightforward. The first community quantiser of this exact model, validated on a DGX Spark, reports that NVIDIA's ModelOpt, LLM Compressor and TensorRT-LLM "all expect nn.ModuleList of nn.Linear — they silently skip the expert parameters, which are 91% of the model", and had to write a custom plugin to unfuse the experts first. Our merged tunes would need the same treatment.
- Quality: Red Hat's card recovers 97 to 103 percent of the 16-bit score on most benchmarks but 91.6 percent on the code benchmark (LiveCodeBench v6), the weakest row. NVIDIA's experts-only recipe is within half a point everywhere on its table, but it was tested on B200. The forum's PSA thread notes MoE models are "not both equally optimized" for NVFP4 yet and that accuracy depends on whether the checkpoint is W4A4 or W4A16. Our exams would have to re-license every seat.

## The cache question

- NVFP4 KV cache is an SGLang feature today (`--kv-cache-dtype nvfp4`), confirmed working on a Spark at about 0.041 GB per thousand tokens against 0.070 for FP8, so about 1.7 times the capacity. Our vLLM release's cache formats are 16-bit or FP8 only.
- FP8 KV cache in our vLLM: the FlashAttention backend only allows it with FlashAttention 3 on Hopper-class chips, which the GB10 is not. The FlashInfer backend has FP8 cache paths, but it is untested here and the forum thread that measured it says "validate model quality and task-specific accuracy before enabling aggressive KV cache quantization."
- More to the point, cache is not our bottleneck once the weights shrink. From our own dial measurements (0.55 to 0.60 added 141,323 tokens of cache for 6.05 GB), this model's cache costs roughly 43 KB per token. FP8 frees about 27 GB, which is roughly 600,000 tokens of cache room. The campaign's need is four concurrent 32,768-token requests, about 131,000 tokens. FP8 clears that several times over with the coding model resident.

## The numbers in one place

| | 16-bit (today) | FP8 | NVFP4 |
|---|---|---|---|
| Weights on the GPU | 53.6 GiB (measured) | ~27 GB (half) | ~16 GB (community cards) |
| Decode speed on the Spark, forum measurement, 30B mixture model | 31.7 tok/s | 55 tok/s | 65 to 68 tok/s |
| Checkpoint | ours | ours, quantised on load | third-party base only |
| Expert kernel with the adapter hook | Triton (in use) | Triton | Marlin (about half speed) |
| Quality vs 16-bit | reference | expected near-lossless, unmeasured here | 91.6% on code (Red Hat); unmeasured with adapters |

## Recommendation

1. Run the staged FP8 measurement lane: our 16-bit weights quantised on load, Triton expert kernel, two adapter slots, coach 6-task exam, product-owner 17-check exam, planner drive, memory read with the coding model resident, dials 0.40 and 0.45. The exams are the quality check; the vLLM log and LiteLLM spend rows are the speed check.
2. Treat NVFP4 as a later experiment only if FP8's speed is not enough for the campaign, and only with the Marlin caveat and a full exam re-run understood up front.
3. Leave the cache format at 16-bit for now.

What Rich physically does: nothing. What is at risk: the lane starts a vLLM process beside the resident coding model. On 2026-09-03 the reverse start order (coding model first, 16-bit vLLM at dial 0.55 second) ended with the kernel killing the coding model. The FP8 lane needs about half the weight memory at a lower dial (0.40, about 48 GB of a 121 GB pool with roughly 104 GB free), so the same failure is unlikely, but it is the one live thing that could be disturbed and Rich should know that before saying go.

## Sources

NVIDIA DGX Spark / GB10 forum:
- [Qwen3.8-27B on DGX Spark using vLLM: NVFP4 vs FP8 performance](https://forums.developer.nvidia.com/t/qwen3-8-27b-on-dgx-spark-using-vllm-nvfp4-vs-fp8-performance/380258) (vLLM 0.27.1; NVFP4 29 to 34% faster; 23.4 vs 30.9 GB)
- [FP4 on DGX Spark: why it doesn't scale like you'd expect](https://forums.developer.nvidia.com/t/fp4-on-dgx-spark-why-it-doesnt-scale-like-youd-expect/360142) (no tcgen05, 99 KB shared memory; 31.7 / 55 / 65-68 tok/s; "Use FP8 when the model fits")
- [PSA: state of FP4/NVFP4 support for DGX Spark in vLLM](https://forums.developer.nvidia.com/t/psa-state-of-fp4-nvfp4-support-for-dgx-spark-in-vllm/353069) (kernels not optimised for sm_121; MoE weaker than dense)
- [NVFP4 vs FP8 KV cache on RTX PRO 6000 Blackwell and DGX Spark](https://forums.developer.nvidia.com/t/nvfp4-vs-fp8-kv-cache-on-rtx-pro-6000-blackwell-and-dgx-spark/377425) (SGLang; 1.7x capacity; validate quality first)
- Also seen, not relied on: [GLM-5.3-Flash on 2x DGX Spark with NVFP4 KV cache](https://forums.developer.nvidia.com/t/glm-5-3-flash-on-2x-dgx-spark-nvfp4-kv-cache-288-b-token-2-2m-token-pool-16-way-serving-900k-context-full-recipe/382120), [Qwen3.8-Flash-Next 180B on a single Spark, NVFP4](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-180b-single-solo-dgx-spark-with-hashk-ple-nvfp4/381519), [TurboQuant KV cache on vLLM 0.19.1](https://forums.developer.nvidia.com/t/dgx-spark-gb10-vllm-0-19-1-turboquant-kv-cache-integration-results-on-qwen3-5-and-nemotron-including-gather-free-triton-decode-and-cuda-wph-decode/365627), [Qwen3.8-Flash-Next NVFP4 on 4x Spark](https://forums.developer.nvidia.com/t/qwen3-8-flash-next-nvfp4-on-4x-dgx-spark-vllm-tp4-serving-4-7m-token-kv-pool-and-the-three-fixes-you-will-need/381897), [vLLM custom build for DGX Spark: stream loading and automatic KV cache](https://forums.developer.nvidia.com/t/vllm-custom-for-dgx-spark-stream-loading-and-automatic-kv-cache/365798), [GLM-5.3-Flash DFLASH2 on 2x Spark](https://forums.developer.nvidia.com/t/glm-5-3-flash-on-2x-nvidia-dgx-spark-43-4-tok-s-peak-checkpoint/381429).

Model cards for this exact base in NVFP4:
- [nvidia/Gemma-4-26B-A4B-NVFP4](https://huggingface.co/nvidia/Gemma-4-26B-A4B-NVFP4) (experts-only recipe, ModelOpt 0.43.0, tested on B200, within 0.5 points of 16-bit on its table)
- [RedHatAI/gemma-4-26B-A4B-it-NVFP4](https://huggingface.co/RedHatAI/gemma-4-26B-A4B-it-NVFP4) (LLM Compressor; 91.6% recovery on LiveCodeBench v6)
- [unsloth/gemma-4-26B-A4B-it-NVFP4](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-NVFP4) (vLLM >= 0.25.0; "Do not use the Marlin backend (around 2x slower)")
- [CyberFitz/gemma-4-26B-A4B-it-NVFP4](https://huggingface.co/CyberFitz/gemma-4-26B-A4B-it-NVFP4) (quantised and validated on a DGX Spark; serves with `--moe-backend marlin --kv-cache-dtype fp8`; benchmarks "coming soon")
- [google/gemma-4-26B-A4B-it discussion 7](https://huggingface.co/google/gemma-4-26B-A4B-it/discussions/7) (49 GB to 16.5 GB on a Spark; fused expert tensors silently skipped by the standard tools)
- Others found: [AEON-7](https://huggingface.co/AEON-7/Gemma-4-26B-A4B-it-Uncensored-NVFP4), [bg-digitalservices](https://huggingface.co/bg-digitalservices/Gemma-4-26B-A4B-it-NVFP4), [nvidia/diffusiongemma-26B-A4B-it-NVFP4](https://huggingface.co/nvidia/diffusiongemma-26B-A4B-it-NVFP4), [vLLM recipes page for the base](https://recipes.vllm.ai/Google/gemma-4-26B-A4B-it).

Our own code reading, image `vllm/vllm-openai:v0.25.0-aarch64-cu129`: `modelopt_fp4` is a registered quantisation method; the adapter hook (`LoRAExpertsMixin`) is carried only by the Triton, Marlin and gpt-oss Triton expert kernels; Marlin accepts NVFP4 weights with 16-bit activations; FlashAttention's FP8 cache needs FlashAttention 3 on a Hopper-class chip; the cache dtype table lists 16-bit and FP8 variants only.
