# DECISION-DF-005 — Single-Spark Serving Topology: LiteLLM as the Unified Front Door

**Status:** ACCEPTED — front-door direction set. **Implementation pending**: this doc is the spec for the work to add a LiteLLM phase to `RUNBOOK-single-spark-bring-up.md`. Point Claude Code at this file to do that work. (Decision recorded under "narrative now, runbook later": the talk/video already present LiteLLM as the front door; the runbook must catch up before filming.)
**Date:** 2026-06-24
**Author:** Rich (pair-programmed with Claude)
**Scope:** The serving topology of the **single** GB10 dark-factory inference layer — how the box presents *one* OpenAI/Anthropic-compatible endpoint to every agent, and where routing/keys/spend/fallback-control live versus model lifecycle/memory.
**Companions:** DECISION-DF-001 (no-cloud-fallback on the unattended critical path — this decision carries that guard onto the LiteLLM layer) · DECISION-DF-004 (two-Spark topology — already commits LiteLLM `:4000` as the unified front door; this is the single-node precursor that makes the single→two-node story continuous) · DECISION-DF-003 (attended frontier-planning path — the *only* sanctioned route to a cloud model; unchanged).
**Related:** `dark-factory-economics-and-model-serving.md` §3.8 (llama-swap vs LiteLLM role split; griffith.mark's three-stage model) · `two-spark-serving-research-and-references.md` · `RUNBOOK-single-spark-bring-up.md` (the runbook this decision amends) · `RUNBOOK-CONVENTIONS.md` (gate/recon pattern) · LiteLLM docs (https://docs.litellm.ai/).

---

## Summary

**The single GB10 presents one front door — LiteLLM on `:4000` — to every agent. LiteLLM is the control plane (one endpoint, per-agent virtual keys, usage/spend tracking, `claude-*` wildcard routing, fallback policy). It routes by model name to llama-swap on `:9000` (the unified-memory lifecycle layer for the llama.cpp fleet) and to any vLLM backends. llama-swap is unchanged underneath; LiteLLM is additive. DF-001's no-cloud-fallback guard is enforced on the LiteLLM layer by a gate. Direct `:9000` access remains a documented fallback if LiteLLM is down.**

This makes the repo a genuine **superset** of the community stack it stands on (martinB78 → Dre Dyson → dasroot, all of which run `client → LiteLLM → llama-swap → vLLM/llama.cpp/Ollama`), instead of a llama-swap-only subset hedged as "not yet production."

---

## 1. Context

### 1.1 The problem this fixes

The repo's strapline is *"executable runbooks **on top of** the community stack."* But the community stack — and the repo's own two-node decision (DF-004) — put **LiteLLM in front of llama-swap + vLLM**. The single-Spark runbook currently stops at llama-swap (`:9000`) as the front door and defers LiteLLM to a "Phase 4 / not yet production" note. That is:

- **Incoherent as a public story.** Shipping the community stack with its top layer removed, behind a limp hedge, reads as a *downgrade*, not a layer on top — and invites exactly the "isn't this just less than martinB78's?" criticism the talk's "stand on the giants" beat is meant to pre-empt.
- **Discontinuous with our own roadmap.** DF-004 makes LiteLLM `:4000` the single front door for two nodes; `dark-factory-economics-and-model-serving.md` §3.8 says *"GuardKit is implementing this now."* The single-node runbook should be the first step of that, not a divergence.

It was not a bad *engineering* call originally — it's "Stage 1" of griffith.mark's three-stage model (Stage 1 = llama-swap lifecycle only; Stage 2 = add LiteLLM routing; Stage 3 = task-aware routing, i.e. Jarvis). The defect is that a *published* runbook shouldn't ship Stage 1 while claiming the full stack.

### 1.2 What LiteLLM and llama-swap each do (they are complementary, not competing)

| Concern | llama-swap (`:9000`) | LiteLLM (`:4000`) |
|---|---|---|
| Model lifecycle / **unified-memory** orchestration (load · swap · evict) | ✅ primary role | ❌ never touches GPU memory |
| One endpoint across **multiple engines** (llama.cpp **+** vLLM **+** Ollama **+** optional cloud) | ❌ llama.cpp-centric | ✅ the unifier |
| **Virtual API keys** / per-agent auth | ❌ | ✅ |
| **Budgets / rate limits / spend tracking** (usage dashboard) | basic web UI | ✅ per-request DB: tokens, latency, cost |
| Cross-backend **fallbacks / retries** & `claude-*` wildcard routing | ❌ | ✅ |
| Anthropic ↔ OpenAI protocol translation | via llama.cpp | ✅ native |

**What LiteLLM is NOT:** not a model server (no kernels/batching/KV cache) and not a memory manager. It is a routing + auth + accounting control plane only. It must be pointed at llama-swap's proxy port (`:9000`), **not** individual model ports, or the swap logic is bypassed.

### 1.3 Why it's worth the extra layer here

This box serves *many* models from *more than one engine* (llama.cpp fleet via llama-swap; vLLM for vision/large models) to *multiple autonomous agents* (Jarvis, Forge, AutoBuild, architect-agent, DeepAgents). That is precisely the regime where a gateway earns its place: one endpoint + one key per agent, a spend/usage view that replaces the cloud billing consoles, `claude-*` wildcards so the Claude/OpenAI SDKs need zero changes, and a single place to enforce the no-cloud-fallback policy. The runtime cost is ~2 ms/request plus one supervised process.

---

## 2. Decision

1. **LiteLLM `:4000` is the single front door** for the single-Spark setup. Every agent points at `:4000`. It routes by model name to llama-swap `:9000` (the llama.cpp fleet) and to vLLM backends as applicable.
2. **llama-swap is unchanged** as the unified-memory/lifecycle layer beneath it. LiteLLM does not load or evict models.
3. **No cloud fallback on local models (DF-001), enforced by a gate.** Auto cloud-fallback is LiteLLM's headline feature and the exact mechanism behind the April Gemini-spend incident. The config ships `fallbacks: []` **and** `context_window_fallbacks: []`. Cloud models (`claude-*`) may be *named* only for the attended DF-003 path — never as an automatic fallback target. Local→local fallback (e.g. strategist → workhorse) is permitted; local→cloud is not.
4. **Direct `:9000` remains a documented fallback** if LiteLLM is unavailable (DF-004 §chokepoint mitigation) — additive, never on the critical path.

---

## 3. Implementation spec (for the runbook work — point Claude Code here)

Add a LiteLLM phase to `RUNBOOK-single-spark-bring-up.md` (after llama-swap is up and the Phase 5 trust gates pass), following the repo's recon → pinned-steps → inline-gates convention.

- [ ] **PINS:** add a pinned LiteLLM version (ARM64) and its port (`4000`). Recon checks the LiteLLM release the morning of a run, same as the other pins.
- [ ] **Install + run LiteLLM** as a **user** systemd unit (mirror the llama-swap supervision model: `systemctl --user`, `loginctl enable-linger`; never from a VS Code terminal — see the v3 §10.2 cgroup trap).
- [ ] **Config (`examples/litellm-config.public.yaml`):** a `model_list` mapping logical names → `openai/<model>` against `api_base: http://localhost:9000/v1` (llama-swap) for the fleet (`workhorse`, `coach`, `chat`, `embed`) and against the vLLM endpoint for any vLLM models; a `claude-*` wildcard alias routing to the local workhorse so SDK clients need no changes.
- [ ] **▶ GATE — no cloud fallback (DF-001):** assert the live config has `fallbacks: []` **and** `context_window_fallbacks: []` (and no `claude-*`/cloud model listed as a fallback target). FAIL → STOP. This is the on-camera "the one community feature I deliberately disable" beat.
- [ ] **▶ GATE — CPU-pin LiteLLM separately from llama-swap:** Dre Dyson's #1 mistake — under concurrent load with the two contending for a core, LiteLLM returns 504s and llama-swap health checks flake. Set non-overlapping `CPUAffinity=` on the two user units; assert the affinities are disjoint. FAIL → STOP (or WARN if you'd rather not hard-gate core layout — author's call).
- [ ] **▶ GATE — front door answers + routes:** a smoke request to `:4000` returns from a known local model; a `claude-*` alias request lands on the local workhorse (not a cloud call). Assert `stop_reason` present and that no outbound cloud request was made.
- [ ] **Decision Gate table:** add the three gates above to the Phase 5.4 table.
- [ ] **Keep the direct `:9000` path documented** as the LiteLLM-down fallback.
- [ ] **Align the narrative docs** so they match reality once this lands: `README.md` "Current stack" (LiteLLM is the front door, drop the "not yet production" hedge), `SLIDES-got-a-spark-now-what.md` (slide 9 + honest-stack notes), and `RUNBOOK-single-spark-video-capture.md` (already updated to LiteLLM front door + the no-cloud-fallback gate beat).
- [ ] **Dry-run end-to-end** before recording so the live demo matches the script.

---

## 4. Consequences

**Positive:** genuine superset of the community stack (kills the "downgrade" criticism) · single→two-node story is now continuous (this is the precursor to DF-004) · per-agent keys + a real spend/usage dashboard · `claude-*` wildcards = zero SDK changes for DeepAgents/AutoBuild · one enforced place for the no-cloud-fallback guard · a strong, honest "gotcha → gate" beat for the video.

**Negative / accepted:** one extra hop (~2 ms) and one more supervised process — accepted · CPU-pinning is now mandatory (gated) — accepted, it's a 20-min one-time setup · LiteLLM is a routing chokepoint — mitigated by the documented direct-`:9000` fallback · everything must be ARM64/SM12.1-compatible — already true of the whole box.

**Guard preserved:** DF-001's no-unattended-cloud invariant is *strengthened*, not weakened — it moves from prose to a config gate that halts the run.

---

## 5. References

- `dark-factory-economics-and-model-serving.md` §3.8 — llama-swap vs LiteLLM role split; griffith.mark's three-stage model (`guardkit` repo).
- `DECISION-DF-004` — two-Spark unified front door (LiteLLM `:4000`); `DECISION-DF-001` — no-cloud-fallback critical-path guard (`guardkit` repo).
- LiteLLM docs — https://docs.litellm.ai/ · virtual keys https://docs.litellm.ai/docs/proxy/virtual_keys · routing/fallbacks https://docs.litellm.ai/docs/routing-load-balancing · config spec https://docs.litellm.ai/docs/proxy/configs
- martinB78 — "Running a full LLM stack on DGX Spark GB10 (App → LiteLLM → llama-swap → vLLM → llama.cpp → Ollama)" — https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580
- Dre Dyson — "5 critical mistakes" (CPU-pinning LiteLLM vs llama-swap) — https://dredyson.com/5-critical-mistakes-everyone-makes-with-running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama-and-how-to-fix-them-before-you-lose-your-mind/

> Verification note: LiteLLM feature claims are from the official docs (directly verified). The NVIDIA forum and dredyson.com return HTTP 403 to automated fetchers, so the Spark-specific specifics (CPU-pinning / 504s) are from indexed search snippets, not full-page reads — confirm against the live pages before relying on exact config details.
