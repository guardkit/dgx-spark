# RESULTS — LiteLLM Front Door (2026-08-04)

**Mode:** fresh add of the overlay on `promaxgb10-41b1`, executed immediately after the base runbook's first green walkthrough ([`RESULTS-single-spark-bring-up-2026-08-04.md`](./RESULTS-single-spark-bring-up-2026-08-04.md)). Executed end-to-end by an agent (Claude Code / Fable 5). **First green walkthrough of the overlay — litellm 1.95.0 is the new validated baseline.**
**Wall-clock:** ~6 min (install ~40 s incl. upgrade deps; fleet bounce to pick up the affinity drop-in re-preloaded in ~20 s, page-cache warm).

## Gate outcomes (Phase 5 table, filled)

| Gate | Result | Note |
|---|---|---|
| P0 Drift report emitted + reviewed | **PASS** | committed `DRIFT-litellm-front-door-2026-08-04.md` (d751383) — expected float 1.89.4→1.95.0; 1 cross-runbook flag |
| P1 base fleet green on `:9000` | **PASS (on intent)** | verbatim gate FAILs on the `chat` alias retired from the base 2026-08-01 — stale spec, see F1; re-assert against the base's current contract (workhorse/coach/embed + user unit) passes |
| P4.1 no-cloud fallback (both lists empty + no cloud target) | **PASS ×2** | DF-001 — the deliberately-disabled community feature, now machine-refused |
| P4.2 CPUAffinity disjoint | **PASS** | litellm `0-3` · llama-swap `4-19` (drop-in applied; WARN-level gate, passed outright) |
| P4.3 front door answers + `claude-*` → local | **PASS** | `:4000/v1/models` lists the fleet + `claude-*`; `claude-sonnet-4-6` served by the local workhorse, 432 chars generated (in `reasoning_content` — accepted by the gate's design) |

## Recorded numbers

- **litellm 1.95.0** — the new validated baseline (previous: 1.89.4, 2026-06-25). Float-with-baseline per CONVENTIONS §3; no pin edit.
- The literal **`claude-*` wildcard resolves in 1.95.0** — the config's F5 explicit-rows fallback was not needed.
- Stack now live: `client → LiteLLM :4000 → llama-swap :9000 (v245) → llama.cpp b9430` — the full community-stack superset (DF-005).

## Drift report

[`DRIFT-litellm-front-door-2026-08-04.md`](./DRIFT-litellm-front-door-2026-08-04.md) (committed d751383). Nothing promoted — float drift is by design; this run's gates proved 1.95.0.

## Failures & follow-ups (non-blocking; bundle into the same amendments PR as the base's F1–F3)

- **F1 — Phase 1 gate + topology diagram still expect `chat`:** retired from the base lineup 2026-08-01; the precondition gate as written FAILs against a *correct* base. PR: drop `chat` from the Phase 1 loop and the diagram line. (`examples/litellm-config.public.yaml` is already correct.)
- **F2 — Phase 2's `pip install` lacks `-U`:** with litellm already on the box, the command as written reports "already satisfied" and does **not** pull latest — contradicting the phase's own "re-running pulls the latest" and CONVENTIONS §3 float semantics. Verified: plain install left 1.89.4; `-U` landed 1.95.0. PR: add `-U` (or `--upgrade`) to the Phase 2 command.
- Base Phase 8 act-two checkbox satisfied: `systemctl --user is-active litellm` → `active`.
