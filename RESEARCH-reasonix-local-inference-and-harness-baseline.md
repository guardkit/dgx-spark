# Reasonix Review — Local Inference and the DeepSeek Harness Baseline

**Status:** Research captured 2026-08-07. This is a baseline-selection input for the standalone continual harness-learning experiment, not a decision to adopt Reasonix wholesale.

## Decision summary

Reasonix does not negate the proposed experiment. It changes what counts as a credible starting point.

- Reasonix can direct its model traffic to a self-hosted OpenAI-compatible Chat Completions endpoint and ships a Linux ARM64 binary. It is therefore a viable local-inference candidate for the two-Spark environment, subject to a live LiteLLM compatibility test.
- It is substantial prior art for a DeepSeek-aware coding harness: stable prompt prefixes, explicit tool contracts, environment context, context pruning and compaction, completion evidence, repetition protection, permissions and benchmark ablations.
- It is not a continual-learning meta-harness. It does not turn benchmark failures into bounded harness candidates, apply a frozen promotion rule, preserve held-out evidence or evolve an incumbent over a week.
- The experiment must not imply that a DeepSeek-specific coding harness did not already exist. Reasonix must be acknowledged and used as a calibration/reference gate so the selected baseline is not artificially weak.
- The complete Reasonix codebase is too large and feature-rich to be the initial unrestricted edit surface. If Reasonix becomes the incumbent, candidate changes must be constrained to an explicitly declared project-level harness surface.

The public distinction is:

> Reasonix answers which hand-engineered DeepSeek harness someone could use today. This experiment asks whether an unchanged local DeepSeek can learn from independently graded failures and improve a harness around itself over time.

## Review scope

The review used the `main-v2` repository at commit [`cfdc5addf9894ecce36b280bb2f7c810e88e5baf`](https://github.com/esengine/DeepSeek-Reasonix/commit/cfdc5addf9894ecce36b280bb2f7c810e88e5baf), plus the public [Reasonix site](https://reasonix.io/), [repository](https://github.com/esengine/DeepSeek-Reasonix), [configuration-path documentation](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/CONFIG_PATHS.md), guide, implementation and benchmark sources.

This was a static source and documentation review. It did not prove compatibility with the project's exact LiteLLM/vLLM route.

## Local-inference finding

Local model inference is supported in principle rather than merely a local user interface wrapped around the hosted DeepSeek API.

Reasonix custom providers can specify:

- `kind = "openai"`;
- a local `base_url` or complete `chat_url`;
- a manual model when model discovery is unavailable;
- an optional API-key environment variable;
- an explicit reasoning protocol, context window, headers and extra request fields.

The official guide explicitly includes [self-hosted OpenAI-compatible services](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/GUIDE.md#custom-openai-compatible-providers), and the repository includes a configuration test using `http://127.0.0.1:8080/v1`. Prebuilt releases include Linux ARM64 according to the [README](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/README.md#installation).

A prospective isolated configuration is:

```toml
default_model = "spark/deepseek-v4-flash"

[[providers]]
name           = "spark"
kind           = "openai"
base_url       = "http://<litellm-host>:4000/v1"
model          = "<litellm-model-alias>"
context_window = <verified-context-limit>

# Use explicitly if the local alias is not assigned the correct model metadata.
reasoning_protocol = "deepseek"
```

`api_key_env` may be omitted for a keyless service. If the LiteLLM proxy uses a virtual key, Reasonix stores the corresponding credential in its own Reasonix-home `.env`; campaign setup should use an isolated `REASONIX_HOME` rather than a normal interactive installation.

### Compatibility boundary

Reasonix's custom OpenAI provider sends Chat Completions requests. A complete `chat_url` does not switch it to the OpenAI Responses API. The live preflight must therefore prove that the local serving route correctly handles:

- `/v1/chat/completions`;
- streaming text and tool-call deltas;
- assistant/tool-call history across turns;
- DeepSeek reasoning fields accepted by the deployed server;
- finish reasons and truncated generations;
- usage, cached-input and output-token fields where available.

Configuration support is not evidence that every one of those behaviours works with the selected model recipe.

## Hosted-only and local differences

Several headline DeepSeek optimisations should not be assumed to transfer unchanged to local inference:

- Reasonix derives DeepSeek's beta assistant-prefix continuation URL only for an official `deepseek.com` endpoint. A local gateway can use the DeepSeek reasoning request shape but does not inherit that hosted endpoint.
- The repository's context-maintenance A/B harness is hardcoded to `https://api.deepseek.com` and requires `DEEPSEEK_API_KEY`.
- Hosted prompt-cache token accounting and pricing do not demonstrate local prefix/KV-cache behaviour. Stable prompt prefixes remain desirable, but effective local caching depends on the LiteLLM and inference-server configuration and must be measured.
- Automatic hosted pricing, cache TTL assumptions and response headers must not be used as local economic evidence.

The relevant sources are the [DeepSeek endpoint guard](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/internal/provider/openai/host.go#L51-L68), [reasoning-provider notes](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/REASONING_PROVIDERS.md) and [benchmark documentation](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/benchmarks/README.md#context-maintenance-e2e).

## What should inform the compact baseline

Reasonix demonstrates that a DeepSeek-aware harness need not rely on a giant system prompt. Its default system instruction is deliberately small; much of the behaviour is encoded in stable tool descriptions and deterministic host controls.

Mechanisms worth considering for the baseline are:

1. A small, cache-stable system prefix and stable tool ordering.
2. A deterministic environment preflight rather than asking the model to rediscover basic workspace facts.
3. Precise, generated or test-backed tool schemas and contracts.
4. Test-before-completion and evidence requirements enforced by the host.
5. Loop, repeated-call and no-progress detection.
6. Protection against editing from stale reads.
7. Stale tool-output snipping followed by bounded context compaction.
8. Checkpointing, permissions and isolated workspaces.
9. Ablation switches that permit a mechanism's contribution to be measured.

Reference sources include the [specification](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/SPEC.md), [tool contract](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/TOOL_CONTRACT.md), [example configuration](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/reasonix.example.toml) and [ablation switches](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/internal/ablation/ablation.go).

Features that should not be copied into the initial experiment merely because Reasonix contains them include its desktop UI, planner/executor mode, subagent fleet, general memory system, broad MCP ecosystem, remote-SSH support and complete Extension Protocol. They would enlarge the search and explanation surface without answering the selected question.

## Benchmark evidence and limitations

Reasonix contains useful evaluation infrastructure:

- a small end-to-end fixture suite;
- diff grading;
- an official SWE-bench Verified mode;
- reports for solved count, failure class, tokens, cost, wall time and cache hits;
- ablation arms for evidence, planning, subagents, retrieval and compaction.

The source review did not find Harbor or Terminal-Bench integration, a committed Terminal-Bench result or a committed public score report establishing Reasonix's strength on the experiment's target benchmark. Its built-in tasks include simple fixtures such as FizzBuzz and palindrome; these are useful engineering regression tests but not a substitute for Terminal-Bench evidence.

Consequently, “just use Reasonix” is a valid implementation suggestion but not proof that the continual-learning experiment has already been performed or that Reasonix is the best target-benchmark harness.

## Why AutoResearch is not the proposed loop

Reasonix Goal/AutoResearch maintains host-owned state, findings, evidence and progress for a long-running goal. The design explicitly states that it is not an autonomous background daemon and advances through normal agent turns.

It does not supply the experiment's required controls:

- learning, promotion-anchor and held-out task pools;
- immutable evaluator and promotion rules;
- versioned harness candidates generated from benchmark traces;
- incumbent-versus-candidate evaluation and rollback;
- held-out evidence quarantine;
- a five-to-seven-day campaign deadline and final frozen evaluation.

Reasonix's benchmark ablations evaluate predefined components. They do not cause Reasonix to learn or promote a new harness. See [Goal and AutoResearch](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/GUIDE.md#goal-and-autoresearch).

## Baseline-selection gate

Reasonix should be evaluated before the seven-day runner is built:

1. Pin the exact Reasonix commit and run it from an isolated Reasonix home.
2. Connect it to the same local LiteLLM model alias intended for the experiment.
3. Prove one ordinary tool loop, one failing-test repair and one representative long-context task.
4. Adapt `reasonix run` to a small Terminal-Bench calibration slice with the same task time, turn/token ceiling, tools, documentation access and generation settings as the compact harness.
5. Record pass/fail, malformed tool calls, timeouts, tokens, wall time and verifier results.
6. Compare stock Reasonix with the prospective compact baseline.

Decision rule:

- If the compact harness is materially weaker for obvious missing mechanisms, strengthen it with the relevant Reasonix lessons before freezing the baseline.
- If stock Reasonix is compatible, tractable and clearly superior, reconsider using it as the incumbent—but constrain candidate edits to an auditable project-level surface.
- If Reasonix requires substantial Harbor adaptation or its large runtime makes controlled mutation impractical, retain the compact Harbor-native harness and record Reasonix as the external calibration rather than a third campaign lane.

Do not allow the proposer to rewrite Reasonix's complete Go codebase, benchmark machinery or full-trust [Extension Protocol](https://github.com/esengine/DeepSeek-Reasonix/blob/main-v2/docs/EXTENSION_PROTOCOL.md). That would destroy the bounded search space and complicate attribution, isolation and explanation.

## Video framing

Reasonix does not need to become an additional on-screen lane. One concise objection-and-answer is sufficient:

> A mature DeepSeek-native harness called Reasonix already exists and can use local inference. I used it as prior art and calibrated against it, so the starting harness was not intentionally weak. But Reasonix is a static human-engineered agent; it does not run this failure-to-candidate-to-promotion-to-held-out-test learning loop.

The selected premise remains:

> Can an unchanged, locally hosted DeepSeek improve a credible coding harness around itself and prove that improvement on evidence it was not allowed to learn from?
