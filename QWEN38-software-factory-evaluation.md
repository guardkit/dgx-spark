# Qwen3.8-Flash-Next: software-factory evaluation

**Status:** preparation notes updated 2026-09-10; no canary or comparison run. This is one application of the general-purpose serving runbooks below. Serving the model does not depend on this evaluation. The [September 10 reassessment](./qwen38-flash-next-reassessment-2026-09-10.md) recommends AutoRound for the first trial; its task-quality and wall-time advantage remain unmeasured.

The retained normal endpoint is `http://spark-fcf6.local:8888/v1`, model `qwen3.8-flash-next-autoround`, now using **22 GB KV under a 120 decimal GB total-RAM guard** (from 2026-09-19; 19 GB before that, and 14 GB from 2026-09-17 to 2026-09-19 while the host kernel was withholding memory). The [2026-09-19 allocation run](./RESULTS-qwen38-flash-next-kv-ceiling-20260919T090408Z.md) passed protocol, single-prefix 250K and growing-history checks at 22 GB, with steady generation of 56–59 tok/s on capped code streams and a slow patch of about 40 tok/s after loading or a very large prompt. On real Factory traffic at 14 GB the seat's own counters averaged 44.6 tok/s with 91% of prompt tokens served from cache. Two independent 130K contexts stay cached together; two full 250K contexts do not, so do not assume the advertised cache-token capacity translates into that behavior. The [2026-09-10 allocation trial](./RESULTS-qwen38-flash-next-kv-ceiling-20260910T181629Z.md) retained 19 GB at 58.79 tok/s, and its 20 GB profile crossed the memory ceiling. The [earlier 12 GB validation](./RESULTS-qwen38-flash-next-autoround-seat-20260910T165917Z.md) remains separate. These are serving receipts, not task-quality results: the module hit its output cap, and no Factory task or baseline comparison ran. Freeze the actual selected KV allocation and memory policy with the evaluation configuration.

| Configuration | Serving procedure | Experiment gateway alias | Trial order |
|---|---|---|---|
| `autoround-mtp3-exact-v1` | [Saren AutoRound hybrid](./RUNBOOK-qwen38-flash-next-autoround-seat.md); full experts, MTP3, exact top-k, prefix cache | `qwen38-flash-next-autoround-player` | First candidate after serving gates |
| `lance-sharp-v2-mtp0` | [Lance Hybrid Sharp reference](./RUNBOOK-qwen38-flash-next-seat.md); MTP off, prefix cache | `qwen38-flash-next-lance-player` | Reference/fallback; separate trial if needed |

Select one configuration per execution and retain its runbook commit, artifact pins and RESULTS receipt. The configurations have different target quantizations and templates, so a difference in task success cannot be attributed solely to their serving engines. Run only one dedicated seat on the Spark at a time; restore the first before starting the other. Keep the model server's distinct served ID in the gateway row, and use the selected experiment alias for Player attribution. Do not reuse an alias while changing its backing recipe within an arm.

## Experiment configuration

| Setting | Value |
|---|---|
| Baseline | Qwen3.6-35B-A3B, UD-Q4_K_XL, llama.cpp; `qwen36-workhorse` |
| Candidate | One named configuration above, with exact checkpoint, template, image and serving settings from its execution results |
| Candidate gateway alias | The selected configuration's experiment alias above |
| Model host | `spark-fcf6` |
| Factory, tuned seats and accounting | `promaxgb10-41b1`; existing keyed LiteLLM/Postgres |
| Initial shared harness window | 131,072 tokens, including the output/tool reserve |
| Initial work in progress | One active feature |

The model server retains its native 262,144-token context. The shared 131,072-token harness policy is specific to this comparison.

## Route and baseline preparation

After the selected serving runbook is green, use its **Appendix B** to add the candidate to the Dell's existing keyed LiteLLM, using the corresponding experiment alias above in place of its general-purpose gateway alias. Calls follow `factory → Dell LiteLLM/Postgres → Spark vLLM`; the Spark does not need a separate dashboard/database for this experiment.

Before editing, snapshot the Dell's current routes and settings privately. Using the actual factory virtual key, require its catalog to contain the baseline and all active tuned-seat aliases, then send a baseline completion and locate its spend record. Record the baseline model file/hash, llama.cpp build/flags, context, template, runner/forge/guardkit versions and adapter hashes. The queue must be idle before changing the Player selection.

From the real runner or repository sandbox, run the serving runbook's protocol and long-stream gates through the Dell door with the candidate alias and factory virtual key. Require a >90-second streamed request, thinking-off preserved, correct tools/JSON and candidate spend records. Only Player calls should change model; the tuned seats stay on the Dell.

## Player integration and experiment readiness

Read the [factory bench card](../ai-transition/docs/bench-preregistration-card-2026-09-06.md) and its amendment before dispatching work. Flash-Next is its later **Arm B**, not its unfrozen dense-27B Arm A. The serving runbook can produce a working model endpoint independently of the formal comparison. Preparation is not a freeze, a promotion or a replacement of the current coder.

Before a Player canary, create a concrete configuration diff for the **currently deployed runner**:

1. Keep the existing `OPENAI_BASE_URL` on the Dell's keyed `:4000/v1`. Select the candidate by its own alias; never repoint the shared `qwen36-workhorse` row or the global base URL to the raw Spark engine.
2. Resolve the effective Player model through the runner's actual settings/CLI path. Guardkit exposes `--model` and a separate `--coach-model`; the general model can also affect specialist calls. Freeze the coach, planner, product owner, QA verifier, review and any specialist routes explicitly. Do not rely on an unused task-frontmatter `player_model` field.
3. Set/verify the **effective harness context and summarisation budget** for both exact provider-prefixed and bare model IDs. Initial Q/B policy is 131,072, with room reserved inside that for output/tools; the server's 262,144 capability is not permission to give only B a larger harness budget. Inspect the installed `guardkitfactory` model registry and the actual resolved model's `profile.max_input_tokens`. On the September 10 deployment, the normal Qwen3.6 alias is registered at 131,072; neither candidate alias is registered. DeepAgents uses an approximately 85% summarisation trigger and 10% retention when it gets a context profile, otherwise a 170,000-token trigger and six-message retention. Registering an alias alone is insufficient if an existing provider profile wins. Assert the effective values for both arms in the real sandbox. This may require a separately reviewed harness change before readiness.
4. Preserve the baseline's effective temperature, sampling, output limits, timeout, tool set and thinking-off behaviour. The diagnostic probes use temperature zero; that does not silently redefine the experiment's sampling. Show the actual serialized candidate request carries `chat_template_kwargs.enable_thinking=false` and the correct model alias.
5. On the current sandbox deployment, verify the runner's model endpoint allowlist/network access, installed package revisions, and effective settings **inside that sandbox**. Do not restart a historical host-side service by assumption. Record source and deployed revisions, because local checkouts alone do not prove runtime state.

Then run a small **disposable canary feature** through the real Player/Coach path, after that canary/configuration change is in the execution scope. Require real Read/Write/Edit/Bash use, tool-result continuations, the expected `player_turn_N.json` accepted by the current validator, completion promises covering the task criteria, honest file lists, tests and a coach receipt. Attribute every role in LiteLLM; only Player requests may use the candidate. Keep queue WIP at one. The serving runbook's Phase 5 schema smoke does not pass this application gate.

Read-only inspection on September 10 reached the running `api-test-deploy` sandbox and its installed harness: `guardkitfactory` 0.2.0 and DeepAgents 0.6.12. The two inspected factory harness/model-config files matched source revision `9bded62c18a28a78aafa0557c8165e005e31f2fd`. Reinspect runtime state before execution; a host-side checkout or virtual environment is not proof of the sandbox's current packages.

Within one DeepAgent invocation, successive tool calls grow the message history. The outer harness creates a fresh agent and initial user message for each invocation, supplies no checkpointer and reports resume unsupported. Summarisation can replace the reusable prefix. Consequently, repeated static-prefix TTFT is a serving gate, not proof of how much AutoBuild time caching saves. Capture rendered prompt lengths, actual cache hits, tool-loop boundaries and summarisation events in the canary. Capture the exact working model-selection command/settings and effective context registration before calling the seat factory-ready.

For the formal comparison, prepare a separate Q/B preregistration with exact baseline weight/build/template hashes and this candidate's pins. Use the nine Story Room clerk sentences verbatim, identical branch bases and context documents, and the recorded planted-defect commit for rung nine. Preserve the September 7 ruling: clerk delivery proceeds independently; compare on separate branches later. Freeze the card before collecting comparison data.

For that **new, still-unfrozen Q/B card**, make **time to independently accepted, correctly completed tasks** the primary comparison. Use identical task sets, starting commits, acceptance tests and context documents; repeat and counterbalance arm order. Set the time budget and allowed assistance before dispatch. Report correctness/completion count alongside total elapsed time, including failed attempts, timeouts, retries, tool/test execution, summaries, queue waits and human intervention. Show per-task outcomes and time-to-acceptance; do not hide failures by averaging only successful tasks. Separate one-time staging/startup cost from the task clock and report it explicitly.

The earlier proposed guardrails—more completed tasks on rungs five–nine, no increase in coach rejections, and at most 1.5× baseline generated tokens per completed task—remain proposals for the new card, not an accepted B policy. Freeze how completion count and wall time resolve tradeoffs; a throughput headline or the runbook's diagnostic decode floor cannot promote a model. Ties or inconclusive evidence retain Q. Record S1–W2, verifier agreement, Player JSON validity, tokens, retries, cold/warm latency, cache reuse, MTP acceptance and wall time. Classify infrastructure failures separately and retain them in the attempted-run record; rerun both arms after a shared harness fix. Never patch a failing run mid-arm and count it as unchanged evidence.

## Results and rollback

Serving results belong in the serving runbook's RESULTS artifact. Capture the effective runner settings, context registration, canary report, tests, coach verdict, role attribution and comparison data in this experiment's own record. A green server does not establish factory readiness or a win over the baseline.

When the evaluation ends, restore the recorded baseline Player/context settings and remove the experiment's gateway alias/key grant while preserving other clients and routes. Confirm a baseline completion and spend record. The Qwen server can remain available for other uses; execute the serving runbook's teardown only when retiring the model session itself.
