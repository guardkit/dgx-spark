# RESULTS — LiteLLM Front Door (2026-07-11)

**Host:** `spark-fcf6` (NVIDIA GB10, aarch64, 20 cores). Additive overlay per
[`RUNBOOK-litellm-front-door.md`](./RUNBOOK-litellm-front-door.md), executed on a box brought GREEN the same
run by [`RUNBOOK-single-spark-bring-up.md`](./RUNBOOK-single-spark-bring-up.md)
(see [`RESULTS-single-spark-bring-up-2026-07-11.md`](./RESULTS-single-spark-bring-up-2026-07-11.md)).
**Outcome: GREEN** — LiteLLM `:4000` front door live over the llama-swap `:9000` fleet, no cloud on the path.

## Gate outcomes (Phase 5 Decision Gate, filled)

| Gate | Result | Note |
|---|---|---|
| P0 Drift report emitted + reviewed | ✅ PASS | [`DRIFT-litellm-front-door-2026-07-11.md`](./DRIFT-litellm-front-door-2026-07-11.md) — litellm floated 1.89.4→1.91.2 (expected), config surface unchanged |
| P1 base fleet green on `:9000` (4 aliases + user unit) | ✅ PASS | `chat`·`coach`·`embed`·`workhorse` served; `llama-swap` user unit active |
| P4.1 LiteLLM no-cloud fallback (both lists empty + no cloud target) | ✅ PASS | `fallbacks: []` + `context_window_fallbacks: []`; no cloud model named anywhere (DF-001) |
| P4.2 LiteLLM ↔ llama-swap CPUAffinity disjoint | ✅ PASS | litellm `0-3`, llama-swap `4-19` (drop-in) — **WARN-level gate, passed** |
| P4.3 front door `:4000` answers + `claude-*` → local | ✅ PASS | `claude-sonnet-4-6` → local workhorse, "Hello, I'm Qwen." (874 chars); zero cost header — no outbound cloud (structural) |

## Recorded numbers

- **litellm:** **1.91.2** (installed latest stable; validated baseline was 1.89.4 on GB10 2026-06-25).
  This run is the new validated baseline — no pin edit (float-with-baseline, CONVENTIONS §3).
- **CPUAffinity:** litellm `0-3` / llama-swap `4-19` (disjoint, 20-core GB10).
- **Routing proof:** `POST :4000/v1/chat/completions {model:"claude-sonnet-4-6"}` → local workhorse (Qwen3.6-35B-A3B);
  `x-litellm-response-cost-original: 0.0` (local, DB-less spend header present).
- **Front-door model list (`:4000/v1/models`):** `chat`, `claude-*`, `coach`, `embed`, `gpt-oss-120b`, `workhorse`.
- **Memory after the affinity restart re-preload:** 77 GB total unified (< 115 GB ceiling); fleet all `ready`.

## Drift report

[`DRIFT-litellm-front-door-2026-07-11.md`](./DRIFT-litellm-front-door-2026-07-11.md). Promoted: nothing — the
1.89.4→1.91.2 float is expected and the gates prove 1.91.2 works; 1.91.2 recorded here as the new validated
baseline (no PINS edit).

## Notes on the one coupling (self-healing)

The `CPUAffinity=4-19` drop-in was applied to llama-swap and picked up via a **restart** — a deliberate cold
reload of the ~65 GB preload (all four models re-loaded to `ready` in ~1–2 min). A future base re-run that
drops the affinity is healed by re-running this overlay (the drop-in heredoc is overwrite-safe).

## Failures & follow-ups

- None for the overlay itself — all gates green on first pass.
- The base bring-up surfaced runbook/script drift (stale llama-swap tarball URL, stage-script gpt-oss-20b
  source/glob, personal-lineup keepalive) — captured in
  [`RESULTS-single-spark-bring-up-2026-07-11.md`](./RESULTS-single-spark-bring-up-2026-07-11.md) as PR candidates.

## Endpoint

`LiteLLM :4000` is the clients' front door (OpenAI + Anthropic compatible, `claude-*` wildcard → local
workhorse, per-request cost header, no cloud fallback). `llama-swap :9000` remains a documented direct-port
fallback (DF-001 §3.3). Manage with `systemctl --user … litellm`; linger enabled.
