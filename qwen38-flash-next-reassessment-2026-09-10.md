# Qwen3.8-Flash-Next: first-trial reassessment, 2026-09-10

**Disposition:** recommend the [Saren AutoRound runbook](./RUNBOOK-qwen38-flash-next-autoround-seat.md) for the first serving trial, followed by a small real application canary if its gates pass. Preserve the [Lance Hybrid Sharp runbook](./RUNBOOK-qwen38-flash-next-seat.md) as a separate reference/fallback. Neither configuration has been run locally by this work. This note supplements the [September 8 research](./qwen38-flash-next-single-spark-research-2026-09-08.md); external benchmark numbers are not local results.

## Why change the trial order?

Prefix caching remains useful, but it does not establish that the roughly 23 tok/s Lance configuration finishes tasks sooner. AutoRound offers a reproducible faster-generation candidate with prefix caching too. It changes target quantization and template, so its quality must be measured along with time. The decision belongs at the task level, using the [evaluation companion](./QWEN38-software-factory-evaluation.md), not a ranking of decode rates alone.

| Recipe | External evidence examined | Consequence for the first trial |
|---|---|---|
| Lance Hybrid Sharp v2, MTP off | The shared [Arena entry](https://spark-arena.com/benchmark/7ec7eaf7-a10c-403d-be52-c44c0fc64539) reports roughly 23 tok/s; the existing runbook pins that recipe | Retain as a reference; application-level cache savings have not been shown to outweigh slower generation |
| Saren AutoRound hybrid, MTP3 | [Pinned source](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound/tree/1633d4bc11701c04d7cbd633994421466d1eff1d) reports code 56.5 and long-code 48.5 tok/s, with prefix caching | First trial, using the supported exact-top-k fallback and full routed-expert count |
| blazux NVFP4, MTP2 with reduced draft vocabulary | [September 8 revision](https://github.com/blazux/qwen3.8-Flash-DGX/tree/bd60fcb1b492ca920f74df7462f05da7b6d98f73) reports roughly 37–38.5 tok/s with caching and 45/51 on its small capability test; MTP3 trades higher speed for 44/51 | Useful second candidate if AutoRound fails quality or serving gates; the tiny score difference is not decisive |
| Tony NVIDIA/MTP | [Repository](https://github.com/tonyd2wild/Qwen3.8-Flash-Next-NVFP4-DGX-Spark) reports about 43.9 median / 44.3 code tok/s, deliberately disabling prefix caching | Strong uncached comparator; repeated large prompts could offset its decode advantage |
| SGLang / HashK variants | [azampatti](https://github.com/azampatti/GB10-3.8-Flash-Next) and [airawatraj](https://github.com/airawatraj/dgx-spark-qwen38-flash-agent) were considered in the research | HashK, context/precision differences and reproducibility limitations complicate a controlled first trial; do not transfer headline rates between forks |

The Saren measurements use tiny prompts, thinking enabled, four runs and a PLE table served from another machine's RAM over RDMA. The author's estimated local-NVMe slowdown is 2–3%, not an independent reproduction. The benchmark names 16 sequences; the top-level launcher uses eight. The new runbook fixes eight, local NVMe and thinking-off probes. It therefore does not claim to reproduce that benchmark exactly. [Pinned benchmark description](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound/blob/1633d4bc11701c04d7cbd633994421466d1eff1d/README.md).

A faster variant that reduces selected experts from ten to five changes target computation and requires its own quality experiment. It is not an interchangeable acceleration flag for the full-expert candidate. Likewise, a perfect synthetic tool-format score does not establish correctness on a software-factory task.

## Selected configuration and unresolved limitations

The runbook pins the prepared Saren AutoRound checkpoint and external FP8 PLE repository separately. Its image is built from exact source over a digest-pinned vLLM base; the execution must record and reuse its local image ID. It retains the full PLE table, ten routed experts, native 262,144 context and BF16 KV. MTP3 uses INT4 draft experts and a private 65,536-token draft vocabulary. No checkpoint conversion or runtime upgrades occur during serving.

The selected **exact-top-k fallback** is deliberate. A [September 10 kernel investigation](https://github.com/jschmied/qwen38-flash-next-gb10/commit/7fede41fc726) reports a shared-memory failure during a 95,239-token prefill using the custom deterministic kernel on GB10. Saren's pinned Dockerfile includes that kernel family; the report does not prove an identical ceiling in Saren's image. Exact top-k avoids that path, at the cost of slower prefill. The supported fallback is documented as roughly 20–40% slower on long prefill; no throughput measurement exists here for the complete selected configuration. [Pinned launcher](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound/blob/1633d4bc11701c04d7cbd633994421466d1eff1d/scripts/serve-intel-ar.sh).

Prefix-cache/Mamba patches still need growing-history correctness checks. The image includes a bounds guard that can skip an invalid state copy; surviving a request after that guard fires is insufficient. The new procedure treats guard hits as failures and tests beyond the reported kernel boundary. Its exact-top-k setting also does not establish bit-identical whole-model output with Marlin atomics enabled. Reduced draft vocabulary can hurt CJK acceptance; validate other workloads separately. [Pinned build and patches](https://github.com/Saren-Arterius/qwen3.8-Flash-DGX-AutoRound/blob/1633d4bc11701c04d7cbd633994421466d1eff1d/Dockerfile).

The upstream [prefix-cache issue #54173](https://github.com/vllm-project/vllm/issues/54173) was still open at reassessment. Discussion of a fix in newer vLLM does not validate applying caching to Tony's pinned image. Keep configuration changes as separate, identified trials.

## What the deployed Factory actually does

Read-only inspection reached the running Dell `api-test-deploy` sandbox, rather than relying only on the Spark's local research checkout. The Forge process ran from `/home/agent/.forge-src/forge`, using `/home/agent/.forge-venv`; installed versions included `guardkitfactory` 0.2.0, DeepAgents 0.6.12, langchain-core 1.6.2 and langchain-openai 1.6.0. The host-side DeepAgents version was older and is not the runtime reference.

The inspected `guardkitfactory` harness and model-configuration files matched [source revision 9bded62](https://github.com/guardkit/guardkitfactory/tree/9bded62c18a28a78aafa0557c8165e005e31f2fd). File SHA-256 values recorded during inspection:

| File | SHA-256 |
|---|---|
| `model_config.py` | `bb08219a11fb34b00dfc6e9db17fb1700039987e6dc3992799c53c90a6529d40` |
| `langgraph_harness.py` | `d3758d416dda9f1c3537a1123e1ea10ef7c8d6bc7678ff963d59c67ed097f108` |

These observations are a dated deployment snapshot, not an assertion that every installed package equals its repository HEAD:

- A new harness invocation constructs a new DeepAgent and starts with one user prompt; it supplies no checkpointer and reports resume unsupported. Within that invocation, tool-loop messages grow. Prefix reuse across outer invocations depends on the actual rendered prompts; it is not automatic session continuation.
- The normal `qwen36-workhorse` registry entry has a 131,072-token window and an 8,192-token Player output limit. No Flash-Next alias was registered. Effective selection still needs tracing through the current runner and verification in serialized requests; the inspection did not establish all active role selections.
- Installed DeepAgents uses a context profile to derive an approximately 85% summarisation trigger and 10% retention. At 131,072, the nominal trigger is about 111,411 tokens. Without that profile it uses a 170,000-token trigger and retains six messages. Old tool arguments can be truncated first; summarisation then changes the reusable prefix. These approximate policies are not a hard context-reserve guarantee.
- The resolver only injects its profile when the model lacks one. A new registry row alone may not override an existing provider profile. Verify the resolved object and effective middleware policy for each exact model ID.

Read-only aggregate queries of Dell LiteLLM spend records found that `openai/qwen36-workhorse` on September 9 had 1,756 calls, median prompt length 28,967, median output 191, and 114 prompts above 64K; maximum prompt length was 105,018. These are **all traffic for that model**, not isolated Player calls or matched feature runs. They show why short-prompt benchmarks are insufficient, but cannot determine the winning recipe.

For scale only, generating 191 tokens at 23.36 versus 43.9 tok/s differs by about 3.8 seconds; at 2,048 tokens it differs by about 41 seconds. Avoiding one large prefill can outweigh the first difference. These arithmetic examples omit queueing, tool time, summaries and correctness and are not AutoBuild predictions. A faster cached recipe makes this a measurable tradeoff rather than a reason to assume the slowest cached recipe wins.

## Evidence required next

First execute serving gates, including changed suffixes, unrelated requests, growing tool history across 94K/96K and up to 250K, observed cache hits, accepted MTP proposals and the memory envelope. Then, in a separately scoped application trial, give both baseline and candidate the same effective context/output policy and measure real Player/Coach task completion. Retain failures and retries in the elapsed-time record. A serving PASS establishes an endpoint; it does not establish a Factory win.
