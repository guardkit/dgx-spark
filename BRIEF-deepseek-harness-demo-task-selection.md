# DeepSeek V4 Flash Continual Harness Learning Experiment — Current Brief

**Status:** Direction selected; experiment design to be validated before implementation. Updated 2026-08-07 with the Reasonix baseline review.

## The selected video premise

> Can a locally served DeepSeek V4 Flash improve the coding harness wrapped around itself by learning from its own failures?

DeepSeek V4 Flash 0731 runs on the fixed two-DGX-Spark cluster. It first attempts a recognised set of terminal/coding tasks through a compact, credible and DeepSeek-aware baseline harness. The same checkpoint then occupies a separate **proposer** role: it reads the development-task traces, proposes bounded changes to the harness, and reruns the tasks. An independent benchmark verifier decides whether each candidate is better. After five to seven days, the best promoted harness is tested against a sealed task set that the proposer never saw.

This is a harness-level continual-learning experiment. It is not model fine-tuning, and DeepSeek does not grade its own work.

## Standalone boundary

The experiment must be completely standalone from the software factory.

The factory provides only the origin story: work on its memory and continual-learning flywheel led to the question. The video may spend approximately 20 seconds establishing that connection, but it must not require the viewer to understand Forge, AutoBuild, Player/Coach, NATS, specialist models, the Chronicler, fleet memory, deployment verification or any other factory component.

The standalone experiment needs only:

- The local OpenAI-compatible DeepSeek endpoint exposed through LiteLLM.
- A small coding-agent harness.
- A baseline-selection preflight that tests the prospective compact harness against stock Reasonix on a representative calibration slice.
- A restartable experiment runner that schedules tasks, stores progress and applies the frozen promotion rules.
- Harbor and a recognised benchmark or declared subset with independent verifiers.
- Versioned harness files, trajectories, scores and resource-usage records.

There is no dependency on a second resident LLM, no model swapping, no cloud inference and no integration back into the production factory during the video experiment.

## Operating model: application, not another runbook

The two existing runbooks end when the two-Spark DeepSeek endpoint and LiteLLM dashboard are healthy. **Do not create a third runbook to conduct the experiment.**

The experiment is a standalone local application driven by a frozen campaign manifest. It establishes the baseline, runs the improvement loop, checkpoints its progress and performs the final evaluation. A short operator note may document how to launch it, inspect status and recover it after an outage, but that operational plumbing is not part of the video premise.

Codex, Claude Code or any other frontier model must not orchestrate the campaign, appear as an experimental lane or be needed to keep it running. Whatever development tools help create the application are irrelevant to the experiment and the viewer story. Once launched, every solver attempt, trace analysis, harness proposal and benchmark evaluation in the campaign runs locally.

The runner is ordinary deterministic software, not another agent. Its persistence exists only so closing a desktop session or restarting a machine does not lose a week of results. Viewers need hear no more than: **the experiment ran unattended for seven days and resumed safely after interruptions.**

## Why this is the right choice

This is not an arbitrary application invented to give the newly served model something to do. It reconnects three existing strands:

1. The software factory now has a live memory/experience flywheel that captures outcomes and supplies prior experience to later builds.
2. The factory's 2026-06-14 meta-harness capture already named DeepSeek V4 Flash across two Sparks as the candidate local proposer for trace-driven harness improvement.
3. LangChain's Interrupt 2026 continual-learning framing separates improvement across the model, harness and context layers, and uses Meta-Harness/Terminal-Bench as its harness-layer example.

The experiment therefore tests the next bounded rung without dragging the whole factory on screen:

```text
task attempts
    -> execution traces and verifier results
    -> DeepSeek proposer diagnoses recurring failures
    -> candidate harness revision
    -> development evaluation
    -> promote only if evidence improves
    -> final sealed evaluation
```

Primary local sources:

- [Forge as a Continual-Learning Meta-Harness](../forge/docs/research/ideas/conversation-capture-2026-06-14-forge-meta-harness.md)
- [Software-factory plan of record](../ai-transition/docs/software-factory-plan-of-record.md)
- [Interrupt 2026 transcript](../../YouTube%20Channel/transcripts/Interrupt%202026%20Keynote%20-%20Continual%20Learning%2C%20Agent%20Divergence%2C%20and%20Fleet.md)

## What “learning” means here

The three layers must remain explicit:

| Layer | Mechanism | This experiment |
|---|---|---|
| Context | Memories, instructions, skills or retrieved information change | Held fixed except where a declared harness revision changes how fixed context is delivered |
| Harness | Prompts, tool descriptions, control flow, verification and completion behaviour change | **The layer being optimised** |
| Model | Weights change through SFT, RL or another post-training process | Out of scope; the DeepSeek checkpoint remains fixed |

The accurate public claim is that DeepSeek improves its **coding harness**, not that its weights update or that the model independently becomes more intelligent.

## Roles and independence

The same DeepSeek checkpoint may be used sequentially in two isolated roles:

- **Solver:** attempts benchmark tasks through the current harness.
- **Proposer:** reads development traces and proposes a new harness version.

This does not recreate the rejected same-model Player/Coach arrangement. The proposer never decides whether its own proposal passed. Harbor's task verifier supplies the external result, and the experiment runner applies a predeclared promotion rule.

The **evaluator** is therefore deterministic benchmark infrastructure, not another LLM seat. The **experiment runner** is ordinary code responsible for isolation, bookkeeping, rollback and scheduling; it does not make qualitative judgments.

## Five-to-seven-day experiment design

### 1. Freeze the experiment before optimisation

Record:

- DeepSeek checkpoint and quantisation.
- Serving stack versions and generation settings.
- Baseline harness commit.
- Benchmark/Harbor versions.
- Development and sealed task manifests.
- Editable harness surface.
- Candidate promotion rule.
- Maximum turns, task timeout and experiment deadline.
- Any published API prices used later for an optional counterfactual cost annotation.

### 2. Establish the baseline

Run the baseline harness against both task groups:

- **Development set:** traces and verifier results may be used by the proposer.
- **Sealed set:** establish a before score, but quarantine every task trace, result detail and artifact from the proposer and improvement loop.

The model has no cross-request memory. Reusing the sealed tasks at the end remains valid only if their baseline trajectories and outcome details are never placed in proposer context.

### 3. Run the continual-improvement loop

For each iteration:

1. Run the incumbent harness over a scheduled development-task batch.
2. Store raw trajectories, verifier results, timings and token counts.
3. Ask the proposer to diagnose evidence-backed failure patterns.
4. Generate one versioned candidate within the allowed edit surface.
5. Evaluate the candidate on the development gate.
6. Promote it only if it beats the incumbent under the predeclared rule; otherwise reject it and retain the incumbent.
7. Checkpoint all state so a service or machine restart can resume rather than invalidate the week.

The loop should keep the cluster productively occupied, but it must not generate meaningless candidates merely to claim continuous activity. Plateau detection, bounded retries and an honest stop state are part of the harness.

### 4. Freeze and test

At the five-to-seven-day deadline:

1. Freeze the best promoted harness.
2. Run the sealed set with the same serving and evaluation conditions as the baseline.
3. Compare baseline and final sealed scores.
4. Publish development progress separately from sealed generalisation.

The sealed result is the main claim. A rising development curve with no sealed improvement is evidence of overfitting, not success.

## Bounded harness search space

The initial experiment should constrain edits to mechanisms a viewer can understand and that can be attributed from traces:

- System instructions for inspect/build/test/fix behaviour.
- Tool descriptions and schemas.
- Environment preflight and task-state injection.
- Test-before-completion and other completion checks.
- Loop/repetition detection and recovery.
- Stop conditions, turn limits and reasoning/token budgets.
- Rules for requesting fixed documentation tools such as Context7.
- Small runner hooks directly supporting the above.

The available tools and information sources should remain fixed across the baseline and learned harness unless the complete-system change is explicitly declared. A documentation advantage must not be silently attributed to orchestration.

The experiment is not permission for DeepSeek to build a second software factory or rewrite unrestricted infrastructure.

## Evaluation

### Primary outcome

- Baseline versus final pass rate/reward on the sealed benchmark set, produced by its independent verifiers.

### Development evidence

- Incumbent development score over time.
- Candidate harnesses proposed, accepted and rejected.
- Score delta produced by each accepted revision.
- Recurring failure categories and the specific harness change intended to address them.

### Operational diagnostics

- Timeouts and premature stops.
- Tool-call or parser failures.
- Model turns and tool calls per task.
- Tests run before completion.
- Input, cached-input and output tokens where reported.
- Wall-clock time and inference duty cycle.
- Service interruptions and successful resumptions.

These diagnostics explain why a score moved; they do not replace the independent benchmark result.

## Benchmark and baseline direction

Terminal-Bench 2.0 under Harbor remains the leading direction because it evaluates autonomous work in prepared terminal environments and supplies independent task verifiers. SWE-bench brings third-party repository setup and explanation overhead that does not improve this story.

The practical implementation may use a declared Terminal-Bench subset, but the split must contain enough signal to support separate development and sealed groups. Task selection, split and any repeated-run policy must be frozen before optimisation.

The compact harness must remain small enough for controlled mutation and viewer explanation, but it must not be artificially weak. The initial generic candidate remains mini-SWE-agent v2 because it supports local OpenAI-compatible endpoints and already integrates with Harbor. Its suitability still requires a live DeepSeek smoke test.

Reasonix is now mandatory prior art and a baseline-selection gate. It is a substantial DeepSeek-native coding harness that supports self-hosted OpenAI-compatible Chat Completions endpoints and Linux ARM64. It includes stable prompt/tool prefixes, deterministic environment context, context pruning and compaction, evidence and completion gates, repetition protection, checkpoints, benchmark ablations and an official SWE-bench mode. It does not currently provide the experiment's continual candidate-generation, promotion and held-out-evaluation loop, and the source review found no Harbor/Terminal-Bench integration or published target-benchmark result.

Before freezing the baseline, run stock Reasonix and the compact candidate through the same local LiteLLM endpoint and a small representative Terminal-Bench calibration slice under equal tools and budgets. If the compact candidate is materially weaker because it lacks obvious harness mechanisms, strengthen it before launch. If Reasonix is clearly superior and tractable, reconsider it as the incumbent—but never expose its complete Go codebase or benchmark infrastructure as an unrestricted candidate-edit surface.

Reasonix is a preflight comparison and design reference, not a third public campaign lane. The detailed review and decision criteria are captured in [Reasonix Review — Local Inference and the DeepSeek Harness Baseline](./RESEARCH-reasonix-local-inference-and-harness-baseline.md).

Relevant precedents:

- LangChain reports improving a fixed `gpt-5.2-codex` agent from **52.8% to 66.5% on Terminal-Bench 2.0** through harness changes: [Improving Deep Agents with harness engineering](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering).
- The Meta-Harness paper reports **37.6% with Claude Haiku 4.5**, compared with published harness results as low as 13.9% for the same model: [paper](https://arxiv.org/abs/2603.28052). The current [Terminal-Bench artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) separately demonstrates the evolved scaffold and its later Opus result.
- The LangChain continual-learning framing explicitly describes model, harness and context learning: [Continual learning for AI agents](https://www.langchain.com/blog/continual-learning-for-ai-agents).

## Privacy and local-AI framing

The primary local-AI claim is control, not token arbitrage:

> The model inference, code, prompts, failure traces and harness proposals remain on hardware under the operator's control while a long-running learning experiment proceeds without a cloud inference dependency.

This is not an air-gap claim. The experiment may use explicitly allowed internet access for public documentation or package retrieval, but project material and execution traces must not be sent to an external LLM provider.

The official hosted DeepSeek API is outside the operator's privacy boundary and is not the economic comparator. Its low price is irrelevant to a service the operator would not trust with local code or traces.

## Resource evidence and optional cost context

### Actual local marginal cost

One plug-in electricity meter on each Spark will record actual energy consumption for the experiment window. Record:

- Start and end meter readings per node.
- Combined kWh.
- Electricity tariff and effective date.
- Calculated electricity cost.
- Experiment start/end timestamps and any material downtime.

The hardware purchase price is not part of this experiment's marginal-cost calculation. The two Sparks already exist, and this video is not an attempt to prove that buying local hardware beats cloud inference on total cost of ownership during a period of unusually high RAM prices.

### LiteLLM token ledger

All model traffic should pass through the LiteLLM dashboard installed by `RUNBOOK-litellm-dashboard.md`, using a dedicated virtual key/tag for this experiment. Preserve raw input, cached-input and output token totals so the calculation can be reproduced after filming.

LiteLLM supports custom per-token pricing in `model_info`. If useful after the run, the dashboard can price the observed local traffic at the current Claude Sonnet API rate while the backend remains local DeepSeek:

```yaml
model_info:
  # Counterfactual Claude Sonnet standard API list price.
  # Backend remains local DeepSeek; this is not billed spend.
  input_cost_per_token: 0.000003
  output_cost_per_token: 0.000015
```

At the end, also calculate the Opus counterfactual from the exported ledger:

```text
Sonnet equivalent = input tokens x $3/M + output tokens x $15/M
Opus equivalent   = input tokens x $5/M + output tokens x $25/M
```

The prices must be snapshotted and dated at experiment start rather than changed during the run. Primary references: [LiteLLM custom pricing](https://github.com/BerriAI/litellm/blob/main/docs/my-website/docs/proxy/custom_pricing.md) and [Anthropic's API rate card](https://www-cdn.anthropic.com/files/4zrzovbb/website/5678bc2f5978e5bcd4f1fe7c14b2c72284dcf9f8.pdf).

### Cost-claim limits

This is optional post-run context, not a frontier-model comparison lane and not part of the continual-learning mechanism. The dashboard value must be labelled **Claude Sonnet list-price equivalent**, not actual spend. Applying Claude prices to DeepSeek token counts is an estimate because the tokenizers and agent trajectories differ. It does not prove that Claude would consume the same tokens, produce the same score or finish the same tasks.

Anthropic prompt caching could reduce input cost. The final report should therefore include an uncached list-price calculation and, if the stable-prefix/cache evidence supports it, a separately labelled cache-adjusted sensitivity case. The benchmark score and the economics must remain separate claims.

The intended message is:

> Owning local compute makes private, long-running agent experiments possible at a predictable marginal cost. Here is the measured electricity, the measured token volume and what that volume represents at published Claude API prices.

## Viewer story

The video should remain understandable without a harness-engineering lecture:

1. **Question:** Can DeepSeek improve the coding agent wrapped around itself?
2. **Baseline:** The fixed model attempts standard independently graded tasks.
3. **Experiment:** It studies development failures and proposes harness changes for five to seven days on two Sparks.
4. **Evidence:** Show a small number of legible failure -> change -> improved-result examples, plus the score curve.
5. **Final test:** Rerun the sealed tasks and reveal whether improvement generalised.
6. **Local angle:** Show measured electricity, LiteLLM token totals and the fact that the complete campaign ran without cloud inference.

The likely “just use Reasonix” objection should be answered once rather than turned into a digression: Reasonix is a strong static, human-engineered harness and was used as prior art/calibration; it does not perform this experiment's failure -> candidate -> independent promotion -> held-out-test learning loop.

A published API list-price equivalent may be shown later as a supporting caption, but it must not become another lane or interrupt the central baseline -> learning loop -> sealed-result story.

A single visually understandable benchmark task may be selected from the resulting traces as an illustration. It is not a separate bespoke demo and must not replace the sealed benchmark result.

Possible concise framing:

> I gave a local AI seven days to improve its own coding harness. No cloud inference and no code or failure traces sent to an LLM provider. An independent benchmark—not DeepSeek—decided whether it actually improved.

## Explicit non-goals

- Do not integrate the experiment into the software factory.
- Do not explain the software factory beyond the short origin story.
- Do not fine-tune DeepSeek or claim model-weight learning.
- Do not introduce a Player/Coach architecture or a second resident model.
- Do not create a third runbook for the campaign.
- Do not use Codex, Claude Code or another frontier model to orchestrate the live experiment.
- Do not build a globe, HTML game, city simulation or arbitrary application merely for visual appeal.
- Do not replace meaningful evaluation with smoke checks such as “the app starts” or “cars move.”
- Do not claim that local hardware is cheaper on total cost of ownership.
- Do not compare with the hosted DeepSeek API as if it were inside the operator's privacy boundary.
- Do not claim Claude-equivalent quality from a Claude-priced token counter.
- Do not promise improvement. A null result, regression or development-only overfit remains a valid finding.
- Do not imply that no DeepSeek-specific coding harness exists; acknowledge Reasonix and record how it influenced baseline selection.
- Do not allow unrestricted mutation of Reasonix's core runtime, benchmark machinery or full-trust extension system.

## Gap analysis and validation gates

The premise is coherent, but it is not ready for a seven-day launch. Three feasibility questions are genuine go/no-go gates; the remaining gaps concern experimental validity. None currently disproves the idea, but resolving them in the wrong order could produce significant implementation work around an experiment that cannot run at useful scale.

### Potential blockers

#### 1. Harbor execution host and architecture compatibility

The two Sparks will be occupied serving DeepSeek, while Harbor still needs a machine on which to build and run task containers. DGX Spark has an ARM64 processor and unified CPU/GPU memory. Terminal-Bench tasks commonly build from multi-architecture Linux base images, but individual tasks may still download x86 binaries, depend on architecture-specific tools or consume resources that interfere with model serving.

Possible Harbor hosts are:

- One Spark alongside inference, subject to ARM compatibility and resource contention.
- The Mac through its Linux container environment, subject to architecture, sleep and long-run reliability constraints.
- A separate always-on x86 Linux machine, if one is available.

Do not assume compatibility across the selected subset. Run the Oracle solution for representative tasks on the intended host and record build failures, architecture assumptions, CPU/memory requirements and runtime. NVIDIA documents Spark's [ARM64 architecture](https://docs.nvidia.com/dgx/dgx-spark/system-overview.html); Harbor confirms that tasks execute in [container environments](https://www.harborframework.com/docs/core-concepts).

**Gate:** The intended host must complete a representative Oracle matrix reliably without destabilising DeepSeek serving.

#### 2. Seven-day campaign throughput

The seven-day window is meaningful only if it contains enough attempts for a baseline, multiple proposal/evaluation cycles and a credible final test. The published Meta-Harness artifact reports 89 tasks x 5 trials, or 445 attempts, for its full result. This experiment adds repeated incumbent/candidate comparisons to that basic evaluation workload.

Measure with a small calibration batch:

- Median and worst-case task duration.
- Input/output tokens per attempt.
- Container setup and verifier overhead.
- Sustainable model-request and task concurrency.
- Generation speed and failure rate while Harbor is active.

Use those observations to calculate the maximum credible trial budget before choosing the split or number of repeated runs. Reference: [Meta-Harness Terminal-Bench artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact).

**Gate:** The measured budget must leave room for the baseline, several genuine optimisation cycles, promotion checks and the final held-out evaluation. If it permits only one or two candidate cycles, the seven-day premise is too weak.

#### 3. End-to-end DeepSeek compatibility

The public Meta-Harness examples currently assume Claude Code as the proposer and describe the released framework as reference code with limited testing beyond proving it runs. A local DeepSeek proposer wrapper is plausible, but it is not yet proven. Reference: [Meta-Harness framework](https://github.com/stanford-iris-lab/meta-harness).

Complete one vertical slice proving that DeepSeek can:

1. Operate the selected baseline coding harness through LiteLLM.
2. Complete a Harbor task/tool loop and produce a gradeable result.
3. Read a failed development trajectory and verifier result.
4. Produce a syntactically valid change inside the bounded harness surface.
5. Rerun through that candidate and record an independent score.

**Gate:** The complete solver -> trace -> proposer -> candidate -> Harbor-result loop must work without a frontier model or human translation of the proposal.

### Experimental-validity gaps

#### 4. Reasonix changes the baseline-validity test

A minimal generic harness may produce easy gains simply because it omits mechanisms already present in a mature DeepSeek-oriented coding agent. Conversely, adopting the whole Reasonix runtime would create a large, difficult-to-attribute search surface and no native Harbor/Terminal-Bench path was found in the reviewed source.

Run stock Reasonix and the compact candidate against the same local endpoint and a small calibration slice. Hold the task prompts, tool and documentation access, generation settings, timeouts and token/turn ceilings constant. Record compatibility failures as well as scores: malformed tool calls, history/reasoning errors, missing usage fields and adapter overhead may determine viability before benchmark performance does.

**Gate:** Freeze a defensible incumbent only after the calibration shows that it is neither a toy baseline nor an uncontrolled general-purpose agent. Record the Reasonix commit, configuration, results and any mechanisms distilled into the selected harness.

#### 5. Development and sealed sets are not enough

The current loop uses development evidence both to generate a candidate and to approve it. Repeated selection against the same tasks will overfit those tasks even if the final sealed set remains untouched.

Use three distinct functions:

- **Learning tasks:** the proposer may see complete trajectories and verifier details.
- **Promotion anchors:** the runner exposes scores only, never trajectories, and uses them to accept or reject candidates.
- **Final held-out tasks:** unavailable to the improvement loop and used for the before/final comparison only.

Restore the previously agreed progressive curriculum: calibration, contained build/debug, multi-step integration/recovery, then long-horizon specialist tasks. Retain fixed anchors while broadening the learning mixture so a score curve remains comparable across tiers.

**Gate:** Freeze the task manifests, tier rules and permitted visibility for each pool before the first optimisation trace is generated.

#### 6. Compute fairness is currently contradictory

The brief freezes maximum turns and timeouts but also lists turn limits and reasoning/token budgets inside the editable harness surface. A higher score caused by twice the inference budget is not clean evidence of a better harness.

Choose one rule before launch:

- Hold task time, turns, token ceilings, tools and information sources constant between baseline and final; or
- Permit compute changes but report score against tokens/time and constrain promotion to a declared efficiency envelope.

Context7 or another documentation source must be equally available to baseline and candidate harnesses. A candidate may learn to use a fixed tool better, but it must not gain a tool or information source that the baseline never had.

**Gate:** Every promoted result must be interpretable as either equal-budget improvement or an explicitly reported quality/cost trade-off.

#### 7. Candidate and verifier isolation is underspecified

The proposer must not be able to change Harbor tasks, verifiers, promotion logic, stored incumbent results, sealed manifests or the experiment runner. Harbor's verifier runs in the agent container by default; a separate verifier environment is available but optional. This means the independence and tamper-resistance of the selected tasks must be checked rather than assumed. Reference: [Harbor verifier environments](https://www.harborframework.com/docs/tasks).

The safest first search space is declarative: system prompts, tool schemas, environment preflight, completion checks and tightly scoped hooks. Candidate files should live in an isolated writable directory, while datasets, evaluation rules and held-out manifests remain immutable and inaccessible.

**Gate:** An automated isolation test must prove that candidate code cannot read or alter the held-out pool, verifier definitions, runner state or promotion rule.

#### 8. The cumulative learning record is undefined

DeepSeek has no persistent model memory between requests. Harness promotion provides cumulative state, but the proposer also needs a compact record of prior hypotheses and outcomes or it may repeatedly propose rejected mechanisms. Conversely, continually inserting every raw trajectory will exhaust the context window.

Maintain a bounded experiment journal:

```text
observed failure -> proposed mechanism -> candidate result -> accepted lesson
```

The journal must be derived only from learning-task evidence and promotion scores permitted by the visibility rules. Its format, maximum size and compaction behaviour should be frozen with the campaign.

**Gate:** A restart and a context-compaction test must show that the loop preserves accepted lessons and candidate lineage without exposing held-out evidence.

### Smaller but necessary gaps

- Pin the exact Terminal-Bench/Harbor dataset version, task manifests, container images or digests and agent-harness commit.
- Describe final tasks as **held out from optimisation**, not necessarily unseen by the model; Terminal-Bench is publicly available.
- Predeclare permitted human intervention. Operational recovery may restart unchanged components, but must not tune prompts, choose candidates or reveal evaluation evidence during the campaign.
- Define plateau, retry and early-stop rules before launch.
- Confirm which token/cache fields the local serving path actually exposes to LiteLLM.
- Snapshot electricity tariff, meter readings, software/model versions and any optional published API rates immediately before launch.

## Recommended validation sequence

Do not implement the complete unattended runner first. Validate in this order:

1. Select the prospective Harbor host and run a representative Oracle task matrix.
2. Smoke-test both stock Reasonix and the compact harness against the exact local LiteLLM route.
3. Run both on an equal-budget Terminal-Bench calibration slice and freeze a defensible baseline.
4. Complete one automated proposal and candidate-evaluation cycle.
5. Measure task/token throughput and calculate the seven-day trial budget.
6. Freeze learning, promotion-anchor and held-out manifests plus the tier curriculum.
7. Freeze compute parity, editable surface, promotion statistics, journal and isolation rules.
8. Only then implement restart/resume and launch the full campaign.

The coding task is no longer the central unresolved choice. The selected project remains the standalone continual harness-learning experiment. Host compatibility, local Reasonix/compact-harness calibration, end-to-end integration and achievable trial volume are the immediate feasibility tests; task isolation, compute fairness and promotion statistics are the next design work.
