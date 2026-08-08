# DRIFT REPORT — RUNBOOK-deepseek-v4-flash-0731-two-spark, run 2026-08-08

Mode: **fresh** — first execution of the 0731 seat (runtime image absent on Node A `promaxgb10-41b1`; Phase 2 builds today, budget 30–60 min/node). Recon per CONVENTIONS §4 + runbook Phase 0. Executed by agent (Claude Code / Fable 5). All 8 fixed sources reachable (no DF-001 degradation). Every fresh `[DRIFT]`/`[FLAG]` item below (19 of them) was adversarially re-verified against its primary source by an independent agent — 19/19 confirmed; items marked ✓. No step edited, no pin changed.

## PIN CHECKS (deterministic)

```
[DRIFT] recipe repo       pinned cd366d5e2; HEAD bf3d4eaca (2026-08-07), 1 commit ahead — ✓ VERIFIED
                          docs-only (+79/−1: README/CREDITS/DEFAULT-CONFIG). Documents an OPTIONAL
                          third-party abliterated 0731 checkpoint (HF-gated, drowzeys/keys-…-Abliterated-32-32,
                          DSpark draft modules left stock). Stock weights remain the documented default;
                          ZERO flag/config changes. Safe to run at the pin.
[FLAG]  runbook internal  PINS block says cd366d5e2 (promoted 08-06, commit 993504f) but Phase 0.1
                          `PINNED=` (line 111) and the Phase 2 checkout (line 211) still say d728faee —
                          the promotion commit missed them. Harmless TODAY only because the cd366d5 delta
                          was docs-only; the "single source of truth" property is broken until fixed.
[OK]    weights           deepseek-ai/DeepSeek-V4-Flash-0731 revision 7872f01b1d1fe23eabc4c98b48bffcef5a386062,
                          lastModified 2026-08-01T03:07Z — static in the scan window. (Community posts citing
                          rev 9e165c30 reference an earlier revision; the repo last moved pre-08-01.)
[INFO]  runtime image     absent on Node A → Phase 2 builds. Upstream publishes NO image: repo has zero
                          tags/releases and the maintainer confirmed no GHCR runtime exists (Issue #12,
                          08-05) — dspark-nvfp4-stage-c stays local-build-only; no image drift possible.
[OK]    MiaAI-Lab lane    repo HEAD a4ce87a unchanged; ghcr.io/anemll/dspark-vllm-gx10 tags exactly
                          {0.1.0, 0.1.1}; 0.1.1 digest sha256:a8394849…, built 2026-07-15, NO re-push.
                          Fallback lane #2 intact (DEFAULT_THINKING flip already pinned).
[DRIFT] eugr FALLBACK     pinned f7d6e3b5; HEAD 15b4f481 (2026-08-06), 27 commits ahead. Upstream added a
                          dedicated recipes/deepseek-v4-flash-0731.yaml (08-01: B12X stack, dspark nst=5,
                          native deepseek_v4 parsers, fp8 KV). ⚠️ that recipe defaults
                          reasoning_effort=high (our documented SILENT NO-OP) and
                          max_num_batched_tokens 8192 (the t/378890 decode-starvation value) — override
                          both if that lane is ever exercised from a newer commit. We run AT the pin.
[OK]    vLLM PR #41834    still OPEN (438 comments); sm120-pr-41834-stable-preview-20260804 remains the
                          latest validated tag; jasl (08-05): "may rework the PR" after FlashInfer 0.6.17.
                          v0.26.0 (07-27) ships no SM12x path. The fork lane is NOT retiring.
[DRIFT] llama.cpp DSpark  PR #25784 ("DeepseekV4 MTP + DSpark") MERGED to mainline 2026-08-02 —
                          deterministic (gh api). GGUF-lane recon note is stale; see source scan.
[DRIFT] unsloth GGUF      pinned UD-IQ2_M quant files byte-unchanged (✓), but repo HEAD moved to fbbb5b93
                          (08-06): turnkey DSpark drafter GGUFs added (Q8_0 at root, BF16 in dspark/,
                          measured identical) + hard llama.cpp build-window docs.
```

## SOURCE SCAN (advisory — items after 2026-08-04 touching a pinned component or an Appendix A row; ✓ = independently verified at the primary source)

### Recipe repo (tonyd2wild)

```
[FLAG]✓ Issue #18 (NEW, 08-05, high-signal): thinking-on + client STOP STRINGS = decapitated reasoning.
        vLLM v1 detokenizer evaluates stops INSIDE the reasoning segment (generation starts inside
        <think>); CoT restates a stop phrase → stop fires mid-reasoning → </think> never arrives →
        content null (~30% of GSM8K at temp 0). Bind-mount detokenizer patch validated (nulls 8-15 → 1,
        GSM8K 0.98); PR promised, not yet opened. Residual mechanism B: temp-0 verbatim loops invariant
        across spec on/off, k, B12X, KV dtype — on BOTH 2x-GB10 stacks, absent on hosted APIs.
        TODAY: send no stop sequences with thinking on; never temp-0 with thinking on.
        https://github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark/issues/18
[FLAG]✓ Issue #6 root-caused (08-07): sporadic EMPTY non-streaming content under thinking:true = model
        emits bare <STORE_AND_RETURN> scaffold with no </think>; parser files everything as reasoning.
        5/60 (8.3%) at temp 0 free-form, 0/300 short-answer, 0/60 STREAMING. PR #17 measured NOT a fix
        (p=0.44). If patching: parser_engine.py, NOT basic_parsers.py (inert). Triage fact for Phase 7
        soft-empty checks: non-streaming-only empties under thinking = this, not the engine.
[FLAG]  Issue #16 refined (maintainer, 08-05): missing <think> is CORRECT behavior (reference encoder
        puts <think> in the PROMPT; output only ever carries </think>). Effort table is MISLABELED in
        the stock encoder: "max" renders upstream's HIGH text (~84 tok); low/high inject NOTHING.
        Our pinned behavior and the /tokenize ~84-token check remain exactly right as written.
[FLAG]  PR #17 still OPEN — manual DSPARK_ENCODING_FILE wiring NOT superseded today, but the maintainer
        agreed a merge path (08-05) and live-confirmed the streaming empty tool_calls:[] bug (3/5 SSE
        frames), validating a zero-regression guard of the #573 patch class. Re-check before next pin
        refresh; when it merges it supersedes our wiring (as PINS already anticipate).
[INFO]  PR #14 MERGED (08-05): "sparkrun" one-command lane — digest-pinned base image
        (ghcr.io/bjk110/vllm-spark@sha256:d8492e…), rebuilds the overlay per-start, fail-fast verifies
        Patch 3 AND Patch 4 before serving. Not our lane, but a validated alternative bring-up path.
[INFO]  PR #13 still open (3 requested changes). Registry-verified triage fact: the base image BAKES
        TP/GLOO_SOCKET_IFNAME=enP7s7 and compose only overrides NCCL's — if gloo rank-init dies on a
        box without enP7s7, that is why. (Our PINS' ifname exports already defend this.)
[INFO]  PR #19 (08-05): warm RESTART of the 1M profile can exceed the engine-ready timeout →
        torch.distributed tears the world down mid-boot (first boot fine). Fix is sparkrun-scoped
        (VLLM_ENGINE_READY_TIMEOUT_S=3600) but the symptom is stack-generic — if a RELAUNCH dies
        mid-boot today after a good first boot, check ready-timeout headroom before suspecting fabric.
```

### Forum t/378824 (recipe companion thread)

```
[OK]    Quiet: zero posts after 08-04 (13 posts total; last is the 08-04 thank-you). No post edited
        after 08-04 — nothing already folded in changed status.
```

### Forum t/372268 tail (#594–#672)

```
[FLAG]✓ The circulating "production-3.8" image (vLLM 0.21-based) is a TRAP: uniform-length assertion in
        dspark_proposer._trim_rejected_target_context crashes the engine under concurrent
        variable-length tool traffic (#607: EngineDeadError). The recipe author DISOWNS it (#662:
        "there's not supposed to be a 3.8"); multi-reported broken (#630/#659/#660). 3.75 remains the
        community image. Our pinned 0.11.2-lineage image is unaffected — do not "upgrade" toward 0.21.
[FLAG]✓ Looping ("Hmm. Let me reconsider.") reports (#604/#615/#616): community first lever =
        num_speculative_tokens 5→4 + probabilistic sampling. Loops ALSO reproduce on OpenRouter's
        hosted 0731 (#606) → model-level, not our stack; keep the pin, use 4 only as a live lever.
        Production guidance (#668): temp/top_p ≈1.0, keep context <300K.
[FLAG]✓ #665: third-party encoding fix DiegoGiovany/DeepSeekV4FlashEncodingFix (drops an extra
        "arguments" wrapper). Single-source, zero in-thread validation — do NOT adopt; watch.
[NOTE]  PINS' open A/B is ANSWERED (#639, voktolom, tool-eval-bench hardmode): patched TRUE max
        (97 tok) = no quality win and ONE prompt-injection-resistance regression vs current "max"
        (= reference HIGH text, 84 tok). Keep pinned behavior verbatim; do not adopt a true-max
        template. (#626 independently: max can overthink.) The "open A/B" clause in PINS can close.
[INFO]  #573 empty-deltas patch: zero mentions in #594–#672 — status unchanged, our 5.6(e) gate stands.
        tool-eval-bench v2.4.x/v2.5.0 rescaled (stricter + grader fixes; 88→84 same config) — never
        compare today's scores to pre-v2.4 baselines. "reffix" packaged effort-fix circulates for the
        eugr container lane only. Heavy-production anecdote: prefill saturation ~700K tok/session.
```

### MiaAI-Lab (fallback lane #2)

```
[FLAG]✓ Issue #21 (opened 08-04, active 08-07, OPEN, no fix anywhere): the OFFICIAL ENCODING PACKAGE
        encoding_dsv4.py::encode_arguments_to_dsml CORRUPTS tool arguments when arguments arrives as a
        dict (json.loads throws → except-branch wraps as {"arguments": <dict>}, tool-name semantics
        lost). It re-renders PRIOR assistant tool calls into the prompt, so ONE bad turn poisons the
        session — first call works, later calls fail; SINGLE-TURN TESTS CANNOT CATCH IT. This is the
        exact package our PINS wire via DSPARK_ENCODING_FILE. TODAY: make Phase 5.6(a) exercise a 2nd
        and 3rd tool call in ONE session; the issue ships a repro pair + one-line type-dispatch fix.
        https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-DSpark-2x-DGX-Spark/issues/21
```

### vLLM upstream

```
[FLAG]✓ PR #51318 (08-06, open): DSv4 C128A decode topk row stride is baked at cudagraph CAPTURE from
        max_model_len; runtime re-lays at the batch's stride → mixed-batch decode rows read
        stale/foreign compressed-KV slot ids → token salad / NaN BOS bursts, WITH SPECULATION OFF,
        precisely when max_model_len ≫ actual context. ⚠️ our 1M lane (max-model-len 1048576) serving
        short/mixed traffic is exactly that shape and the pinned tag lacks the fix; the 160K short lane
        is far less exposed. --enforce-eager and single-request traffic are clean. Watch Phase 7 (c=4).
[FLAG]✓ Issue #51340 (08-07, open, 0 comments): kernel_warmup() has NO inter-rank barrier between
        stages issuing real TP/EP collectives — rank timing skew can interleave collectives and HANG
        multi-node startup. Filed from a 2-node TP=2 GB10 pair serving 0731 (v0.26 + Ray; trigger was a
        custom warmup stage). Triage row class: a launch hang in warmup ≠ fabric fault.
[FLAG]  Appendix A status correction: vLLM #48140 (our "GB10 UMA accounting" row, listed "open") was
        CLOSED not_planned 2026-07-10 and the filer RETRACTED the diagnosis (MemorySnapshot already
        uses MemAvailable on integrated GPUs; residual gap = reclaimable slab from shard loads, only
        ~50% credited). Our boot-to-boot KV-variance observation stands; the upstream citation does
        not. Practical residue unchanged: clean reboot before the demo session.
[INFO]  #51163: on DSv4 hybrid-KV, vllm:cache_config_info block_size/token arithmetic is PER-KV-GROUP
        and self-inconsistent as labeled — never hand-size KV capacity from that metric.
```

### HF weights repo discussions

```
[FLAG]✓ #40 + vLLM #51041: 0731 KV measured ~8x/token vs preview (56 vs 7.2 B) when the hybrid KV
        manager gets silently DISABLED (SWA 128-token layers promoted to full attention; suspect
        trigger: KV connector without HMA support; dspark_* fields ruled out). 2x H20 held 151K tokens
        vs preview's ~1M. TODAY: if the Phase 4 KV line reads far under the ~1.5M-tok/~10 GiB
        expectation, check hybrid-manager status BEFORE blaming UMA wobble.
[FLAG]✓ #39/#50: the depth-5 corruption saga is CLOSED — sglang SM120 allocation bug (mHC einsum
        transients inside an NCCL symmetric-memory region), model and DSpark head exonerated; NOT our
        stack's code. Two portable takeaways: (1) vLLM 0.26-lineage hard-floors num_speculative_tokens
        at dspark_block_size=5 — below-5 is fork-only territory; (2) zero-false-positive health
        signature: any decode-batch interval with mean accept length ≤2.0 UNDER LOAD = something is
        corrupting. Cheap to watch during Phases 5/7. Separately: loops reproduce with speculation
        FULLY OFF on 0.26 — a distinct open mechanism.
[FLAG]✓ #43: DSpark draft-indexer emits topk=192 (no instantiated SM120 CUTLASS bucket) → BOOT CRASH,
        observed on DGX Spark sm_121 among 3 environments (sglang path; fixes sglang#33407 +
        FlashInfer#4309; FlashInfer 0.6.16 segfaults SM120 graph capture — 0.6.15.post1 pinned there).
        Also: tool calls degrade to repetition/babble ~250K tok (~88% context), across recipes,
        model-specific. Relevant if the demo pushes deep context.
[FLAG]✓ #45: streaming tool-call detector bug family is AMPLIFIED by speculative decoding (bigger
        per-step deltas). Portable discriminator for today's 5.6 gate: rerun one failing case
        NON-streaming — clean result = detector bug, not the model.
[FLAG]✓ #47: independent 2x GB10 TP=2 nvfp4_ds_mla recipe published (dkmode22 repo): full 1M context,
        3.39M-token KV pool, 653 tok/s peak @c=16. Independently corroborates Patch 4 — acceptance
        ~0.14 unpatched (worse than our banked 0.257 figure). Claims its patches were "since upstreamed
        into vLLM 0.26" (UNVERIFIED — do not act on it). Read after the run as a reference config.
[INFO]  #44: stock vLLM 0.26.0 serves 0731 on SM120 (RTX 6000 Pro; DP=2+EP, JIT DeepGEMM) — SM120 is
        not SM121/GB10 and #41834 remains unmerged; no action. #46: GGUF looping on CUDA 13.2, fixed by
        13.3 (unsloth #4849) — check CUDA if the GGUF lane is ever exercised. #51/#49: Ampere/A100
        community forks — ecosystem context only.
```

### GGUF / 1x-Spark lane (recon watch only — its own future runbook, never a lane of this one)

```
[DRIFT]✓ STATUS REVERSED: llama.cpp DSpark is MAINLINE (PR #25784 merged 08-02, checked
        deterministically) and a firsthand GB10 report (note.com, 08-05, single-source) measures
        47.9% (prose) / 66.2% (agent reasoning) acceptance, ~25 tok/s decode on UD-IQ2_M + Q8_0 drafter
        (vs 19.7 baseline), 329-340 tok/s prefill. Runbook 0.2's "DSpark UNPROVEN on GB10 / 0% accept"
        note is stale — the 0% attempt was a pre-mainline fork. Single-node quantized seat with NO
        fleet drain on the other node is now a REAL candidate for its own runbook.
[FLAG]✓ Build window trap (unsloth dspark/README): b10228 minimum ("dflash.attention.sliding_window_
        pattern" key error below), b10259–b10268 BROKEN (drafter abort; broke #26531, fixed #26577),
        b10269+ recommended; --mtp/draft-mtp will NOT work with these files. note.com gotchas:
        -DCMAKE_CUDA_ARCHITECTURES=121 mandatory; drafter conversion needs transformers 4.57.6, not 5.x.
[FLAG]✓ llama.cpp #26741 (08-07, ggerganov confirmed; fix PR #26756 pending): -np>1 + DSpark = garbled
        output (per-ubatch compressor plans snapshot one pending-rollback array; replay poisons the
        compressed KV) — backend-agnostic, applies to GB10. Do NOT combine the drafter with parallel
        slots until merged. The known-good 08-04 4-slot Spark config ran WITHOUT a drafter — unaffected.
[INFO]  Tuning field data (Strix Halo, mainline, 08-06): acceptance cliff n-max 2→3 (79%→47%); top-p
        1.0 makes DSpark a net LOSS — start --spec-draft-n-max 1-2 (not unsloth's 3), keep top-p 0.95.
        ds4-on-spark fork: v0.5.5 fixed its illegal-memory crash, 28 h/236-req clean soak at 256K,
        v0.5.6 (08-08) adds Claude Code compat — six releases in seven days, watch only.
        t/379129 #4: working ds4-fork 1M-on-one-Spark config posted (counters the 0%-accept report).
```

### Beyond the fixed list (broad sweep)

```
[INFO]  t/379184 (new thread): eugr-lane 0731 load hangs at shard 44/48 + draft lazy-load — cleared by
        explicit IB ifnames + instanttensor draft loader. Corroborates the PR-#13 ifname failure class
        and gives a triage shape if OUR launch ever stalls in shard/draft load.
[INFO]  t/379560 (new thread): "on-prem 0731 underperforms deepseek.com" — zero config disclosed,
        contested in-thread. Watch only; the symptom class matches exactly the parser/encoding/effort
        misconfigurations our PINS defend against.
```

## VERDICT

**5 drifts, 15 flags. Procedure unchanged — the run proceeds on current PINS** (all five drifts are benign for today: docs-only recipe commit, fallback lanes move but we run at pins, GGUF lane is watch-only). Zero items contradict a pinned dial; several independently corroborate them (Patch 4 at ~0.14 unpatched, ifname exports, nst≤5, native tool path, effort no-op).

Operator attention, in order:
1. **Pre-run mechanical fix (recommended):** Phase 0.1 line 111 + Phase 2 line 211 still say `d728faee` — finish the ratified 08-06 promotion to `cd366d5e2` (one line each).
2. **Today, in-run:** no client stop-strings with thinking on, never temp-0 with thinking on (Issue #18); extend 5.6(a) to a multi-turn 2nd/3rd tool call in one session (MiaAI #21); watch mean accept length ≤2.0-under-load as a corruption signature (HF #50); if the KV line comes up tiny, hybrid-KV-manager first (#51041); if launch hangs in warmup, vLLM #51340 before fabric; if a relaunch dies mid-boot, ready-timeout (PR #19 class).
3. **Post-run amendment candidates (PR per CONVENTIONS §6):** close the PINS "open A/B" clause (#639 answered — keep mislabeled max); Appendix A #48140 row open→closed/retracted; refresh the 0.2 GGUF-lane note (PR 25784 merged; GB10 field-proven 47.9–66.2% accept, single-source); consider recipe-pin fast-forward cd366d5→bf3d4ea (docs-only) at next promotion; new Appendix A row candidates: #51318 stride corruption (1M lane exposure), #51340 warmup hang, #51041 KV inflation, Issue #6/#18 empty-content mechanisms.
