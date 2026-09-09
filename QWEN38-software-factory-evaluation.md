# Qwen3.8-Flash-Next: software-factory evaluation

**Status:** preparation notes, 2026-09-09; no canary or comparison run. This is one application of the general-purpose [single-Spark serving runbook](./RUNBOOK-qwen38-flash-next-seat.md). Serving the model does not depend on this evaluation.

## Experiment configuration

| Setting | Value |
|---|---|
| Baseline | Qwen3.6-35B-A3B, UD-Q4_K_XL, llama.cpp; `qwen36-workhorse` |
| Candidate | The exact checkpoint, template, image and serving settings from the serving runbook and its execution results |
| Candidate gateway alias | `qwen38-flash-next-player` (a distinct alias for attribution) |
| Model host | `spark-fcf6` |
| Factory, tuned seats and accounting | `promaxgb10-41b1`; existing keyed LiteLLM/Postgres |
| Initial shared harness window | 131,072 tokens, including the output/tool reserve |
| Initial work in progress | One active feature |

The model server retains its native 262,144-token context. The shared 131,072-token harness policy is specific to this comparison.

## Route and baseline preparation

After the serving runbook is green, use its **Appendix B** to add the candidate to the Dell's existing keyed LiteLLM, using `qwen38-flash-next-player` as the gateway alias. Calls follow `factory → Dell LiteLLM/Postgres → Spark vLLM`; the Spark does not need a separate dashboard/database for this experiment.

Before editing, snapshot the Dell's current routes and settings privately. Using the actual factory virtual key, require its catalog to contain the baseline and all active tuned-seat aliases, then send a baseline completion and locate its spend record. Record the baseline model file/hash, llama.cpp build/flags, context, template, runner/forge/guardkit versions and adapter hashes. The queue must be idle before changing the Player selection.

From the real runner or repository sandbox, run the serving runbook's protocol and long-stream gates through the Dell door with the candidate alias and factory virtual key. Require a >90-second streamed request, thinking-off preserved, correct tools/JSON and candidate spend records. Only Player calls should change model; the tuned seats stay on the Dell.

## Player integration and experiment readiness

Read the [factory bench card](../ai-transition/docs/bench-preregistration-card-2026-09-06.md) and its amendment before dispatching work. Flash-Next is its later **Arm B**, not its unfrozen dense-27B Arm A. The serving runbook can produce a working model endpoint independently of the formal comparison. Preparation is not a freeze, a promotion or a replacement of the current coder.

Before a Player canary, create a concrete configuration diff for the **currently deployed runner**:

1. Keep the existing `OPENAI_BASE_URL` on the Dell's keyed `:4000/v1`. Select the candidate by its own alias; never repoint the shared `qwen36-workhorse` row or the global base URL to the raw Spark engine.
2. Resolve the effective Player model through the runner's actual settings/CLI path. Guardkit exposes `--model` and a separate `--coach-model`; the general model can also affect specialist calls. Freeze the coach, planner, product owner, QA verifier, review and any specialist routes explicitly. Do not rely on an unused task-frontmatter `player_model` field.
3. Set/verify the **effective harness context and summarisation budget** for both exact provider-prefixed and bare model IDs. Initial Q/B policy is 131,072, with room reserved inside that for output/tools; the server's 262,144 capability is not permission to give only B a larger harness budget. Inspect `MODEL_CONTEXT_WINDOWS` or its current equivalent in the installed harness; an unknown-model default around 170K would exceed the baseline window. This may require a small separately reviewed harness change before readiness.
4. Preserve the baseline's effective temperature, sampling, output limits, timeout, tool set and thinking-off behaviour. The diagnostic probes use temperature zero; that does not silently redefine the experiment's sampling. Show the actual serialized candidate request carries `chat_template_kwargs.enable_thinking=false` and the correct model alias.
5. On the current sandbox deployment, verify the runner's model endpoint allowlist/network access, installed package revisions, and effective settings **inside that sandbox**. Do not restart a historical host-side service by assumption. Record source and deployed revisions, because local checkouts alone do not prove runtime state.

Then run a small **disposable canary feature** through the real Player/Coach path, after that canary/configuration change is in the execution scope. Require real Read/Write/Edit/Bash use, tool-result continuations, the expected `player_turn_N.json` accepted by the current validator, completion promises covering the task criteria, honest file lists, tests and a coach receipt. Attribute every role in LiteLLM; only Player requests may use the candidate. Keep queue WIP at one. The serving runbook's Phase 5 schema smoke does not pass this application gate.

The local research workspace did not contain the deployed forge runner or its installed external harness. This boundary requires runtime inspection and verification. Capture the exact working model-selection command/settings and context registration in the evaluation record before calling the seat factory-ready.

For the formal comparison, prepare a separate Q/B preregistration with exact baseline weight/build/template hashes and this candidate's pins. Use the nine Story Room clerk sentences verbatim, identical branch bases and context documents, and the recorded planted-defect commit for rung nine. Preserve the September 7 ruling: clerk delivery proceeds independently; compare on separate branches later. Freeze the card before collecting comparison data.

Suggested decision rule for that **new, still-unfrozen Q/B card**: on rungs five–nine, require more completed tasks with no increase in coach rejections and no more than 1.5× baseline generated tokens per completed task; ties keep Q. This adapts the existing Q/A rule and is a proposal, not an already accepted B policy. Record S1–W2, verifier agreement, Player JSON validity, tokens, retries, cold/warm latency and wall time. Classify infrastructure failures separately and rerun both arms after a shared harness fix. Never patch a failing run mid-arm and count it as unchanged evidence.

## Results and rollback

Serving results belong in the serving runbook's RESULTS artifact. Capture the effective runner settings, context registration, canary report, tests, coach verdict, role attribution and comparison data in this experiment's own record. A green server does not establish factory readiness or a win over the baseline.

When the evaluation ends, restore the recorded baseline Player/context settings and remove the experiment's gateway alias/key grant while preserving other clients and routes. Confirm a baseline completion and spend record. The Qwen server can remain available for other uses; execute the serving runbook's teardown only when retiring the model session itself.
